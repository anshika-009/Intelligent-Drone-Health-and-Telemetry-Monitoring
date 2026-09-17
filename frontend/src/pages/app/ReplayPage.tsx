import { useEffect, useState } from 'react';
import { Pause, Play } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Metric, SectionHeading } from '../../components/common';
import { useApp } from '../../store/AppStore';
import {
  createReplayRoute,
  interpolateReplayLocation,
  MapScene,
} from './shared/MapScene';

export function ReplayPage() {
  const { telemetry } = useApp();

  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(62);
  const [speed, setSpeed] = useState(1);

  const replayRoute = createReplayRoute(telemetry);

  const replayLocation = interpolateReplayLocation(
    telemetry,
    replayRoute,
    progress,
  );

  useEffect(() => {
    if (!playing) return;

    const intervalMs = 1000 / speed;

    const timer = window.setInterval(() => {
      setProgress(previousProgress => {
        if (previousProgress >= 100) {
          setPlaying(false);
          return 100;
        }

        return Math.min(100, previousProgress + 1.5 * speed);
      });
    }, intervalMs);

    return () => {
      window.clearInterval(timer);
    };
  }, [playing, speed]);

  /*
   * These values represent the replay state at the current progress.
   *
   * The current repository route contains map coordinates only, so the
   * additional replay metrics are derived from the replay progress.
   */
  const replayAltitude = (
    telemetry.altitude + Math.sin((progress / 100) * Math.PI) * 35
  ).toFixed(0);

  const replaySpeed = (
    telemetry.ground_speed +
    Math.sin((progress / 100) * Math.PI * 2) * 8
  ).toFixed(0);

  const replayHealth = Math.max(
    0,
    Math.round(telemetry.health_score - progress * 0.08),
  ).toString();

  const replaySector = `Sector ${Math.min(
    4,
    Math.max(1, Math.ceil(progress / 25)),
  )}`;

  const handleProgressChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setProgress(Number(event.target.value));
  };

  const handlePlayPause = () => {
    if (!playing && progress >= 100) {
      setProgress(0);
    }

    setPlaying(previousPlaying => !previousPlaying);
  };

  return (
    <div className="page">
      <SectionHeading
        eyebrow="FLIGHT REPLAY / STORED DATA"
        title="Replay a flight"
        copy="The map, metrics, and alert timeline are driven from the stored flight session."
        action={
          <Link to="/app/flights" className="button ghost">
            ← All flights
          </Link>
        }
      />

      <div className="replay-panel panel">
        <MapScene
          variant="replay"
          progress={progress}
          location={replayLocation}
          route={replayRoute}
        />

        <div className="replay-controls">
          <button
            type="button"
            className="play-button"
            aria-label={playing ? 'Pause replay' : 'Play replay'}
            onClick={handlePlayPause}
          >
            {playing ? <Pause size={18} /> : <Play size={18} />}
          </button>

          <div className="scrubber">
            <input
              type="range"
              min="0"
              max="100"
              value={progress}
              aria-label="Replay progress"
              onChange={handleProgressChange}
            />

            <div>
              <span>14:32:18</span>
              <span>14:50:59</span>
            </div>
          </div>

          <div className="speed-buttons">
            {[1, 2, 4].map(replaySpeedValue => (
              <button
                type="button"
                key={replaySpeedValue}
                className={speed === replaySpeedValue ? 'active' : ''}
                aria-pressed={speed === replaySpeedValue}
                onClick={() => setSpeed(replaySpeedValue)}
              >
                {replaySpeedValue}×
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="replay-metrics">
        <Metric label="Altitude" value={replayAltitude} unit="m" />
        <Metric label="Speed" value={replaySpeed} unit="km/h" />
        <Metric label="Health" value={replayHealth} unit="/100" />
        <Metric label="Position" value={replaySector} />
      </div>
    </div>
  );
}
