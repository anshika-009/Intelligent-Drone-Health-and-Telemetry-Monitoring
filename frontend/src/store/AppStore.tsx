import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useAuth } from '@clerk/react';
import { initialTelemetry, seedAlerts } from '../data/mock';
import type { Alert, Scenario, Telemetry } from '../types';

export type Theme = 'light' | 'dark';
export type AlertThresholds = { battery: number; signal: number; vibration: number; temperature: number };
const DEFAULT_THRESHOLDS: AlertThresholds = { battery: 30, signal: 45, vibration: 0.48, temperature: 58 };

type DroneLocation = {
  drone_id?: string;
  flight_id?: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  altitude: number;
  heading?: number;
};

const LOCATION_WS_URL = import.meta.env.VITE_LOCATION_WS_URL
  || (import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/telemetry').replace('/ws/telemetry', '/ws/drone-location');
type Store = { telemetry: Telemetry; scenario: Scenario; setScenario: (s: Scenario) => void; simulatorActive: boolean; setSimulatorActive: (v: boolean) => void; alerts: Alert[]; acknowledgeAlert: (id: string) => void; theme: Theme;
  toggleTheme: () => void; alertThresholds: AlertThresholds; setAlertThresholds: (t: AlertThresholds) => void; resetAlertThresholds: () => void; reducedMotion: boolean; toggleReducedMotion: () => void; };

const Context = createContext<Store | null>(null);
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/telemetry';

function nextLocalTelemetry(previous: Telemetry, scenario: Scenario): Telemetry {
  let battery = previous.battery_percentage - (scenario === 'low_battery' || scenario === 'multi_fault' ? .18 : .035);
  let signal = previous.signal_strength + Math.sin(Date.now() / 1800) * .7;
  let vibration = previous.vibration + Math.abs(Math.sin(Date.now() / 2300)) * .01;
  let gps = true;
  let temperature = 38 + Math.sin(Date.now() / 2600) * 2;
  if (scenario === 'signal_degradation' || scenario === 'multi_fault') signal = previous.signal_strength - .22;
  if (scenario === 'motor_vibration' || scenario === 'multi_fault') vibration = Math.min(.86, previous.vibration + .012);
  if (scenario === 'gps_loss' || (scenario === 'multi_fault' && Math.sin(Date.now() / 4000) > .2)) gps = false;
  if (scenario === 'multi_fault') temperature = Math.min(74, previous.temperature + .02);
  const health = Math.max(42, Math.round(100 - (100 - battery) * .2 - (100 - signal) * .18 - vibration * 30 - (gps ? 0 : 18) - Math.max(0, temperature - 55) * .4));
  return {
    ...previous, timestamp: new Date().toISOString(), latitude: previous.latitude + Math.cos(Date.now() / 2400) * 0.00008,
    longitude: previous.longitude + Math.sin(Date.now() / 2100) * 0.0001, altitude: Math.max(74, Math.min(162, previous.altitude + Math.sin(Date.now() / 2700) * 1.5)), ground_speed: Math.max(18, 42 + Math.sin(Date.now() / 1500) * 7), vertical_speed: Math.sin(Date.now() / 1100) * 2, heading: (previous.heading + .8) % 360, battery_percentage: Math.max(15, battery), signal_strength: Math.max(24, signal), vibration, gps_fix: gps, gps_satellites: gps ? 14 : 0, temperature, health_score: health, estimated_remaining_flight_time: Math.round(Math.max(5, battery * .21))
  };
}

function deriveLocalAlerts(telemetry: Telemetry): Alert[] {
  const next: Alert[] = [];
  if (telemetry.battery_percentage < 30) next.push({ id: 'LIVE-BATTERY', timestamp: 'just now', severity: 'WARNING', source: 'Battery rule', title: 'Battery reserve is low', explanation: 'Remaining reserve is approaching the configured mission threshold.', metric: `${telemetry.battery_percentage.toFixed(0)}%`, recommendation: 'Plan a return and recharge the battery before the next flight.', acknowledged: false });
  if (telemetry.signal_strength < 45) next.push({ id: 'LIVE-SIGNAL', timestamp: 'just now', severity: 'WARNING', source: 'Communication rule', title: 'Communication signal degrading', explanation: 'Link reliability is decreasing progressively during this session.', metric: `${telemetry.signal_strength.toFixed(0)}%`, recommendation: 'Prepare Return-To-Home.', acknowledged: false });
  if (telemetry.vibration > .48) next.push({ id: 'LIVE-MOTOR', timestamp: 'just now', severity: 'CRITICAL', source: 'Motor rule', title: 'Motor vibration above baseline', explanation: 'Motor vibration has crossed the bearing inspection threshold.', metric: `${telemetry.vibration.toFixed(2)} g`, recommendation: 'Land safely and inspect motor bearing before another extended flight.', acknowledged: false });
  if (!telemetry.gps_fix) next.push({ id: 'LIVE-GPS', timestamp: 'just now', severity: 'CRITICAL', source: 'GPS rule', title: 'GPS fix unavailable', explanation: 'The aircraft is not receiving a valid position solution.', metric: '0 satellites', recommendation: 'Hold position if safe and initiate Return-To-Home.', acknowledged: false });
  return next;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  const [telemetry, setTelemetry] = useState(initialTelemetry);
  const [scenario, setScenarioState] = useState<Scenario>('normal');
  const [simulatorActive, setSimulatorActive] = useState(true);
  const [alerts, setAlerts] = useState(seedAlerts);

  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('idhtm-theme');
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    localStorage.setItem('idhtm-theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const toggleTheme = () => setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));

  const [alertThresholds, setAlertThresholds] = useState<AlertThresholds>(() => {
    const saved = localStorage.getItem('idhtm-thresholds');
    if (saved) { try { return { ...DEFAULT_THRESHOLDS, ...JSON.parse(saved) }; } catch { /* fall through to default */ } }
    return DEFAULT_THRESHOLDS;
  });
  useEffect(() => { localStorage.setItem('idhtm-thresholds', JSON.stringify(alertThresholds)); }, [alertThresholds]);
  const resetAlertThresholds = () => setAlertThresholds(DEFAULT_THRESHOLDS);

  const [reducedMotion, setReducedMotion] = useState(() => {
    const saved = localStorage.getItem('idhtm-reduced-motion');
    if (saved === 'true' || saved === 'false') return saved === 'true';
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });
  useEffect(() => {
    localStorage.setItem('idhtm-reduced-motion', String(reducedMotion));
    document.documentElement.classList.toggle('reduced-motion', reducedMotion);
  }, [reducedMotion]);
  const toggleReducedMotion = () => setReducedMotion(prev => !prev);

  const postScenario = async (next: Scenario) => {
    const token = await getToken();
    void fetch(`${API_URL}/telemetry/scenario`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: JSON.stringify({ scenario: next }) }).catch(() => undefined);
  };
  const setScenario = (next: Scenario) => { setScenarioState(next); void postScenario(next); };

  useEffect(() => {
    if (!simulatorActive) return;
    let fallbackTimer: number | undefined;
    let socket: WebSocket | undefined;
    let locationSocket: WebSocket | undefined;
    let cancelled = false;
    const startFallback = () => { if (fallbackTimer) return; fallbackTimer = window.setInterval(() => setTelemetry(previous => nextLocalTelemetry(previous, scenario)), 1000); };
    const connect = async () => {
      // Clerk's session token gets attached as a query param since the browser
      // WebSocket API can't set custom headers during the handshake.
      const token = await getToken();
      if (cancelled) return;
      const authQuery = token ? `${WS_URL.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}` : '';
      const locationAuthQuery = token ? `${LOCATION_WS_URL.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}` : '';
      try {
        socket = new WebSocket(`${WS_URL}${authQuery}`);
        socket.onopen = () => { void postScenario(scenario); };
        socket.onmessage = event => { const payload = JSON.parse(event.data) as { telemetry?: Telemetry; alerts?: Alert[] }; if (payload.telemetry) setTelemetry(payload.telemetry); if (payload.alerts) setAlerts(previous => [...payload.alerts!.map(incoming => { const existing = previous.find(p => p.id === incoming.id); return existing ? { ...incoming, acknowledged: existing.acknowledged } : incoming; }), ...previous.filter(a => a.id.startsWith('LIVE-'))]); };
        socket.onerror = () => { startFallback(); };
        try {
          locationSocket = new WebSocket(`${LOCATION_WS_URL}${locationAuthQuery}`);

          locationSocket.onmessage = event => {
            const location = JSON.parse(event.data) as DroneLocation;

            if (typeof location.latitude === 'number' && typeof location.longitude === 'number') {
              setTelemetry(previous => ({
                ...previous,
                timestamp: location.timestamp || previous.timestamp,
                latitude: location.latitude,
                longitude: location.longitude,
                altitude: typeof location.altitude === 'number' ? location.altitude : previous.altitude,
                heading: typeof location.heading === 'number' ? location.heading : previous.heading,
              }));
            }
          };

          locationSocket.onerror = () => {
            // The telemetry socket or local simulator remains the fallback.
          };
        } catch {
          // The location stream is optional until the backend endpoint is available.
        }
      } catch { startFallback(); }
      window.setTimeout(() => { if (!socket || socket.readyState !== WebSocket.OPEN) startFallback(); }, 1500);
    };
    void connect();
    return () => { cancelled = true; if (fallbackTimer) window.clearInterval(fallbackTimer); socket?.close(); locationSocket?.close(); };
  }, [scenario, simulatorActive, getToken]);

  useEffect(() => {
    // If telemetry came from the backend, we don't want to generate duplicate local alerts.
    // We can rely on the fact that if a websocket is connected, we shouldn't derive local alerts.
    // We'll use a simple heuristic: if simulatorActive is true and we haven't fallen back, we assume backend is handling alerts.
    // However, to be perfectly safe without adding more state, we just filter out LIVE- alerts if we're generating them.
    const next = deriveLocalAlerts(telemetry);
    setAlerts(previous => {
      const hasBackendAlerts = previous.some(a => a.id.startsWith('RULE-'));
      // If we have active backend alerts, skip local generation to avoid duplicates.
      if (hasBackendAlerts) return previous.filter(a => !a.id.startsWith('LIVE-'));
      // If no backend alerts are present, it's safe to show local alerts (either backend sent [] or we are in fallback).
      if (!next.length) return previous.filter(a => !a.id.startsWith('LIVE-'));
      return [...next, ...previous.filter(a => !a.id.startsWith('LIVE-'))].slice(0, 8);
    });
  }, [telemetry]);
  const value = useMemo(() => ({ telemetry, scenario, setScenario, simulatorActive, setSimulatorActive, alerts, acknowledgeAlert: (id: string) => setAlerts(previous => previous.map(a => a.id === id ? { ...a, acknowledged: true } : a)), theme, toggleTheme, alertThresholds, setAlertThresholds, resetAlertThresholds, reducedMotion, toggleReducedMotion }), [telemetry, scenario, simulatorActive, alerts, theme, alertThresholds, reducedMotion]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useApp() { const ctx = useContext(Context); if (!ctx) throw new Error('useApp must be used inside AppProvider'); return ctx; }