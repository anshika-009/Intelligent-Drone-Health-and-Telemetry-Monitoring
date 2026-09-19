import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronRight,
  MapPin,
  Pause,
  Play,
  SlidersHorizontal,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  AlertRow,
  Chart,
  Eyebrow,
  Metric,
  ScoreBar,
  Sparkline,
  StatusPill,
} from "../../components/common";
import { chartSeries, components, scenarioLabels } from "../../data/mock";
import { useApp } from "../../store/AppStore";
import type { Scenario, Telemetry } from "../../types";
import { MapScene } from "./shared/MapScene";
import { ScenarioPicker } from "./shared/ScenarioPicker";

export function DashboardPage() {
  const {
    telemetry,
    alerts,
    scenario,
    setScenario,
    simulatorActive,
    setSimulatorActive,
    acknowledgeAlert,
    isConnected,
    startTelemetryFeed,
    stopTelemetryFeed,
    homePosition,
  } = useApp();
  const [showScenario, setShowScenario] = useState(false);

  // The backend only connects to the drone while a flight is open, so
  // opening the dashboard (with the feed running) must start one, and
  // leaving it must end it. Without this the backend stays idle and
  // /api/telemetry/latest returns 503.
  // Keep the map on the last REAL position while the feed is paused (or
  // the link drops). Passing `undefined` there makes the map fall back to
  // its default centre (San Francisco) and pan away from the flight.
  const lastLiveTelemetry = useRef<Telemetry | undefined>(undefined);
  if (isConnected) lastLiveTelemetry.current = telemetry;
  const mapLocation = isConnected ? telemetry : lastLiveTelemetry.current;

  const feedRunning = useRef(simulatorActive);
  feedRunning.current = simulatorActive;
  useEffect(() => {
    if (feedRunning.current) startTelemetryFeed();
    return () => {
      if (feedRunning.current) stopTelemetryFeed();
    };
    // Mount/unmount only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const points = chartSeries.map(
    (_, i) => telemetry.altitude + Math.sin(i) * 8,
  );
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <Eyebrow>LIVE MONITOR / DRONE-01</Eyebrow>
          <h1>Flight overview</h1>
          <p className="page-subtitle">
            A live operational picture with the reasoning layer kept close to
            the signal.
          </p>
        </div>
        <div className="head-actions">
          <button
            className="button ghost"
            onClick={() => setShowScenario(!showScenario)}
          >
            <SlidersHorizontal size={15} /> {scenarioLabels[scenario]}
          </button>
          <button
            className={`button ${simulatorActive ? "secondary" : ""}`}
            onClick={() => setSimulatorActive(!simulatorActive)}
          >
            {simulatorActive ? <Pause size={15} /> : <Play size={15} />}{" "}
            {simulatorActive ? "Pause feed" : "Start feed"}
          </button>
        </div>
      </div>
      {showScenario && (
        <ScenarioPicker value={scenario} onChange={setScenario} />
      )}
      <div className="status-strip">
        <span>
          <span className="live-dot" />{" "}
          {simulatorActive ? "SIMULATOR ACTIVE" : "TELEMETRY PAUSED"}
        </span>
        <span>Source: telemetry + live location stream</span>
        <span>
          Last packet{" "}
          {new Date(telemetry.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </span>
        <span>
          Flight mode <strong>{telemetry.flight_mode}</strong>
        </span>
      </div>
      <div className="dashboard-grid">
        <section
          className="health-card panel"
          style={
            {
              "--health-image":
                "url('/assets/images/drones/drone-industrial.webp')",
            } as React.CSSProperties
          }
        >
          <div className="panel-head">
            <div>
              <Eyebrow>PRIMARY SIGNAL</Eyebrow>
              <h3>Aircraft health</h3>
            </div>
            <StatusPill
              label={
                telemetry.health_score > 85
                  ? "Operational"
                  : telemetry.health_score > 65
                    ? "Watch"
                    : "Action required"
              }
              tone={
                telemetry.health_score > 85
                  ? "green"
                  : telemetry.health_score > 65
                    ? "amber"
                    : "red"
              }
            />
          </div>
          <div className="health-score">
            <div
              className="score-ring"
              style={
                {
                  "--score": `${telemetry.health_score * 3.6}deg`,
                } as React.CSSProperties
              }
            >
              <div className="score-ring-content">
                <strong>{telemetry.health_score}</strong>
                <span>/ 100</span>
              </div>
            </div>
            <div className="health-explain">
              <strong>
                {telemetry.health_score > 85
                  ? "Within expected envelope"
                  : "Flight condition changing"}
              </strong>
              <p>
                Rule engine is watching{" "}
                {alerts.filter((a) => !a.acknowledged).length || 1} active
                signal
                {alerts.filter((a) => !a.acknowledged).length === 1 ? "" : "s"}{" "}
                across 5 systems.
              </p>
              <Link to="/app/health" className="inline-link">
                Inspect health model <ArrowRight size={14} />
              </Link>
            </div>
          </div>
          <div className="health-components">
            {components.slice(0, 4).map((c) => (
              <div key={c.key}>
                <span>{c.name}</span>
                <strong>
                  {c.key === "motors"
                    ? Math.max(45, Math.round(telemetry.health_score - 12))
                    : c.health}
                </strong>
                <Sparkline
                  points={Array.from(
                    { length: 8 },
                    (_, i) => c.health + Math.sin(i) * 2,
                  )}
                />
              </div>
            ))}
          </div>
        </section>
        <section className="decision-panel panel">
          <div className="panel-head">
            <div>
              <Eyebrow>NEXT BEST ACTION</Eyebrow>
              <h3>Prepare the aircraft</h3>
            </div>
            <span className="decision-mark">
              <Check size={15} />
            </span>
          </div>
          <div className="decision-action">
            <div>
              <strong>Inspect Motor 2 before the next extended flight.</strong>
              <p>
                Vibration is trending upward while the rest of the airframe
                remains inside its expected envelope.
              </p>
            </div>
            <Link className="inline-link" to="/app/maintenance">
              Open maintenance <ArrowRight size={14} />
            </Link>
          </div>
          <div className="decision-footer">
            <span>Evidence linked</span>
            <span>Rule MOT-VIB-02</span>
            <span>Priority medium</span>
          </div>
        </section>
        <section className="map-card panel">
          <div className="panel-head">
            <div>
              <Eyebrow>POSITION / LIVE</Eyebrow>
              <h3>Mission area</h3>
            </div>
            <span className="map-coords">
              <MapPin size={14} /> {telemetry.latitude.toFixed(4)}° N,{" "}
              {Math.abs(telemetry.longitude).toFixed(4)}° W
            </span>
          </div>
                    <MapScene
            location={mapLocation}
            home={homePosition}
            offline={!isConnected}
            offlineMessage={simulatorActive ? 'Simulator offline' : 'Telemetry paused'}
          />
        </section>
        <section className="flight-status panel">
          <div className="panel-head">
            <div>
              <Eyebrow>FLIGHT STATUS</Eyebrow>
              <h3>Survey / active</h3>
            </div>
            <StatusPill label="In progress" tone="blue" />
          </div>
          <div className="flight-status-stats">
            <Metric label="Elapsed" value="18:42" />
            <Metric
              label="Remaining"
              value={telemetry.estimated_remaining_flight_time}
              unit="min"
            />
            <Metric label="Mode" value={telemetry.flight_mode} />
          </div>
          <div className="flight-progress">
            <div style={{ width: "68%" }} />
            <span>Takeoff 14:32</span>
            <span>Estimated landing 14:59</span>
          </div>
          <div className="flight-footer">
            <span>Mission: industrial perimeter scan</span>
            <Link to="/app/flights/FLT-2026-0821-07">
              Open flight <ChevronRight size={14} />
            </Link>
          </div>
        </section>
        <section className="telemetry-panel panel">
          <div className="panel-head">
            <div>
              <Eyebrow>TELEMETRY / 24H</Eyebrow>
              <h3>Altitude and speed</h3>
            </div>
            <div className="chart-legend">
              <span>
                <i className="blue" /> Altitude
              </span>
              <span>
                <i className="gray" /> Baseline
              </span>
            </div>
          </div>
          <div className="chart-large">
            <Chart type="area" points={points} labels />
          </div>
          <div className="metric-row">
            <Metric
              label="Altitude"
              value={telemetry.altitude.toFixed(0)}
              unit="m"
              note="+4.2%"
              tone="healthy"
            />
            <Metric
              label="Ground speed"
              value={telemetry.ground_speed.toFixed(0)}
              unit="m/s"
            />
            <Metric
              label="Vertical speed"
              value={telemetry.vertical_speed.toFixed(1)}
              unit="m/s"
            />
            <Metric
              label="Temperature"
              value={telemetry.temperature.toFixed(0)}
              unit="°C"
            />
          </div>
        </section>
        <section className="alert-panel panel">
          <div className="panel-head">
            <div>
              <Eyebrow>RULE ENGINE / ACTIVE</Eyebrow>
              <h3>Signals requiring attention</h3>
            </div>
            <Link className="inline-link" to="/app/alerts">
              View all <ArrowRight size={14} />
            </Link>
          </div>
          {alerts.slice(0, 2).map((a) => (
            <AlertRow
              key={a.id}
              {...a}
              onAcknowledge={() => acknowledgeAlert(a.id)}
            />
          ))}
        </section>
      </div>
    </div>
  );
}