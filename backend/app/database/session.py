import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[2] / "idhtm_demo.sqlite3"


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialize() -> None:
    db = connection()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        scenario TEXT NOT NULL,
        health_score INTEGER NOT NULL,
        battery REAL NOT NULL,
        signal REAL NOT NULL,
        gps_fix INTEGER NOT NULL,
        vibration REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS maintenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        component TEXT NOT NULL,
        issue TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    db.commit()
    db.close()


def persist_telemetry(event: dict[str, Any], scenario: str) -> None:
    db = connection()
    db.execute(
        "INSERT INTO telemetry(timestamp, scenario, health_score, battery, signal, gps_fix, vibration) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            event["timestamp"],
            scenario,
            event["health_score"],
            event["battery_percentage"],
            event["signal_strength"],
            int(event["gps_fix"]),
            event["vibration"],
        ),
    )
    db.commit()
    db.close()
