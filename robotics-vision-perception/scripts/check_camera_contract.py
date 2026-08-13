#!/usr/bin/env python3
"""Validate an offline ROS 2 Image/CameraInfo contract snapshot."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from result_contract import emit_result, make_result, portable_path


SKILL = "robotics-vision-perception"
MAX_INPUT_BYTES = 20 * 1024 * 1024
BYTES_PER_PIXEL = {
    "mono8": 1,
    "mono16": 2,
    "rgb8": 3,
    "bgr8": 3,
    "rgba8": 4,
    "bgra8": 4,
    "16UC1": 2,
    "32FC1": 4,
}
DISTORTION_LENGTH = {
    "plumb_bob": 5,
    "rational_polynomial": 8,
    "equidistant": 4,
}


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def finite_vector(value: Any, length: int | None = None) -> bool:
    return (
        isinstance(value, list)
        and (length is None or len(value) == length)
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(item)
            for item in value
        )
    )


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"camera snapshot is not a file: {portable_path(path)}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"snapshot exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot parse camera snapshot: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("camera snapshot root must be an object")
    return data


def validate(data: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    image = data.get("image")
    info = data.get("camera_info")
    if not isinstance(image, dict):
        return [fail("image_contract", "image must be an object")]
    if not isinstance(info, dict):
        return [fail("camera_info_contract", "camera_info must be an object")]

    width, height = image.get("width"), image.get("height")
    if not positive_int(width) or not positive_int(height):
        findings.append(fail("image_dimensions", "image dimensions must be positive"))
    encoding = image.get("encoding")
    bytes_per_pixel = BYTES_PER_PIXEL.get(encoding)
    if bytes_per_pixel is None:
        findings.append(
            fail("image_encoding", f"unsupported or missing encoding: {encoding!r}")
        )
    step = image.get("step")
    data_length = image.get("data_length")
    if not positive_int(step):
        findings.append(fail("image_step", "image.step must be a positive integer"))
    elif positive_int(width) and bytes_per_pixel and step < width * bytes_per_pixel:
        findings.append(
            fail("image_step", "image.step is smaller than encoded row width")
        )
    if (
        not isinstance(data_length, int)
        or isinstance(data_length, bool)
        or data_length < 0
        or not positive_int(height)
        or not positive_int(step)
        or data_length != step * height
    ):
        findings.append(
            fail(
                "image_data_length",
                "image.data_length must equal image.step * image.height",
            )
        )
    if not isinstance(image.get("is_bigendian"), bool):
        findings.append(
            fail("image_endianness", "image.is_bigendian must be boolean")
        )
    image_frame = image.get("frame_id")
    info_frame = info.get("frame_id")
    if (
        not isinstance(image_frame, str)
        or not image_frame
        or image_frame != info_frame
    ):
        findings.append(
            fail(
                "camera_frame_match",
                "Image and CameraInfo must declare the same nonempty frame_id",
            )
        )
    if info.get("width") != width or info.get("height") != height:
        findings.append(
            fail(
                "camera_info_dimensions",
                "CameraInfo dimensions must match Image dimensions",
            )
        )
    model = info.get("distortion_model")
    minimum_d = DISTORTION_LENGTH.get(model)
    if minimum_d is None:
        findings.append(
            fail("distortion_model", f"unrecognized distortion model: {model!r}")
        )
    elif not finite_vector(info.get("d")) or len(info["d"]) < minimum_d:
        findings.append(
            fail(
                "distortion_coefficients",
                f"{model} requires at least {minimum_d} finite coefficients",
            )
        )
    for key, length in (("k", 9), ("r", 9), ("p", 12)):
        if not finite_vector(info.get(key), length):
            findings.append(
                fail(
                    f"camera_info_{key}",
                    f"CameraInfo {key.upper()} must have {length} finite values",
                )
            )

    stamps = data.get("acquisition_stamps_ns")
    if (
        not isinstance(stamps, list)
        or not stamps
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in stamps
        )
        or any(current <= previous for previous, current in zip(stamps, stamps[1:]))
    ):
        findings.append(
            fail(
                "acquisition_stamp_monotonic",
                "acquisition_stamps_ns must be nonnegative and strictly increasing",
            )
        )
    skew = data.get("pairing_skew_ms")
    limit = data.get("max_pairing_skew_ms")
    if (
        not isinstance(skew, list)
        or not skew
        or any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
            for value in skew
        )
        or not isinstance(limit, (int, float))
        or isinstance(limit, bool)
        or not math.isfinite(limit)
        or limit < 0
    ):
        findings.append(
            fail(
                "pairing_skew_contract",
                "pairing skew samples and a finite nonnegative limit are required",
            )
        )
    elif max(skew) > limit:
        findings.append(
            fail(
                "pairing_skew",
                f"maximum pairing skew {max(skew)} ms exceeds {limit} ms",
            )
        )
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load(args.snapshot)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="camera_contract",
            summary="camera snapshot input is invalid",
            inputs=[portable_path(args.snapshot)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No Image or CameraInfo fields were validated."],
        )
        emit_result(result, args.output)
        return 2
    findings = validate(data)
    skew = data.get("pairing_skew_ms", [])
    result = make_result(
        skill=SKILL,
        check="camera_contract",
        summary=(
            "camera contract is admissible"
            if not findings
            else "camera contract failed admission"
        ),
        inputs=[portable_path(args.snapshot)],
        metrics={
            "maximum_pairing_skew_ms": {
                "value": max(skew) if isinstance(skew, list) and skew else None,
                "unit": "ms",
                "direction": "lower_is_better",
            },
            "sample_count": {
                "value": len(data.get("acquisition_stamps_ns", [])),
                "unit": "messages",
                "direction": "informational",
            },
        },
        findings=findings,
        limitations=[
            "Offline metadata does not prove live QoS, calibration accuracy, or latency."
        ],
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
