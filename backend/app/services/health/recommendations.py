"""
IDHTM Recommendation Engine
---------------------------

This module converts detected rules into operational recommendations.

Rules answer:

    "What is wrong?"

Recommendations answer:

    "What should the operator do?"

This is still deterministic rule-based intelligence.
"""

from typing import Any


def generate_recommendations(
    telemetry: dict[str, Any],
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Generates unique recommendations from active health rules.
    """

    recommendations: list[dict[str, Any]] = []

    rule_ids = {
        rule.get("id")
        for rule in rules
    }

    # Battery + signal correlation

    if (
        "battery-low" in rule_ids
        or "battery-critical" in rule_ids
    ) and (
        "signal-weak" in rule_ids
        or "signal-critical" in rule_ids
    ):

        recommendations.append(
            {
                "id": "rec-priority-rth",
                "priority": "CRITICAL",
                "title": "Prioritize Return-To-Home",
                "reason": (
                    "Battery reserve and communication quality "
                    "are both degraded."
                ),
                "action": (
                    "Prioritize Return-To-Home instead of "
                    "continuing the mission."
                ),
            }
        )
    # GPS + signal correlation

    if (
        "gps-loss" in rule_ids
        and (
            "signal-weak" in rule_ids
            or "signal-critical" in rule_ids
        )
    ):

        recommendations.append(
            {
                "id": "rec-navigation-risk",
                "priority": "CRITICAL",
                "title": "Navigation reliability degraded",
                "reason": (
                    "GPS position information and communication "
                    "quality are both degraded."
                ),
                "action": (
                    "Avoid autonomous navigation until the "
                    "navigation and communication systems recover."
                ),
            }
        )

    # Vibration + temperature

    vibration_active = (
        "motor-vibration" in rule_ids
        or "motor-vibration-critical" in rule_ids
    )

    temperature_active = (
        "temperature-high" in rule_ids
        or "temperature-critical" in rule_ids
    )

    if vibration_active and temperature_active:

        recommendations.append(
            {
                "id": "rec-propulsion-stress",
                "priority": "CRITICAL",
                "title": "Possible propulsion stress",
                "reason": (
                    "High vibration and elevated temperature "
                    "are occurring together."
                ),
                "action": (
                    "Reduce load, land safely and inspect "
                    "motors, propellers and bearings."
                ),
            }
        )

    # Multi-fault

    if "multi-fault" in rule_ids:

        recommendations.append(
            {
                "id": "rec-multi-fault",
                "priority": "CRITICAL",
                "title": "Terminate mission if safe",
                "reason": (
                    "Multiple independent health conditions "
                    "are simultaneously abnormal."
                ),
                "action": (
                    "Prioritize safe landing or Return-To-Home "
                    "and perform a complete post-flight inspection."
                ),
            }
        )

    # Add rule-level recommendations

    for rule in rules:

        recommendation = rule.get("recommendation")

        if not recommendation:
            continue

        # Don't duplicate recommendations already generated
        # by a correlation rule.
        existing_actions = {
            item["action"]
            for item in recommendations
        }

        if recommendation in existing_actions:
            continue

        recommendations.append(
            {
                "id": f"rule-rec-{rule['id']}",
                "priority": rule["severity"],
                "title": rule["title"],
                "reason": rule["explanation"],
                "action": recommendation,
            }
        )

    return recommendations