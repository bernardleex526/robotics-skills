#!/usr/bin/env python3
"""Read-only audit of a legged whole-body-control model contract."""

from __future__ import annotations

import argparse
import importlib
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

from result_contract import emit_result, make_result, portable_path


SKILL = "robotics-legged-wbc"
MAX_INPUT_BYTES = 3 * 1024 * 1024
FALLBACK_STATES = {
    "support_hold",
    "damping_mode",
    "controlled_lowering",
    "sit_down",
    "freeze_reference",
}


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def nonnegative_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def positive_array(value: Any, length: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(positive_number(item) for item in value)
    )


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"WBC contract is not a file: {portable_path(path)}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"contract exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot parse WBC contract: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("WBC contract root must be a mapping")
    return data


def resolve_urdf(contract_path: Path, data: dict[str, Any]) -> Path:
    value = data.get("urdf")
    if not isinstance(value, str) or not value:
        raise ValueError("urdf must be a relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("urdf must be a safe relative path")
    path = contract_path.parent / relative
    if not path.is_file():
        raise ValueError(f"URDF is not a file: {portable_path(path)}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"URDF exceeds {MAX_INPUT_BYTES} bytes")
    return path


def inertia_positive(element: ET.Element) -> bool:
    try:
        ixx = float(element.get("ixx", "nan"))
        ixy = float(element.get("ixy", "nan"))
        ixz = float(element.get("ixz", "nan"))
        iyy = float(element.get("iyy", "nan"))
        iyz = float(element.get("iyz", "nan"))
        izz = float(element.get("izz", "nan"))
    except ValueError:
        return False
    values = (ixx, ixy, ixz, iyy, iyz, izz)
    if not all(math.isfinite(value) for value in values):
        return False
    minor2 = ixx * iyy - ixy * ixy
    determinant = (
        ixx * (iyy * izz - iyz * iyz)
        - ixy * (ixy * izz - iyz * ixz)
        + ixz * (ixy * iyz - iyy * ixz)
    )
    return ixx > 0 and minor2 > 0 and determinant > 0


def parse_urdf(path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ET.ParseError) as exc:
        raise ValueError(f"cannot parse URDF: {exc}") from exc
    if root.tag != "robot":
        raise ValueError("URDF root must be <robot>")
    findings: list[dict[str, str]] = []
    links: set[str] = set()
    link_mass: dict[str, float] = {}
    for link in root.findall("link"):
        name = link.get("name")
        if not name or name in links:
            raise ValueError("URDF link names must be unique and nonempty")
        links.add(name)
        inertial = link.find("inertial")
        if inertial is None:
            continue
        mass_element = inertial.find("mass")
        inertia_element = inertial.find("inertia")
        try:
            mass = float(mass_element.get("value", "nan")) if mass_element is not None else math.nan
        except ValueError:
            mass = math.nan
        if not positive_number(mass) or inertia_element is None or not inertia_positive(inertia_element):
            findings.append(
                fail("link_inertial", f"link {name} has invalid mass/inertia")
            )
        else:
            link_mass[name] = mass
    joints: dict[str, dict[str, Any]] = {}
    actuated_order: list[str] = []
    dynamic_children: set[str] = set()
    for joint in root.findall("joint"):
        name = joint.get("name")
        parent = joint.find("parent")
        child = joint.find("child")
        if (
            not name
            or name in joints
            or parent is None
            or child is None
            or parent.get("link") not in links
            or child.get("link") not in links
        ):
            raise ValueError("URDF joints need unique names and existing links")
        joint_type = joint.get("type")
        child_name = child.get("link")
        joints[name] = {"type": joint_type, "child": child_name}
        if joint_type not in {"fixed", "floating"}:
            actuated_order.append(name)
            dynamic_children.add(child_name)
            limit = joint.find("limit")
            required = ("effort", "velocity")
            if joint_type in {"revolute", "prismatic"}:
                required += ("lower", "upper")
            if limit is None:
                findings.append(fail("joint_limits", f"joint {name} has no limits"))
            else:
                for key in required:
                    try:
                        value = float(limit.get(key, "nan"))
                    except ValueError:
                        value = math.nan
                    if not math.isfinite(value) or (
                        key in {"effort", "velocity"} and value <= 0
                    ):
                        findings.append(
                            fail("joint_limits", f"joint {name} has invalid {key}")
                        )
    for child in dynamic_children:
        if child not in link_mass:
            findings.append(
                fail("link_inertial", f"dynamic link {child} has no valid inertial")
            )
    return {
        "links": links,
        "joints": joints,
        "actuated_order": actuated_order,
        "total_mass": sum(link_mass.values()),
    }, findings


def validate(
    data: dict[str, Any], model: dict[str, Any]
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    base = data.get("base")
    if (
        not isinstance(base, dict)
        or base.get("link") not in model["links"]
        or base.get("representation") != "floating_base_quaternion"
        or base.get("position_dimension") != 7
        or base.get("velocity_dimension") != 6
        or base.get("quaternion_order") != "xyzw"
    ):
        findings.append(
            fail(
                "base_representation",
                "base link, free-flyer dimensions and XYZW order are required",
            )
        )
    configured_order = data.get("actuated_joint_order")
    if configured_order != model["actuated_order"]:
        findings.append(
            fail(
                "actuated_joint_order",
                f"configured order {configured_order} must equal URDF order {model['actuated_order']}",
            )
        )
    expected_mass = data.get("expected_total_mass_kg")
    tolerance = data.get("mass_tolerance_kg")
    if (
        not positive_number(expected_mass)
        or not nonnegative_number(tolerance)
        or abs(model["total_mass"] - expected_mass) > tolerance
    ):
        findings.append(
            fail(
                "total_mass",
                f"URDF mass {model['total_mass']} kg does not meet declared expectation",
            )
        )
    contact_frames = data.get("contact_frames")
    if (
        not isinstance(contact_frames, list)
        or not contact_frames
        or len(set(contact_frames)) != len(contact_frames)
        or any(frame not in model["links"] for frame in contact_frames)
    ):
        findings.append(
            fail("contact_frames", "contact_frames must be unique existing links")
        )
        contact_frames = []
    estimator = data.get("state_estimator")
    if not isinstance(estimator, dict) or any(
        not positive_number(estimator.get(key))
        for key in ("rate_hz", "max_state_age_s")
    ) or estimator.get("quaternion_order") != "xyzw" or not isinstance(
        estimator.get("world_frame"), str
    ):
        findings.append(
            fail("state_estimator", "estimator rate, age, frame and XYZW order are required")
        )
    contact_estimator = data.get("contact_estimator")
    if (
        not isinstance(contact_estimator, dict)
        or contact_estimator.get("contact_order") != contact_frames
        or not positive_number(contact_estimator.get("max_contact_age_s"))
    ):
        findings.append(
            fail("contact_estimator", "contact order and maximum contact age are required")
        )
    controller = data.get("controller")
    if not isinstance(controller, dict) or any(
        not positive_number(controller.get(key))
        for key in ("rate_hz", "command_timeout_s")
    ):
        findings.append(
            fail("controller_timing", "controller rate and command timeout are required")
        )
    rate_contract = data.get("rate_contract")
    ratio = rate_contract.get("min_estimator_to_controller_ratio") if isinstance(rate_contract, dict) else None
    if (
        not positive_number(ratio)
        or not isinstance(estimator, dict)
        or not isinstance(controller, dict)
        or not positive_number(estimator.get("rate_hz"))
        or not positive_number(controller.get("rate_hz"))
        or estimator["rate_hz"] / controller["rate_hz"] < ratio
    ):
        findings.append(
            fail("rate_relationship", "estimator/controller rate ratio fails its declaration")
        )
    contacts = data.get("contacts")
    if not isinstance(contacts, list) or {
        item.get("frame") for item in contacts if isinstance(item, dict)
    } != set(contact_frames):
        findings.append(
            fail("contact_constraints", "one contact constraint per contact frame is required")
        )
    else:
        for item in contacts:
            if (
                not positive_number(item.get("friction_coefficient"))
                or not nonnegative_number(item.get("normal_force_min_N"))
                or not positive_number(item.get("normal_force_max_N"))
                or item["normal_force_max_N"] <= item["normal_force_min_N"]
            ):
                findings.append(
                    fail("contact_constraints", f"contact {item.get('frame')} bounds are invalid")
                )
    tasks = data.get("tasks")
    names: set[str] = set()
    if not isinstance(tasks, list) or not tasks:
        findings.append(fail("wbc_tasks", "tasks must be nonempty"))
    else:
        for item in tasks:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("name"), str)
                or not item["name"]
                or item["name"] in names
                or not isinstance(item.get("dimension"), int)
                or isinstance(item.get("dimension"), bool)
                or item["dimension"] <= 0
                or not positive_number(item.get("weight"))
                or not isinstance(item.get("priority"), int)
                or isinstance(item.get("priority"), bool)
                or item["priority"] < 0
            ):
                findings.append(fail("wbc_tasks", "task names/dimensions/weights/priorities are invalid"))
            else:
                names.add(item["name"])
    solver = data.get("solver")
    if not isinstance(solver, dict) or any(
        not positive_number(solver.get(key))
        for key in ("max_solve_time_s", "max_primal_residual", "max_dual_residual")
    ) or not isinstance(solver.get("max_iterations"), int) or isinstance(
        solver.get("max_iterations"), bool
    ) or solver["max_iterations"] <= 0:
        findings.append(
            fail("solver_gates", "solver time, iterations and residual gates are required")
        )
    limits = data.get("command_limits")
    joint_count = len(model["actuated_order"])
    if not isinstance(limits, dict) or any(
        not positive_array(limits.get(key), joint_count)
        for key in ("max_torque_Nm", "max_joint_velocity_rad_s", "max_position_error_rad")
    ):
        findings.append(
            fail("command_limits", "ordered positive command limit arrays are required")
        )
    fallback = data.get("fallback")
    for key in (
        "command_timeout_state",
        "estimator_invalid_state",
        "solver_failure_state",
        "degraded_state",
    ):
        if not isinstance(fallback, dict) or fallback.get(key) not in FALLBACK_STATES:
            findings.append(
                fail(key, f"fallback.{key} must name a reviewed bounded state")
            )
    return findings


def pinocchio_check(
    urdf: Path, expected_order: list[str]
) -> tuple[str, list[dict[str, str]], dict[str, Any], list[str]]:
    try:
        pin = importlib.import_module("pinocchio")
    except ModuleNotFoundError:
        return "skip", [], {}, ["optional Pinocchio module is unavailable"]
    try:
        model = pin.buildModelFromUrdf(str(urdf), pin.JointModelFreeFlyer())
        names = [
            str(name)
            for name in model.names
            if str(name) not in {"universe", "root_joint"}
        ]
    except Exception as exc:
        return "pass", [fail("pinocchio_model", f"Pinocchio could not build model: {exc}")], {}, []
    findings: list[dict[str, str]] = []
    if names != expected_order:
        findings.append(
            fail("pinocchio_joint_order", f"Pinocchio joints {names} differ from {expected_order}")
        )
    if model.nq != 7 + len(expected_order) or model.nv != 6 + len(expected_order):
        findings.append(
            fail("pinocchio_dimensions", f"Pinocchio nq/nv are {model.nq}/{model.nv}")
        )
    return "pass", findings, {
        "pinocchio_version": getattr(pin, "__version__", "unknown"),
        "pinocchio_nq": model.nq,
        "pinocchio_nv": model.nv,
    }, []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--pinocchio-check", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load_yaml(args.contract)
        urdf = resolve_urdf(args.contract, data)
        model, model_findings = parse_urdf(urdf)
        findings = model_findings + validate(data, model)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="wbc_contract",
            summary="WBC contract input is invalid",
            inputs=[portable_path(args.contract)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No complete WBC model check was performed."],
        )
        emit_result(result, args.output)
        return 2
    requested_status = "pass"
    environment: dict[str, Any] = {}
    limitations = [
        "Static admission does not prove estimator validity, real-time solve, balance, recovery, or hardware safety."
    ]
    if args.pinocchio_check and not findings:
        requested_status, pin_findings, discovered, pin_limits = pinocchio_check(
            urdf, model["actuated_order"]
        )
        findings.extend(pin_findings)
        environment.update(discovered)
        limitations.extend(pin_limits)
    result = make_result(
        skill=SKILL,
        check="wbc_contract",
        summary=(
            "WBC contract is admissible"
            if not findings and requested_status == "pass"
            else "WBC contract passed; optional Pinocchio check was skipped"
            if not findings
            else "WBC contract failed admission"
        ),
        inputs=[portable_path(args.contract)],
        environment=environment,
        metrics={
            "actuated_joint_count": {
                "value": len(model["actuated_order"]),
                "unit": "joints",
                "direction": "informational",
            },
            "contact_count": {
                "value": len(data.get("contact_frames", [])),
                "unit": "contacts",
                "direction": "informational",
            },
            "urdf_total_mass_kg": {
                "value": model["total_mass"],
                "unit": "kg",
                "direction": "informational",
            },
        },
        findings=findings,
        limitations=limitations,
        requested_status=requested_status,
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
