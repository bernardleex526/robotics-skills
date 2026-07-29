#!/usr/bin/env python3
"""Analyze a bounded six-axis wrench CSV through an explicit YAML contract."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any

import yaml

from result_contract import emit_result, make_result


SKILL = "robotics-force-control"
AXES = ("fx", "fy", "fz", "tx", "ty", "tz")
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_CSV_BYTES = 64 * 1024 * 1024


def fail(code: str, message: str) -> dict[str, str]:
    return {"level": "fail", "code": code, "message": message}


def finite_array(value: Any, positive: bool = False) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 6
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(item)
            and (not positive or item > 0)
            for item in value
        )
    )


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"wrench manifest is not a file: {path}")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError(f"manifest exceeds {MAX_MANIFEST_BYTES} bytes")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot parse wrench manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("wrench manifest root must be a mapping")
    return data


def contract_findings(data: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if data.get("time_unit") != "s":
        findings.append(fail("time_unit", "time_unit must be s"))
    if data.get("force_unit") != "N":
        findings.append(fail("force_unit", "force_unit must be N"))
    if data.get("torque_unit") != "N*m":
        findings.append(fail("torque_unit", "torque_unit must be N*m"))
    if not isinstance(data.get("frame_id"), str) or not data["frame_id"]:
        findings.append(fail("wrench_frame", "frame_id is required"))
    columns = data.get("columns")
    if (
        not isinstance(columns, dict)
        or not isinstance(columns.get("time"), str)
        or not isinstance(columns.get("wrench"), list)
        or len(columns["wrench"]) != 6
        or any(not isinstance(item, str) or not item for item in columns["wrench"])
    ):
        findings.append(
            fail("column_contract", "columns must name time and six wrench axes")
        )
    if not finite_array(data.get("saturation_limits"), positive=True):
        findings.append(
            fail("saturation_limits", "six positive saturation limits are required")
        )
    gates = data.get("gates")
    if not isinstance(gates, dict):
        findings.append(fail("log_gates", "gates must be a mapping"))
    else:
        fraction = gates.get("max_saturation_fraction")
        if (
            not isinstance(fraction, (int, float))
            or isinstance(fraction, bool)
            or not math.isfinite(fraction)
            or not 0 <= fraction <= 1
        ):
            findings.append(
                fail("saturation_gate", "max_saturation_fraction must be in [0,1]")
            )
        for key in ("max_abs_bias", "max_rms", "max_abs_drift_per_s"):
            if not finite_array(gates.get(key), positive=True):
                findings.append(fail("log_gates", f"{key} needs six positive values"))
    return findings


def read_csv(
    manifest_path: Path, data: dict[str, Any]
) -> tuple[list[float], list[list[float]]]:
    value = data.get("csv")
    if not isinstance(value, str) or not value:
        raise ValueError("csv must be a relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("csv must be a safe relative path")
    path = manifest_path.parent / relative
    if not path.is_file():
        raise ValueError(f"wrench CSV is not a file: {path}")
    if path.stat().st_size > MAX_CSV_BYTES:
        raise ValueError(f"CSV exceeds {MAX_CSV_BYTES} bytes")
    columns = data["columns"]
    expected = [columns["time"], *columns["wrench"]]
    times: list[float] = []
    rows: list[list[float]] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None or any(
                name not in reader.fieldnames for name in expected
            ):
                raise ValueError("CSV does not contain every declared column")
            for index, row in enumerate(reader, start=2):
                try:
                    values = [float(row[name]) for name in expected]
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"CSV row {index} is not numeric") from exc
                if not all(math.isfinite(value) for value in values):
                    raise ValueError(f"CSV row {index} contains nonfinite values")
                times.append(values[0])
                rows.append(values[1:])
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"cannot read wrench CSV: {exc}") from exc
    if len(rows) < 3:
        raise ValueError("wrench CSV needs at least three samples")
    return times, rows


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def slope(times: list[float], values: list[float]) -> float:
    time_mean = mean(times)
    value_mean = mean(values)
    denominator = sum((value - time_mean) ** 2 for value in times)
    if denominator == 0:
        return 0.0
    return sum(
        (time - time_mean) * (value - value_mean)
        for time, value in zip(times, values)
    ) / denominator


def analyze(
    times: list[float], rows: list[list[float]], data: dict[str, Any]
) -> tuple[dict[str, float | int], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    monotonic = all(current > previous for previous, current in zip(times, times[1:]))
    if not monotonic:
        findings.append(
            fail("timestamp_monotonic", "wrench timestamps must strictly increase")
        )
    duration = times[-1] - times[0]
    sample_rate = (len(times) - 1) / duration if duration > 0 else 0.0
    columns = [[row[index] for row in rows] for index in range(6)]
    biases = [mean(values) for values in columns]
    rms_values = [
        math.sqrt(mean([(value - bias) ** 2 for value in values]))
        for values, bias in zip(columns, biases)
    ]
    drift_values = [slope(times, values) for values in columns]
    limits = data["saturation_limits"]
    saturated = sum(
        any(abs(value) >= limit for value, limit in zip(row, limits))
        for row in rows
    )
    saturation_fraction = saturated / len(rows)
    gates = data["gates"]
    if saturation_fraction > gates["max_saturation_fraction"]:
        findings.append(
            fail(
                "saturation_fraction",
                f"saturation fraction {saturation_fraction} exceeds {gates['max_saturation_fraction']}",
            )
        )
    for index, axis in enumerate(AXES):
        if abs(biases[index]) > gates["max_abs_bias"][index]:
            findings.append(fail("bias_gate", f"{axis} bias exceeds its gate"))
        if rms_values[index] > gates["max_rms"][index]:
            findings.append(fail("rms_gate", f"{axis} RMS exceeds its gate"))
        if abs(drift_values[index]) > gates["max_abs_drift_per_s"][index]:
            findings.append(fail("drift_gate", f"{axis} drift exceeds its gate"))
    metrics: dict[str, float | int] = {
        "sample_count": len(rows),
        "sample_rate_hz": sample_rate,
        "saturation_count": saturated,
        "saturation_fraction": saturation_fraction,
    }
    for index, axis in enumerate(AXES):
        metrics[f"{axis}_bias"] = biases[index]
        metrics[f"{axis}_rms_about_mean"] = rms_values[index]
        metrics[f"{axis}_drift_per_s"] = drift_values[index]
    return metrics, findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load_manifest(args.manifest)
        initial_findings = contract_findings(data)
        if initial_findings:
            metrics: dict[str, float | int] = {}
            findings = initial_findings
        else:
            times, rows = read_csv(args.manifest, data)
            metrics, findings = analyze(times, rows, data)
    except ValueError as exc:
        result = make_result(
            skill=SKILL,
            check="wrench_log",
            summary="wrench log input is invalid",
            inputs=[str(args.manifest)],
            findings=[fail("invalid_input", str(exc))],
            limitations=["No complete wrench analysis was performed."],
        )
        emit_result(result, args.output)
        return 2
    metric_results: dict[str, dict[str, Any]] = {}
    for name, value in metrics.items():
        if name == "sample_rate_hz":
            unit = "Hz"
        elif name.endswith("_fraction"):
            unit = "ratio"
        elif name.endswith("_count") or name == "sample_count":
            unit = "samples"
        elif name.startswith("f"):
            unit = "N/s" if name.endswith("_per_s") else "N"
        elif name.startswith("t"):
            unit = "N*m/s" if name.endswith("_per_s") else "N*m"
        else:
            unit = "unspecified"
        metric_results[name] = {
            "value": value,
            "unit": unit,
            "direction": (
                "lower_is_better"
                if any(token in name for token in ("rms", "drift", "saturation"))
                else "informational"
            ),
        }
    result = make_result(
        skill=SKILL,
        check="wrench_log",
        summary=(
            "wrench log passed declared gates"
            if not findings
            else "wrench log failed declared gates"
        ),
        inputs=[str(args.manifest)],
        environment={"frame_id": data.get("frame_id")},
        metrics=metric_results,
        findings=findings,
        limitations=[
            "Offline statistics do not infer contact or prove calibration, gravity compensation, or control stability."
        ],
    )
    emit_result(result, args.output)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
