#!/usr/bin/env python3
"""Cross-check a portable MoveIt 2 configuration snapshot."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

from result_contract import emit_result, make_result


SKILL = "robotics-manipulation"
MAX_FILE_BYTES = 5 * 1024 * 1024
REQUIRED_KEYS = {
    "urdf",
    "srdf",
    "kinematics",
    "joint_limits",
    "planning_pipelines",
    "moveit_controllers",
}


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def load_text(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"required file is missing: {path}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"required file exceeds {MAX_FILE_BYTES} bytes: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(load_text(path))
    except yaml.YAMLError as exc:
        raise ValueError(f"cannot parse YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def resolve_snapshot(directory: Path) -> dict[str, Path]:
    if not directory.is_dir():
        raise ValueError(f"snapshot is not a directory: {directory}")
    manifest = load_yaml(directory / "manifest.yaml")
    missing = REQUIRED_KEYS - set(manifest)
    if missing:
        raise ValueError(f"manifest missing keys: {sorted(missing)}")
    paths: dict[str, Path] = {}
    for key in REQUIRED_KEYS:
        value = manifest[key]
        if not isinstance(value, str) or not value:
            raise ValueError(f"manifest.{key} must be a relative path")
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"manifest.{key} is not a safe relative path")
        paths[key] = directory / relative
    return paths


def parse_xml(path: Path) -> ET.Element:
    try:
        return ET.fromstring(load_text(path))
    except ET.ParseError as exc:
        raise ValueError(f"cannot parse XML {path}: {exc}") from exc


def urdf_model(root: ET.Element) -> dict[str, Any]:
    if root.tag != "robot":
        raise ValueError("URDF root must be <robot>")
    links = {element.get("name") for element in root.findall("link")}
    if None in links or not links:
        raise ValueError("URDF links need nonempty names")
    joints: dict[str, dict[str, Any]] = {}
    for element in root.findall("joint"):
        name = element.get("name")
        parent = element.find("parent")
        child = element.find("child")
        if (
            not name
            or name in joints
            or parent is None
            or child is None
            or not parent.get("link")
            or not child.get("link")
        ):
            raise ValueError("URDF joint names and parent/child links must be unique")
        joints[name] = {
            "type": element.get("type"),
            "parent": parent.get("link"),
            "child": child.get("link"),
            "mimic": element.find("mimic") is not None,
            "limit": element.find("limit"),
        }
    interfaces: dict[str, dict[str, set[str]]] = {}
    for element in root.findall(".//ros2_control/joint"):
        name = element.get("name")
        if not name:
            continue
        interfaces[name] = {
            "command": {
                item.get("name")
                for item in element.findall("command_interface")
                if item.get("name")
            },
            "state": {
                item.get("name")
                for item in element.findall("state_interface")
                if item.get("name")
            },
        }
    return {"links": links, "joints": joints, "interfaces": interfaces}


def chain_joints(
    model: dict[str, Any], base: str, tip: str
) -> list[str] | None:
    by_child = {
        joint["child"]: name for name, joint in model["joints"].items()
    }
    current = tip
    reverse: list[str] = []
    seen: set[str] = set()
    while current != base:
        if current in seen or current not in by_child:
            return None
        seen.add(current)
        name = by_child[current]
        reverse.append(name)
        current = model["joints"][name]["parent"]
    return list(reversed(reverse))


def srdf_model(root: ET.Element, model: dict[str, Any]) -> tuple[dict[str, set[str]], set[str], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    groups: dict[str, set[str]] = {}
    for group in root.findall("group"):
        name = group.get("name")
        if not name:
            findings.append(fail("srdf_group", "SRDF group has no name"))
            continue
        members = {
            item.get("name")
            for item in group.findall("joint")
            if item.get("name")
        }
        for chain in group.findall("chain"):
            base, tip = chain.get("base_link"), chain.get("tip_link")
            if not base or not tip:
                findings.append(fail("srdf_chain", f"group {name} has incomplete chain"))
                continue
            resolved = chain_joints(model, base, tip)
            if resolved is None:
                findings.append(
                    fail("srdf_chain", f"group {name} chain {base}->{tip} is invalid")
                )
            else:
                members.update(resolved)
        unknown = members - set(model["joints"])
        if unknown:
            findings.append(
                fail("srdf_joint", f"group {name} has unknown joints {sorted(unknown)}")
            )
        groups[name] = members
    passive = {
        item.get("name")
        for item in root.findall("passive_joint")
        if item.get("name")
    }
    for end_effector in root.findall("end_effector"):
        if (
            end_effector.get("group") not in groups
            or end_effector.get("parent_link") not in model["links"]
        ):
            findings.append(
                fail("end_effector", "SRDF end effector group/parent link is invalid")
            )
    for virtual in root.findall("virtual_joint"):
        if virtual.get("child_link") not in model["links"]:
            findings.append(
                fail("virtual_joint", "SRDF virtual joint child link is unknown")
            )
    return groups, passive, findings


def validate(
    paths: dict[str, Path]
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    model = urdf_model(parse_xml(paths["urdf"]))
    srdf_root = parse_xml(paths["srdf"])
    groups, passive, findings = srdf_model(srdf_root, model)
    movable = {
        name
        for name, joint in model["joints"].items()
        if joint["type"] not in {"fixed", "floating"}
    }
    actuated = {
        name
        for name in movable
        if not model["joints"][name]["mimic"] and name not in passive
    }
    for name in movable:
        joint = model["joints"][name]
        if joint["type"] in {"revolute", "prismatic"}:
            limit = joint["limit"]
            if limit is None or any(
                limit.get(key) is None for key in ("lower", "upper", "effort", "velocity")
            ):
                findings.append(
                    fail("urdf_joint_limit", f"joint {name} lacks complete limits")
                )

    kinematics = load_yaml(paths["kinematics"])
    for group, config in kinematics.items():
        if group not in groups:
            findings.append(
                fail("kinematics_group", f"kinematics group {group} is not in SRDF")
            )
        if not isinstance(config, dict) or not isinstance(
            config.get("kinematics_solver"), str
        ):
            findings.append(
                fail("kinematics_solver", f"group {group} has no solver plugin")
            )
    for group in groups:
        if group not in kinematics:
            findings.append(
                fail("kinematics_group", f"SRDF group {group} has no kinematics entry")
            )

    limits = load_yaml(paths["joint_limits"]).get("joint_limits")
    if not isinstance(limits, dict):
        findings.append(
            fail("joint_limits", "joint_limits YAML needs joint_limits mapping")
        )
    else:
        unknown = set(limits) - movable
        if unknown:
            findings.append(
                fail("joint_limit_joint", f"joint limit overrides unknown {sorted(unknown)}")
            )
        for name, config in limits.items():
            if not isinstance(config, dict):
                findings.append(fail("joint_limits", f"{name} limit must be a mapping"))
                continue
            if config.get("has_velocity_limits"):
                value = config.get("max_velocity")
                if (
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                    or value <= 0
                ):
                    findings.append(
                        fail("joint_velocity_limit", f"{name} max_velocity is invalid")
                    )

    pipelines = load_yaml(paths["planning_pipelines"])
    available = pipelines.get("planning_pipelines")
    default = pipelines.get("default_planning_pipeline")
    if (
        not isinstance(available, list)
        or not available
        or any(not isinstance(item, str) or not item for item in available)
        or default not in available
    ):
        findings.append(
            fail(
                "planning_pipelines",
                "planning pipelines must be nonempty and include the default",
            )
        )

    controller_yaml = load_yaml(paths["moveit_controllers"])
    manager = controller_yaml.get("moveit_simple_controller_manager")
    controller_joints: set[str] = set()
    action_names: list[str] = []
    if not isinstance(manager, dict) or not isinstance(
        manager.get("controller_names"), list
    ):
        findings.append(
            fail("controller_config", "simple controller manager mapping is required")
        )
    else:
        for name in manager["controller_names"]:
            config = manager.get(name)
            if not isinstance(config, dict):
                findings.append(
                    fail("controller_config", f"controller {name} has no configuration")
                )
                continue
            joints = config.get("joints")
            if (
                not isinstance(joints, list)
                or not joints
                or len(set(joints)) != len(joints)
                or any(joint not in model["joints"] for joint in joints)
            ):
                findings.append(
                    fail("controller_joint_set", f"controller {name} joints are invalid")
                )
                continue
            controller_joints.update(joints)
            action_ns = config.get("action_ns")
            if config.get("type") != "FollowJointTrajectory" or not isinstance(
                action_ns, str
            ) or not action_ns:
                findings.append(
                    fail("controller_action", f"controller {name} action mapping is invalid")
                )
            else:
                action_names.append(f"{name}/{action_ns}")
    if controller_joints != actuated:
        findings.append(
            fail(
                "controller_joint_set",
                f"controller joints {sorted(controller_joints)} must equal actuated joints {sorted(actuated)}",
            )
        )
    for name in controller_joints:
        interfaces = model["interfaces"].get(name)
        if interfaces is None or "position" not in interfaces["command"]:
            findings.append(
                fail(
                    "ros2_control_interface",
                    f"joint {name} lacks a position command interface",
                )
            )
    return findings, {
        "links": len(model["links"]),
        "movable_joints": len(movable),
        "actuated_joints": len(actuated),
        "groups": len(groups),
        "action_names": action_names,
    }


def ros_discovery() -> tuple[str, dict[str, Any], list[str]]:
    ros2 = shutil.which("ros2")
    if ros2 is None:
        return "skip", {}, ["ros2 CLI is unavailable"]
    packages = {}
    missing: list[str] = []
    for package in ("moveit_ros_move_group", "moveit_msgs"):
        completed = subprocess.run(
            [ros2, "pkg", "prefix", package],
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode == 0:
            packages[package] = completed.stdout.strip()
        else:
            missing.append(package)
    if missing:
        return "skip", {"packages": packages}, [
            f"optional MoveIt packages unavailable: {', '.join(missing)}"
        ]
    return "pass", {"packages": packages}, []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--ros-check", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        paths = resolve_snapshot(args.snapshot)
        findings, counts = validate(paths)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="moveit_config",
            summary="MoveIt snapshot input is invalid",
            inputs=[str(args.snapshot)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No complete MoveIt cross-file check was performed."],
        )
        emit_result(result, args.output)
        return 2
    requested_status = "pass"
    environment: dict[str, Any] = {"baseline": "ROS 2 Humble"}
    limitations = [
        "Static configuration admission does not prove planning, live actions, control, or hardware readiness."
    ]
    if args.ros_check and not findings:
        requested_status, discovered, discovery_limits = ros_discovery()
        environment.update(discovered)
        limitations.extend(discovery_limits)
    result = make_result(
        skill=SKILL,
        check="moveit_config",
        summary=(
            "MoveIt configuration is admissible"
            if not findings and requested_status == "pass"
            else "MoveIt configuration passed; optional ROS discovery was skipped"
            if not findings
            else "MoveIt configuration failed admission"
        ),
        inputs=[str(args.snapshot)],
        environment=environment,
        metrics={
            "link_count": {
                "value": counts["links"],
                "unit": "links",
                "direction": "informational",
            },
            "movable_joint_count": {
                "value": counts["movable_joints"],
                "unit": "joints",
                "direction": "informational",
            },
            "planning_group_count": {
                "value": counts["groups"],
                "unit": "groups",
                "direction": "informational",
            },
        },
        findings=findings,
        evidence=[{"configured_actions": counts["action_names"]}],
        limitations=limitations,
        requested_status=requested_status,
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
