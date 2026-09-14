import { useState, type ComponentType } from 'react';
import { Activity, Bell, ChevronDown, CircleGauge, Cpu, FileText, Gauge, History, LayoutDashboard, Menu, Radio, Settings, ShieldCheck, Wrench, X, LogOut } from 'lucide-react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Brand, StatusPill } from '../components/common';
import { useApp } from '../store/AppStore';
import { useUser, UserButton } from '@clerk/react';

type NavIcon = ComponentType<{ size?: number }>;
type NavItem = { label: string; to: string; Icon: NavIcon };
const groups: { label: string; items: NavItem[] }[] = [
  { label: 'Monitoring', items: [{ label: 'Dashboard', to: '/app/dashboard', Icon: LayoutDashboard }, { label: 'Cockpit', to: '/app/cockpit', Icon: Gauge }, { label: 'Health', to: '/app/health', Icon: ShieldCheck }, { label: 'Alerts', to: '/app/alerts', Icon: Bell }] },
  { label: 'Flight operations', items: [{ label: 'Flights', to: '/app/flights', Icon: History }, { label: 'Flight replay', to: '/app/flights/FLT-2026-0821-07/replay', Icon: Radio }] },
  { label: 'Operations', items: [{ label: 'Maintenance', to: '/app/maintenance', Icon: Wrench }, { label: 'Reports', to: '/app/reports', Icon: FileText }] },
  { label: 'System', items: [{ label: 'Connections', to: '/app/connections', Icon: Cpu }, { label: 'Settings', to: '/app/settings', Icon: Settings }] }
];

export function AppShell() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { telemetry, scenario, simulatorActive } = useApp();
  const { user } = useUser();

  const displayName = user?.fullName || user?.primaryEmailAddress?.emailAddress || 'Flight operator';
  const title = location.pathname.includes('cockpit') ? 'Cockpit' : location.pathname.includes('health') ? 'Health' : location.pathname.includes('alerts') ? 'Alerts' : location.pathname.includes('flights') ? 'Flights' : location.pathname.includes('maintenance') ? 'Maintenance' : location.pathname.includes('reports') ? 'Reports' : location.pathname.includes('connections') ? 'Connections' : location.pathname.includes('settings') ? 'Settings' : 'Dashboard';

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-head">
          <Brand/>
          <button className="icon-button mobile-only" onClick={() => setOpen(false)} aria-label="Close navigation">
            <X size={17}/>
          </button>
        </div>
        <div className="sidebar-drone">
          <div className="drone-avatar"><CircleGauge size={18}/></div>
          <div><span>SELECTED AIRCRAFT</span><strong>DRONE-01 <ChevronDown size={14}/></strong></div>
        </div>
        <nav className="side-nav">
          {groups.map(group => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {group.items.map(({ label, to, Icon }) => (
                <NavLink 
                  key={label} 
                  to={to} 
                  onClick={() => setOpen(false)} 
                  className={({ isActive }) => `side-link ${isActive ? 'active' : ''}`}
                >
                  <Icon size={16}/>
                  <span>{label}</span>
                  {label === 'Alerts' && <b>{telemetry.health_score < 80 ? '3' : '1'}</b>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="connection-mini">
            <span className="live-dot"/>
            <div>
              <strong>{simulatorActive ? 'Simulator active' : 'Telemetry paused'}</strong>
              <small>{scenario.replace('_', ' ')} / 1 Hz</small>
            </div>
          </div>
          <div 
            className="side-link logout" 
            style={{ cursor: 'pointer' }}
            onClick={(e) => {
              const btn = e.currentTarget.querySelector('button');
              if (btn && !btn.contains(e.target as Node)) {
                btn.click();
              }
            }}
          >
            <UserButton/>
            <span>Account</span>
          </div>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <button className="icon-button mobile-only" onClick={() => setOpen(true)} aria-label="Open navigation">
            <Menu size={18}/>
          </button>
          <div className="breadcrumb">
            <span>Operations</span><strong> / {title}</strong>
          </div>
          <div className="top-actions">
            <div className="top-status">
              <StatusPill label={simulatorActive ? 'Simulator active' : 'Offline'} tone={simulatorActive ? 'green' : 'gray'}/>
              <span className="telemetry-pulse"><span className="live-dot"/> Telemetry 1 Hz</span>
            </div>
            <button className="icon-button has-badge" onClick={() => navigate('/app/alerts')} aria-label="Notifications">
              <Bell size={18}/>
              <b>{telemetry.health_score < 80 ? 3 : 1}</b>
            </button>
            <div className="user-menu">
              <span className="user-avatar">{displayName.slice(0, 2).toUpperCase()}</span>
              <span className="user-name">{displayName}</span>
            </div>
          </div>
        </header>
        <main className="app-content">
          <Outlet/>
        </main>
      </div>
    </div>
  );
}