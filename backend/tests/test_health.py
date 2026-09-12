from app.services.health.engine import calculate_health, explainable_rules


def test_low_battery_rule():
    telemetry = {
        "battery_percentage": 22,
        "signal_strength": 90,
        "vibration": 0.2,
        "gps_fix": True,
        "temperature": 38,
    }
    assert calculate_health({**telemetry}) < 100
    assert any(rule["id"] == "battery-low" for rule in explainable_rules(telemetry))


def test_gps_loss_rule():
    telemetry = {
        "battery_percentage": 90,
        "signal_strength": 90,
        "vibration": 0.2,
        "gps_fix": False,
        "temperature": 38,
    }
    assert any(rule["id"] == "gps-loss" for rule in explainable_rules(telemetry))
