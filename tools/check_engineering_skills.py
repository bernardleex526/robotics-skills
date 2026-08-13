#!/usr/bin/env python3
"""Validate portable engineering-skill assets and runtime independence."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any

import yaml


REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "tools/engineering_skills_manifest.yaml"
CROSS_SKILL = re.compile(r"robotics-[a-z0-9-]+")
FORBIDDEN_RUNTIME = (
    "from tools",
    "import tools",
    "../",
    "/home/",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("engineering manifest must have schema_version: 1")
    skills = data.get("skills")
    if not isinstance(skills, dict) or not skills:
        raise ValueError("engineering manifest must declare skills")
    return data


def safe_relative(value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def check(repo: Path = REPO, manifest_path: Path = MANIFEST) -> list[str]:
    problems: list[str] = []
    try:
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"manifest: {exc}"]

    root_schema = repo / "tools/result.schema.json"
    root_helper = repo / "tools/result_contract_template.py"
    if not root_schema.is_file():
        problems.append("missing tools/result.schema.json")
    if not root_helper.is_file():
        problems.append("missing tools/result_contract_template.py")

    for skill, entry in sorted(manifest["skills"].items()):
        if not isinstance(entry, dict):
            problems.append(f"{skill}: manifest entry must be a mapping")
            continue
        root = repo / skill
        required = [
            Path("SKILL.md"),
            Path("LICENSE.txt"),
            Path("assets/result.schema.json"),
            Path("assets/run_manifest.example.yaml"),
            Path("scripts/result_contract.py"),
        ]
        scripts = entry.get("primary_scripts")
        if not isinstance(scripts, list) or not scripts:
            problems.append(f"{skill}: primary_scripts must be a nonempty list")
            scripts = []
        cases = entry.get("cases")
        if not isinstance(cases, list) or not cases:
            problems.append(f"{skill}: cases must be a nonempty list")
            cases = []
        case_scripts = {
            case.get("script")
            for case in cases
            if isinstance(case, dict)
        }
        if case_scripts != set(scripts):
            problems.append(
                f"{skill}: cases must cover each primary script exactly"
            )
        values = scripts + [
            entry.get("valid_fixture"),
            entry.get("invalid_fixture"),
        ]
        for index, case in enumerate(cases):
            if not isinstance(case, dict):
                problems.append(f"{skill}: cases[{index}] must be a mapping")
                continue
            values.extend(
                [
                    case.get("valid_fixture"),
                    case.get("invalid_fixture"),
                ]
            )
            if case.get("valid_exit") != 0:
                problems.append(f"{skill}: cases[{index}].valid_exit must be 0")
            invalid_exits = case.get("invalid_exits")
            if (
                not isinstance(invalid_exits, list)
                or not invalid_exits
                or any(value not in {1, 2} for value in invalid_exits)
            ):
                problems.append(
                    f"{skill}: cases[{index}].invalid_exits must use 1 or 2"
                )
        for value in values:
            relative = safe_relative(value)
            if relative is None:
                problems.append(f"{skill}: unsafe or invalid manifest path {value!r}")
            else:
                required.append(relative)
        for relative in required:
            if not (root / relative).exists():
                problems.append(f"{skill}: missing {relative.as_posix()}")

        local_schema = root / "assets/result.schema.json"
        if root_schema.is_file() and local_schema.is_file():
            if digest(root_schema) != digest(local_schema):
                problems.append(f"{skill}: result schema differs from root template")
        local_helper = root / "scripts/result_contract.py"
        if root_helper.is_file() and local_helper.is_file():
            if digest(root_helper) != digest(local_helper):
                problems.append(f"{skill}: result helper differs from root template")

        scripts_root = root / "scripts"
        if scripts_root.is_dir():
            for path in sorted(scripts_root.glob("*.py")):
                text = path.read_text(encoding="utf-8")
                for forbidden in FORBIDDEN_RUNTIME:
                    if forbidden in text:
                        problems.append(
                            f"{path.relative_to(repo).as_posix()}: "
                            f"forbidden runtime path {forbidden!r}"
                        )
                foreign = {
                    name for name in CROSS_SKILL.findall(text) if name != skill
                }
                if foreign:
                    problems.append(
                        f"{path.relative_to(repo).as_posix()}: "
                        f"cross-skill reference {sorted(foreign)}"
                    )
    return problems


def main() -> int:
    problems = check()
    if problems:
        print(
            f"engineering skill check failed ({len(problems)} findings):",
            file=sys.stderr,
        )
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    skill_count = len(load_manifest()["skills"])
    print(f"engineering skill check passed ({skill_count} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
