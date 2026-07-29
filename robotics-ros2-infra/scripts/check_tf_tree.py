#!/usr/bin/env python3
"""Inspect a ROS 2 TF graph without depending on wall time for sampling.

Exit codes: 0 healthy, 1 findings marked FAIL, 2 invalid arguments/environment.
The pure ``analyze`` function is intentionally importable without ROS 2.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Mapping
from collections.abc import Callable
from typing import Any


Result = tuple[str, str, str]


def application_args(
    argv: list[str],
    remove_ros_args: Callable[..., list[str]],
) -> list[str]:
    """Return tool arguments while preserving ROS arguments for rclpy.init."""
    program = "check_tf_tree.py"
    remaining = remove_ros_args(args=[program, *argv])
    if remaining and remaining[0] == program:
        return remaining[1:]
    return remaining


def _find_cycles(parents: Mapping[str, str | None]) -> list[list[str]]:
    """Return unique parent-pointer cycles."""
    cycles: list[list[str]] = []
    seen_cycles: set[frozenset[str]] = set()

    for start in parents:
        path: list[str] = []
        positions: dict[str, int] = {}
        current: str | None = start
        while current and current in parents:
            if current in positions:
                cycle = path[positions[current]:]
                key = frozenset(cycle)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    cycles.append(cycle)
                break
            positions[current] = len(path)
            path.append(current)
            current = parents.get(current)
    return cycles


def analyze(
    frames: Mapping[str, Mapping[str, Any]],
    now_s: float,
    stale_s: float,
    chain: list[str],
) -> tuple[list[Result], list[str]]:
    """Analyze output parsed from ``tf2_ros.Buffer.all_frames_as_yaml``."""
    results: list[Result] = []
    tree_lines: list[str] = []

    if not frames:
        results.append(
            (
                "FAIL",
                "TF 存在性",
                "缓冲区没有变换；检查 /tf、/tf_static、命名空间和发现范围",
            )
        )
        return results, tree_lines

    parents: dict[str, str | None] = {
        str(frame): (
            str(info.get("parent"))
            if info.get("parent") not in (None, "", "NO_PARENT")
            else None
        )
        for frame, info in frames.items()
    }
    all_frames = set(parents)
    all_frames.update(parent for parent in parents.values() if parent)
    roots = sorted(frame for frame in all_frames if not parents.get(frame))
    cycles = _find_cycles(parents)

    results.append(
        ("PASS", "帧数量", f"{len(all_frames)} 个帧，{len(frames)} 条父子关系")
    )

    if cycles:
        rendered = "; ".join(" → ".join(cycle + [cycle[0]]) for cycle in cycles)
        results.append(("FAIL", "TF 环", f"检测到父子关系环：{rendered}"))

    if not roots:
        results.append(
            (
                "FAIL",
                "树连通性",
                "没有可识别的根帧；常见原因是 TF 环或父帧数据损坏",
            )
        )
    elif len(roots) > 1:
        results.append(
            (
                "FAIL",
                "树连通性",
                f"检测到 {len(roots)} 个根：{roots}；跨根 TF 查询会失败",
            )
        )
    elif not cycles:
        results.append(("PASS", "树连通性", f"单根 `{roots[0]}`"))

    stale: list[tuple[str, float]] = []
    future: list[tuple[str, float]] = []
    checked_dynamic = 0
    for frame, info in frames.items():
        recent = info.get("most_recent_transform")
        rate = info.get("rate")
        try:
            recent_s = float(recent)
            rate_hz = float(rate)
        except (TypeError, ValueError):
            continue
        # all_frames_as_yaml does not retain the source topic. Zero rate/stamp is
        # therefore only a static candidate, not proof that the edge came from
        # /tf_static. Avoid inventing an age for entries without usable timing.
        if recent_s == 0.0 or rate_hz <= 0.0:
            continue
        checked_dynamic += 1
        age = now_s - recent_s
        if age < 0:
            future.append((frame, age))
        elif age > stale_s:
            stale.append((frame, age))

    if future:
        detail = "; ".join(
            f"{frame} 超前 {-age:.3f}s" for frame, age in future[:6]
        )
        results.append(
            (
                "WARN",
                "变换新鲜度",
                f"变换时间晚于当前 ROS 时钟：{detail}；先核对 /clock、use_sim_time 和主机对时",
            )
        )
    if stale:
        detail = "; ".join(
            f"{frame} 落后 {age:.2f}s"
            for frame, age in sorted(stale, key=lambda item: -item[1])[:6]
        )
        results.append(
            (
                "FAIL",
                "变换新鲜度",
                f"{len(stale)} 个动态变换超过 {stale_s:g}s：{detail}",
            )
        )
    if checked_dynamic and not future and not stale:
        results.append(
            ("PASS", "变换新鲜度", f"动态变换均在 {stale_s:g}s 阈值内")
        )
    elif not checked_dynamic:
        results.append(
            (
                "WARN",
                "变换新鲜度",
                "未识别到可做时效检查的动态变换；all_frames YAML 不能可靠区分"
                " /tf_static 与低频/一次性动态 TF，请结合 topic 记录确认来源",
            )
        )

    if chain:
        broken: list[str] = []
        for ancestor, descendant in zip(chain, chain[1:]):
            if ancestor not in all_frames or descendant not in all_frames:
                broken.append(f"{ancestor}→{descendant}（帧不存在）")
                continue
            current: str | None = descendant
            visited: set[str] = set()
            while current and current not in visited and current != ancestor:
                visited.add(current)
                current = parents.get(current)
            if current != ancestor:
                broken.append(f"{ancestor}→{descendant}（不连通或遇到环）")
        if broken:
            results.append(("FAIL", "期望链路", "；".join(broken)))
        else:
            results.append(("PASS", "期望链路", " → ".join(chain)))

    children: dict[str, list[str]] = {}
    for child, parent in parents.items():
        if parent:
            children.setdefault(parent, []).append(child)

    drawn: set[str] = set()

    def draw(node: str, prefix: str = "", is_last: bool = True) -> None:
        marker = "" if not prefix else ("└─ " if is_last else "├─ ")
        if node in drawn:
            tree_lines.append(f"{prefix}{marker}{node}  [cycle]")
            return
        drawn.add(node)
        info = frames.get(node, {})
        tag = ""
        try:
            rate_hz = float(info.get("rate"))
            if float(info.get("most_recent_transform")) == 0.0 or rate_hz <= 0:
                tag = "  [无速率/零时间；来源未判定]"
            else:
                tag = f"  [{rate_hz:.1f} Hz]"
        except (TypeError, ValueError):
            pass
        tree_lines.append(f"{prefix}{marker}{node}{tag}")
        kids = sorted(children.get(node, []))
        for index, child in enumerate(kids):
            extension = "   " if is_last else "│  "
            draw(child, prefix + extension, index == len(kids) - 1)

    for root in roots:
        draw(root)

    return results, tree_lines


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="检查 ROS 2 TF 树的连通性、父子环、新鲜度与期望链路"
    )
    parser.add_argument("--duration", type=float, default=3.0, help="采样秒数")
    parser.add_argument("--stale", type=float, default=1.0, help="动态 TF 陈旧阈值秒")
    parser.add_argument(
        "--chain",
        nargs="+",
        default=[],
        help="期望链路，例如 --chain map odom base_link laser",
    )
    args = parser.parse_args(argv)
    if args.duration <= 0:
        parser.error("--duration 必须大于 0")
    if args.stale <= 0:
        parser.error("--stale 必须大于 0")
    if args.chain and len(args.chain) < 2:
        parser.error("--chain 至少需要两个帧")
    return args


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if raw_args in (["-h"], ["--help"]):
        parse_args(raw_args)
    try:
        import rclpy
        import yaml
        from rclpy.node import Node
        from rclpy.utilities import remove_ros_args
        from tf2_ros import Buffer, TransformListener
    except ImportError as exc:
        print(
            f"[FATAL] ROS 2 依赖导入失败: {exc}\n"
            "请先 source /opt/ros/<distro>/setup.bash，并安装 tf2_ros 与 PyYAML",
            file=sys.stderr,
        )
        return 2
    args = parse_args(application_args(raw_args, remove_ros_args))

    class TfInspector(Node):
        def __init__(self) -> None:
            super().__init__("tf_tree_inspector")
            self.buffer = Buffer()
            self.listener = TransformListener(self.buffer, self)

        def snapshot(self) -> dict[str, dict[str, Any]]:
            raw = self.buffer.all_frames_as_yaml()
            if not raw or raw.strip() in ("", "{}"):
                return {}
            data = yaml.safe_load(raw)
            return data if isinstance(data, dict) else {}

    rclpy.init(args=["check_tf_tree.py", *raw_args])
    node = None
    try:
        node = TfInspector()
        deadline = time.monotonic() + args.duration
        print(f"监听 /tf 与 /tf_static {args.duration:g} s ...\n")
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)

        results, tree = analyze(
            node.snapshot(),
            node.get_clock().now().nanoseconds * 1e-9,
            args.stale,
            args.chain,
        )
        if tree:
            print("TF 树:")
            for line in tree:
                print(f"  {line}")
            print()

        failed = False
        for level, check, detail in results:
            print(f"[{level}] {check} — {detail}")
            failed |= level == "FAIL"
        print("\n结论:", "TF 树存在 FAIL" if failed else "未发现 TF FAIL")
        return 1 if failed else 0
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
