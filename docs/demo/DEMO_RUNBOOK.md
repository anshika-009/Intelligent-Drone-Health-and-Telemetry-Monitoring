# IDHTM Demo Runbook

1. Start the frontend and backend, or run `docker compose up --build` when Docker is available.
2. Open the landing page and choose **Launch monitor**.
3. Use `operator@idhtm.dev` and `demo-flight`, or register a new local operator.
4. Let the system transition through **AUTHENTICATED**, **IDHTM SYSTEM ONLINE**, **DRONE-01 CONNECTED**, **HEALTH CHECK**, and **MONITORING ACTIVE**.
5. On **Flight overview**, open the scenario control and select **Motor Vibration**, **Signal Degradation**, **GPS Loss**, **Low Battery**, or **Multi-Fault**.
6. Start the feed and observe the telemetry values, health score, component state, and alert list respond to the selected scenario.
7. Open **Health** to select Motors or another component, inspect its evidence, and use **Create maintenance task**.
8. Open **Alerts & recommendations** to inspect explainable rule output and acknowledge a signal.
9. Open **Flights**, select a historical flight, and use **Replay flight** to scrub the stored session visualization.
10. Review **Maintenance**, **Reports**, and **Connections**. The Connections page distinguishes the active local simulator from available Pixhawk / MAVLink and ArduPilot SITL boundaries.

The application labels the simulator as active and does not claim physical hardware or implemented AI. The current backend health engine is rule-based and its recommendations are intentionally explainable.
