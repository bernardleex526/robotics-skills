#!/usr/bin/env python3
"""Validate immutable provenance and experiment-design declarations."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from result_contract import emit_result, make_result, portable_path


SKILL = "robotics-research-reproduction"
SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
MAX_INPUT_BYTES = 2 * 1024 * 1024
DIRECTIONS = {
    "higher_is_better",
    "lower_is_better",
    "target",
    "informational",
}


def finding(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def nonempty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def validate(data: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    source = data.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("repository"), str):
        findings.append(finding("repository_url", "source.repository is required"))
    revision = source.get("revision") if isinstance(source, dict) else None
    if not isinstance(revision, str) or not SHA40.fullmatch(revision):
        findings.append(
            finding(
                "immutable_revision",
                "source.revision must be a full 40-character commit SHA",
            )
        )

    environment = data.get("environment")
    if not isinstance(environment, dict):
        findings.append(finding("environment_identity", "environment is required"))
    else:
        digest = environment.get("container_digest")
        inventory = environment.get("inventory")
        locked_inventory = (
            isinstance(inventory, dict)
            and all(inventory.get(key) for key in ("os", "python", "lock_sha256"))
            and SHA256.fullmatch(str(inventory.get("lock_sha256", "")))
        )
        if not (
            isinstance(digest, str) and IMAGE_DIGEST.fullmatch(digest)
        ) and not locked_inventory:
            findings.append(
                finding(
                    "environment_identity",
                    "provide a container sha256 digest or locked environment inventory",
                )
            )

    datasets = data.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        findings.append(finding("dataset_identity", "datasets must be nonempty"))
    else:
        for index, dataset in enumerate(datasets):
            if not isinstance(dataset, dict):
                findings.append(
                    finding("dataset_identity", f"datasets[{index}] must be a mapping")
                )
                continue
            for key in ("source", "license", "split"):
                if not isinstance(dataset.get(key), str) or not dataset[key].strip():
                    findings.append(
                        finding(
                            "dataset_identity",
                            f"datasets[{index}].{key} is required",
                        )
                    )
            if not SHA256.fullmatch(str(dataset.get("sha256", ""))):
                findings.append(
                    finding(
                        "dataset_sha256",
                        f"datasets[{index}].sha256 must contain 64 hex characters",
                    )
                )

    seeds = data.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(not isinstance(seed, int) or isinstance(seed, bool) for seed in seeds)
        or len(set(seeds)) != len(seeds)
    ):
        findings.append(
            finding("seed_policy", "seeds must be a nonempty unique integer list")
        )
    repeat = data.get("repeat_policy")
    if (
        not isinstance(repeat, dict)
        or not isinstance(repeat.get("repeats"), int)
        or isinstance(repeat.get("repeats"), bool)
        or not 1 <= repeat["repeats"] <= 100
        or repeat.get("failed_runs") not in {"include", "retain_with_reason"}
    ):
        findings.append(
            finding(
                "repeat_policy",
                "repeat_policy requires bounded repeats and failed-run handling",
            )
        )

    baseline = data.get("baseline")
    if not isinstance(baseline, dict):
        findings.append(finding("baseline_contract", "baseline is required"))
    else:
        command = baseline.get("command")
        if not nonempty_strings(command):
            findings.append(
                finding("baseline_command", "baseline.command must be an argv array")
            )
        if not SHA256.fullmatch(str(baseline.get("config_sha256", ""))):
            findings.append(
                finding(
                    "baseline_config",
                    "baseline.config_sha256 must identify the exact configuration",
                )
            )

    metrics = data.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        findings.append(finding("metric_contract", "metrics must be nonempty"))
    else:
        for index, metric in enumerate(metrics):
            if (
                not isinstance(metric, dict)
                or not isinstance(metric.get("name"), str)
                or not isinstance(metric.get("unit"), str)
                or metric.get("direction") not in DIRECTIONS
            ):
                findings.append(
                    finding(
                        "metric_contract",
                        f"metrics[{index}] needs name, unit and explicit direction",
                    )
                )

    ablations = data.get("ablations")
    if not isinstance(ablations, list):
        findings.append(finding("ablation_contract", "ablations must be a list"))
    else:
        for index, ablation in enumerate(ablations):
            changed = (
                ablation.get("changed_variables")
                if isinstance(ablation, dict)
                else None
            )
            if not isinstance(changed, list) or len(changed) != 1:
                findings.append(
                    finding(
                        "isolated_ablation",
                        f"ablations[{index}] must change exactly one variable",
                    )
                )

    if not nonempty_strings(data.get("evidence")):
        findings.append(
            finding("evidence_paths", "evidence must contain portable paths or URIs")
        )
    if not isinstance(data.get("deviations"), list):
        findings.append(
            finding("declared_deviations", "deviations must be declared as a list")
        )
    return findings


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"required manifest is not a file: {portable_path(path)}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"manifest exceeds {MAX_INPUT_BYTES} bytes")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot parse manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load(args.manifest)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="reproduction_manifest",
            summary="manifest input is invalid",
            inputs=[portable_path(args.manifest)],
            findings=[finding("invalid_input", str(exc))],
            limitations=["No experiment fields were validated."],
        )
        emit_result(result, args.output)
        return 2

    findings = validate(data)
    result = make_result(
        skill=SKILL,
        check="reproduction_manifest",
        summary=(
            "reproduction manifest is admissible"
            if not findings
            else "reproduction manifest failed admission"
        ),
        inputs=[portable_path(args.manifest)],
        metrics={
            "dataset_count": {
                "value": len(data.get("datasets", [])),
                "unit": "datasets",
                "direction": "informational",
            },
            "seed_count": {
                "value": len(data.get("seeds", [])),
                "unit": "seeds",
                "direction": "informational",
            },
        },
        findings=findings,
        evidence=list(data.get("evidence", []))
        if isinstance(data.get("evidence"), list)
        else [],
        limitations=[
            "This check does not execute code, retrieve artifacts, or verify paper metrics."
        ],
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
