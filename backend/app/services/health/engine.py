
"""
IDHTM Health Intelligence Engine
--------------------------------

This file combines:

    1. Rule detection
    2. Component health scoring
    3. Overall health score
    4. Operational recommendations

Architecture:

    Telemetry
        ↓
    evaluate_rules()
        ↓
    component_health()
        ↓
    calculate_health()
        ↓
    generate_recommendations()
        ↓
    Health Analysis
"""

from typing import Any

from app.services.health.rules import evaluate_rules
from app.services.health.scoring import (
    calculate_health,
    component_health,
)
from app.services.health.recommendations import (
    generate_recommendations,
)


def explainable_rules(
    telemetry: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Backward-compatible function used by existing API endpoints.

    Returns only currently active rules.
    """

    return evaluate_rules(telemetry)


def analyze_health(
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    """
    Runs the complete health intelligence pipeline.

    Returns:

        score
        components
        rules
        recommendations
    """

    rules = evaluate_rules(telemetry)

    components = component_health(telemetry)

    score = calculate_health(telemetry)

    recommendations = generate_recommendations(
        telemetry,
        rules,
    )

    return {
        "score": score,
        "components": components,
        "rules": rules,
        "recommendations": recommendations,
    }


# Re-export these functions so existing imports continue working.
__all__ = [
    "calculate_health",
    "component_health",
    "explainable_rules",
    "analyze_health",
]





















# from typing import Any


# def component_health(telemetry: dict[str, Any]) -> dict[str, int]:
#     battery = round(max(0, min(100, telemetry["battery_percentage"] + 10)))
#     motors = round(max(0, min(100, 100 - telemetry["vibration"] * 42)))
#     gps = 98 if telemetry["gps_fix"] else 20
#     sensors = round(max(0, min(100, 96 - max(0, telemetry["temperature"] - 55) * 1.4)))
#     communication = round(max(0, min(100, telemetry["signal_strength"])))
#     return {
#         "battery": battery,
#         "motors": motors,
#         "gps": gps,
#         "sensors": sensors,
#         "communication": communication,
#     }


# def calculate_health(telemetry: dict[str, Any]) -> int:
#     c = component_health(telemetry)
#     return round(
#         c["battery"] * 0.20
#         + c["motors"] * 0.25
#         + c["gps"] * 0.20
#         + c["sensors"] * 0.15
#         + c["communication"] * 0.20
#     )


# def explainable_rules(telemetry: dict[str, Any]) -> list[dict[str, Any]]:
#     rules = []
#     # if telemetry["battery_percentage"] < 30:
#     #     rules.append(
#     #         {
#     #             "id": "battery-low",
#     #             "severity": "WARNING",
#     #             "source": "Battery rule",
#     #             "title": "Battery reserve is low",
#     #             "explanation": "Remaining reserve is approaching the configured mission threshold.",
#     #             "metric": f"{telemetry['battery_percentage']:.0f}%",
#     #             "recommendation": "Plan a return and recharge the battery before the next flight.",
#     #         }
#     #     )
#     if telemetry["battery_percentage"] < 20:
#         rules.append(
#             {
#                 "id": "battery-critical",
#                 "severity": "CRITICAL",
#                 "source": "Battery rule",
#                 "title": "Battery critically low",
#                 "explanation": "Battery reserve has fallen below the critical threshold.",
#                 "metric": f"{telemetry["battery_percentage"]:.0f}%",
#                 "recommendation": "Immediately initiate Return-To-Home or land safely.",
#             }
#         )
#     elif telemetry["battery_percentage"] < 30:
#         rules.append(
#             {
#                 "id": "battery-low",
#                 "severity": "WARNING",
#                 "source": "Battery rule",
#                 "title": "Battery reserve is low",
#                 "explanation": "Remaining battery is approaching the configured mission reserve threshold.",
#                 "metric": f"{telemetry["battery_percentage"]:.0f}%",
#                 "recommendation": "Plan Return-To-Home and recharge the battery.",
#             }
#         )

#     if telemetry["signal_strength"] < 25:
#         rules.append(
#             {
#                 "id": "signal-critical",
#                 "severity": "CRITICAL",
#                 "source": "Communication rule",
#                 "title": "Communication link critically weak",
#                 "explanation": (
#                     "Communication strength has fallen to a critical level."
#                 ),
#                 "metric": f"{telemetry["signal_strength"]:.0f}%",
#                 "recommendation": (
#                     "Initiate Return-To-Home if communication continues degrading."
#                 ),
#             }
#         )

#     elif telemetry["signal_strength"] < 45:
#         rules.append(
#             {
#                 "id": "signal-weak",
#                 "severity": "WARNING",
#                 "source": "Communication rule",
#                 "title": "Communication signal degrading",
#                 "explanation": ("Communication link reliability is decreasing."),
#                 "metric": f"{telemetry["signal_strength"]:.0f}%",
#                 "recommendation": "Prepare Return-To-Home.",
#             }
#         )
#     if telemetry["vibration"] > 0.65:
#         rules.append(
#             {
#                 "id": "motor-vibration-critical",
#                 "severity": "CRITICAL",
#                 "source": "Motor rule",
#                 "title": "Motor vibration critically high",
#                 "explanation": (
#                     "Vibration has exceeded the critical inspection threshold."
#                 ),
#                 "metric": f"{telemetry["vibration"]:.2f} g",
#                 "recommendation": (
#                     "Land safely and inspect motor, propeller and bearing condition."
#                 ),
#             }
#         )
#     elif telemetry["vibration"] > 0.48:
#         rules.append(
#             {
#                 "id": "motor-vibration",
#                 "severity": "WARNING",
#                 "source": "Motor rule",
#                 "title": "Motor vibration above baseline",
#                 "explanation": (
#                     "Motor vibration has crossed the bearing inspection threshold."
#                 ),
#                 "metric": f"{telemetry["vibration"]:.2f} g",
#                 "recommendation": ("Inspect motor bearing and propeller condition."),
#             }
#         )
#     if not telemetry["gps_fix"]:
#         rules.append(
#             {
#                 "id": "gps-loss",
#                 "severity": "CRITICAL",
#                 "source": "GPS rule",
#                 "title": "GPS fix unavailable",
#                 "explanation": (
#                     "The aircraft is not receiving a valid position solution."
#                 ),
#                 "metric": f"{telemetry["gps_satellites"]} satellites",
#                 "recommendation": (
#                     "Hold position if safe and initiate Return-To-Home."
#                 ),
#             }
#         )
#     if telemetry["gps_satellites"] < 6:
#         rules.append(
#             {
#                 "id": "gps-weak",
#                 "severity": "WARNING",
#                 "source": "GPS rule",
#                 "title": "Low GPS satellite count",
#                 "explanation": (
#                     "The number of visible satellites is below the preferred "
#                     "operating level."
#                 ),
#                 "metric": f"{telemetry["gps_satellites"]} satellites",
#                 "recommendation": (
#                     "Monitor GPS quality and avoid aggressive navigation."
#                 ),
#             }
#         )
#     if telemetry["temperature"] > 70:
#         rules.append(
#             {
#                 "id": "temperature-critical",
#                 "severity": "CRITICAL",
#                 "source": "Temperature rule",
#                 "title": "Temperature critically high",
#                 "explanation": (
#                     "Temperature has entered a potentially unsafe operating range."
#                 ),
#                 "metric": f"{telemetry["temperature"]:.0f} °C",
#                 "recommendation": ("Reduce load and land as soon as safely possible."),
#             }
#         )
#     elif telemetry["temperature"] > 50:
#         rules.append(
#             {
#                 "id": "temperature-high",
#                 "severity": "WARNING",
#                 "source": "Temperature rule",
#                 "title": "Temperature above operating baseline",
#                 "explanation": ("Thermal load is above the normal operating envelope."),
#                 "metric": f"{telemetry["temperature"]:.0f} °C",
#                 "recommendation": (
#                     "Reduce load and inspect cooling before another extended flight."
#                 ),
#             }
#         )
#     return rules
