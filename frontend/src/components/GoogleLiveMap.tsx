import { useEffect, useMemo,useRef, useState, type ReactNode } from 'react';
import { Circle, MapContainer, Marker, Polyline, TileLayer, ZoomControl, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Telemetry } from '../types';

type Location = Pick<Telemetry, 'latitude' | 'longitude' | 'altitude' | 'heading' | 'timestamp'>;
type LatLng = [number, number];
type Props = {
  location?: Location;
  route?: LatLng[];
  fallback?: ReactNode;
};

const DEFAULT_CENTER: LatLng = [37.7749, -122.4194];

function RecenterMap({ location }: { location: Location }) {
  const map = useMap();
  const lastCenter = useRef<[number, number] | null>(null);

  useEffect(() => {
    const next: [number, number] = [location.latitude, location.longitude];
    const prev = lastCenter.current;
    const movedEnough = !prev || map.distance(prev, next) > 25;
    if (!movedEnough) return;

    lastCenter.current = next;
    map.panTo(next, { animate: true, duration: 1.4, easeLinearity: 0.4 });
  }, [location.latitude, location.longitude, map]);

  return null;
}

export function LiveGoogleMap({ location, route, fallback }: Props) {
  const current: Location = location || {
    latitude: DEFAULT_CENTER[0],
    longitude: DEFAULT_CENTER[1],
    altitude: 0,
    heading: 0,
    timestamp: '',
  };
  const [tileError, setTileError] = useState(false);
  const [track, setTrack] = useState<LatLng[]>(() => route?.length ? route : [[current.latitude, current.longitude]]);

  useEffect(() => {
    if (route?.length) {
      setTrack(route);
      return;
    }
    if (!location) return;

    const point: LatLng = [location.latitude, location.longitude];
    setTrack(previous => {
      const last = previous[previous.length - 1];
      if (last && last[0] === point[0] && last[1] === point[1]) return previous;
      return [...previous, point].slice(-80);
    });
  }, [location, route]);

  const droneIcon = useMemo(() => L.divIcon({
    className: 'idhtm-leaflet-drone-icon',
    html: `<div class="idhtm-leaflet-drone" style="transform:rotate(${current.heading}deg)" aria-label="Drone heading ${current.heading.toFixed(0)} degrees"><span></span></div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  }), [current.heading]);

  const position: LatLng = [current.latitude, current.longitude];

  return (
    <div className="live-google-map idhtm-openstreet-map" aria-label="OpenStreetMap with live drone location">
      <MapContainer
        center={position}
        zoom={15}
        zoomControl={false}
        scrollWheelZoom
        style={{ width: '100%', height: '100%' }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
          eventHandlers={{ tileerror: () => setTileError(true) }}
        />
        <ZoomControl position="topright" />
        <RecenterMap location={current} />
        {track.length > 1 && (
          <Polyline
            positions={track}
            pathOptions={{ color: '#2364a1', weight: 3, opacity: 0.85 }}
          />
        )}
        <Circle
          center={position}
          radius={35}
          pathOptions={{
            color: '#2364a1',
            weight: 1,
            opacity: 0.45,
            fillColor: '#2364a1',
            fillOpacity: 0.08,
          }}
        />
        <Marker position={position} icon={droneIcon} />
      </MapContainer>

      <div className="live-map-topline">
        <span><span className="live-dot" /> OPENSTREETMAP / LIVE</span>
        <strong>DRONE-01</strong>
      </div>
      <div className="live-map-readout">
        <span>ALT {current.altitude.toFixed(0)} m</span>
        <span>{current.latitude.toFixed(5)}°, {current.longitude.toFixed(5)}°</span>
        <span>HDG {current.heading.toFixed(0)}°</span>
      </div>
      <div className="map-attribution">&copy; OpenStreetMap contributors · live position</div>
    </div>
  );
}
