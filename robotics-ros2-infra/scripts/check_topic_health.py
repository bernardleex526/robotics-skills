#!/usr/bin/env python3
"""Measure ROS 2 topic rate and observable timestamp properties.

Sampling duration uses ``time.monotonic`` so frozen simulated time cannot hang
the process. Timestamp age is only meaningful when publisher and subscriber
ROS clocks share a domain; the tool reports evidence, not an invented cause.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from typing import Any


Result = tuple[str, str, str]

# Illustrative admission checks. Override topic names and thresholds for the
# actual sensor, driver mode, and task.
PRESETS: dict[str, dict[str, float]] = {
    "slam2d": {"/scan": 10.0, "/odom": 20.0},
    "lio": {"/points": 10.0, "/imu/data": 200.0},
    "vio": {"/camera/image_raw": 15.0, "/imu/data": 100.0},
    "control": {"/joint_states": 50.0},
}

NEAR_ZERO_AGE_S = 0.0005


def application_args(
    argv: list[str],
    remove_ros_args: Callable[..., list[str]],
) -> list[str]:
    """Return tool arguments while leaving the original ROS arguments intact."""
    program = "check_topic_health.py"
    remaining = remove_ros_args(args=[program, *argv])
    if remaining and remaining[0] == program:
        return remaining[1:]
    return remaining


def require_single_topic_type(name: str, types: Sequence[str]) -> str:
    """Reject an ambiguous ROS graph instead of silently choosing one type."""
    if len(types) != 1:
        rendered = ", ".join(types) if types else "none"
        raise ValueError(f"{name} 发现多个类型或无唯一类型: {rendered}")
    return types[0]


def resolve_topic_targets(
    targets: Mapping[str, float | None],
    resolve_name: Callable[[str], str],
) -> dict[str, float | None]:
    """Resolve relative ROS names exactly as the checker node will use them."""
    resolved: dict[str, float | None] = {}
    for requested, threshold in targets.items():
        canonical = resolve_name(requested)
        if canonical in resolved and resolved[canonical] != threshold:
            raise ValueError(
                f"{requested} 与其他输入解析到同一话题 {canonical}，但门槛不同"
            )
        resolved[canonical] = threshold
    return resolved


class TopicProbe:
    """Accumulate transport-independent observations for one topic."""

    def __init__(self, name: str, expect_hz: float | None):
        self.name = name
        self.expect_hz = expect_hz
        self.publisher_count = 1
        self.arrival: deque[float] = deque()
        self.stamps: list[float] = []
        self.ages: list[float] = []
        self.has_header: bool | None = None
        self.zero_stamps = 0
        self.backward = 0
        self.duplicates = 0
        self._last_stamp: float | None = None

    def add_observation(
        self,
        arrival_mono_s: float,
        stamp_s: float | None,
        receipt_ros_s: float,
    ) -> None:
        self.arrival.append(arrival_mono_s)
        if stamp_s is None:
            self.has_header = False
            return
        self.has_header = True
        if stamp_s == 0.0:
            self.zero_stamps += 1
            return
        self.stamps.append(stamp_s)
        self.ages.append(receipt_ros_s - stamp_s)
        if self._last_stamp is not None:
            if stamp_s < self._last_stamp:
                self.backward += 1
            elif stamp_s == self._last_stamp:
                self.duplicates += 1
        self._last_stamp = stamp_s

    def add_message(
        self, msg: Any, arrival_mono_s: float, receipt_ros_s: float
    ) -> None:
        stamp = getattr(getattr(msg, "header", None), "stamp", None)
        stamp_s = None
        if stamp is not None:
            stamp_s = float(stamp.sec) + float(stamp.nanosec) * 1e-9
        self.add_observation(arrival_mono_s, stamp_s, receipt_ros_s)

    @property
    def count(self) -> int:
        return len(self.arrival)

    def rate_hz(self) -> float:
        if self.count < 2:
            return 0.0
        span = self.arrival[-1] - self.arrival[0]
        return (self.count - 1) / span if span > 0 else 0.0

    def evaluate(self, observation_duration_s: float | None = None) -> list[Result]:
        output: list[Result] = []
        if self.count == 0:
            return [
                (
                    "FAIL",
                    "有数据",
                    "采样窗口内没有消息；检查发布节点、话题名、发现范围与 QoS",
                )
            ]

        interarrival_rate = self.rate_hz()
        if observation_duration_s is not None and observation_duration_s > 0:
            window_rate = self.count / observation_duration_s
            admission_rate = min(window_rate, interarrival_rate)
            rate_detail = (
                f"窗口 {window_rate:.1f} Hz；消息内到达率 "
                f"{interarrival_rate:.1f} Hz；验收率 {admission_rate:.1f} Hz"
            )
        else:
            admission_rate = interarrival_rate
            rate_detail = f"验收率 {admission_rate:.1f} Hz（未提供完整观察窗口）"
        if self.expect_hz is None and self.count < 2:
            output.append(
                (
                    "WARN",
                    "频率",
                    f"{rate_detail}；只有 {self.count} 条消息，不足以估计周期频率",
                )
            )
        elif self.expect_hz is None:
            output.append(("PASS", "频率", f"{rate_detail}；未配置任务门槛"))
        elif admission_rate >= self.expect_hz:
            output.append(
                ("PASS", "频率", f"{rate_detail} ≥ 门槛 {self.expect_hz:g} Hz")
            )
        else:
            output.append(
                ("FAIL", "频率", f"{rate_detail} < 门槛 {self.expect_hz:g} Hz")
            )

        if self.count >= 5:
            gaps = sorted(
                self.arrival[index + 1] - self.arrival[index]
                for index in range(self.count - 1)
            )
            median = gaps[len(gaps) // 2]
            worst = gaps[-1]
            if median > 0 and worst / median > 5:
                output.append(
                    (
                        "WARN",
                        "到达抖动",
                        f"最大间隔 {worst * 1e3:.1f}ms，是中位值的 "
                        f"{worst / median:.1f} 倍",
                    )
                )
            else:
                output.append(("PASS", "到达抖动", f"最大间隔 {worst * 1e3:.1f}ms"))

        if self.has_header is False:
            output.append(("WARN", "时间戳", "消息没有 header，跳过 stamp 检查"))
            return output

        if self.zero_stamps:
            output.append(
                (
                    "FAIL",
                    "时间戳非零",
                    f"{self.zero_stamps}/{self.count} 条消息 stamp 为 0",
                )
            )
        if self.backward:
            if self.publisher_count > 1:
                output.append(
                    (
                        "WARN",
                        "多发布者",
                        f"图中有 {self.publisher_count} 个 publisher，合流后检测到 "
                        f"{self.backward} 次全局 stamp 回退；Humble rclpy 回调不暴露"
                        " publisher GID，需分源录包/改名后才能判定单源单调性",
                    )
                )
            else:
                output.append(
                    (
                        "FAIL",
                        "时间戳单调",
                        f"检测到 {self.backward} 次回退；检查乱序和时钟重置",
                    )
                )
        elif self.stamps:
            output.append(("PASS", "时间戳单调", "没有回退"))
        if self.duplicates:
            output.append(
                ("WARN", "时间戳重复", f"检测到 {self.duplicates} 次重复 stamp")
            )

        if self.ages:
            ordered = sorted(self.ages)
            mean = sum(ordered) / len(ordered)
            low, high = ordered[0], ordered[-1]
            if low < -1e-6:
                output.append(
                    (
                        "WARN",
                        "时间戳来源",
                        f"至少一条 stamp 晚于本节点 ROS 时钟"
                        f"（最小 age {low * 1e3:.2f}ms）；"
                        "先核对时钟同步、/clock 与 use_sim_time，不能据此判定驱动错误",
                    )
                )
            elif mean < NEAR_ZERO_AGE_S:
                output.append(
                    (
                        "WARN",
                        "时间戳来源",
                        f"观测 age 均值 {mean * 1e6:.1f}µs，接近零；这可能来自低延迟"
                        "链路或回调时赋值，不能据此判定驱动覆盖了采集时间",
                    )
                )
            else:
                output.append(
                    (
                        "PASS",
                        "时间戳来源",
                        f"在 ROS 时钟可比的前提下，age mean/min/max = "
                        f"{mean * 1e3:.1f}/{low * 1e3:.1f}/{high * 1e3:.1f}ms；"
                        "采集时间来源仍需结合驱动配置或硬件触发验证",
                    )
                )
        return output


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="检查 ROS 2 话题频率、到达抖动与可观测时间戳性质",
        epilog="preset 是示例门槛，实际项目请用显式 topic 与 --expect-hz",
    )
    parser.add_argument("topics", nargs="*", help="话题名，可多个")
    parser.add_argument("--expect-hz", type=float, help="显式话题共用的最低频率")
    parser.add_argument("--duration", type=float, default=5.0, help="采样秒数")
    parser.add_argument(
        "--discovery-wait", type=float, default=1.0, help="创建订阅前等待发现的秒数"
    )
    parser.add_argument("--preset", choices=sorted(PRESETS))
    parser.add_argument(
        "--transient-local",
        action="store_true",
        help="为 /map 等历史样本显式请求 TRANSIENT_LOCAL；默认 VOLATILE",
    )
    parser.add_argument(
        "--reliable",
        action="store_true",
        help="显式请求 RELIABLE；传感器默认使用 BEST_EFFORT",
    )
    args = parser.parse_args(argv)
    if args.duration <= 0:
        parser.error("--duration 必须大于 0")
    if args.discovery_wait < 0:
        parser.error("--discovery-wait 不能小于 0")
    if args.expect_hz is not None and args.expect_hz <= 0:
        parser.error("--expect-hz 必须大于 0")
    if not args.preset and not args.topics:
        parser.error("需要至少一个 topic 或 --preset")
    return args


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if raw_args in (["-h"], ["--help"]):
        parse_args(raw_args)
    try:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import (
            DurabilityPolicy,
            HistoryPolicy,
            QoSProfile,
            ReliabilityPolicy,
        )
        from rclpy.utilities import remove_ros_args
        from rosidl_runtime_py.utilities import get_message
    except ImportError as exc:
        print(
            f"[FATAL] ROS 2 依赖导入失败: {exc}\n"
            "请先 source /opt/ros/<distro>/setup.bash",
            file=sys.stderr,
        )
        return 2
    args = parse_args(application_args(raw_args, remove_ros_args))

    targets: dict[str, float | None] = {}
    if args.preset:
        targets.update(PRESETS[args.preset])
    targets.update({topic: args.expect_hz for topic in args.topics})

    class HealthChecker(Node):
        def __init__(self) -> None:
            super().__init__("topic_health_checker")
            self.probes: dict[str, TopicProbe] = {}
            self.missing: list[str] = []
            self.invalid: dict[str, str] = {}
            self.subscription_handles: list[Any] = []

        def configure(self) -> None:
            available = dict(self.get_topic_names_and_types())
            qos = QoSProfile(
                depth=50,
                history=HistoryPolicy.KEEP_LAST,
                reliability=(
                    ReliabilityPolicy.RELIABLE
                    if args.reliable
                    else ReliabilityPolicy.BEST_EFFORT
                ),
                durability=(
                    DurabilityPolicy.TRANSIENT_LOCAL
                    if args.transient_local
                    else DurabilityPolicy.VOLATILE
                ),
            )
            resolved_targets = resolve_topic_targets(
                targets, self.resolve_topic_name
            )
            for name, threshold in resolved_targets.items():
                types = available.get(name)
                if not types:
                    self.missing.append(name)
                    continue
                try:
                    message_type = require_single_topic_type(name, types)
                    msg_class = get_message(message_type)
                except (ImportError, ValueError) as exc:
                    self.get_logger().error(f"{name}: 无法确定/加载消息类型: {exc}")
                    self.invalid[name] = str(exc)
                    continue
                probe = TopicProbe(name, threshold)
                probe.publisher_count = max(
                    1, len(self.get_publishers_info_by_topic(name))
                )
                self.probes[name] = probe
                subscription = self.create_subscription(
                    msg_class,
                    name,
                    lambda msg, item=probe: item.add_message(
                        msg,
                        time.monotonic(),
                        self.get_clock().now().nanoseconds * 1e-9,
                    ),
                    qos,
                )
                self.subscription_handles.append(subscription)

    rclpy.init(args=["check_topic_health.py", *raw_args])
    node = None
    try:
        node = HealthChecker()
        discovery_deadline = time.monotonic() + args.discovery_wait
        while time.monotonic() < discovery_deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
        node.configure()

        sample_started = time.monotonic()
        deadline = sample_started + args.duration
        print(f"采样 {args.duration:g}s ...\n")
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
        sample_ended = time.monotonic()

        failed = False
        for name in node.missing:
            print(f"■ {name}\n  [FAIL] 存在性 — 发现阶段未找到该话题\n")
            failed = True
        for name, detail in node.invalid.items():
            print(f"■ {name}\n  [FAIL] 消息类型 — {detail}\n")
            failed = True
        for name, probe in node.probes.items():
            probe.publisher_count = max(
                1, len(node.get_publishers_info_by_topic(name))
            )
            print(f"■ {name}（{probe.count} 条）")
            for level, check, detail in probe.evaluate(
                observation_duration_s=sample_ended - sample_started
            ):
                print(f"  [{level}] {check} — {detail}")
                failed |= level == "FAIL"
            print()
        print("结论:", "存在 FAIL" if failed else "未发现 FAIL")
        return 1 if failed else 0
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
