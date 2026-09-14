import * as React from 'react';
import { Gauge } from 'lucide-react';
import { LiveGoogleMap } from '../../../components/GoogleLiveMap';

export type MapVariant = 'live' | 'detail' | 'replay';
export type MapLocation = { latitude: number; longitude: number; altitude: number; heading: number; timestamp: string };
export type RoutePoint = [number, number];

export function StaticMapScene({ variant = 'live', progress = 62 }: { variant?: MapVariant; progress?: number }) {
  const className = variant === 'replay' ? 'replay-stage map-scene' : `map-visual map-scene${variant === 'detail' ? ' large' : ''}`;
  const [zoom, setZoom] = React.useState(1);
  const handleZoomIn = () => setZoom(z => Math.min(z + 0.3, 2.5));
  const handleZoomOut = () => setZoom(z => Math.max(z - 0.3, 0.5));
  const handleCenter = () => setZoom(1);

  return <div className={className}>
    <div style={{ transform: `scale(${zoom})`, width: '100%', height: '100%', transition: 'transform 0.3s ease', transformOrigin: 'center' }}>
      <div className="map-grid"/><div className="map-water"/><div className="map-park park-a"/><div className="map-park park-b"/>
      <div className="map-road road-a"/><div className="map-road road-b"/><div className="map-road road-c"/><div className="map-road road-d"/>
      {variant === 'detail' ? <><div className="route-detail"/><div className="route-point p1"/><div className="route-point p2"/></> : variant === 'replay' ? <div className="replay-route" style={{ '--progress': `${progress}%` } as React.CSSProperties}/> : <div className="map-route"/>}
      <div className={`map-drone ${variant === 'replay' ? 'replay-drone' : ''}`} style={variant === 'replay' ? { left: `${progress}%` } : undefined}><span className="map-pulse"/><Gauge size={17}/></div>
      <span className="map-label label-a">{variant === 'detail' ? 'TAKEOFF' : variant === 'replay' ? '14:44:38 / MOTOR 2' : 'NORTH SECTOR'}</span><span className="map-label label-b">{variant === 'detail' ? 'LANDING' : 'DRONE-01 / NOW'}</span><span className="map-label label-c">NORTH ROAD</span>
    </div>
    <div className="map-controls" aria-label="Map controls"><button type="button" aria-label="Zoom in" onClick={handleZoomIn}>+</button><button type="button" aria-label="Zoom out" onClick={handleZoomOut}>−</button><button type="button" aria-label="Center aircraft" onClick={handleCenter}>⌖</button></div><div className="map-scale">100 m</div><div className="map-attribution">IDHTM basemap · live position</div>
  </div>;
}

export function MapScene({ variant = 'live', progress = 62, location, route }: { variant?: MapVariant; progress?: number; location?: MapLocation; route?: RoutePoint[] }) {
  if (variant === 'live' || variant === 'replay' || variant === 'detail') return <LiveGoogleMap location={location} route={route} fallback={<StaticMapScene variant={variant} progress={progress} />} />;
  return <StaticMapScene variant={variant} progress={progress} />;
}

export const REPLAY_OFFSETS: RoutePoint[] = [[0, 0], [.0008, .0011], [.0017, .0005], [.0012, -.0007], [.0002, -.0012], [-.0008, -.0004], [-.0012, .0007], [-.0004, .0014], [.0007, .0018]];

export function createReplayRoute(location: MapLocation): RoutePoint[] {
  return REPLAY_OFFSETS.map(([latitude, longitude]) => [location.latitude + latitude, location.longitude + longitude]);
}

export function interpolateReplayLocation(location: MapLocation, route: RoutePoint[], progress: number): MapLocation {
  const scaled = Math.max(0, Math.min(100, progress)) / 100 * (route.length - 1);
  const lowerIndex = Math.min(route.length - 1, Math.floor(scaled));
  const upperIndex = Math.min(route.length - 1, lowerIndex + 1);
  const blend = scaled - lowerIndex;
  const lower = route[lowerIndex] || [location.latitude, location.longitude];
  const upper = route[upperIndex] || lower;
  return {
    ...location,
    latitude: lower[0] + (upper[0] - lower[0]) * blend,
    longitude: lower[1] + (upper[1] - lower[1]) * blend,
    heading: (location.heading + progress * .55) % 360,
  };
}
