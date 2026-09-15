import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useAuth } from "@clerk/react";
import { initialTelemetry } from "../data/mock";
import { telemetryService } from "../services/api";
import type { Alert, Scenario, Telemetry } from "../types";

export type Theme = "light" | "dark";
export type AlertThresholds = {
  battery: number;
  signal: number;
  vibration: number;
  temperature: number;
};
const DEFAULT_THRESHOLDS: AlertThresholds = {
  battery: 30,
  signal: 45,
  vibration: 0.48,
  temperature: 58,
};

type Store = {
  telemetry: Telemetry;
  scenario: Scenario;
  setScenario: (s: Scenario) => void;
  simulatorActive: boolean;
  setSimulatorActive: (v: boolean) => void;
  isConnected: boolean;
  alerts: Alert[];
  acknowledgeAlert: (id: string) => void;
  theme: Theme;
  toggleTheme: () => void;
  alertThresholds: AlertThresholds;
  setAlertThresholds: (t: AlertThresholds) => void;
  resetAlertThresholds: () => void;
  reducedMotion: boolean;
  toggleReducedMotion: () => void;
};

const Context = createContext<Store | null>(null);
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

function nextLocalTelemetry(
  previous: Telemetry,
  scenario: Scenario,
): Telemetry {
  let battery =
    previous.battery_percentage -
    (scenario === "low_battery" || scenario === "multi_fault" ? 0.18 : 0.035);
  let signal = previous.signal_strength + Math.sin(Date.now() / 1800) * 0.7;
  let vibration =
    previous.vibration + Math.abs(Math.sin(Date.now() / 2300)) * 0.01;
  let gps = true;
  let temperature = 38 + Math.sin(Date.now() / 2600) * 2;
  if (scenario === "signal_degradation" || scenario === "multi_fault")
    signal = previous.signal_strength - 0.22;
  if (scenario === "motor_vibration" || scenario === "multi_fault")
    vibration = Math.min(0.86, previous.vibration + 0.012);
  if (
    scenario === "gps_loss" ||
    (scenario === "multi_fault" && Math.sin(Date.now() / 4000) > 0.2)
  )
    gps = false;
  if (scenario === "multi_fault")
    temperature = Math.min(74, previous.temperature + 0.02);
  const health = Math.max(
    42,
    Math.round(
      100 -
        (100 - battery) * 0.2 -
        (100 - signal) * 0.18 -
        vibration * 30 -
        (gps ? 0 : 18) -
        Math.max(0, temperature - 55) * 0.4,
    ),
  );
  return {
    ...previous,
    timestamp: new Date().toISOString(),
    latitude: previous.latitude + Math.cos(Date.now() / 2400) * 0.00008,
    longitude: previous.longitude + Math.sin(Date.now() / 2100) * 0.0001,
    altitude: Math.max(
      74,
      Math.min(162, previous.altitude + Math.sin(Date.now() / 2700) * 1.5),
    ),
    ground_speed: Math.max(18, 42 + Math.sin(Date.now() / 1500) * 7),
    vertical_speed: Math.sin(Date.now() / 1100) * 2,
    heading: (previous.heading + 0.8) % 360,
    battery_percentage: Math.max(15, battery),
    signal_strength: Math.max(24, signal),
    vibration,
    gps_fix: gps,
    gps_satellites: gps ? 14 : 0,
    temperature,
    health_score: health,
    estimated_remaining_flight_time: Math.round(Math.max(5, battery * 0.21)),
  };
}

function mergeLiveTelemetry(
  previous: Telemetry,
  incoming: Partial<Telemetry>,
): Telemetry {
  const next = { ...previous };
  for (const key of Object.keys(previous) as Array<keyof Telemetry>) {
    const value = incoming[key];
    if (value !== null && value !== undefined) next[key] = value as never;
  }
  return next;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  const [telemetry, setTelemetry] = useState(initialTelemetry);
  const [scenario, setScenarioState] = useState<Scenario>("normal");
  const [simulatorActive, setSimulatorActive] = useState(true);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem("idhtm-theme");
    if (saved === "dark" || saved === "light") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    localStorage.setItem("idhtm-theme", theme);
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  const toggleTheme = () =>
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));

  const [alertThresholds, setAlertThresholds] = useState<AlertThresholds>(
    () => {
      const saved = localStorage.getItem("idhtm-thresholds");
      if (saved) {
        try {
          return { ...DEFAULT_THRESHOLDS, ...JSON.parse(saved) };
        } catch {
          /* fall through to default */
        }
      }
      return DEFAULT_THRESHOLDS;
    },
  );
  useEffect(() => {
    localStorage.setItem("idhtm-thresholds", JSON.stringify(alertThresholds));
  }, [alertThresholds]);
  const resetAlertThresholds = () => setAlertThresholds(DEFAULT_THRESHOLDS);

  const [reducedMotion, setReducedMotion] = useState(() => {
    const saved = localStorage.getItem("idhtm-reduced-motion");
    if (saved === "true" || saved === "false") return saved === "true";
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });
  useEffect(() => {
    localStorage.setItem("idhtm-reduced-motion", String(reducedMotion));
    document.documentElement.classList.toggle("reduced-motion", reducedMotion);
  }, [reducedMotion]);
  const toggleReducedMotion = () => setReducedMotion((prev) => !prev);

  const postScenario = async (next: Scenario) => {
    const token = await getToken();
    void fetch(`${API_URL}/telemetry/scenario`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ scenario: next }),
    }).catch(() => undefined);
  };
  const setScenario = (next: Scenario) => {
    setScenarioState(next);
    void postScenario(next);
  };

  const [isConnected, setIsConnected] = useState(false);
  useEffect(() => {
    if (!simulatorActive) {
      setIsConnected(false);
      return;
    }
    let fallbackTimer: number | undefined;
    let pollTimer: number | undefined;
    let cancelled = false;
    const startFallback = () => {
      if (fallbackTimer) return;
      setIsConnected(false);
      fallbackTimer = window.setInterval(
        () =>
          setTelemetry((previous) => nextLocalTelemetry(previous, scenario)),
        1000,
      );
    };
    const pollLatest = async () => {
      try {
        const token = await getToken();
        const latest = (await telemetryService.latest(
          token,
        )) as Partial<Telemetry>;
        if (cancelled) return;
        setTelemetry((previous) => mergeLiveTelemetry(previous, latest));
        const backendAlerts = (await telemetryService.alerts(token)) as Alert[];
        if (cancelled) return;
        setAlerts(backendAlerts);
        setIsConnected(true);
        if (fallbackTimer) {
          window.clearInterval(fallbackTimer);
          fallbackTimer = undefined;
        }
      } catch {
        if (!cancelled) startFallback();
      }
    };
    void pollLatest();
    pollTimer = window.setInterval(() => void pollLatest(), 1000);
    return () => {
      cancelled = true;
      if (fallbackTimer) window.clearInterval(fallbackTimer);
      if (pollTimer) window.clearInterval(pollTimer);
    };
  }, [scenario, simulatorActive, getToken]);

  const value = useMemo(
    () => ({
      telemetry,
      scenario,
      setScenario,
      simulatorActive,
      setSimulatorActive,
      isConnected,
      alerts,
      acknowledgeAlert: (id: string) =>
        setAlerts((previous) =>
          previous.map((a) => (a.id === id ? { ...a, acknowledged: true } : a)),
        ),
      theme,
      toggleTheme,
      alertThresholds,
      setAlertThresholds,
      resetAlertThresholds,
      reducedMotion,
      toggleReducedMotion,
    }),
    [
      telemetry,
      scenario,
      simulatorActive,
      isConnected,
      alerts,
      theme,
      alertThresholds,
      reducedMotion,
    ],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useApp() {
  const ctx = useContext(Context);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
