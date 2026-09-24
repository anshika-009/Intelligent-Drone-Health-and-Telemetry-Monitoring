import sys
from datetime import datetime, timezone

from pymavlink.dialects.v20 import common as mavlink2

sys.path.insert(0, "telemetry_pipeline")

from src.orchestrator.pipeline_runner import PipelineRunner
from src.integration.backend_adapter import adapt_to_backend
from app.services.rule_engine import IDHTMRuleEngine


def test_pipeline_telemetry_triggers_ai_alerts():
    mav = mavlink2.MAVLink(None)

    # Dangerous battery: 10.3 V
    battery_msg = mav.sys_status_encode(
        onboard_control_sensors_present=0,
        onboard_control_sensors_enabled=0,
        onboard_control_sensors_health=0,
        load=500,
        voltage_battery=10300,
        current_battery=1500,
        battery_remaining=20,
        drop_rate_comm=0,
        errors_comm=0,
        errors_count1=0,
        errors_count2=0,
        errors_count3=0,
        errors_count4=0,
    )

    # Dangerous acceleration:
    # sqrt(20^2 + 20^2 + 20^2) = 34.64
    imu_msg = mav.raw_imu_encode(
        time_usec=0,
        xacc=2039,
        yacc=2039,
        zacc=2039,
        xgyro=0,
        ygyro=0,
        zgyro=0,
        xmag=0,
        ymag=0,
        zmag=0,
        id=0,
        temperature=3500,
    )

    # Encode both messages into a temporary MAVLink log.
    import tempfile
    import struct
    import time

    with tempfile.NamedTemporaryFile(suffix=".tlog") as f:
        for msg in [battery_msg, imu_msg]:
            encoded = msg.pack(mav)
            f.write(struct.pack(">Q", int(time.time() * 1e6)))
            f.write(encoded)

        f.flush()

        runner = PipelineRunner(f.name)
        runner.start()

        assert runner.poll_once()
        assert runner.poll_once()

        state = runner.get_state()
        event = adapt_to_backend(state)

        engine = IDHTMRuleEngine()

        battery_eval = engine.evaluate_battery_state(event["battery_voltage"])
        motor_eval = engine.evaluate_motor_health(
            event["ax"],
            event["ay"],
            event["az"],
        )

        assert battery_eval["status"] == "CRITICAL"
        assert battery_eval["action"] == "Trigger automated RTL"

        assert motor_eval["vibration_alert"] is True
        assert motor_eval["risk"] == "Severe mechanical failure risk"

        runner.stop()
