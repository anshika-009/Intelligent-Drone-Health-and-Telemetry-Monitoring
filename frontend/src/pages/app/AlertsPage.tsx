import { Filter } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@clerk/react";
import { AlertRow, Metric, SectionHeading } from "../../components/common";
import { useApp } from "../../store/AppStore";
import { telemetryService } from "../../services/api";

export function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const { acknowledgeAlert } = useApp();
  const { getToken } = useAuth();

  useEffect(() => {
    let mounted = true;
    const loadAlerts = async () => {
      const token = await getToken();
      const data = await telemetryService.alerts(token);
      if (mounted) setAlerts(data as any[]);
    };
    void loadAlerts();
    return () => {
      mounted = false;
    };
  }, [getToken]);

  return (
    <div className="page">
      <SectionHeading
        eyebrow="RULE ENGINE / EXPLAINABLE"
        title="Alerts & recommendations"
        copy="Every signal includes its source, current value, and a recommended next action."
        action={
          <button className="button ghost">
            <Filter size={15} /> Filter
          </button>
        }
      />
      <div className="alert-summary">
        <Metric
          label="Active signals"
          value={alerts.filter((a) => !a.acknowledged).length}
        />
        <Metric
          label="Warnings"
          value={
            alerts.filter((a) => a.severity === "WARNING" && !a.acknowledged)
              .length
          }
          tone="warning"
        />
        <Metric
          label="Critical"
          value={
            alerts.filter((a) => a.severity === "CRITICAL" && !a.acknowledged)
              .length
          }
          tone="critical"
        />
        <Metric
          label="Acknowledged"
          value={alerts.filter((a) => a.acknowledged).length}
        />
      </div>
      <div className="alert-list">
        {alerts.map((a) => (
          <AlertRow
            key={a.id}
            {...a}
            onAcknowledge={() => acknowledgeAlert(a.id)}
          />
        ))}
      </div>
    </div>
  );
}
