import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, beforeEach, vi } from 'vitest';
import { AppProvider } from '../store/AppStore';
import { LandingPage } from '../pages/public/LandingPage';
import { AuthPage } from '../pages/public/AuthPage';
import { DashboardPage, HealthPage, AlertsPage, MaintenancePage, ReplayPage, FlightsPage, SettingsPage } from '../pages/app/AppPages';
import { AppShell } from '../layouts/AppShell';

function renderWithProviders(ui: React.ReactNode, initialEntries = ['/']) {
  return render(<MemoryRouter initialEntries={initialEntries}><AppProvider>{ui}</AppProvider></MemoryRouter>);
}

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  vi.stubGlobal('WebSocket', class { static OPEN = 1; readyState = 0; close() {} } as unknown as typeof WebSocket);
});

describe('public and authentication surfaces', () => {
  it('renders the complete landing story and primary actions', () => {
    renderWithProviders(<LandingPage/>);
    expect(screen.getByRole('heading', { name: /Understand your drone before it fails/i })).toBeInTheDocument();
    expect(screen.getByText('Raw telemetry is not the mission.')).toBeInTheDocument();
    expect(screen.getByText('From measurement to a better decision.')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /Launch monitor/i })).toHaveLength(1);
    expect(screen.getByText('See inside the decision.')).toBeInTheDocument();
    expect(screen.getByText('BATTERY')).toBeInTheDocument();
    expect(screen.getAllByText('MOTORS').length).toBeGreaterThan(0);
    expect(screen.getByAltText('Industrial drone airframe')).toBeInTheDocument();
  });

  it('renders login fields and transitions into system initialization', async () => {
    renderWithProviders(<AuthPage mode="login"/>);
    fireEvent.click(screen.getByRole('button', { name: /Authenticate/i }));
    expect(await screen.findByText('IDHTM system online')).toBeInTheDocument();
    expect(screen.getByText('DRONE-01 CONNECTED')).toBeInTheDocument();
  });
});

describe('protected operational surfaces', () => {
  it('renders live dashboard telemetry and simulator controls', () => {
    renderWithProviders(<DashboardPage/>);
    expect(screen.getByText('Flight overview')).toBeInTheDocument();
    expect(screen.getByText('Aircraft health')).toBeInTheDocument();
    expect(screen.getByText('SIMULATOR ACTIVE')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Normal Flight/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Zoom in' })).toBeInTheDocument();
    expect(screen.getByText('© OpenStreetMap contributors · live position')).toBeInTheDocument();
    expect(screen.getByText('Prepare the aircraft')).toBeInTheDocument();
  });

  it('opens the scenario picker and changes the selected scenario', () => {
    renderWithProviders(<DashboardPage/>);
    fireEvent.click(screen.getByRole('button', { name: /Normal Flight/i }));
    expect(screen.getByText('Motor Vibration')).toBeInTheDocument();
    const motorButtons = screen.getAllByRole('button', { name: /Motor Vibration/i });
    fireEvent.click(motorButtons[motorButtons.length - 1]);
    expect(screen.getAllByRole('button', { name: /Motor Vibration/i }).length).toBeGreaterThan(0);
  });

  it('shows health components, score bars, and a maintenance handoff', () => {
    renderWithProviders(<HealthPage/>);
    expect(screen.getByText('Health monitoring')).toBeInTheDocument();
    expect(screen.getAllByRole('meter', { name: /Health score 82 out of 100/i }).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('link', { name: /Create maintenance task/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /GPS98/i }));
    expect(screen.getByAltText('GPS component')).toBeInTheDocument();
    expect(document.querySelectorAll('img').length).toBeGreaterThanOrEqual(6);
  });

  it('acknowledges an alert and updates the action label', () => {
    renderWithProviders(<AlertsPage/>);
    const action = screen.getAllByRole('button', { name: 'Acknowledge' })[0];
    fireEvent.click(action);
    expect(screen.getAllByRole('button', { name: 'Acknowledged' }).length).toBeGreaterThan(0);
  });

  it('creates and advances a maintenance task', () => {
    renderWithProviders(<MaintenancePage/>);
    fireEvent.click(screen.getByRole('button', { name: /Create task/i }));
    expect(screen.getByText('Discharge curve review')).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: /Start task/i })[0]);
    expect(screen.getByRole('button', { name: /Complete/i })).toBeInTheDocument();
  });

  it('keeps settings status badges inside the settings surface', () => {
    renderWithProviders(<SettingsPage/>);
    expect(screen.getAllByText('Configured')).toHaveLength(4);
    expect(screen.getByText('Operator profile')).toBeInTheDocument();
  });

  it('renders replay controls and changes the timeline position', () => {
    renderWithProviders(<ReplayPage/>);
    const scrubber = screen.getByRole('slider');
    fireEvent.change(scrubber, { target: { value: '80' } });
    expect(scrubber).toHaveValue('80');
    fireEvent.click(screen.getByRole('button', { name: '' }));
  });
});

describe('application shell and route protection', () => {
  it('renders the shell navigation around a protected page', () => {
    localStorage.setItem('idhtm-user', JSON.stringify({ name: 'Test Operator', email: 'test@example.com' }));
    renderWithProviders(<AppShell/>);
    expect(screen.getByText('DRONE-01')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Health' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
  });
});
