import { useState } from "react";
import { ChevronRight, Wrench } from "lucide-react";
import { Link } from "react-router-dom";
import {
  Chart,
  Eyebrow,
  Metric,
  ScoreBar,
  SectionHeading,
  StatusPill,
} from "../../components/common";
import { chartSeries, components } from "../../data/mock";
import { useApp } from "../../store/AppStore";

export function HealthPage() {
  const { telemetry } = useApp();
  const [selected, setSelected] = useState(components[1]);
  //for maintenance
  const currentHealth =
    selected.key === "motors"
      ? Math.max(45, Math.round(telemetry.health_score - 12))
      : selected.health;

  const severityLevel: 'Low' | 'Medium' | 'High' | 'Critical' =
    currentHealth > 90
      ? 'Low'
      : currentHealth > 75
        ? 'Medium'
        : currentHealth > 50
          ? 'High'
          : 'Critical';
  return (
    <div className="page">
      <SectionHeading
        eyebrow="COMPONENT INTELLIGENCE"
        title="Health monitoring"
        copy="A component-by-component view of what the rule engine currently understands."
      />
      <div className="health-layout">
        <div className="component-list">
          {components.map((c) => (
            <button
              key={c.key}
              className={`component-card ${selected.key === c.key ? "selected" : ""}`}
              onClick={() => setSelected(c)}
            >
              <img src={c.image} alt="" />
              <div>
                <span>{c.name}</span>
                <strong>
                  {c.key === "motors"
                    ? Math.max(45, Math.round(telemetry.health_score - 12))
                    : c.health}
                  <small>/ 100</small>
                </strong>
                <ScoreBar
                  score={
                    c.key === "motors"
                      ? Math.max(45, Math.round(telemetry.health_score - 12))
                      : c.health
                  }
                  tone={
                    c.health > 90 ? "green" : c.health > 75 ? "amber" : "red"
                  }
                />
                <StatusPill
                  label={c.state}
                  tone={
                    c.health > 90 ? "green" : c.health > 75 ? "amber" : "red"
                  }
                />
              </div>
              <ChevronRight size={16} />
            </button>
          ))}
        </div>
        <div
          className="component-detail panel"
          style={
            {
              "--component-image": `url(${selected.image})`,
            } as React.CSSProperties
          }
        >
          <div className="component-detail-image">
            <img src={selected.image} alt={`${selected.name} component`} />
            <div>
              <span>SELECTED COMPONENT</span>
              <strong>{selected.name}</strong>
            </div>
          </div>
          <div className="component-detail-copy">
            <div className="detail-score">
              <strong>{currentHealth}</strong>
              <span>health score</span>
              {/* <strong>
                {selected.key === "motors"
                  ? Math.max(45, Math.round(telemetry.health_score - 12))
                  : selected.health}
              </strong> */}
            </div>
            <ScoreBar
              score={currentHealth}
              tone={
                selected.health > 90
                  ? "green"
                  : selected.health > 75
                    ? "amber"
                    : "red"
              }
            />
            <StatusPill
              label={selected.state}
              tone={
                selected.health > 90
                  ? "green"
                  : selected.health > 75
                    ? "amber"
                    : "red"
              }
            />
            <p>{selected.recommendation}</p>
            <div className="detail-metrics">
              <Metric label="Current metric" value={selected.metric} />
              <Metric label="Trend" value={selected.trend} />
            </div>
            <div className="detail-chart">
              <Eyebrow>7-DAY COMPONENT TREND</Eyebrow>
              <Chart
                points={chartSeries.map(
                  (_, i) => selected.health - i * 0.2 + Math.sin(i) * 2,
                )}
                labels
              />
            </div>
            <Link
              className="button secondary"
              to="/app/maintenance"
              state={{
                prefill: {
                  component: selected.name,
                  issue: `${selected.state} (Health score: ${currentHealth}/100)`,
                  recommendation: selected.recommendation,
                  severity: severityLevel,
                },
              }}
            >
              Create maintenance task <Wrench size={15} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}