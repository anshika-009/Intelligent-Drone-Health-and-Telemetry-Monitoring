from fastapi.testclient import TestClient

from app.database.session import initialize
from app.main import app

initialize()
client = TestClient(app)


def test_health_and_all_scenarios_flow() -> None:
    assert client.get("/api/healthcheck").status_code == 200
    scenarios = client.get("/api/telemetry/scenarios").json()
    scenario_ids = [item["id"] for item in scenarios]
    assert {
        "normal",
        "low_battery",
        "gps_loss",
        "signal_degradation",
        "motor_vibration",
        "multi_fault",
    } <= set(scenario_ids)
    for scenario in scenario_ids:
        response = client.post("/api/telemetry/scenario", json={"scenario": scenario})
        assert response.status_code == 200
        health = client.get("/api/health").json()
        assert health["scenario"] == scenario
        assert 0 <= health["score"] <= 100
        assert set(health["components"]) >= {
            "battery",
            "motors",
            "gps",
            "sensors",
            "communication",
        }


def test_auth_and_operational_endpoints() -> None:
    login = client.post(
        "/api/auth/login",
        json={"email": "operator@idhtm.dev", "password": "demo-flight"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "operator@idhtm.dev"
    for path in [
        "/api/drones",
        "/api/alerts",
        "/api/flights",
        "/api/maintenance",
        "/api/reports",
        "/api/connections",
        "/api/telemetry/latest",
    ]:
        response = client.get(path)
        assert response.status_code == 200, path


def test_websocket_emits_normalized_telemetry_and_alerts() -> None:
    with client.websocket_connect("/ws/telemetry") as socket:
        payload = socket.receive_json()
        assert payload["telemetry"]["drone_id"] == "DRONE-01"
        assert payload["telemetry"]["flight_id"] == "FLT-LIVE-01"
        assert payload["telemetry"]["timestamp"]
        assert "health_score" in payload["telemetry"]
        assert isinstance(payload["alerts"], list)


def test_drone_location_websocket_emits_moving_coordinates() -> None:
    required = {
        "drone_id",
        "flight_id",
        "timestamp",
        "latitude",
        "longitude",
        "altitude",
        "heading",
    }
    with client.websocket_connect("/ws/drone-location") as socket:
        first = socket.receive_json()
        second = socket.receive_json()

    assert required <= set(first)
    assert first["drone_id"] == "DRONE-01"
    assert first["flight_id"] == "FLT-LIVE-01"
    assert first["timestamp"]
    assert (
        first["latitude"] != second["latitude"]
        or first["longitude"] != second["longitude"]
    )
