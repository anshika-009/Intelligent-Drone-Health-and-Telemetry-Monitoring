import React from 'react';
import ReactDOM from 'react-dom/client';
import { ClerkProvider, Show } from '@clerk/react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppProvider } from './store/AppStore';
import { LandingPage } from './pages/public/LandingPage';
import { AuthPage } from './pages/public/AuthPage';
import { AppShell } from './layouts/AppShell';
import { AlertsPage, ConnectionsPage, CockpitPage, DashboardPage, FlightDetailPage, FlightsPage, HealthPage, MaintenancePage, ReplayPage, ReportsPage, SettingsPage } from './pages/app/AppPages';
import './styles/global.css';

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY — add it to your .env file (get it from the Clerk dashboard).');
}

function Protected() {
  return <><Show when="signed-in"><AppShell/></Show><Show when="signed-out"><Navigate to="/" replace/></Show></>;
}
function PublicPlaceholder({title,copy}:{title:string;copy:string}) { return <div className="simple-public"><header className="public-nav"><a href="/"><strong>IDHTM</strong></a><a href="/login" className="button small">Launch monitor</a></header><main><div className="simple-public-copy"><span className="eyebrow">IDHTM / PRODUCT STORY</span><h1>{title}</h1><p>{copy}</p><a href="/" className="inline-link">← Back to the product story</a></div></main></div>; }
function App() { return <Routes><Route path="/" element={<LandingPage/>}/><Route path="/product" element={<PublicPlaceholder title="A complete operational picture for every flight." copy="Live dashboard, cockpit instrumentation, flight history, component intelligence, and reports are designed as one connected system."/>}/><Route path="/how-it-works" element={<PublicPlaceholder title="Telemetry becomes understanding." copy="IDHTM normalizes the signal, applies explainable health rules, surfaces alerts, and recommends the next action without hiding the reasoning."/>}/><Route path="/architecture" element={<PublicPlaceholder title="Built around a clean telemetry boundary." copy="Simulator, Pixhawk, and ArduPilot SITL sources can flow into the same FastAPI services and operator experience."/>}/><Route path="/future-ai" element={<PublicPlaceholder title="AI-ready, not AI-faked." copy="Today’s health engine is rule-based and transparent. Future anomaly detection and predictive maintenance belong behind explicit, testable service boundaries."/>}/><Route path="/login/*" element={<AuthPage mode="login"/>}/><Route path="/register/*" element={<AuthPage mode="register"/>}/><Route element={<Protected/>}><Route path="/app" element={<Navigate to="/app/dashboard" replace/>}/><Route path="/app/dashboard" element={<DashboardPage/>}/><Route path="/app/cockpit" element={<CockpitPage/>}/><Route path="/app/health" element={<HealthPage/>}/><Route path="/app/alerts" element={<AlertsPage/>}/><Route path="/app/flights" element={<FlightsPage/>}/><Route path="/app/flights/:flightId/replay" element={<ReplayPage/>}/><Route path="/app/flights/:flightId" element={<FlightDetailPage/>}/><Route path="/app/maintenance" element={<MaintenancePage/>}/><Route path="/app/reports" element={<ReportsPage/>}/><Route path="/app/connections" element={<ConnectionsPage/>}/><Route path="/app/settings" element={<SettingsPage/>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes>; }
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY} afterSignOutUrl="/"><BrowserRouter><AppProvider><App/></AppProvider></BrowserRouter></ClerkProvider></React.StrictMode>);