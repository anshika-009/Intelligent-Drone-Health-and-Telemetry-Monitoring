import { useEffect, useMemo, useState } from "react";
import { Play } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "@clerk/react";
import {
  Chart,
  EmptyState,
  Eyebrow,
  Metric,
  SectionHeading,
  StatusPill,
} from "../../components/common";
import { flightsService } from "../../services/api";
import { MapScene } from "./shared/MapScene";
import type { MapLocation, RoutePoint } from "./shared/MapScene";

/* ------------------------------------------------------------------ */
/* Types + helpers                                                     */
/* ------------------------------------------------------------------ */

// One stored telemetry row. Every field is optional because the DB row
// only contains the columns that were persisted for that flight.
type Sample = {
  timestamp?: string;
  health_score?: number | null;
  battery?: number | null;
  battery_percentage?: number | null;
  signal?: number | null;
  signal_strength?: number | null;
  vibration?: number | null;
  gps_fix?: boolean | number | null;
  latitude?: number | null;
  longitude?: number | null;
  altitude?: number | null;
  ground_speed?: number | null;
};

type FlightRecord = {
  id: number | string;
  drone_id?: string | null;
  scenario?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  telemetry?: Sample[];
};

const isNum = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v);

const pick = (s: Sample, ...keys: (keyof Sample)[]): number | null => {
  for (const k of keys) {
    const v = s[k];
    if (isNum(v)) return v;
  }
  return null;
};

const series = (samples: Sample[], ...keys: (keyof Sample)[]): number[] =>
  samples.map((s) => pick(s, ...keys)).filter(isNum);

const avg = (xs: number[]) =>
  xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;

const fmt = (v: number | null, digits = 0) =>
  v === null ? "—" : v.toFixed(digits);

function formatDuration(ms: number): string {
  if (!isNum(ms) || ms < 0) return "—";
  const total = Math.round(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h ? `${h}h ${m}m ${s}s` : `${m}m ${s}s`;
}

function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export function FlightDetailPage() {
  const { flightId } = useParams();
  const { getToken } = useAuth();

  const [flight, setFlight] = useState<FlightRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!flightId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const token = await getToken();
        const data = (await flightsService.get(token, flightId)) as FlightRecord;
        if (!cancelled) setFlight(data);
      } catch {
        if (!cancelled) {
          setFlight(null);
          setError("This flight session could not be loaded.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
    // getToken identity can change between renders; the flight id is what matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flightId]);

  const samples = useMemo<Sample[]>(() => flight?.telemetry ?? [], [flight]);

  const stats = useMemo(() => {
    const health = series(samples, "health_score");
    const signal = series(samples, "signal", "signal_strength");
    const battery = series(samples, "battery", "battery_percentage");
    const altitude = series(samples, "altitude");
    const speed = series(samples, "ground_speed");

    const startMs = flight?.started_at ? Date.parse(flight.started_at) : NaN;
    const lastTs = samples.length
      ? Date.parse(samples[samples.length - 1].timestamp ?? "")
      : NaN;
    const endMs = flight?.ended_at ? Date.parse(flight.ended_at) : lastTs;

    return {
      health,
      avgHealth: avg(health),
      minSignal: signal.length ? Math.min(...signal) : null,
      maxAltitude: altitude.length ? Math.max(...altitude) : null,
      avgSpeed: avg(speed),
      batteryStart: battery.length ? battery[0] : null,
      batteryEnd: battery.length ? battery[battery.length - 1] : null,
      durationMs: endMs - startMs,
      // Sample-based fallback if timestamps on the flight row are missing.
      durationLabel: formatDuration(endMs - startMs),
    };
  }, [samples, flight]);

  // Route + last known position, only when lat/lon were actually stored.
  const { route, location } = useMemo(() => {
    const pts = samples.filter(
      (s) => isNum(s.latitude) && isNum(s.longitude),
    );
    const r: RoutePoint[] = pts.map((s) => [
      s.latitude as number,
      s.longitude as number,
    ]);
    const last = pts[pts.length - 1];
    const loc: MapLocation | undefined = last
      ? {
          latitude: last.latitude as number,
          longitude: last.longitude as number,
          altitude: last.altitude ?? 0,
          heading: 0,
          timestamp: last.timestamp ?? "",
        }
      : undefined;
    return { route: r, location: loc };
  }, [samples]);

  const isOpen = !!flight && !flight.ended_at;

  /* ---------- loading / error / empty states ---------- */

  if (loading) {
    return (
      <div className="page">
        <div className="back-link">
          <Link to="/app/flights">← Flight history</Link>
        </div>
        <EmptyState title="Loading flight" copy="Fetching this session's telemetry…" />
      </div>
    );
  }

  if (error || !flight) {
    return (
      <div className="page">
        <div className="back-link">
          <Link to="/app/flights">← Flight history</Link>
        </div>
        <EmptyState
          title="Flight not found"
          copy={error ?? "This flight does not exist or belongs to another account."}
          action={
            <Link className="button" to="/app/flights">
              Back to flight history
            </Link>
          }
        />
      </div>
    );
  }

  /* ---------- main view ---------- */

  return (
    <div className="page">
      <div className="back-link">
        <Link to="/app/flights">← Flight history</Link>
      </div>
      <SectionHeading
        eyebrow="FLIGHT DETAIL"
        title={`Flight #${flight.id}`}
        copy="All telemetry below was recorded during this flight session."
        action={
          <Link className="button" to={`/app/flights/${flight.id}/replay`}>
            {" "}
            <Play size={15} /> Replay flight
          </Link>
        }
      />
      <div className="flight-detail-grid">
        <div className="panel route-card">
          <div className="panel-head">
            <div>
              <Eyebrow>ROUTE / {stats.durationLabel}</Eyebrow>
              <h3>{flight.drone_id ?? "Drone"} · {flight.scenario ?? "flight"}</h3>
            </div>
            <StatusPill
              label={isOpen ? "In progress" : "Completed"}
              tone={isOpen ? "amber" : "green"}
            />
          </div>
          {location ? (
            <MapScene variant="detail" location={location} route={route} />
          ) : (
            <EmptyState
              title="No route recorded"
              copy="GPS coordinates were not stored for this flight."
            />
          )}
        </div>

        <div className="panel event-card">
          <div className="panel-head">
            <div>
              <Eyebrow>SESSION SUMMARY</Eyebrow>
              <h3>Flight facts</h3>
            </div>
          </div>
          <div className="event-list">
            {[
              ["Started", formatDate(flight.started_at)],
              ["Ended", flight.ended_at ? formatDate(flight.ended_at) : "Still active"],
              ["Duration", stats.durationLabel],
              ["Samples recorded", String(samples.length)],
            ].map(([label, value], i) => (
              <div className="event-item" key={label}>
                <span>{String(i + 1).padStart(2, "0")}</span>
                <strong>{label}</strong>
                <small>{value}</small>
              </div>
            ))}
          </div>
        </div>

        <div className="panel flight-telemetry">
          <div className="panel-head">
            <div>
              <Eyebrow>SESSION TELEMETRY</Eyebrow>
              <h3>Health over time</h3>
            </div>
          </div>
          {stats.health.length >= 2 ? (
            <Chart points={stats.health} labels />
          ) : (
            <EmptyState
              title="Not enough data"
              copy="At least two telemetry samples are needed to draw a chart."
            />
          )}
          <div className="metric-row">
            <Metric label="Avg. health" value={fmt(stats.avgHealth)} unit="/100" />
            <Metric label="Min. signal" value={fmt(stats.minSignal)} unit="%" />
            <Metric label="Max. altitude" value={fmt(stats.maxAltitude)} unit="m" />
            <Metric label="Avg. speed" value={fmt(stats.avgSpeed, 1)} unit="m/s" />
            <Metric
              label="Battery"
              value={`${fmt(stats.batteryStart)} → ${fmt(stats.batteryEnd)}`}
              unit="%"
            />
          </div>
        </div>
      </div>
    </div>
  );
}