import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { initialTelemetry, seedAlerts } from '../data/mock';
import type { Alert, Scenario, Telemetry } from '../types';

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
type Store = { telemetry: Telemetry; scenario: Scenario; setScenario: (s: Scenario) => void; simulatorActive: boolean; setSimulatorActive: (v: boolean) => void; alerts: Alert[]; acknowledgeAlert: (id: string) => void; user: { name: string; email: string } | null; signIn: (email: string, name?: string) => void; signOut: () => void; };
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
  return { ...previous, timestamp: new Date().toISOString(),latitude: previous.latitude + Math.cos(Date.now() / 2400) * 0.00008,
    longitude: previous.longitude + Math.sin(Date.now() / 2100) * 0.0001, altitude: Math.max(74, Math.min(162, previous.altitude + Math.sin(Date.now() / 2700) * 1.5)), ground_speed: Math.max(18, 42 + Math.sin(Date.now() / 1500) * 7), vertical_speed: Math.sin(Date.now() / 1100) * 2, heading: (previous.heading + .8) % 360, battery_percentage: Math.max(15, battery), signal_strength: Math.max(24, signal), vibration, gps_fix: gps, gps_satellites: gps ? 14 : 0, temperature, health_score: health, estimated_remaining_flight_time: Math.round(Math.max(5, battery * .21)) };
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
  const [telemetry, setTelemetry] = useState(initialTelemetry);
  const [scenario, setScenarioState] = useState<Scenario>('normal');
  const [simulatorActive, setSimulatorActive] = useState(true);
  const [alerts, setAlerts] = useState(seedAlerts);
  const [user, setUser] = useState<{ name: string; email: string } | null>(() => { const raw = localStorage.getItem('idhtm-user'); return raw ? JSON.parse(raw) : null; });
  const setScenario = (next: Scenario) => { setScenarioState(next); void fetch(`${API_URL}/telemetry/scenario`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario: next }) }).catch(() => undefined); };

  useEffect(() => {
    if (!simulatorActive) return;
    let fallbackTimer: number | undefined;
    let socket: WebSocket | undefined;
    let locationSocket: WebSocket | undefined;
    const startFallback = () => { if (fallbackTimer) return; fallbackTimer = window.setInterval(() => setTelemetry(previous => nextLocalTelemetry(previous, scenario)), 1000); };
    try {
      socket = new WebSocket(WS_URL);
      socket.onopen = () => { void fetch(`${API_URL}/telemetry/scenario`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario }) }).catch(() => undefined); };
      socket.onmessage = event => { const payload = JSON.parse(event.data) as { telemetry?: Telemetry; alerts?: Array<Omit<Alert, 'id'|'timestamp'|'acknowledged'>> }; if (payload.telemetry) setTelemetry(payload.telemetry); if (payload.alerts?.length) setAlerts(payload.alerts.map((a, i) => ({ ...a, id: `BACKEND-${i}`, timestamp: 'just now', acknowledged: false }))); };
      socket.onerror = () => { startFallback(); };
      try {
        locationSocket = new WebSocket(LOCATION_WS_URL);
      
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
    const timeout = window.setTimeout(() => { if (!socket || socket.readyState !== WebSocket.OPEN) startFallback(); }, 1500);
    return () => { window.clearTimeout(timeout); if (fallbackTimer) window.clearInterval(fallbackTimer); socket?.close(); locationSocket?.close(); };
  }, [scenario, simulatorActive]);

  useEffect(() => { const next = deriveLocalAlerts(telemetry); if (next.length) setAlerts(previous => [...next, ...previous.filter(a => !a.id.startsWith('LIVE-') && !a.id.startsWith('BACKEND-'))].slice(0, 8)); }, [telemetry]);
  const value = useMemo(() => ({ telemetry, scenario, setScenario, simulatorActive, setSimulatorActive, alerts, acknowledgeAlert: (id: string) => setAlerts(previous => previous.map(a => a.id === id ? { ...a, acknowledged: true } : a)), user, signIn: (email: string, name = 'Flight Operator') => { const next = { email, name }; localStorage.setItem('idhtm-user', JSON.stringify(next)); setUser(next); }, signOut: () => { localStorage.removeItem('idhtm-user'); setUser(null); } }), [telemetry, scenario, simulatorActive, alerts, user]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useApp() { const ctx = useContext(Context); if (!ctx) throw new Error('useApp must be used inside AppProvider'); return ctx; }
