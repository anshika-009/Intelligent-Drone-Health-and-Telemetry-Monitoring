-- IDHTM relational foundation
CREATE TABLE IF NOT EXISTS telemetry (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  drone_id TEXT NOT NULL,
  flight_id TEXT NOT NULL,
  scenario TEXT NOT NULL,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  altitude DOUBLE PRECISION,
  ground_speed DOUBLE PRECISION,
  airspeed DOUBLE PRECISION,
  vertical_speed DOUBLE PRECISION,
  heading DOUBLE PRECISION,
  flight_mode TEXT,
  battery_percentage DOUBLE PRECISION,
  battery_voltage DOUBLE PRECISION,
  signal_strength DOUBLE PRECISION,
  gps_fix BOOLEAN,
  gps_satellites INTEGER,
  vibration DOUBLE PRECISION,
  temperature DOUBLE PRECISION,
  health_score INTEGER
);
CREATE INDEX IF NOT EXISTS telemetry_timestamp_idx ON telemetry (timestamp DESC);
CREATE INDEX IF NOT EXISTS telemetry_flight_idx ON telemetry (flight_id, timestamp DESC);
CREATE TABLE IF NOT EXISTS maintenance_records (
  id BIGSERIAL PRIMARY KEY,
  component TEXT NOT NULL,
  issue TEXT NOT NULL,
  recommendation TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ
);
