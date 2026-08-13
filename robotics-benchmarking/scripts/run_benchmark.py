#!/usr/bin/env python3
"""Run a validated benchmark only after explicit --execute authorization."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from result_contract import emit_result, make_result, portable_path
from validate_benchmark_manifest import (
    SKILL,
    finding,
    load_manifest,
    validate_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def command_for(command: list[str], seed: int) -> list[str]:
    return [item.replace("{seed}", str(seed)) for item in command]


def extract_metrics(
    stdout: str, definitions: list[dict[str, Any]]
) -> dict[str, float]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    metrics: dict[str, float] = {}
    for definition in definitions:
        value = payload.get(definition["field"])
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            metrics[definition["name"]] = float(value)
    return metrics


def execute_once(
    argv: list[str], cwd: Path, timeout: float, seed: int
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            shell=False,
            timeout=timeout,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        duration = time.monotonic() - started
        return {
            "status": "pass" if completed.returncode == 0 else "fail",
            "returncode": completed.returncode,
            "duration_seconds": duration,
            "seed": seed,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "fail",
            "returncode": None,
            "duration_seconds": time.monotonic() - started,
            "seed": seed,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "failure": "timeout",
        }


def invalid_result(path: Path, code: str, message: str) -> dict[str, Any]:
    return make_result(
        skill=SKILL,
        check="benchmark_execution",
        summary="benchmark execution input is invalid",
        inputs=[portable_path(path)],
        findings=[finding(code, message)],
        limitations=["No benchmark run was started."],
    )


def main() -> int:
    args = parse_args()
    try:
        data = load_manifest(args.manifest)
    except ValueError as exc:
        emit_result(
            invalid_result(args.manifest, "invalid_input", str(exc)), args.output
        )
        return 2
    findings = validate_manifest(data)
    if findings:
        result = make_result(
            skill=SKILL,
            check="benchmark_execution",
            summary="benchmark manifest failed admission",
            inputs=[portable_path(args.manifest)],
            findings=findings,
            limitations=["No benchmark run was started."],
        )
        emit_result(result, args.output)
        return 1
    if not args.execute:
        result = make_result(
            skill=SKILL,
            check="benchmark_execution",
            summary="benchmark validated; execution requires --execute",
            inputs=[portable_path(args.manifest)],
            requested_status="skip",
            limitations=["The benchmark command was deliberately not executed."],
        )
        emit_result(result, args.output)
        return 0

    output_dir = args.output_dir
    if output_dir is None:
        output_dir = args.manifest.parent / data["output_directory"]
    if output_dir.exists() and any(output_dir.iterdir()):
        emit_result(
            invalid_result(
                args.manifest,
                "output_directory_not_empty",
                f"refusing nonempty output directory: {portable_path(output_dir)}",
            ),
            args.output,
        )
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)

    working = Path(data["working_directory"])
    if not working.is_absolute():
        working = (args.manifest.parent / working).resolve()
    if not working.is_dir():
        emit_result(
            invalid_result(
                args.manifest,
                "working_directory",
                f"working directory is not a directory: {portable_path(working)}",
            ),
            args.output,
        )
        return 2

    seeds = data["seed_policy"]["seeds"]
    command = data["command"]
    timeout = float(data["timeout_seconds"])
    for index in range(data["warmups"]):
        seed = seeds[index % len(seeds)]
        execute_once(command_for(command, seed), working, timeout, seed)

    records: list[dict[str, Any]] = []
    for index in range(data["repeats"]):
        seed = seeds[index % len(seeds)]
        record = execute_once(
            command_for(command, seed), working, timeout, seed
        )
        record["run_index"] = index
        record["metrics"] = extract_metrics(
            record["stdout"], data["metrics"]
        )
        records.append(record)
        (output_dir / f"run-{index:04d}.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (output_dir / "manifest.yaml").write_text(
        yaml.safe_dump(data, sort_keys=True), encoding="utf-8"
    )

    failures = sum(record["status"] == "fail" for record in records)
    successes = len(records) - failures
    execution_findings = (
        [
            finding(
                "benchmark_run_failure",
                f"{failures} of {len(records)} measured runs failed",
            )
        ]
        if failures
        else []
    )
    result = make_result(
        skill=SKILL,
        check="benchmark_execution",
        summary=(
            "all benchmark runs completed"
            if not failures
            else "one or more benchmark runs failed"
        ),
        inputs=[portable_path(args.manifest)],
        metrics={
            "total_runs": {
                "value": len(records),
                "unit": "runs",
                "direction": "informational",
            },
            "successful_runs": {
                "value": successes,
                "unit": "runs",
                "direction": "higher_is_better",
            },
            "failure_rate": {
                "value": failures / len(records),
                "unit": "ratio",
                "direction": "lower_is_better",
            },
        },
        findings=execution_findings,
        evidence=[portable_path(output_dir)],
        limitations=[
            "Execution success does not establish scientific or hardware validity."
        ],
    )
    emit_result(result, args.output)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
