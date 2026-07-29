#!/usr/bin/env python3
"""Evaluate deterministic 2D box predictions against ground truth."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from result_contract import emit_result, make_result


SKILL = "robotics-vision-perception"
MAX_INPUT_BYTES = 50 * 1024 * 1024


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def box_valid(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(item)
            for item in value
        )
        and value[2] > 0
        and value[3] > 0
    )


def iou(left: list[float], right: list[float]) -> float:
    left_x2, left_y2 = left[0] + left[2], left[1] + left[3]
    right_x2, right_y2 = right[0] + right[2], right[1] + right[3]
    intersection_width = max(0.0, min(left_x2, right_x2) - max(left[0], right[0]))
    intersection_height = max(
        0.0, min(left_y2, right_y2) - max(left[1], right[1])
    )
    intersection = intersection_width * intersection_height
    union = left[2] * left[3] + right[2] * right[3] - intersection
    return intersection / union if union > 0 else 0.0


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"detection record is not a file: {path}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"record exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot parse detection record: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("detection record root must be an object")
    return data


def validate_items(
    items: Any, prediction: bool, label: str
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not isinstance(items, list):
        return [fail(f"{label}_records", f"{label} must be an array")]
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            findings.append(
                fail(f"{label}_record", f"{label}[{index}] must be an object")
            )
            continue
        if not isinstance(item.get("image_id"), str) or not item["image_id"]:
            findings.append(
                fail("image_id", f"{label}[{index}].image_id is required")
            )
        if not isinstance(item.get("class"), str) or not item["class"]:
            findings.append(
                fail("class_label", f"{label}[{index}].class is required")
            )
        if not box_valid(item.get("box")):
            findings.append(
                fail(
                    "box_geometry",
                    f"{label}[{index}].box must be finite [x,y,width,height] with positive size",
                )
            )
        if prediction:
            score = item.get("score")
            if (
                not isinstance(score, (int, float))
                or isinstance(score, bool)
                or not math.isfinite(score)
                or not 0 <= score <= 1
            ):
                findings.append(
                    fail("prediction_score", f"{label}[{index}].score must be in [0,1]")
                )
    return findings


def evaluate(data: dict[str, Any]) -> tuple[dict[str, float | int], list[dict[str, str]]]:
    findings = validate_items(data.get("ground_truth"), False, "ground_truth")
    findings.extend(validate_items(data.get("predictions"), True, "predictions"))
    score_threshold = data.get("score_threshold")
    iou_threshold = data.get("iou_threshold")
    for name, value in (
        ("score_threshold", score_threshold),
        ("iou_threshold", iou_threshold),
    ):
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            findings.append(fail(name, f"{name} must be finite and in [0,1]"))
    if findings:
        return {}, findings

    truths = data["ground_truth"]
    predictions = sorted(
        (
            item
            for item in data["predictions"]
            if item["score"] >= score_threshold
        ),
        key=lambda item: item["score"],
        reverse=True,
    )
    unmatched = set(range(len(truths)))
    matched_ious: list[float] = []
    false_positive = 0
    for prediction in predictions:
        candidates = [
            (iou(prediction["box"], truths[index]["box"]), index)
            for index in unmatched
            if truths[index]["image_id"] == prediction["image_id"]
            and truths[index]["class"] == prediction["class"]
        ]
        best = max(candidates, default=(0.0, -1))
        if best[0] >= iou_threshold and best[1] >= 0:
            unmatched.remove(best[1])
            matched_ious.append(best[0])
        else:
            false_positive += 1
    true_positive = len(matched_ious)
    false_negative = len(unmatched)
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": (
            true_positive / precision_denominator if precision_denominator else 0.0
        ),
        "recall": true_positive / recall_denominator if recall_denominator else 0.0,
        "mean_matched_iou": (
            sum(matched_ious) / len(matched_ious) if matched_ious else 0.0
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
            check="vision_2d_evaluation",
            summary="detection record input is invalid",
            inputs=[str(args.record)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No detections were evaluated."],
        )
        emit_result(result, args.output)
        return 2
    values, findings = evaluate(data)
    metrics = {
        name: {
            "value": value,
            "unit": "count"
            if name in {"true_positive", "false_positive", "false_negative"}
            else "ratio",
            "direction": (
                "higher_is_better"
                if name in {"precision", "recall", "mean_matched_iou"}
                else "informational"
            ),
        }
        for name, value in values.items()
    }
    result = make_result(
        skill=SKILL,
        check="vision_2d_evaluation",
        summary=(
            "2D detections evaluated"
            if not findings
            else "2D detection record failed admission"
        ),
        inputs=[str(args.record)],
        metrics=metrics,
        findings=findings,
        limitations=[
            "This deterministic box matcher is not COCO mAP, mask, tracking, or safety evaluation."
        ],
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
