"""
Tests for IDHTM Health Intelligence Engine.

These tests verify:

    - health scoring
    - individual fault rules
    - multi-fault detection
    - recommendations
    - missing telemetry handling

The tests do NOT require MAVLink or SITL.
"""

from app.services.health.engine import (
    analyze_health,
    calculate_health,
    explainable_rules,
)


# Test telemetry        

def normal_telemetry() -> dict:
    """
    Creates a normal healthy telemetry snapshot.
    """

    return {
        "battery_percentage": 85,
        "battery_voltage": 12.2,
        "battery_current": 10,
        "signal_strength": 90,
        "gps_fix": True,
        "gps_satellites": 14,
        "vibration": 0.10,
        "temperature": 40,
        "ax": 0,
        "ay": 0,
        "az": 9.80665,
    }

# Normal health

def test_normal_health():

    telemetry = normal_telemetry()

    score = calculate_health(
        telemetry
    )

    assert score >= 85


# Low battery

def test_low_battery():

    telemetry = normal_telemetry()

    telemetry["battery_percentage"] = 25

    rules = explainable_rules(
        telemetry
    )

    ids = {
        rule["id"]
        for rule in rules
    }

    assert "battery-low" in ids


# Critical battery

def test_critical_battery():

    telemetry = normal_telemetry()

    telemetry["battery_percentage"] = 15

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "battery-critical"
        and rule["severity"] == "CRITICAL"
        for rule in rules
    )


# Weak signal

def test_weak_signal():

    telemetry = normal_telemetry()

    telemetry["signal_strength"] = 35

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "signal-weak"
        for rule in rules
    )


# Critical signal

def test_critical_signal():

    telemetry = normal_telemetry()

    telemetry["signal_strength"] = 15

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "signal-critical"
        for rule in rules
    )


# GPS loss

def test_gps_loss():

    telemetry = normal_telemetry()

    telemetry["gps_fix"] = False

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "gps-loss"
        for rule in rules
    )


# Low GPS satellites

def test_low_gps_satellites():

    telemetry = normal_telemetry()

    telemetry["gps_satellites"] = 4

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "gps-weak"
        for rule in rules
    )


# High vibration

def test_high_vibration():

    telemetry = normal_telemetry()

    telemetry["vibration"] = 0.55

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "motor-vibration"
        for rule in rules
    )


# Critical vibration

def test_critical_vibration():

    telemetry = normal_telemetry()

    telemetry["vibration"] = 0.80

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "motor-vibration-critical"
        for rule in rules
    )


# High temperature

def test_high_temperature():

    telemetry = normal_telemetry()

    telemetry["temperature"] = 65

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "temperature-high"
        for rule in rules
    )


# Critical temperature

def test_critical_temperature():

    telemetry = normal_telemetry()

    telemetry["temperature"] = 75

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "temperature-critical"
        for rule in rules
    )


# Multi-fault

def test_multi_fault():

    telemetry = normal_telemetry()

    telemetry["battery_percentage"] = 20

    telemetry["signal_strength"] = 30

    telemetry["gps_fix"] = False

    telemetry["vibration"] = 0.60

    rules = explainable_rules(
        telemetry
    )

    assert any(
        rule["id"] == "multi-fault"
        for rule in rules
    )


# Correlated recommendation

def test_battery_signal_recommendation():

    telemetry = normal_telemetry()

    telemetry["battery_percentage"] = 20

    telemetry["signal_strength"] = 30

    analysis = analyze_health(
        telemetry
    )

    recommendation_ids = {
        recommendation["id"]
        for recommendation
        in analysis["recommendations"]
    }

    assert (
        "rec-priority-rth"
        in recommendation_ids
    )


# Missing telemetry

def test_missing_telemetry_does_not_crash():

    telemetry = normal_telemetry()

    telemetry["battery_percentage"] = None

    telemetry["signal_strength"] = None

    telemetry["temperature"] = None

    telemetry["vibration"] = None

    analysis = analyze_health(
        telemetry
    )

    assert "score" in analysis

    assert "components" in analysis

    assert "rules" in analysis

    assert "recommendations" in analysis


