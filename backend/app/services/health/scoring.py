"""
IDHTM Health Scoring
--------------------

Converts telemetry values into component health scores from 0-100.

Current weights:

    Battery        20%
    Motors         25%
    GPS            20%
    Sensors        15%
    Communication 20%

This is deterministic scoring, NOT ML.
"""

from typing import Any


# Utility

def clamp(value: float, minimum: float = 0, maximum: float = 100) -> int:
    """
    Keeps a number between minimum and maximum.

    Example:

        clamp(120) -> 100
        clamp(-10) -> 0
    """

    return round(max(minimum, min(maximum, value)))


# Battery score

def battery_score(telemetry: dict[str, Any]) -> int:
    battery = telemetry.get("battery_percentage")

    if battery is None:
        # Unknown is represented as a neutral score for now.
        # We do not want stale telemetry to immediately create
        # a false critical health score.
        return 50

    return clamp(battery)


# Motor score

def motor_score(telemetry: dict[str, Any]) -> int:
    vibration = telemetry.get("vibration")

    if vibration is None:
        return 50

    # 0.0 g = excellent.
    # 0.65 g = critical boundary.
    score = 100 - (vibration / 0.65) * 100

    return clamp(score)


# GPS score

def gps_score(telemetry: dict[str, Any]) -> int:
    gps_fix = telemetry.get("gps_fix")
    satellites = telemetry.get("gps_satellites")

    if gps_fix is None:
        return 50

    if gps_fix is False:
        return 20

    if satellites is None:
        return 80

    if satellites < 6:
        return 60

    if satellites < 10:
        return 80

    return 98


# Sensor score

def sensor_score(telemetry: dict[str, Any]) -> int:
    temperature = telemetry.get("temperature")

    if temperature is None:
        return 50

    if temperature >= 70:
        return 20

    if temperature > 58:
        # Gradually reduce score between 58 and 70.
        score = 100 - ((temperature - 58) / 12) * 80
        return clamp(score)

    return 98


# Communication score

def communication_score(
    telemetry: dict[str, Any],
) -> int:

    signal = telemetry.get("signal_strength")

    if signal is None:
        return 50

    return clamp(signal)


# Component health

def component_health(
    telemetry: dict[str, Any],
) -> dict[str, int]:
    """
    Calculates health for each major drone subsystem.
    """

    return {
        "battery": battery_score(telemetry),
        "motors": motor_score(telemetry),
        "gps": gps_score(telemetry),
        "sensors": sensor_score(telemetry),
        "communication": communication_score(telemetry),
    }


# Overall health

def calculate_health(
    telemetry: dict[str, Any],
) -> int:
    """
    Calculates the overall drone health score.

    Weighted average:

        Battery        20%
        Motors         25%
        GPS            20%
        Sensors        15%
        Communication 20%
    """

    components = component_health(telemetry)

    score = (
        components["battery"] * 0.20
        + components["motors"] * 0.25
        + components["gps"] * 0.20
        + components["sensors"] * 0.15
        + components["communication"] * 0.20
    )

    return clamp(score)