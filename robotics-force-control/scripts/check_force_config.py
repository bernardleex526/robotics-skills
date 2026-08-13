#!/usr/bin/env python3
"""Statically audit a force-control configuration without commanding a robot."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import yaml

from result_contract import emit_result, make_result, portable_path


SKILL = "robotics-force-control"
AXES = ("fx", "fy", "fz", "tx", "ty", "tz")
MAX_INPUT_BYTES = 2 * 1024 * 1024
GRAVITY_SAFE_STATES = {
    "gravity_compensated_hold",
    "controlled_lowering",
    "support_hold",
}
NON_GRAVITY_SAFE_STATES = GRAVITY_SAFE_STATES | {
    "controlled_stop",
    "zero_command",
}


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def finite_array(
    value: Any, length: int, positive: bool = False, nonnegative: bool = False
) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(item)
            and (not positive or item > 0)
            and (not nonnegative or item >= 0)
            for item in value
        )
    )


def positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"force configuration is not a file: {portable_path(path)}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"configuration exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot parse force configuration: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("force configuration root must be a mapping")
    return data


def validate(data: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    interfaces = data.get("interfaces")
    if (
        not isinstance(interfaces, dict)
        or interfaces.get("wrench_axes") != list(AXES)
    ):
        findings.append(
            fail(
                "wrench_interface_mapping",
                "interfaces.wrench_axes must be [fx, fy, fz, tx, ty, tz]",
            )
        )
    frames = data.get("frames")
    if not isinstance(frames, dict) or any(
        not isinstance(frames.get(name), str) or not frames[name]
        for name in ("sensor", "control", "world", "gravity")
    ):
        findings.append(
            fail("force_frames", "sensor/control/world/gravity frames are required")
        )
    kinematics = data.get("kinematics")
    if not isinstance(kinematics, dict) or any(
        not isinstance(kinematics.get(name), str) or not kinematics[name]
        for name in ("package", "plugin")
    ):
        findings.append(
            fail("kinematics_plugin", "kinematics package and plugin are required")
        )
    selected = data.get("selected_axes")
    if (
        not isinstance(selected, list)
        or len(selected) != 6
        or any(not isinstance(value, bool) for value in selected)
        or not any(selected)
    ):
        findings.append(
            fail("selected_axes", "selected_axes needs six booleans and one active axis")
        )
    admittance = data.get("admittance")
    if not isinstance(admittance, dict):
        findings.append(fail("admittance", "admittance mapping is required"))
    else:
        if not finite_array(admittance.get("mass"), 6, positive=True):
            findings.append(fail("admittance_mass", "six positive masses are required"))
        if not finite_array(admittance.get("damping"), 6, positive=True):
            findings.append(
                fail("admittance_damping", "six positive damping values are required")
            )
        if not finite_array(admittance.get("stiffness"), 6, nonnegative=True):
            findings.append(
                fail("admittance_stiffness", "six nonnegative stiffness values are required")
            )
    payload = data.get("payload")
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("mass_kg"), (int, float))
        or isinstance(payload.get("mass_kg"), bool)
        or not math.isfinite(payload["mass_kg"])
        or payload["mass_kg"] < 0
        or not finite_array(payload.get("cog_m"), 3)
        or not positive_number(payload.get("gravity_m_s2"))
    ):
        findings.append(
            fail("payload_gravity", "payload mass, CoG and gravity magnitude are required")
        )
    filters = data.get("filters")
    if not isinstance(filters, dict) or any(
        not positive_number(filters.get(name))
        for name in ("wrench_cutoff_hz", "command_cutoff_hz")
    ):
        findings.append(
            fail("filter_contract", "positive wrench/command cutoff values are required")
        )
    timing = data.get("timing")
    if not isinstance(timing, dict) or any(
        not positive_number(timing.get(name))
        for name in ("sensor_rate_hz", "control_rate_hz", "max_message_age_s")
    ):
        findings.append(
            fail("timing_contract", "sensor/control rate and maximum message age are required")
        )
    limits = data.get("limits")
    if (
        not isinstance(limits, dict)
        or not finite_array(limits.get("max_force_N"), 3, positive=True)
        or not finite_array(limits.get("max_torque_Nm"), 3, positive=True)
        or not finite_array(limits.get("command_slew_per_s"), 6, positive=True)
    ):
        findings.append(
            fail("force_limits", "force, torque and six-axis slew limits are required")
        )
    watchdog = data.get("watchdog")
    if not isinstance(watchdog, dict) or not positive_number(
        watchdog.get("timeout_s")
    ):
        findings.append(fail("watchdog", "a positive watchdog timeout is required"))
    gravity_loaded = data.get("gravity_loaded")
    if not isinstance(gravity_loaded, bool):
        findings.append(fail("gravity_loaded", "gravity_loaded must be boolean"))
    safe_state = watchdog.get("timeout_safe_state") if isinstance(watchdog, dict) else None
    allowed = GRAVITY_SAFE_STATES if gravity_loaded is True else NON_GRAVITY_SAFE_STATES
    if safe_state not in allowed:
        findings.append(
            fail(
                "timeout_safe_state",
                "timeout_safe_state is missing or not gravity-aware for this mechanism",
            )
        )
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load(args.config)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="force_config",
            summary="force configuration input is invalid",
            inputs=[portable_path(args.config)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No force-control configuration check was performed."],
        )
        emit_result(result, args.output)
        return 2
    findings = validate(data)
    result = make_result(
        skill=SKILL,
        check="force_config",
        summary=(
            "force-control configuration is admissible"
            if not findings
            else "force-control configuration failed admission"
        ),
        inputs=[portable_path(args.config)],
        environment={"baseline": "ROS 2 Humble"},
        metrics={
            "selected_axis_count": {
                "value": sum(data.get("selected_axes", []))
                if isinstance(data.get("selected_axes"), list)
                else 0,
                "unit": "axes",
                "direction": "informational",
            }
        },
        findings=findings,
        limitations=[
            "Static admission does not prove closed-loop stability, contact safety, or hardware protective functions."
        ],
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
