#!/usr/bin/env python3
"""Validate and decode a bounded PointCloud2 JSON byte-layout fixture."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any

from result_contract import emit_result, make_result, portable_path


SKILL = "robotics-3d-perception"
MAX_INPUT_BYTES = 64 * 1024 * 1024
DATATYPES = {
    1: ("b", 1),
    2: ("B", 1),
    3: ("h", 2),
    4: ("H", 2),
    5: ("i", 4),
    6: ("I", 4),
    7: ("f", 4),
    8: ("d", 8),
}


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"cloud fixture is not a file: {portable_path(path)}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"fixture exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot parse cloud fixture: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("cloud fixture root must be an object")
    return data


def parse_fields(
    data: dict[str, Any], point_step: Any
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    fields = data.get("fields")
    if not isinstance(fields, list) or not fields:
        return {}, [fail("point_fields", "fields must be a nonempty array")]
    by_name: dict[str, dict[str, Any]] = {}
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            findings.append(
                fail("point_field", f"fields[{index}] must be an object")
            )
            continue
        name = field.get("name")
        datatype = field.get("datatype")
        offset = field.get("offset")
        count = field.get("count")
        if not isinstance(name, str) or not name or name in by_name:
            findings.append(
                fail("point_field_name", f"fields[{index}] needs a unique name")
            )
            continue
        if datatype not in DATATYPES:
            findings.append(
                fail("point_field_datatype", f"field {name} has invalid datatype")
            )
            continue
        if (
            not isinstance(offset, int)
            or isinstance(offset, bool)
            or offset < 0
            or not positive_int(count)
        ):
            findings.append(
                fail("point_field_layout", f"field {name} has invalid offset/count")
            )
            continue
        size = DATATYPES[datatype][1] * count
        if not positive_int(point_step) or offset + size > point_step:
            findings.append(
                fail(
                    "point_field_bounds",
                    f"field {name} extends beyond point_step",
                )
            )
            continue
        by_name[name] = field
    return by_name, findings


def validate_and_decode(
    data: dict[str, Any]
) -> tuple[list[dict[str, str]], int, float]:
    findings: list[dict[str, str]] = []
    width, height = data.get("width"), data.get("height")
    point_step, row_step = data.get("point_step"), data.get("row_step")
    if not positive_int(width) or not positive_int(height):
        findings.append(fail("cloud_dimensions", "width/height must be positive"))
    if not positive_int(point_step):
        findings.append(fail("point_step", "point_step must be positive"))
    if (
        not positive_int(row_step)
        or (positive_int(width) and positive_int(point_step) and row_step < width * point_step)
    ):
        findings.append(
            fail("row_step", "row_step must cover width * point_step")
        )
    fields, field_findings = parse_fields(data, point_step)
    findings.extend(field_findings)
    for coordinate in ("x", "y", "z"):
        field = fields.get(coordinate)
        if field is None:
            findings.append(fail("xyz_fields", f"missing {coordinate} field"))
        elif field["datatype"] not in {7, 8} or field["count"] != 1:
            findings.append(
                fail(
                    "xyz_datatype",
                    f"{coordinate} must be one FLOAT32 or FLOAT64 value",
                )
            )
    requirements = data.get("requirements", {})
    if not isinstance(requirements, dict):
        findings.append(fail("requirements", "requirements must be an object"))
    else:
        for key, code in (
            ("time_field", "required_time_field"),
            ("ring_field", "required_ring_field"),
        ):
            value = requirements.get(key)
            if value is not None and (
                not isinstance(value, str) or not value or value not in fields
            ):
                findings.append(
                    fail(code, f"declared {key} {value!r} is absent")
                )
    if not isinstance(data.get("frame_id"), str) or not data["frame_id"]:
        findings.append(fail("cloud_frame", "frame_id is required"))
    stamp = data.get("stamp_ns")
    if (
        not isinstance(stamp, int)
        or isinstance(stamp, bool)
        or stamp < 0
    ):
        findings.append(fail("cloud_stamp", "stamp_ns must be nonnegative"))
    if not isinstance(data.get("is_bigendian"), bool):
        findings.append(
            fail("cloud_endianness", "is_bigendian must be boolean")
        )
    data_hex = data.get("data_hex")
    try:
        payload = bytes.fromhex(data_hex) if isinstance(data_hex, str) else b""
    except ValueError:
        payload = b""
        findings.append(fail("data_hex", "data_hex is not valid hexadecimal"))
    expected = (
        row_step * height
        if positive_int(row_step) and positive_int(height)
        else None
    )
    if expected is None or len(payload) != expected:
        findings.append(
            fail(
                "data_length",
                f"decoded payload length {len(payload)} must equal row_step * height",
            )
        )
    if findings:
        return findings, 0, 0.0

    prefix = ">" if data["is_bigendian"] else "<"
    finite = 0
    decoded = 0
    for row in range(height):
        for column in range(width):
            base = row * row_step + column * point_step
            xyz: list[float] = []
            for name in ("x", "y", "z"):
                field = fields[name]
                format_code = DATATYPES[field["datatype"]][0]
                value = struct.unpack_from(
                    prefix + format_code, payload, base + field["offset"]
                )[0]
                xyz.append(float(value))
            decoded += 1
            if all(math.isfinite(value) for value in xyz):
                finite += 1
    return findings, decoded, finite / decoded if decoded else 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cloud", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load(args.cloud)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="pointcloud_contract",
            summary="point cloud input is invalid",
            inputs=[portable_path(args.cloud)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No PointCloud2 bytes were decoded."],
        )
        emit_result(result, args.output)
        return 2
    findings, decoded, finite_ratio = validate_and_decode(data)
    result = make_result(
        skill=SKILL,
        check="pointcloud_contract",
        summary=(
            "point cloud contract is admissible"
            if not findings
            else "point cloud contract failed admission"
        ),
        inputs=[portable_path(args.cloud)],
        metrics={
            "decoded_point_count": {
                "value": decoded,
                "unit": "points",
                "direction": "informational",
            },
            "finite_ratio": {
                "value": finite_ratio,
                "unit": "ratio",
                "direction": "higher_is_better",
            },
        },
        findings=findings,
        limitations=[
            "Byte-layout admission does not prove timing, deskew, extrinsics, or geometric accuracy."
        ],
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
