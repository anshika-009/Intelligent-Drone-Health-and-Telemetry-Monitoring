import { useState, type ChangeEvent } from 'react';
import { ChevronDown } from 'lucide-react';
import { SectionHeading } from '../../components/common';
import { useApp, type AlertThresholds } from '../../store/AppStore';
import { useUser } from '@clerk/react';

export function SettingsPage() {
  const { alertThresholds, setAlertThresholds, resetAlertThresholds, reducedMotion, toggleReducedMotion } = useApp();
  const { user } = useUser();
  const [thresholdsOpen, setThresholdsOpen] = useState(false);
  const [draft, setDraft] = useState<AlertThresholds>(alertThresholds);
  const [saved, setSaved] = useState(false);

  const openThresholds = () => { setDraft(alertThresholds); setSaved(false); setThresholdsOpen(v => !v); };
  const updateDraft = (key: keyof AlertThresholds) => (e: ChangeEvent<HTMLInputElement>) => {
    const value = Number(e.target.value);
    setDraft(previous => ({ ...previous, [key]: Number.isFinite(value) ? value : previous[key] }));
  };
  const saveThresholds = () => { setAlertThresholds(draft); setSaved(true); window.setTimeout(() => setSaved(false), 2200); };
  const resetThresholds = () => { resetAlertThresholds(); setDraft(alertThresholds); setSaved(false); };

  const displayName = user?.fullName || user?.primaryEmailAddress?.emailAddress || 'Flight operator';
  const email = user?.primaryEmailAddress?.emailAddress;
  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0])
    .join('')
    .toUpperCase() || 'FO';

  const rows: [string, string, string][] = [
    ['Telemetry refresh', '1 Hz', 'Set simulator and stream frequency'],
  ];

  return (
    <div className="page">
      <div className="settings-heading-center">
        <SectionHeading eyebrow="SYSTEM / OPERATOR PREFERENCES" title="Settings" copy="Keep the operational workspace aligned to the way your team flies." />
      </div>
      <div className="settings-list">
        <div className="setting-row profile-row">
          <div className="profile-identity">
            <span className="profile-avatar">{initials}</span>
            <div>
              <strong>{displayName}</strong>
              <p>{email || 'Update identity and contact details'}</p>
            </div>
          </div>
          <span className="profile-role">Operator profile</span>
          <span className="setting-status">Signed in</span>
        </div>

        <div className="setting-row expandable">
          <button type="button" className="setting-row-main" onClick={openThresholds} aria-expanded={thresholdsOpen}>
            <div>
              <strong>Alert thresholds</strong>
              <p>Battery, sensor and motor limits that trigger live alerts</p>
            </div>
            <ChevronDown
              size={16}
              className="threshold-chevron"
              style={{ transform: thresholdsOpen ? 'rotate(180deg)' : 'none', transition: '.18s ease' }}
            />
          </button>
          {thresholdsOpen && (
            <div className="threshold-panel">
              <div className="threshold-grid">
                <div className="threshold-field">
                  <label>Battery reserve<span>{draft.battery}%</span></label>
                  <input type="range" min={5} max={60} step={1} value={draft.battery} onChange={updateDraft('battery')} />
                  <input type="number" min={5} max={60} value={draft.battery} onChange={updateDraft('battery')} aria-label="Battery threshold percent" />
                </div>
                <div className="threshold-field">
                  <label>Signal / sensor strength<span>{draft.signal}%</span></label>
                  <input type="range" min={10} max={80} step={1} value={draft.signal} onChange={updateDraft('signal')} />
                  <input type="number" min={10} max={80} value={draft.signal} onChange={updateDraft('signal')} aria-label="Signal threshold percent" />
                </div>
                <div className="threshold-field">
                  <label>Motor vibration<span>{draft.vibration.toFixed(2)}g</span></label>
                  <input type="range" min={0.2} max={0.9} step={0.01} value={draft.vibration} onChange={updateDraft('vibration')} />
                  <input type="number" min={0.2} max={0.9} step={0.01} value={draft.vibration} onChange={updateDraft('vibration')} aria-label="Motor vibration threshold in g" />
                </div>
                <div className="threshold-field">
                  <label>Motor temperature<span>{draft.temperature}°C</span></label>
                  <input type="range" min={40} max={90} step={1} value={draft.temperature} onChange={updateDraft('temperature')} />
                  <input type="number" min={40} max={90} value={draft.temperature} onChange={updateDraft('temperature')} aria-label="Motor temperature threshold in celsius" />
                </div>
              </div>
              <div className="threshold-actions">
                {saved && <span className="threshold-saved-note">Saved — live alerts now use these limits.</span>}
                <button type="button" className="button ghost small" onClick={resetThresholds}>Reset to defaults</button>
                <button type="button" className="button small" onClick={saveThresholds}>Save thresholds</button>
              </div>
            </div>
          )}
        </div>

        {rows.map(([title, value, copy]) => (
          <div className="setting-row" key={title}>
            <div><strong>{title}</strong><p>{copy}</p></div>
            <span>{value}</span>
            <span className="setting-status">Configured</span>
          </div>
        ))}

        <div className="setting-row">
          <div>
            <strong>Reduced motion</strong>
            <p>Turns off animations and transitions across the app</p>
          </div>
          <span>{reducedMotion ? 'Reduced motion on' : 'Respect system preference'}</span>
          <button
            type="button"
            className={`toggle-switch ${reducedMotion ? 'on' : ''}`}
            role="switch"
            aria-checked={reducedMotion}
            aria-label="Toggle reduced motion"
            onClick={toggleReducedMotion}
          >
            <span />
          </button>
        </div>
      </div>
    </div>
  );
}