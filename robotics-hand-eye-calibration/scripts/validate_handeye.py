#!/usr/bin/env python3
"""Validate hand-eye motion-pair observability and AX=XB closure."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from result_contract import emit_result, make_result, portable_path


SKILL = "robotics-hand-eye-calibration"
MAX_INPUT_BYTES = 20 * 1024 * 1024


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def finite_vector(value: Any, length: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(item)
            for item in value
        )
    )


def normalize_quaternion(values: list[float]) -> tuple[float, float, float, float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("zero quaternion")
    return tuple(value / norm for value in values)  # type: ignore[return-value]


def quaternion_multiply(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    x1, y1, z1, w1 = left
    x2, y2, z2, w2 = right
    return (
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    )


def quaternion_inverse(
    quaternion: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    return (-quaternion[0], -quaternion[1], -quaternion[2], quaternion[3])


def rotate_vector(
    quaternion: tuple[float, float, float, float],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    pure = (vector[0], vector[1], vector[2], 0.0)
    rotated = quaternion_multiply(
        quaternion_multiply(quaternion, pure), quaternion_inverse(quaternion)
    )
    return rotated[0], rotated[1], rotated[2]


Transform = tuple[
    tuple[float, float, float], tuple[float, float, float, float]
]


def compose(left: Transform, right: Transform) -> Transform:
    rotated = rotate_vector(left[1], right[0])
    translation = tuple(
        left[0][index] + rotated[index] for index in range(3)
    )
    rotation = normalize_quaternion(
        list(quaternion_multiply(left[1], right[1]))
    )
    return translation, rotation


def inverse(transform: Transform) -> Transform:
    rotation = quaternion_inverse(transform[1])
    translated = rotate_vector(
        rotation,
        (-transform[0][0], -transform[0][1], -transform[0][2]),
    )
    return translated, rotation


def angular_distance_deg(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    dot = abs(sum(a * b for a, b in zip(left, right)))
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def parse_transform(
    value: Any, label: str, findings: list[dict[str, str]]
) -> Transform | None:
    if not isinstance(value, dict):
        findings.append(fail("transform", f"{label} must be an object"))
        return None
    translation = value.get("translation_m")
    quaternion = value.get("rotation_xyzw")
    if not finite_vector(translation, 3):
        findings.append(
            fail("translation", f"{label}.translation_m must be finite xyz")
        )
        return None
    if not finite_vector(quaternion, 4):
        findings.append(
            fail("quaternion", f"{label}.rotation_xyzw must be finite XYZW")
        )
        return None
    norm = math.sqrt(sum(component * component for component in quaternion))
    if not 0.999 <= norm <= 1.001:
        findings.append(
            fail(
                "quaternion_norm",
                f"{label} quaternion norm {norm:.6g} is outside [0.999, 1.001]",
            )
        )
    if norm == 0:
        return None
    return (
        tuple(float(item) for item in translation),  # type: ignore[arg-type]
        normalize_quaternion([float(item) for item in quaternion]),
    )


def rotation_axis(
    quaternion: tuple[float, float, float, float]
) -> tuple[float, float, float] | None:
    vector_norm = math.sqrt(sum(value * value for value in quaternion[:3]))
    angle = 2.0 * math.atan2(vector_norm, abs(quaternion[3]))
    if angle < math.radians(5) or vector_norm < 1e-12:
        return None
    return tuple(value / vector_norm for value in quaternion[:3])  # type: ignore[return-value]


def rmse(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values))


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"hand-eye dataset is not a file: {portable_path(path)}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"dataset exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot parse hand-eye dataset: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("hand-eye dataset root must be an object")
    return data


def validate(
    data: dict[str, Any]
) -> tuple[list[dict[str, str]], dict[str, float | int]]:
    findings: list[dict[str, str]] = []
    if data.get("mode") not in {"eye_in_hand", "eye_to_hand"}:
        findings.append(fail("calibration_mode", "mode must be eye_in_hand or eye_to_hand"))
    frames = data.get("frames")
    required_frames = ("x_parent", "x_child", "motion_a", "motion_b")
    if not isinstance(frames, dict) or any(
        not isinstance(frames.get(key), str) or not frames[key]
        for key in required_frames
    ):
        findings.append(fail("frame_labels", "all candidate and motion frame labels are required"))
        frames = {}
    candidate_value = data.get("candidate")
    if (
        not isinstance(candidate_value, dict)
        or candidate_value.get("parent_frame") != frames.get("x_parent")
        or candidate_value.get("child_frame") != frames.get("x_child")
    ):
        findings.append(fail("candidate_frames", "candidate parent/child frames do not match"))
    candidate = parse_transform(candidate_value, "candidate", findings)

    thresholds = data.get("thresholds")
    threshold_names = (
        "max_pairing_skew_ms",
        "min_translation_span_m",
        "min_rotation_axis_separation_deg",
        "max_fit_translation_rmse_m",
        "max_fit_rotation_rmse_deg",
        "max_holdout_translation_rmse_m",
        "max_holdout_rotation_rmse_deg",
    )
    if not isinstance(thresholds, dict):
        findings.append(fail("thresholds", "thresholds must be an object"))
        thresholds = {}
    for name in threshold_names:
        value = thresholds.get(name)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            findings.append(fail("thresholds", f"{name} must be finite and nonnegative"))

    samples = data.get("samples")
    if not isinstance(samples, list) or len(samples) < 5:
        findings.append(fail("sample_count", "at least five motion pairs are required"))
        samples = []
    parsed: list[tuple[str, Transform, Transform]] = []
    identifiers: set[str] = set()
    signatures: set[str] = set()
    max_skew = 0.0
    for index, sample in enumerate(samples):
        label = f"samples[{index}]"
        if not isinstance(sample, dict):
            findings.append(fail("sample", f"{label} must be an object"))
            continue
        identifier = sample.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            findings.append(fail("sample_uniqueness", f"{label}.id must be unique"))
        else:
            identifiers.add(identifier)
        partition = sample.get("partition")
        if partition not in {"fit", "holdout"}:
            findings.append(fail("sample_partition", f"{label}.partition is invalid"))
            continue
        if (
            sample.get("a_label") != frames.get("motion_a")
            or sample.get("b_label") != frames.get("motion_b")
        ):
            findings.append(fail("motion_labels", f"{label} motion labels do not match"))
        a_stamp, b_stamp = sample.get("a_stamp_ns"), sample.get("b_stamp_ns")
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in (a_stamp, b_stamp)
        ):
            findings.append(fail("sample_stamp", f"{label} stamps must be nonnegative"))
        else:
            skew = abs(a_stamp - b_stamp) / 1_000_000.0
            max_skew = max(max_skew, skew)
            if isinstance(thresholds.get("max_pairing_skew_ms"), (int, float)) and skew > thresholds["max_pairing_skew_ms"]:
                findings.append(
                    fail("pairing_skew", f"{label} pairing skew {skew} ms exceeds threshold")
                )
        a_transform = parse_transform(sample.get("a"), f"{label}.a", findings)
        b_transform = parse_transform(sample.get("b"), f"{label}.b", findings)
        if a_transform and b_transform:
            signature = json.dumps(
                [a_transform, b_transform], sort_keys=True
            )
            if signature in signatures:
                findings.append(fail("sample_uniqueness", f"{label} duplicates a motion pair"))
            signatures.add(signature)
            parsed.append((partition, a_transform, b_transform))

    fit = [item for item in parsed if item[0] == "fit"]
    holdout = [item for item in parsed if item[0] == "holdout"]
    if len(fit) < 3 or len(holdout) < 1:
        findings.append(fail("sample_partition", "need at least three fit and one holdout pair"))
    translations = [item[1][0] for item in fit]
    span = max(
        (math.dist(left, right) for left in translations for right in translations),
        default=0.0,
    )
    if isinstance(thresholds.get("min_translation_span_m"), (int, float)) and span < thresholds["min_translation_span_m"]:
        findings.append(fail("translation_span", f"fit translation span {span} m is too small"))
    axes = [
        axis for _, transform, _ in fit if (axis := rotation_axis(transform[1]))
    ]
    max_axis_separation = max(
        (
            math.degrees(
                math.acos(
                    max(
                        -1.0,
                        min(
                            1.0,
                            abs(sum(a * b for a, b in zip(left, right))),
                        ),
                    )
                )
            )
            for left in axes
            for right in axes
        ),
        default=0.0,
    )
    if isinstance(thresholds.get("min_rotation_axis_separation_deg"), (int, float)) and max_axis_separation < thresholds["min_rotation_axis_separation_deg"]:
        findings.append(
            fail(
                "rotation_axis_diversity",
                f"maximum material axis separation {max_axis_separation} deg is too small",
            )
        )

    metrics: dict[str, float | int] = {
        "sample_count": len(parsed),
        "fit_sample_count": len(fit),
        "holdout_sample_count": len(holdout),
        "maximum_pairing_skew_ms": max_skew,
        "translation_span_m": span,
        "maximum_axis_separation_deg": max_axis_separation,
    }
    if candidate and fit and holdout:
        residuals: dict[str, tuple[list[float], list[float]]] = {
            "fit": ([], []),
            "holdout": ([], []),
        }
        for partition, a_transform, b_transform in parsed:
            left = compose(a_transform, candidate)
            right = compose(candidate, b_transform)
            residuals[partition][0].append(math.dist(left[0], right[0]))
            residuals[partition][1].append(
                angular_distance_deg(left[1], right[1])
            )
        for partition in ("fit", "holdout"):
            translation_rmse = rmse(residuals[partition][0])
            rotation_rmse = rmse(residuals[partition][1])
            metrics[f"{partition}_translation_rmse_m"] = translation_rmse
            metrics[f"{partition}_rotation_rmse_deg"] = rotation_rmse
            if isinstance(thresholds.get(f"max_{partition}_translation_rmse_m"), (int, float)) and translation_rmse > thresholds[f"max_{partition}_translation_rmse_m"]:
                findings.append(
                    fail(
                        f"{partition}_translation_residual",
                        f"{partition} translation RMSE {translation_rmse} m exceeds threshold",
                    )
                )
            if isinstance(thresholds.get(f"max_{partition}_rotation_rmse_deg"), (int, float)) and rotation_rmse > thresholds[f"max_{partition}_rotation_rmse_deg"]:
                findings.append(
                    fail(
                        f"{partition}_rotation_residual",
                        f"{partition} rotation RMSE {rotation_rmse} deg exceeds threshold",
                    )
                )
    return findings, metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load(args.dataset)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="handeye_validation",
            summary="hand-eye dataset input is invalid",
            inputs=[portable_path(args.dataset)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No motion-pair or candidate validation was performed."],
        )
        emit_result(result, args.output)
        return 2
    findings, values = validate(data)
    metrics: dict[str, dict[str, Any]] = {}
    for name, value in values.items():
        unit = (
            "m"
            if name.endswith("_m")
            else "ms"
            if name.endswith("_ms")
            else "deg"
            if name.endswith("_deg")
            else "samples"
        )
        metrics[name] = {
            "value": value,
            "unit": unit,
            "direction": (
                "lower_is_better"
                if "rmse" in name or "skew" in name
                else "informational"
            ),
        }
    result = make_result(
        skill=SKILL,
        check="handeye_validation",
        summary=(
            "hand-eye dataset and candidate are admissible"
            if not findings
            else "hand-eye validation failed admission"
        ),
        inputs=[portable_path(args.dataset)],
        metrics=metrics,
        findings=findings,
        limitations=[
            "AX=XB closure does not prove intrinsic calibration, frame truth, rigidity, or task-space accuracy."
        ],
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
