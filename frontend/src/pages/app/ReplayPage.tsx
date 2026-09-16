import { useEffect, useState } from 'react';
import { Pause, Play } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Metric, SectionHeading } from '../../components/common';
import { useApp } from '../../store/AppStore';
import { createReplayRoute, interpolateReplayLocation, MapScene } from './shared/MapScene';

export function ReplayPage() {
  const { telemetry } = useApp();
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(62);
  const [speed, setSpeed] = useState(1);

  const replayRoute = createReplayRoute(telemetry);
  const replayLocation = interpolateReplayLocation(telemetry, replayRoute, progress);

  useEffect(() => {
    if (!playing) return;

    const intervalMs = 1000 / speed;
    const timer = window.setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) return 100;
        return Math.min(100, prev + 1.5 * speed);
      });
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [playing, speed]);

  const replaySpeed = Math.max(18, Math.min(88, 20 + progress * 0.7)).toFixed(0);
  const replayHealth = Math.max(50, Math.min(100, 100 - progress * 0.2)).toFixed(0);

  return (
    <div className="page">
      <SectionHeading
        eyebrow="FLIGHT REPLAY / STORED DATA"
        title="Replay a flight"
        copy="The map, metrics, and alert timeline are driven from the stored flight session."
        action={<Link to="/app/flights" className="button ghost">← All flights</Link>}
      />

      <div className="replay-panel panel">
        <MapScene variant="replay" progress={progress} location={replayLocation} route={replayRoute} />

        <div className="replay-controls">
          <button
            className="play-button"
            onClick={() => setPlaying(prev => !prev)}
          >
            {playing ? <Pause size={18} /> : <Play size={18} />}
          </button>

          <div className="scrubber">
            <input
              type="range"
              min="0"
              max="100"
              value={progress}
              onChange={e => setProgress(Number(e.target.value))}
            />
            <div>
              <span>14:32:18</span>
              <span>14:50:59</span>
            </div>
          </div>

          <div className="speed-buttons">
            {[1, 2, 4].map(value => (
              <button
                key={value}
                className={speed === value ? 'active' : ''}
                onClick={() => setSpeed(value)}
              >
                {value}×
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="replay-metrics">
        <Metric label="Altitude" value={replayLocation.altitude.toFixed(0)} unit="m" />
        <Metric label="Speed" value={replaySpeed} unit="km/h" />
        <Metric label="Health" value={replayHealth} unit="/100" />
        <Metric label="Position" value={`Sector ${Math.min(4, Math.max(1, Math.ceil(progress / 25)))}`} />
      </div>
    </div>
  );
}
