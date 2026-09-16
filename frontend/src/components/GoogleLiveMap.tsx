import { useEffect, useMemo,useRef, useState, type ReactNode } from 'react';
import { Circle, MapContainer, Marker, Polyline, TileLayer, Tooltip, ZoomControl, useMap } from 'react-leaflet';
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
  // Start with an EMPTY track. Seeding this with the fallback/default
  // center (used only before real telemetry arrives) is what caused a
  // spurious line to be drawn from that fallback point all the way to
  // the drone's real first GPS fix. We only ever want to record points
  // that came from actual telemetry.
  const [track, setTrack] = useState<LatLng[]>(() => (route?.length ? route : []));

  // The HOME marker is the very first real position we ever see. Once
  // set, it never moves again - it marks the takeoff/start location for
  // the whole session, independent of where the drone is now.
  const [home, setHome] = useState<LatLng | null>(() => (route?.length ? route[0] : null));

  useEffect(() => {
    if (route?.length) {
      setTrack(route);
      setHome(previous => previous ?? route[0]);
      return;
    }
    // No real telemetry yet - don't record anything, so no line is drawn
    // until the drone actually reports a position.
    if (!location) return;

    const point: LatLng = [location.latitude, location.longitude];
    setHome(previous => previous ?? point);
    setTrack(previous => {
      const last = previous[previous.length - 1];
      if (last && last[0] === point[0] && last[1] === point[1]) return previous;
      return [...previous, point].slice(-80);
    });
  }, [location, route]);

  const droneIcon = useMemo(() => L.divIcon({
    className: 'idhtm-leaflet-drone-icon',
    html: `<div class="idhtm-leaflet-aircraft" style="transform:rotate(${current.heading}deg)" aria-label="Aircraft heading ${current.heading.toFixed(0)} degrees">
      <svg viewBox="0 0 24 24" width="26" height="26" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 1.5c-.9 0-1.6.73-1.6 1.63v5.1L2.3 12.9c-.2.13-.3.36-.3.6v1.4c0 .3.28.53.58.47l7.82-1.9v4.2l-2.2 1.62c-.14.1-.22.27-.22.44v1.05c0 .27.24.47.5.42l3.52-.72 3.52.72c.26.05.5-.15.5-.42v-1.05c0-.17-.08-.34-.22-.44l-2.2-1.62v-4.2l7.82 1.9c.3.06.58-.17.58-.47v-1.4c0-.24-.12-.47-.3-.6l-8.1-4.67v-5.1c0-.9-.72-1.63-1.6-1.63z"/>
      </svg>
    </div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  }), [current.heading]);

  // Red teardrop/pin marker for the home/takeoff location. Sized to
  // sit visually in line with the 26px aircraft glyph rather than
  // dominating it.
  const homeIcon = useMemo(() => L.divIcon({
    className: 'idhtm-leaflet-home-icon',
    html: `<div class="idhtm-leaflet-home" aria-label="Home / takeoff location">
      <svg viewBox="0 0 24 32" width="20" height="27" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 0C5.9 0 1 4.9 1 11c0 8.25 11 21 11 21s11-12.75 11-21C23 4.9 18.1 0 12 0z"/>
        <circle cx="12" cy="11" r="4.2" class="idhtm-leaflet-home-dot"/>
      </svg>
    </div>`,
    iconSize: [20, 27],
    iconAnchor: [10, 27],
  }), []);

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
        {home && (
          <Marker position={home} icon={homeIcon}>
            <Tooltip direction="top" offset={[0, -30]} opacity={1}>
              Home / takeoff<br />
              {home[0].toFixed(6)}°, {home[1].toFixed(6)}°
            </Tooltip>
          </Marker>
        )}
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