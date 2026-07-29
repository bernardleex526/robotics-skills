#!/usr/bin/env python3
"""Aggregate benchmark run records without dropping failures or skips."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml

from result_contract import emit_result, make_result


SKILL = "robotics-benchmarking"


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile / 100.0 * len(ordered)) - 1)
    return ordered[index]


def load_records(directory: Path) -> list[dict[str, Any]]:
    paths = sorted(directory.glob("run-*.json"))
    if not paths:
        raise ValueError("no run-*.json records found")
    records: list[dict[str, Any]] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot parse {path.name}: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("status") not in {
            "pass",
            "fail",
            "skip",
        }:
            raise ValueError(f"{path.name} has no valid status")
        if not isinstance(payload.get("metrics", {}), dict):
            raise ValueError(f"{path.name}.metrics must be a mapping")
        records.append(payload)
    return records


def load_definitions(directory: Path) -> dict[str, dict[str, Any]]:
    path = directory / "manifest.yaml"
    if not path.is_file():
        return {}
    try:
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}
    metrics = manifest.get("metrics", []) if isinstance(manifest, dict) else []
    return {
        item["name"]: item
        for item in metrics
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }


def aggregate(
    records: list[dict[str, Any]],
    definitions: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    total = len(records)
    failures = sum(record["status"] == "fail" for record in records)
    skips = sum(record["status"] == "skip" for record in records)
    successes = total - failures - skips
    metrics: dict[str, dict[str, Any]] = {
        "total_runs": {
            "value": total,
            "unit": "runs",
            "direction": "informational",
        },
        "successful_runs": {
            "value": successes,
            "unit": "runs",
            "direction": "higher_is_better",
        },
        "failure_rate": {
            "value": failures / total,
            "unit": "ratio",
            "direction": "lower_is_better",
        },
        "skip_rate": {
            "value": skips / total,
            "unit": "ratio",
            "direction": "lower_is_better",
        },
    }
    names = sorted(
        {
            name
            for record in records
            if record["status"] == "pass"
            for name, value in record.get("metrics", {}).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    )
    findings: list[dict[str, str]] = []
    for name in names:
        values = [
            float(record["metrics"][name])
            for record in records
            if record["status"] == "pass"
            and isinstance(record.get("metrics", {}).get(name), (int, float))
            and not isinstance(record["metrics"][name], bool)
        ]
        definition = definitions.get(name, {})
        unit = str(definition.get("unit", "unspecified"))
        direction = str(definition.get("direction", "informational"))
        metrics[f"{name}_sample_count"] = {
            "value": len(values),
            "unit": "samples",
            "direction": "informational",
        }
        metrics[f"{name}_mean"] = {
            "value": statistics.fmean(values),
            "unit": unit,
            "direction": direction,
        }
        metrics[f"{name}_median"] = {
            "value": statistics.median(values),
            "unit": unit,
            "direction": direction,
        }
        metrics[f"{name}_population_stddev"] = {
            "value": statistics.pstdev(values),
            "unit": unit,
            "direction": "informational",
        }
        for percentile in definition.get("percentiles", []):
            label = str(percentile).replace(".", "_")
            metrics[f"{name}_p{label}"] = {
                "value": nearest_rank(values, float(percentile)),
                "unit": unit,
                "direction": direction,
            }
        threshold = definition.get("threshold")
        if isinstance(threshold, (int, float)) and not isinstance(threshold, bool):
            observed = metrics[f"{name}_mean"]["value"]
            passed = (
                observed >= threshold
                if direction == "higher_is_better"
                else observed <= threshold
                if direction == "lower_is_better"
                else True
            )
            if not passed:
                findings.append(
                    fail(
                        f"{name}_threshold",
                        f"{name} mean {observed} failed threshold {threshold}",
                    )
                )
    return metrics, findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_directory", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if not args.result_directory.is_dir():
            raise ValueError("result directory does not exist")
        records = load_records(args.result_directory)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="benchmark_aggregation",
            summary="benchmark records are invalid",
            inputs=[str(args.result_directory)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No aggregate statistics were computed."],
        )
        emit_result(result, args.output)
        return 2
    metrics, findings = aggregate(
        records, load_definitions(args.result_directory)
    )
    result = make_result(
        skill=SKILL,
        check="benchmark_aggregation",
        summary=(
            "benchmark results aggregated"
            if not findings
            else "benchmark regression threshold failed"
        ),
        inputs=[str(args.result_directory)],
        metrics=metrics,
        findings=findings,
        evidence=[str(args.result_directory)],
        limitations=[
            "Statistics describe bundled records and do not establish sample independence."
        ],
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
