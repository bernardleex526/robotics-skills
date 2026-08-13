#!/usr/bin/env python3
"""Match framed 3D objects using explicit engineering admission gates."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from result_contract import emit_result, make_result, portable_path


SKILL = "robotics-3d-perception"
MAX_INPUT_BYTES = 50 * 1024 * 1024


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def finite_vector(value: Any, length: int, positive: bool = False) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(item)
            and (not positive or item > 0)
            for item in value
        )
    )


def wrapped_yaw_error(left: float, right: float) -> float:
    return abs((left - right + math.pi) % (2 * math.pi) - math.pi)


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"3D result record is not a file: {portable_path(path)}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"record exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot parse 3D result record: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("3D result record root must be an object")
    return data


def validate_objects(
    items: Any, label: str, frame: str, prediction: bool
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not isinstance(items, list):
        return [fail(f"{label}_records", f"{label} must be an array")]
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            findings.append(fail("object_record", f"{label}[{index}] must be an object"))
            continue
        if item.get("frame_id") != frame:
            findings.append(
                fail(
                    "object_frame",
                    f"{label}[{index}].frame_id must equal top-level frame_id",
                )
            )
        if not isinstance(item.get("class"), str) or not item["class"]:
            findings.append(fail("object_class", f"{label}[{index}].class is required"))
        if not finite_vector(item.get("center_m"), 3):
            findings.append(
                fail("object_center", f"{label}[{index}].center_m must be finite xyz")
            )
        if not finite_vector(item.get("size_m"), 3, positive=True):
            findings.append(
                fail("object_size", f"{label}[{index}].size_m must be positive xyz")
            )
        yaw = item.get("yaw_rad")
        if (
            not isinstance(yaw, (int, float))
            or isinstance(yaw, bool)
            or not math.isfinite(yaw)
        ):
            findings.append(fail("object_yaw", f"{label}[{index}].yaw_rad is invalid"))
        if prediction:
            score = item.get("score")
            if (
                not isinstance(score, (int, float))
                or isinstance(score, bool)
                or not math.isfinite(score)
                or not 0 <= score <= 1
            ):
                findings.append(
                    fail("object_score", f"{label}[{index}].score must be in [0,1]")
                )
    return findings


def evaluate(data: dict[str, Any]) -> tuple[dict[str, float | int], list[dict[str, str]]]:
    frame = data.get("frame_id")
    findings: list[dict[str, str]] = []
    if not isinstance(frame, str) or not frame:
        findings.append(fail("evaluation_frame", "top-level frame_id is required"))
        frame = ""
    findings.extend(
        validate_objects(data.get("ground_truth"), "ground_truth", frame, False)
    )
    findings.extend(
        validate_objects(data.get("predictions"), "predictions", frame, True)
    )
    gate_names = (
        "score_threshold",
        "max_center_distance_m",
        "max_size_error_ratio",
        "max_yaw_error_deg",
    )
    for name in gate_names:
        value = data.get(name)
        lower_bound = 0
        upper_bound = 1 if name == "score_threshold" else None
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < lower_bound
            or (upper_bound is not None and value > upper_bound)
        ):
            findings.append(fail(name, f"{name} must be finite and nonnegative"))
    if findings:
        return {}, findings

    truths = data["ground_truth"]
    predictions = sorted(
        (
            item
            for item in data["predictions"]
            if item["score"] >= data["score_threshold"]
        ),
        key=lambda item: item["score"],
        reverse=True,
    )
    unmatched = set(range(len(truths)))
    translation_errors: list[float] = []
    yaw_errors: list[float] = []
    false_positive = 0
    yaw_limit = math.radians(data["max_yaw_error_deg"])
    for prediction in predictions:
        candidates: list[tuple[float, float, int]] = []
        for index in unmatched:
            truth = truths[index]
            if truth["class"] != prediction["class"]:
                continue
            center_error = math.dist(prediction["center_m"], truth["center_m"])
            size_error = max(
                abs(predicted - expected) / expected
                for predicted, expected in zip(
                    prediction["size_m"], truth["size_m"]
                )
            )
            yaw_error = wrapped_yaw_error(
                prediction["yaw_rad"], truth["yaw_rad"]
            )
            if (
                center_error <= data["max_center_distance_m"]
                and size_error <= data["max_size_error_ratio"]
                and yaw_error <= yaw_limit
            ):
                candidates.append((center_error, yaw_error, index))
        if candidates:
            center_error, yaw_error, index = min(candidates)
            unmatched.remove(index)
            translation_errors.append(center_error)
            yaw_errors.append(math.degrees(yaw_error))
        else:
            false_positive += 1
    true_positive = len(translation_errors)
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": len(unmatched),
        "mean_translation_error_m": (
            sum(translation_errors) / true_positive if true_positive else 0.0
        ),
        "mean_yaw_error_deg": (
            sum(yaw_errors) / true_positive if true_positive else 0.0
        ),
    }, []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load(args.record)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="three_d_evaluation",
            summary="3D result input is invalid",
            inputs=[portable_path(args.record)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No 3D objects were evaluated."],
        )
        emit_result(result, args.output)
        return 2
    values, findings = evaluate(data)
    metrics: dict[str, dict[str, Any]] = {}
    for name, value in values.items():
        if name.endswith("_m"):
            unit, direction = "m", "lower_is_better"
        elif name.endswith("_deg"):
            unit, direction = "deg", "lower_is_better"
        else:
            unit, direction = "count", "informational"
        metrics[name] = {"value": value, "unit": unit, "direction": direction}
    result = make_result(
        skill=SKILL,
        check="three_d_evaluation",
        summary=(
            "3D objects evaluated"
            if not findings
            else "3D object record failed admission"
        ),
        inputs=[portable_path(args.record)],
        metrics=metrics,
        findings=findings,
        limitations=[
            "Matching uses center, relative size, and yaw gates; it is not oriented 3D IoU."
        ],
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
