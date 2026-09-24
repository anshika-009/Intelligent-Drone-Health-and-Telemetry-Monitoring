"""Postgres persistence for users, flights and their telemetry.

Tables
------
users             one row per Clerk user_id
flights           one row per flight session, owned by a user
flight_telemetry  one row per telemetry snapshot, linked to a flight
drone_home        each user's LAST KNOWN home for a drone (display only)

Connection string comes from DATABASE_URL (docker-compose already sets it).
"""

import os
import threading
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://idhtm:idhtm_dev@localhost:5432/idhtm",
)

# One shared connection guarded by a lock. Telemetry is written many times
# per second, so opening a new connection per snapshot would be too slow.
_conn: psycopg.Connection | None = None
_lock = threading.Lock()


def _get_conn() -> psycopg.Connection:
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)
    return _conn


def _run(sql: str, params: tuple = (), fetch: str | None = None):
    """Execute one statement, reconnecting once if the connection dropped."""
    global _conn
    with _lock:
        for attempt in (1, 2):
            try:
                with _get_conn().cursor() as cur:
                    cur.execute(sql, params)
                    if fetch == "one":
                        return cur.fetchone()
                    if fetch == "all":
                        return cur.fetchall()
                    return None
            except psycopg.OperationalError:
                _conn = None
                if attempt == 2:
                    raise


def _to_dt(value: Any) -> datetime:
    """Accept ISO strings, epoch numbers or datetimes; fall back to now()."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else value


def initialize() -> None:
    # Table 1: users (Clerk user id) - owns flights.
    _run("""
    CREATE TABLE IF NOT EXISTS users (
        user_id     TEXT PRIMARY KEY,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_seen   TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    # Table 2: flights (one row per flight session, owned by a user).
    _run("""
    CREATE TABLE IF NOT EXISTS flights (
        id          BIGSERIAL PRIMARY KEY,
        user_id     TEXT NOT NULL,
        drone_id    TEXT NOT NULL,
        scenario    TEXT NOT NULL,
        started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        ended_at    TIMESTAMPTZ
    )
    """)
    # Takeoff ("home") position, written once per flight and never changed.
    _run("ALTER TABLE flights ADD COLUMN IF NOT EXISTS home_latitude DOUBLE PRECISION")
    _run("ALTER TABLE flights ADD COLUMN IF NOT EXISTS home_longitude DOUBLE PRECISION")
    _run("ALTER TABLE flights ADD COLUMN IF NOT EXISTS home_altitude DOUBLE PRECISION")
    # Users that already own flights (created before the users table existed).
    _run("INSERT INTO users (user_id) SELECT DISTINCT user_id FROM flights ON CONFLICT DO NOTHING")
    _run("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'flights_user_fk') THEN
            ALTER TABLE flights ADD CONSTRAINT flights_user_fk
                FOREIGN KEY (user_id) REFERENCES users(user_id);
        END IF;
    END $$
    """)
    # Older version keyed drone_home by drone_id only (shared by all users).
    # It only holds values derived from GPS fixes, so drop it and let it be
    # re-recorded per user.
    _run("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'drone_home')
           AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = 'drone_home' AND column_name = 'user_id') THEN
            DROP TABLE drone_home;
        END IF;
    END $$
    """)
    # Table 3: drone_home. Each user's LAST KNOWN home for a drone, updated
    # when a new flight records its own first fix. Display only (GET
    # /api/home) - it never decides which flight is resumed.
    _run("""
    CREATE TABLE IF NOT EXISTS drone_home (
        user_id        TEXT NOT NULL REFERENCES users(user_id),
        drone_id       TEXT NOT NULL,
        latitude       DOUBLE PRECISION NOT NULL,
        longitude      DOUBLE PRECISION NOT NULL,
        altitude       DOUBLE PRECISION,
        set_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
        set_by_flight  BIGINT,
        PRIMARY KEY (user_id, drone_id)
    )
    """)
    _run("CREATE INDEX IF NOT EXISTS flights_user_idx ON flights (user_id, started_at DESC)")
    _run("""
    CREATE TABLE IF NOT EXISTS flight_telemetry (
        id                  BIGSERIAL PRIMARY KEY,
        flight_id           BIGINT NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
        timestamp           TIMESTAMPTZ NOT NULL,
        latitude            DOUBLE PRECISION,
        longitude           DOUBLE PRECISION,
        altitude            DOUBLE PRECISION,
        ground_speed        DOUBLE PRECISION,
        airspeed            DOUBLE PRECISION,
        vertical_speed      DOUBLE PRECISION,
        heading             DOUBLE PRECISION,
        flight_mode         TEXT,
        battery_percentage  DOUBLE PRECISION,
        battery_voltage     DOUBLE PRECISION,
        signal_strength     DOUBLE PRECISION,
        gps_fix             BOOLEAN,
        gps_satellites      INTEGER,
        vibration           DOUBLE PRECISION,
        temperature         DOUBLE PRECISION,
        health_score        INTEGER
    )
    """)
    _run("CREATE INDEX IF NOT EXISTS flight_telemetry_flight_idx ON flight_telemetry (flight_id, timestamp)")


# --------------------------------------------------------------------------
# Flights
# --------------------------------------------------------------------------

def start_flight(user_id: str, drone_id: str, scenario: str) -> int:
    row = _run(
        "INSERT INTO flights (user_id, drone_id, scenario) VALUES (%s, %s, %s) RETURNING id",
        (user_id, drone_id, scenario),
        fetch="one",
    )
    return row["id"]


def end_flight(flight_id: int) -> None:
    _run(
        "UPDATE flights SET ended_at = now() WHERE id = %s AND ended_at IS NULL",
        (flight_id,),
    )


def ensure_user(user_id: str) -> None:
    _run(
        """
        INSERT INTO users (user_id) VALUES (%s)
        ON CONFLICT (user_id) DO UPDATE SET last_seen = now()
        """,
        (user_id,),
    )


def resume_or_start_flight(user_id: str, drone_id: str, scenario: str) -> tuple[int, bool]:
    """Return (flight_id, resumed).

    Resume this user's most recent flight for this drone only if the gap
    since it stopped is short enough to be a genuine interruption (a page
    refresh, a brief MAVLink drop) - not "the drone happened to take off
    from the same place again". Anything older always starts a brand new
    flight, so two unrelated sessions never get silently merged into one
    flight row just because they share a home position."""
    ensure_user(user_id)
    RESUME_WINDOW_SECONDS = 120
    row = _run(
        """
        SELECT id FROM flights
        WHERE user_id = %s AND drone_id = %s
          AND (ended_at IS NULL OR ended_at > now() - (%s * interval '1 second'))
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (user_id, drone_id, RESUME_WINDOW_SECONDS),
        fetch="one",
    )
    if row:
        _run("UPDATE flights SET ended_at = NULL WHERE id = %s", (row["id"],))
        return row["id"], True
    return start_flight(user_id, drone_id, scenario), False


def close_open_flights() -> None:
    """Mark flights left open by a previous backend run as ended."""
    _run("UPDATE flights SET ended_at = now() WHERE ended_at IS NULL")


def set_flight_home(flight_id: int, latitude: float, longitude: float, altitude: float | None) -> bool:
    """Record the takeoff position. Write-once: only succeeds while the
    flight has no home yet, so it can never be overwritten. Returns True
    if this call set it."""
    row = _run(
        """
        UPDATE flights
        SET home_latitude = %s, home_longitude = %s, home_altitude = %s
        WHERE id = %s AND home_latitude IS NULL
        RETURNING id
        """,
        (latitude, longitude, altitude, flight_id),
        fetch="one",
    )
    return row is not None


def get_drone_home(user_id: str, drone_id: str) -> dict | None:
    row = _run(
        "SELECT latitude, longitude, altitude, set_at FROM drone_home WHERE user_id = %s AND drone_id = %s",
        (user_id, drone_id),
        fetch="one",
    )
    if not row:
        return None
    return {
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "altitude": row["altitude"],
        "set_at": _iso(row["set_at"]),
    }


def record_flight_home(flight_id: int, latitude: float, longitude: float, altitude: float | None) -> dict | None:
    """Give this flight its own home position, from its own first GPS fix.

    If the flight ALREADY has a home (for example it was resumed after a
    pause, so the caller is passing a mid-flight position), nothing is
    changed and the existing home is returned. Only when this call really
    sets the flight's home is the user's "last known home" refreshed."""
    flight = _run("SELECT user_id, drone_id FROM flights WHERE id = %s", (flight_id,), fetch="one")
    if not flight:
        return None
    user_id, drone_id = flight["user_id"], flight["drone_id"]

    if not set_flight_home(flight_id, latitude, longitude, altitude):
        row = _run(
            "SELECT home_latitude, home_longitude, home_altitude FROM flights WHERE id = %s",
            (flight_id,),
            fetch="one",
        )
        return {
            "latitude": row["home_latitude"],
            "longitude": row["home_longitude"],
            "altitude": row["home_altitude"],
        }

    _run(
        """
        INSERT INTO drone_home (user_id, drone_id, latitude, longitude, altitude, set_by_flight)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, drone_id) DO UPDATE
        SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude,
            altitude = EXCLUDED.altitude, set_at = now(), set_by_flight = EXCLUDED.set_by_flight
        """,
        (user_id, drone_id, latitude, longitude, altitude, flight_id),
    )
    return {"latitude": latitude, "longitude": longitude, "altitude": altitude}


def reset_drone_home(user_id: str, drone_id: str) -> None:
    """Forget this user's home for the drone (e.g. they moved to a new
    takeoff site). Their open flights lose the copy too, so they re-record
    from the next fix."""
    _run("DELETE FROM drone_home WHERE user_id = %s AND drone_id = %s", (user_id, drone_id))
    _run(
        """
        UPDATE flights SET home_latitude = NULL, home_longitude = NULL, home_altitude = NULL
        WHERE user_id = %s AND drone_id = %s AND ended_at IS NULL
        """,
        (user_id, drone_id),
    )


def get_flight_home(flight_id: int) -> dict | None:
    """The flight's OWN home, or None until its first GPS fix is recorded.

    There is deliberately no fallback to the user's last-known home: that
    would show the previous flight's location (possibly a different city)
    on the map until the new flight's own home arrives, then jump."""
    row = _run(
        "SELECT started_at, home_latitude, home_longitude, home_altitude FROM flights WHERE id = %s",
        (flight_id,),
        fetch="one",
    )
    if not row:
        return None
    home = None
    if row["home_latitude"] is not None and row["home_longitude"] is not None:
        home = {
            "latitude": row["home_latitude"],
            "longitude": row["home_longitude"],
            "altitude": row["home_altitude"],
        }
    return {"started_at": _iso(row["started_at"]), "home": home}


def persist_telemetry(flight_id: int, event: dict[str, Any]) -> None:
    _run(
        """
        INSERT INTO flight_telemetry (
            flight_id, timestamp, latitude, longitude, altitude, ground_speed,
            airspeed, vertical_speed, heading, flight_mode, battery_percentage,
            battery_voltage, signal_strength, gps_fix, gps_satellites,
            vibration, temperature, health_score
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            flight_id,
            _to_dt(event.get("timestamp")),
            event.get("latitude"),
            event.get("longitude"),
            event.get("altitude"),
            event.get("ground_speed"),
            event.get("airspeed"),
            event.get("vertical_speed"),
            event.get("heading"),
            event.get("flight_mode"),
            event.get("battery_percentage"),
            event.get("battery_voltage"),
            event.get("signal_strength"),
            None if event.get("gps_fix") is None else bool(event.get("gps_fix")),
            event.get("gps_satellites"),
            event.get("vibration"),
            event.get("temperature"),
            event.get("health_score"),
        ),
    )


def list_flights(user_id: str) -> list[dict]:
    rows = _run(
        """
        SELECT f.id, f.drone_id, f.scenario, f.started_at, f.ended_at,
               f.home_latitude, f.home_longitude, f.home_altitude,
               COUNT(t.id)                 AS samples,
               ROUND(AVG(t.health_score))  AS avg_health
        FROM flights f
        LEFT JOIN flight_telemetry t ON t.flight_id = f.id
        WHERE f.user_id = %s
        GROUP BY f.id
        ORDER BY f.started_at DESC
        """,
        (user_id,),
        fetch="all",
    )
    return [
        {
            **r,
            "started_at": _iso(r["started_at"]),
            "ended_at": _iso(r["ended_at"]),
            "avg_health": int(r["avg_health"]) if r["avg_health"] is not None else None,
        }
        for r in rows
    ]


def get_flight(flight_id: int, user_id: str) -> dict | None:
    """Return one flight with all its telemetry, or None if it isn't this user's."""
    flight = _run(
        "SELECT id, drone_id, scenario, started_at, ended_at, home_latitude, home_longitude, home_altitude FROM flights WHERE id = %s AND user_id = %s",
        (flight_id, user_id),
        fetch="one",
    )
    if not flight:
        return None
    samples = _run(
        """
        SELECT timestamp, latitude, longitude, altitude, ground_speed, airspeed,
               vertical_speed, heading, flight_mode, battery_percentage,
               battery_voltage, signal_strength, gps_fix, gps_satellites,
               vibration, temperature, health_score
        FROM flight_telemetry WHERE flight_id = %s ORDER BY timestamp
        """,
        (flight_id,),
        fetch="all",
    )
    for s in samples:
        s["timestamp"] = _iso(s["timestamp"])
    return {
        **flight,
        "started_at": _iso(flight["started_at"]),
        "ended_at": _iso(flight["ended_at"]),
        "telemetry": samples,
    }