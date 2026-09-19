import { useEffect, useState } from "react";
import { ChevronRight, Download, Search, SlidersHorizontal } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "@clerk/react";
import { SectionHeading } from "../../components/common";
import { flightsService } from "../../services/api";

type FlightRow = {
  id: number;
  drone_id: string;
  scenario: string;
  started_at: string;
  ended_at: string | null;
  home_latitude: number | null;
  home_longitude: number | null;
  samples: number;
  avg_health: number | null;
};

function formatDuration(startedAt: string, endedAt: string | null): string {
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  const totalSeconds = Math.max(0, Math.round((end - start) / 1000));
  return `${Math.floor(totalSeconds / 60)}m ${totalSeconds % 60}s`;
}

export function FlightsPage() {
  const { getToken } = useAuth();
  const [flights, setFlights] = useState<FlightRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getToken();
        const rows = (await flightsService.list(token)) as FlightRow[];
        if (!cancelled) setFlights(rows);
      } catch {
        if (!cancelled) setError("Could not load your flights.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [getToken]);

  return (
    <div className="page">
      <SectionHeading
        eyebrow="FLIGHT OPERATIONS"
        title="Flight history"
        copy="Every flight you've started, with the telemetry recorded during it."
        action={
          <button
            className="button ghost"
            disabled={flights.length === 0}
            onClick={() => {
              const rows = flights.map(
                (f) =>
                  `${f.id},${f.started_at},${formatDuration(f.started_at, f.ended_at)},${f.samples},${f.avg_health ?? ""}`,
              );
              const blob = new Blob(
                [`flight_id,started_at,duration,samples,avg_health\n${rows.join("\n")}`],
                { type: "text/csv" },
              );
              const link = document.createElement("a");
              link.href = URL.createObjectURL(blob);
              link.download = "idhtm-flight-log.csv";
              link.click();
              URL.revokeObjectURL(link.href);
            }}
          >
            <Download size={15} /> Export log
          </button>
        }
      />
      <div className="table-toolbar">
        <div className="search-input">
          <Search size={15} />
          <input placeholder="Search flights" />
        </div>
        <button className="icon-button">
          <SlidersHorizontal size={17} />
        </button>
      </div>

      {loading && <p className="empty-state">Loading your flights…</p>}
      {error && <p className="empty-state">{error}</p>}
      {!loading && !error && flights.length === 0 && (
        <p className="empty-state">
          No flights recorded yet. Start the feed from the dashboard to begin one.
        </p>
      )}

      {!loading && !error && flights.length > 0 && (
        <div className="data-table">
          <div className="table-head">
            <span>Flight ID</span>
            <span>Started</span>
            <span>Duration</span>
            <span>Status</span>
            <span>Avg. health</span>
            <span>Samples</span>
            <span />
          </div>
          {flights.map((f) => (
            <Link className="table-row" to={`/app/flights/${f.id}`} key={f.id}>
              <strong>#{f.id}</strong>
              <span>{new Date(f.started_at).toLocaleString()}</span>
              <span>{formatDuration(f.started_at, f.ended_at)}</span>
              <span className={f.ended_at ? "text-green" : "text-amber"}>
                {f.ended_at ? "Completed" : "In progress"}
              </span>
              <span className={f.avg_health != null && f.avg_health > 90 ? "text-green" : "text-amber"}>
                {f.avg_health != null ? `${f.avg_health} / 100` : "—"}
              </span>
              <span>{f.samples}</span>
              <ChevronRight size={16} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}