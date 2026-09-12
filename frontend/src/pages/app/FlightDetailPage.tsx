import { Play } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import {
  Chart,
  Eyebrow,
  Metric,
  SectionHeading,
  StatusPill,
} from "../../components/common";
import { chartSeries } from "../../data/mock";
import { useApp } from "../../store/AppStore";
import { MapScene } from "./shared/MapScene";

export function FlightDetailPage() {
  const { flightId } = useParams();
  const { telemetry } = useApp();
  return (
    <div className="page">
      <div className="back-link">
        <Link to="/app/flights">← Flight history</Link>
      </div>
      <SectionHeading
        eyebrow="FLIGHT DETAIL"
        title={flightId || "Flight session"}
        copy="All telemetry, events, alerts, and health changes below belong to the same flight session."
        action={
          <Link className="button" to={`/app/flights/${flightId}/replay`}>
            {" "}
            <Play size={15} /> Replay flight
          </Link>
        }
      />
      <div className="flight-detail-grid">
        <div className="panel route-card">
          <div className="panel-head">
            <div>
              <Eyebrow>ROUTE / 18m 42s</Eyebrow>
              <h3>Industrial perimeter scan</h3>
            </div>
            <StatusPill label="Completed" tone="green" />
          </div>
          <MapScene variant="detail" location={telemetry} />
        </div>
        <div className="panel event-card">
          <div className="panel-head">
            <div>
              <Eyebrow>EVENT TIMELINE</Eyebrow>
              <h3>What changed</h3>
            </div>
          </div>
          <div className="event-list">
            {[
              "Takeoff · AUTO mode engaged",
              "Signal fluctuation · 14:46:22",
              "Health engine recalculated · 14:48:10",
              "Landing · mission completed",
            ].map((e, i) => (
              <div className="event-item" key={e}>
                <span>{String(i + 1).padStart(2, "0")}</span>
                <strong>{e}</strong>
                <small>
                  {["14:32:18", "14:46:22", "14:48:10", "14:50:59"][i]}
                </small>
              </div>
            ))}
          </div>
        </div>
        <div className="panel flight-telemetry">
          <div className="panel-head">
            <div>
              <Eyebrow>SESSION TELEMETRY</Eyebrow>
              <h3>Signal and health</h3>
            </div>
          </div>
          <Chart points={chartSeries.map((s) => s.health)} labels />
          <div className="metric-row">
            <Metric label="Avg. health" value="92" unit="/100" />
            <Metric label="Min. signal" value="76" unit="%" />
            <Metric label="Max. altitude" value="162" unit="m" />
            <Metric label="Alerts" value="2" />
          </div>
        </div>
      </div>
    </div>
  );
}
