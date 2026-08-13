#!/usr/bin/env python3
"""Validate a bounded benchmark manifest without executing its command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from result_contract import emit_result, make_result, portable_path


SKILL = "robotics-benchmarking"
MAX_INPUT_BYTES = 2 * 1024 * 1024
DIRECTIONS = {
    "higher_is_better",
    "lower_is_better",
    "target",
    "informational",
}


def finding(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"benchmark manifest is not a file: {portable_path(path)}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"manifest exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot parse benchmark manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("benchmark manifest root must be a mapping")
    return data


def validate_manifest(data: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    command = data.get("command")
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(item, str) or not item for item in command)
    ):
        findings.append(
            finding(
                "argv_array_required",
                "command must be a nonempty YAML string array; scalar shell commands are rejected",
            )
        )

    timeout = data.get("timeout_seconds")
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not 0 < timeout <= 3600
    ):
        findings.append(
            finding("bounded_timeout", "timeout_seconds must be in (0, 3600]")
        )
    repeats = data.get("repeats")
    if (
        not isinstance(repeats, int)
        or isinstance(repeats, bool)
        or not 1 <= repeats <= 100
    ):
        findings.append(
            finding("bounded_repeats", "repeats must be an integer in [1, 100]")
        )
    warmups = data.get("warmups")
    if (
        not isinstance(warmups, int)
        or isinstance(warmups, bool)
        or not 0 <= warmups <= 20
    ):
        findings.append(
            finding("bounded_warmups", "warmups must be an integer in [0, 20]")
        )
    for key in ("working_directory", "output_directory"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            findings.append(finding(key, f"{key} must be a nonempty path string"))

    policy = data.get("seed_policy")
    seeds = policy.get("seeds") if isinstance(policy, dict) else None
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(not isinstance(seed, int) or isinstance(seed, bool) for seed in seeds)
    ):
        findings.append(
            finding("seed_policy", "seed_policy.seeds must be nonempty integers")
        )

    metrics = data.get("metrics")
    names: set[str] = set()
    if not isinstance(metrics, list) or not metrics:
        findings.append(finding("metric_contract", "metrics must be nonempty"))
    else:
        for index, metric in enumerate(metrics):
            if not isinstance(metric, dict):
                findings.append(
                    finding("metric_contract", f"metrics[{index}] must be a mapping")
                )
                continue
            name = metric.get("name")
            if not isinstance(name, str) or not name or name in names:
                findings.append(
                    finding(
                        "metric_name",
                        f"metrics[{index}].name must be unique and nonempty",
                    )
                )
            else:
                names.add(name)
            if not isinstance(metric.get("unit"), str) or not metric["unit"]:
                findings.append(
                    finding("metric_unit", f"metrics[{index}].unit is required")
                )
            if metric.get("direction") not in DIRECTIONS:
                findings.append(
                    finding(
                        "metric_direction",
                        f"metrics[{index}].direction must be explicit",
                    )
                )
            if metric.get("source") != "stdout_json" or not isinstance(
                metric.get("field"), str
            ):
                findings.append(
                    finding(
                        "metric_source",
                        f"metrics[{index}] must declare stdout_json and a field",
                    )
                )
            percentiles = metric.get("percentiles", [])
            if not isinstance(percentiles, list) or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0 < value <= 100
                for value in percentiles
            ):
                findings.append(
                    finding(
                        "metric_percentiles",
                        f"metrics[{index}].percentiles must be in (0, 100]",
                    )
                )
    return findings


def result_for(
    path: Path, data: dict[str, Any], findings: list[dict[str, str]]
) -> dict[str, Any]:
    return make_result(
        skill=SKILL,
        check="benchmark_manifest",
        summary=(
            "benchmark manifest is admissible"
            if not findings
            else "benchmark manifest failed admission"
        ),
        inputs=[portable_path(path)],
        metrics={
            "declared_repeats": {
                "value": data.get("repeats"),
                "unit": "runs",
                "direction": "informational",
            }
        },
        findings=findings,
        limitations=["The benchmark command was not executed."],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load_manifest(args.manifest)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="benchmark_manifest",
            summary="benchmark manifest input is invalid",
            inputs=[portable_path(args.manifest)],
            findings=[finding("invalid_input", str(exc))],
            limitations=["No benchmark fields were validated."],
        )
        emit_result(result, args.output)
        return 2
    findings = validate_manifest(data)
    emit_result(result_for(args.manifest, data, findings), args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
