import { useEffect, useMemo, useState } from 'react';
import { Pause, Play } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '@clerk/react';
import { Metric, SectionHeading } from '../../components/common';
import { flightsService } from '../../services/api';
import { MapScene, type MapLocation, type RoutePoint } from './shared/MapScene';

type TelemetrySample = {
  timestamp: string;
  latitude: number | null;
  longitude: number | null;
  altitude: number | null;
  ground_speed: number | null;
  heading: number | null;
  health_score: number | null;
  gps_fix: boolean | null;
};

type FlightDetail = {
  id: number;
  telemetry: TelemetrySample[];
};

type FlightListItem = { id: number; samples: number };

export function ReplayPage() {
  // Opened from a specific flight: /app/flights/:flightId/replay.
  // Opened from the sidebar: /app/replay (no id) -> replay the most
  // recent flight that has recorded telemetry.
  const { flightId: routeFlightId } = useParams();
  const { getToken } = useAuth();
  const [latestFlightId, setLatestFlightId] = useState<string | null>(null);
  const [noFlights, setNoFlights] = useState(false);
  const flightId = routeFlightId ?? latestFlightId ?? undefined;

  const [flight, setFlight] = useState<FlightDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed] = useState(1);

  useEffect(() => {
    if (routeFlightId) return;
    let cancelled = false;
    (async () => {
      try {
        const token = await getToken();
        const list = (await flightsService.list(token)) as FlightListItem[];
        if (cancelled) return;
        // The list is newest-first; pick the newest one that has data.
        const latest = list.find((f) => f.samples > 0);
        if (latest) {
          setLatestFlightId(String(latest.id));
        } else {
          setNoFlights(true);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError('Could not load your flights.');
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [routeFlightId, getToken]);

  useEffect(() => {
    if (!flightId) return;
    let cancelled = false;
    (async () => {
      try {
        const token = await getToken();
        const data = (await flightsService.get(token, flightId)) as FlightDetail;
        if (!cancelled) setFlight(data);
      } catch {
        if (!cancelled) setError('Could not load this flight.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [flightId, getToken]);

  const samples = flight?.telemetry ?? [];

  // Route line: only the samples that actually had a GPS fix.
  const route: RoutePoint[] = useMemo(
    () =>
      samples
        .filter((s) => s.latitude != null && s.longitude != null)
        .map((s) => [s.latitude as number, s.longitude as number]),
    [samples],
  );

  const currentIndex = samples.length > 0
    ? Math.min(samples.length - 1, Math.floor((progress / 100) * (samples.length - 1)))
    : 0;
  const currentSample = samples[currentIndex];

  // If the current sample has no fix, fall back to the nearest earlier one
  // that did, so the marker doesn't disappear during a brief GPS dropout.
  const currentLocation: MapLocation | undefined = useMemo(() => {
    if (!currentSample) return undefined;
    if (currentSample.latitude != null && currentSample.longitude != null) {
      return {
        latitude: currentSample.latitude,
        longitude: currentSample.longitude,
        altitude: currentSample.altitude ?? 0,
        heading: currentSample.heading ?? 0,
        timestamp: currentSample.timestamp,
      };
    }
    for (let i = currentIndex - 1; i >= 0; i--) {
      const s = samples[i];
      if (s.latitude != null && s.longitude != null) {
        return {
          latitude: s.latitude,
          longitude: s.longitude,
          altitude: s.altitude ?? 0,
          heading: s.heading ?? 0,
          timestamp: currentSample.timestamp,
        };
      }
    }
    return undefined;
  }, [currentSample, currentIndex, samples]);

  useEffect(() => {
    if (!playing || samples.length === 0) return;
    const intervalMs = 1000 / speed;
    const timer = window.setInterval(() => {
      setProgress((previous) => {
        if (previous >= 100) {
          setPlaying(false);
          return 100;
        }
        return Math.min(100, previous + 1.5 * speed);
      });
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [playing, speed, samples.length]);

  const handleProgressChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setProgress(Number(event.target.value));
  };

  const handlePlayPause = () => {
    if (!playing && progress >= 100) setProgress(0);
    setPlaying((p) => !p);
  };

  if (loading) return <div className="page"><p className="empty-state">Loading flight…</p></div>;
  if (noFlights) {
    return (
      <div className="page">
        <SectionHeading
          eyebrow="FLIGHT REPLAY / STORED DATA"
          title="Replay a flight"
          copy="There are no recorded flights to replay yet. Start the live feed on the dashboard and a flight will be recorded."
          action={<Link to="/app/dashboard" className="button ghost">Go to dashboard</Link>}
        />
      </div>
    );
  }
  if (error || !flight) return <div className="page"><p className="empty-state">{error || 'Flight not found.'}</p></div>;
  if (samples.length === 0) {
    return (
      <div className="page">
        <SectionHeading
          eyebrow="FLIGHT REPLAY / STORED DATA"
          title="Replay a flight"
          copy="This flight has no recorded telemetry to replay yet."
          action={<Link to="/app/flights" className="button ghost">← All flights</Link>}
        />
      </div>
    );
  }

  const startTime = new Date(samples[0].timestamp).toLocaleTimeString();
  const endTime = new Date(samples[samples.length - 1].timestamp).toLocaleTimeString();

  return (
    <div className="page">
      <SectionHeading
        eyebrow="FLIGHT REPLAY / STORED DATA"
        title={`Replay flight #${flight.id}`}
        copy="The map, metrics, and timeline below are the actual telemetry recorded during this flight."
        action={<Link to="/app/flights" className="button ghost">← All flights</Link>}
      />

      <div className="replay-panel panel">
        <MapScene variant="replay" progress={progress} location={currentLocation} route={route} />

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
              <span>{startTime}</span>
              <span>{endTime}</span>
            </div>
          </div>

          <div className="speed-buttons">
            {[1, 2, 4].map((v) => (
              <button
                type="button"
                key={v}
                className={speed === v ? 'active' : ''}
                aria-pressed={speed === v}
                onClick={() => setSpeed(v)}
              >
                {v}×
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="replay-metrics">
        <Metric label="Altitude" value={currentSample.altitude != null ? currentSample.altitude.toFixed(0) : '—'} unit="m" />
        <Metric label="Speed" value={currentSample.ground_speed != null ? currentSample.ground_speed.toFixed(0) : '—'} unit="km/h" />
        <Metric label="Health" value={currentSample.health_score != null ? String(currentSample.health_score) : '—'} unit="/100" />
        <Metric label="Time" value={new Date(currentSample.timestamp).toLocaleTimeString()} />
      </div>
    </div>
  );
}