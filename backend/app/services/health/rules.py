"""
IDHTM Health Rule Engine
------------------------

This file contains deterministic, explainable rules for detecting
known drone health problems.

IMPORTANT:
    This is NOT machine learning.

    Each rule checks a telemetry value against a known threshold.

Example:

    battery_percentage < 30
            ↓
        WARNING
            ↓
      Return-To-Home

The advantage of rule-based intelligence is that every alert can
be explained to the operator.
"""

from typing import Any


# ---------------------------------------------------------
# Helper function
# ---------------------------------------------------------

def is_available(value: Any) -> bool:
    """
    Returns True when a telemetry value is actually available.

    The telemetry pipeline uses None when a value becomes stale.

    We MUST NOT treat None as 0.

    Example:

        signal_strength = None

    means:

        "We don't currently know the signal strength."

    It does NOT mean:

        "Signal strength is 0."
    """

    return value is not None


# ---------------------------------------------------------
# Battery rule
# ---------------------------------------------------------

def battery_rule(telemetry: dict[str, Any]) -> dict[str, Any] | None:
    """
    Detects low battery conditions.
    """

    battery = telemetry.get("battery_percentage")

    # No battery information available.
    if battery is None:
        return None

    if battery < 20:
        return {
            "id": "battery-critical",
            "severity": "CRITICAL",
            "source": "Battery rule",
            "title": "Battery critically low",
            "explanation": (
                "Battery reserve has fallen below the critical "
                "operating threshold."
            ),
            "metric": f"{battery:.0f}%",
            "recommendation": (
                "Immediately initiate Return-To-Home or land safely."
            ),
        }

    if battery < 30:
        return {
            "id": "battery-low",
            "severity": "WARNING",
            "source": "Battery rule",
            "title": "Battery reserve is low",
            "explanation": (
                "Remaining battery is approaching the configured "
                "mission reserve threshold."
            ),
            "metric": f"{battery:.0f}%",
            "recommendation": (
                "Plan Return-To-Home and recharge the battery."
            ),
        }

    return None


# ---------------------------------------------------------
# Communication rule
# ---------------------------------------------------------

def signal_rule(telemetry: dict[str, Any]) -> dict[str, Any] | None:
    """
    Detects weak communication signal.
    """

    signal = telemetry.get("signal_strength")

    if signal is None:
        return None

    if signal < 25:
        return {
            "id": "signal-critical",
            "severity": "CRITICAL",
            "source": "Communication rule",
            "title": "Communication link critically weak",
            "explanation": (
                "Communication strength has fallen to a "
                "critical level."
            ),
            "metric": f"{signal:.0f}%",
            "recommendation": (
                "Initiate Return-To-Home if the communication link "
                "continues degrading."
            ),
        }

    if signal < 45:
        return {
            "id": "signal-weak",
            "severity": "WARNING",
            "source": "Communication rule",
            "title": "Communication signal degrading",
            "explanation": (
                "Communication link reliability is decreasing."
            ),
            "metric": f"{signal:.0f}%",
            "recommendation": "Prepare Return-To-Home.",
        }

    return None


# ---------------------------------------------------------
# GPS rule
# ---------------------------------------------------------

def gps_rule(telemetry: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Detects GPS loss and weak GPS reception.

    Returns a LIST because GPS loss and low satellite count
    can both be relevant.
    """

    rules: list[dict[str, Any]] = []

    gps_fix = telemetry.get("gps_fix")
    satellites = telemetry.get("gps_satellites")

    # GPS fix unavailable.
    if gps_fix is False:

        satellite_text = (
            f"{satellites} satellites"
            if satellites is not None
            else "satellite count unavailable"
        )

        rules.append(
            {
                "id": "gps-loss",
                "severity": "CRITICAL",
                "source": "GPS rule",
                "title": "GPS fix unavailable",
                "explanation": (
                    "The aircraft is not currently receiving "
                    "a valid GPS position solution."
                ),
                "metric": satellite_text,
                "recommendation": (
                    "Hold position if safe and initiate Return-To-Home."
                ),
            }
        )

    # Weak satellite coverage.
    if satellites is not None and satellites < 6:

        rules.append(
            {
                "id": "gps-weak",
                "severity": "WARNING",
                "source": "GPS rule",
                "title": "Low GPS satellite count",
                "explanation": (
                    "The number of visible satellites is below "
                    "the preferred operating level."
                ),
                "metric": f"{satellites} satellites",
                "recommendation": (
                    "Monitor GPS quality and avoid aggressive navigation."
                ),
            }
        )

    return rules


# ---------------------------------------------------------
# Vibration rule
# ---------------------------------------------------------

def vibration_rule(telemetry: dict[str, Any]) -> dict[str, Any] | None:
    """
    Detects excessive vibration.

    vibration is expected to be represented in g.
    """

    vibration = telemetry.get("vibration")

    if vibration is None:
        return None

    if vibration > 0.65:
        return {
            "id": "motor-vibration-critical",
            "severity": "CRITICAL",
            "source": "Motor rule",
            "title": "Motor vibration critically high",
            "explanation": (
                "Measured acceleration variation has exceeded "
                "the critical mechanical threshold."
            ),
            "metric": f"{vibration:.2f} g",
            "recommendation": (
                "Land safely and inspect motor, propeller and "
                "bearing condition."
            ),
        }

    if vibration > 0.48:
        return {
            "id": "motor-vibration",
            "severity": "WARNING",
            "source": "Motor rule",
            "title": "Motor vibration above baseline",
            "explanation": (
                "Vibration has crossed the configured "
                "mechanical inspection threshold."
            ),
            "metric": f"{vibration:.2f} g",
            "recommendation": (
                "Inspect motor and propeller condition."
            ),
        }

    return None


# ---------------------------------------------------------
# Temperature rule
# ---------------------------------------------------------

def temperature_rule(
    telemetry: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Detects excessive temperature.
    """

    temperature = telemetry.get("temperature")

    if temperature is None:
        return None

    if temperature > 70:
        return {
            "id": "temperature-critical",
            "severity": "CRITICAL",
            "source": "Temperature rule",
            "title": "Temperature critically high",
            "explanation": (
                "Temperature has entered a potentially unsafe "
                "operating range."
            ),
            "metric": f"{temperature:.0f} °C",
            "recommendation": (
                "Reduce load and land as soon as safely possible."
            ),
        }

    if temperature > 58:
        return {
            "id": "temperature-high",
            "severity": "WARNING",
            "source": "Temperature rule",
            "title": "Temperature above operating baseline",
            "explanation": (
                "Thermal load is above the normal operating envelope."
            ),
            "metric": f"{temperature:.0f} °C",
            "recommendation": (
                "Reduce load and inspect cooling before another "
                "extended flight."
            ),
        }

    return None


# ---------------------------------------------------------
# Multi-fault rule
# ---------------------------------------------------------

def multi_fault_rule(
    telemetry: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Detects simultaneous abnormal conditions.

    This is useful because multiple moderate problems can
    together represent a much more dangerous situation.
    """

    fault_count = 0

    battery = telemetry.get("battery_percentage")
    signal = telemetry.get("signal_strength")
    gps = telemetry.get("gps_fix")
    vibration = telemetry.get("vibration")
    temperature = telemetry.get("temperature")

    if battery is not None and battery < 30:
        fault_count += 1

    if signal is not None and signal < 45:
        fault_count += 1

    if gps is False:
        fault_count += 1

    if vibration is not None and vibration > 0.48:
        fault_count += 1

    if temperature is not None and temperature > 58:
        fault_count += 1

    if fault_count >= 3:
        return {
            "id": "multi-fault",
            "severity": "CRITICAL",
            "source": "Multi-fault correlation",
            "title": "Multiple drone health risks detected",
            "explanation": (
                f"{fault_count} independent health conditions "
                "are currently outside the normal operating envelope."
            ),
            "metric": f"{fault_count} active fault conditions",
            "recommendation": (
                "Prioritize safe flight termination and inspect "
                "the affected systems before another flight."
            ),
        }

    return None


# ---------------------------------------------------------
# Main rule collection
# ---------------------------------------------------------

def evaluate_rules(
    telemetry: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Runs every health rule.

    This function is the single entry point used by the
    Health Engine.
    """

    rules: list[dict[str, Any]] = []

    battery = battery_rule(telemetry)
    if battery:
        rules.append(battery)

    signal = signal_rule(telemetry)
    if signal:
        rules.append(signal)

    rules.extend(gps_rule(telemetry))

    vibration = vibration_rule(telemetry)
    if vibration:
        rules.append(vibration)

    temperature = temperature_rule(telemetry)
    if temperature:
        rules.append(temperature)

    multi_fault = multi_fault_rule(telemetry)
    if multi_fault:
        rules.append(multi_fault)

    return rules