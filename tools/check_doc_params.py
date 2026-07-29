#!/usr/bin/env python3
"""Validate version-scoped parameter names used in repository documentation.

This is a regression guard backed by a reviewed manifest snapshot. It does not
query upstream repositories and must not be described as proof that every
parameter in every ROS distribution is valid.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("param_manifest.yaml")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^```")
PARAM_LIKE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]{2,}$")
ALLOW_MENTION = re.compile(r"<!--\s*param-check:\s*allow-mention\s*-->")


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("需要 PyYAML：python3 -m pip install -r requirements-dev.txt") from exc
    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict) or not isinstance(data.get("projects"), dict):
        raise ValueError(f"{path}: manifest 缺少 projects 映射")
    if not isinstance(data.get("forbidden", {}), dict):
        raise ValueError(f"{path}: forbidden 必须是映射")
    return data


def compile_owns(
    manifest: dict[str, Any],
) -> list[tuple[str, re.Pattern[str], set[str], str]]:
    compiled: list[tuple[str, re.Pattern[str], set[str], str]] = []
    for project, specification in manifest["projects"].items():
        known = set(specification.get("known") or [])
        source = str(specification.get("source", ""))
        for pattern in specification.get("owns") or []:
            compiled.append((project, re.compile(pattern), known, source))
    return compiled


def token_candidates(token: str) -> list[str]:
    candidates = [token]
    generic = re.sub(r"\.<[^>]+>\.", ".", token)
    if generic != token:
        candidates.append(generic)
    parts = token.split(".")
    if len(parts) == 3:
        candidates.append(f"{parts[0]}.{parts[2]}")
    return candidates


def extract_tokens(text: str) -> list[tuple[int, str]]:
    tokens: list[tuple[int, str]] = []
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            for match in re.finditer(r"([A-Za-z][A-Za-z0-9_.]{2,})\s*:", line):
                tokens.append((line_number, match.group(1)))
            for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9_.]{2,})\b", line):
                tokens.append((line_number, match.group(1)))
        else:
            for match in INLINE_CODE.finditer(line):
                for word in re.split(r"[\s,;()\[\]{}<>=\"']+", match.group(1).strip()):
                    word = word.strip().rstrip(":")
                    if word:
                        tokens.append((line_number, word))
    return tokens


def display_name(path: Path, display_root: Path | None) -> str:
    if display_root is not None:
        try:
            return str(path.resolve().relative_to(display_root.resolve()))
        except ValueError:
            pass
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def check_file(
    path: Path,
    owns: list[tuple[str, re.Pattern[str], set[str], str]],
    forbidden: dict[str, dict[str, str]],
    *,
    display_root: Path | None = None,
) -> list[str]:
    text = path.read_text(encoding="utf-8")
    shown = display_name(path, display_root)
    lines = text.splitlines()
    allowed = {
        line_number
        for line_number, line in enumerate(lines, start=1)
        if ALLOW_MENTION.search(line)
    }
    problems: list[str] = []

    for line_number, line in enumerate(lines, start=1):
        if line_number in allowed:
            continue
        for bad, information in forbidden.items():
            if re.search(rf"\b{re.escape(bad)}\b", line):
                problems.append(
                    f"{shown}:{line_number}: 禁用参数 `{bad}` — "
                    f"{information.get('reason', '')}; 建议 "
                    f"{information.get('instead', '?')}"
                )

    for line_number, token in extract_tokens(text):
        if line_number in allowed or not PARAM_LIKE.match(token):
            continue
        for project, pattern, known, source in owns:
            candidates = token_candidates(token)
            if not any(pattern.search(candidate) for candidate in candidates):
                continue
            if any(candidate in known for candidate in candidates):
                break
            problems.append(
                f"{shown}:{line_number}: `{token}` 匹配 {project} 的受管参数家族"
                f"（{pattern.pattern}）但不在该版本清单；来源 {source}"
            )
            break
    return problems


def selftest() -> int:
    manifest = load_manifest(MANIFEST)
    owns = compile_owns(manifest)
    forbidden = manifest.get("forbidden") or {}
    cases = [
        ("Tune `sm_search_window`.\n", True),
        ("Tune `loop_search_minimum_distance`.\n", True),
        ("Tune `loop_search_maximum_distance`.\n", False),
        ("Tune `correlation_search_space_smear_deviation`.\n", False),
        ("Tune `correlation_search_space_bogus`.\n", True),
        ("Set `imuAccNoise`.\n", False),
        ("Set `imuBogusNoise`.\n", True),
        ("Set `constraints.goal_time`.\n", False),
        ("Set `constraints.bogus_tolerance`.\n", True),
        (
            "`sm_search_window` is an invalid example "
            "<!-- param-check: allow-mention -->\n",
            False,
        ),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for index, (content, should_fail) in enumerate(cases):
            path = root / f"case-{index}.md"
            path.write_text(content, encoding="utf-8")
            problems = check_file(
                path, owns, forbidden, display_root=root
            )
            if bool(problems) != should_fail:
                failures.append(
                    f"case {index}: expected {'FAIL' if should_fail else 'PASS'}: "
                    f"{content.strip()}"
                )
    if failures:
        print("\n".join(failures))
        return 1
    print(f"selftest passed ({len(cases)} cases)")
    return 0


def markdown_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix.lower() == ".md" else []
    return sorted(
        path
        for path in root.rglob("*.md")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("root", nargs="?", help="待扫描目录或 Markdown 文件")
    args = parser.parse_args(argv)
    try:
        if args.selftest:
            return selftest()
        manifest = load_manifest(MANIFEST)
    except (RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    root = Path(args.root).resolve() if args.root else REPO
    if not root.exists():
        print(f"[ERROR] 路径不存在：{root}", file=sys.stderr)
        return 2
    files = markdown_files(root)
    if not files:
        print("[ERROR] 没有 Markdown 文件", file=sys.stderr)
        return 2

    owns = compile_owns(manifest)
    forbidden = manifest.get("forbidden") or {}
    problems: list[str] = []
    display_root = root if root.is_dir() else root.parent
    for path in files:
        problems.extend(
            check_file(path, owns, forbidden, display_root=display_root)
        )
    print(
        f"checked {len(files)} markdown files against "
        f"{len(manifest['projects'])} version-scoped snapshots"
    )
    for problem in problems:
        print(f"  {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
