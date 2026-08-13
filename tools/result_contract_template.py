#!/usr/bin/env python3
"""Portable result construction shared by engineering-skill scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


STATUSES = {"pass", "warn", "fail", "skip"}
LEVELS = {"info", "warn", "fail"}


def overall_status(
    findings: Iterable[Mapping[str, Any]],
    requested: str = "pass",
    gates: Iterable[Mapping[str, Any]] = (),
) -> str:
    """Resolve status with fail > skip > warn > pass precedence."""
    if requested not in STATUSES:
        raise ValueError(f"unsupported requested status: {requested}")
    finding_levels = {item.get("level") for item in findings}
    if "fail" in finding_levels or any(
        not gate.get("passed", False) and gate.get("level") == "fail"
        for gate in gates
    ):
        return "fail"
    if requested == "skip":
        return "skip"
    if requested == "fail":
        return "fail"
    if "warn" in finding_levels or any(
        not gate.get("passed", False) and gate.get("level") == "warn"
        for gate in gates
    ):
        return "warn"
    return requested


def make_result(
    *,
    skill: str,
    check: str,
    summary: str,
    findings: Iterable[Mapping[str, Any]] | None = None,
    metrics: Mapping[str, Mapping[str, Any]] | None = None,
    inputs: Iterable[Any] | None = None,
    environment: Mapping[str, Any] | None = None,
    gates: Iterable[Mapping[str, Any]] | None = None,
    evidence: Iterable[Any] | None = None,
    limitations: Iterable[str] | None = None,
    requested_status: str = "pass",
) -> dict[str, Any]:
    """Build a deterministic common result dictionary."""
    finding_items = [dict(item) for item in findings or ()]
    gate_items = [dict(item) for item in gates or ()]
    for item in finding_items:
        if item.get("level") not in LEVELS:
            raise ValueError(f"unsupported finding level: {item.get('level')}")
    for item in gate_items:
        if item.get("level") not in LEVELS:
            raise ValueError(f"unsupported gate level: {item.get('level')}")
    return {
        "schema_version": "1.0.0",
        "skill": skill,
        "check": check,
        "status": overall_status(
            finding_items, requested=requested_status, gates=gate_items
        ),
        "summary": summary,
        "inputs": list(inputs or ()),
        "environment": dict(environment or {}),
        "metrics": {
            name: dict(value) for name, value in (metrics or {}).items()
        },
        "gates": gate_items,
        "findings": finding_items,
        "evidence": list(evidence or ()),
        "limitations": list(limitations or ()),
    }


def portable_path(value: str | Path) -> str:
    """Render a filesystem path as a stable POSIX-style string.

    Structured payload fields (``inputs``, ``evidence``) and user-facing
    messages must not leak platform-native separators, so Windows runs emit
    forward-slash paths identical to POSIX runs.
    """
    return Path(value).as_posix()


def exit_code(result: Mapping[str, Any]) -> int:
    """Map a completed result to the repository CLI exit contract."""
    return 1 if result.get("status") == "fail" else 0


def json_text(result: Mapping[str, Any]) -> str:
    """Serialize a result reproducibly for stdout and artifacts."""
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)


def emit_result(
    result: Mapping[str, Any], output: str | Path | None = None
) -> None:
    """Print JSON and optionally write the same deterministic payload."""
    payload = json_text(result) + "\n"
    if output is not None:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload, encoding="utf-8")
    print(payload, end="")
