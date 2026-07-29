from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "robotics-ros2-infra/scripts/check_topic_health.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_topic_health", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TopicHealthAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def make_probe(self, expect_hz=5.0):
        return self.module.TopicProbe("/sensor", expect_hz)

    def test_rate_uses_monotonic_arrival_times(self) -> None:
        probe = self.make_probe()
        for index in range(6):
            probe.add_observation(
                arrival_mono_s=index * 0.1,
                stamp_s=100.0 + index * 0.1,
                receipt_ros_s=100.01 + index * 0.1,
            )
        self.assertAlmostEqual(probe.rate_hz(), 10.0)
        self.assertTrue(
            any(level == "PASS" and check == "频率" for level, check, _ in probe.evaluate())
        )

    def test_near_zero_age_is_evidence_not_proof_of_timestamp_overwrite(self) -> None:
        probe = self.make_probe()
        for index in range(6):
            stamp = 100.0 + index * 0.1
            probe.add_observation(index * 0.1, stamp, stamp + 0.0001)
        source_results = [
            item for item in probe.evaluate() if item[1] == "时间戳来源"
        ]
        self.assertTrue(source_results)
        self.assertEqual(source_results[0][0], "WARN")
        self.assertIn("不能据此判定", source_results[0][2])

    def test_future_stamp_is_clock_warning_not_causal_failure(self) -> None:
        probe = self.make_probe()
        for index in range(6):
            probe.add_observation(index * 0.1, 200.0 + index, 100.0 + index)
        source_results = [
            item for item in probe.evaluate() if item[1] == "时间戳来源"
        ]
        self.assertEqual(source_results[0][0], "WARN")
        self.assertIn("时钟", source_results[0][2])

    def test_mixed_future_and_past_stamps_still_warn_about_clock(self) -> None:
        probe = self.make_probe()
        ages = (-0.2, 0.1, 0.1, 0.1, 0.1, 0.1)
        for index, age in enumerate(ages):
            stamp = 100.0 + index
            probe.add_observation(index * 0.1, stamp, stamp + age)
        source_results = [
            item for item in probe.evaluate() if item[1] == "时间戳来源"
        ]
        self.assertEqual(source_results[0][0], "WARN")
        self.assertIn("时钟", source_results[0][2])

    def test_backward_stamp_is_failure(self) -> None:
        probe = self.make_probe()
        probe.add_observation(0.0, 10.0, 10.1)
        probe.add_observation(0.1, 9.0, 10.2)
        self.assertTrue(
            any(
                level == "FAIL" and check == "时间戳单调"
                for level, check, _ in probe.evaluate()
            )
        )

    def test_stamps_are_checked_per_publisher(self) -> None:
        probe = self.make_probe()
        probe.publisher_count = 2
        probe.add_observation(0.0, 10.0, 10.1)
        probe.add_observation(0.1, 5.0, 10.2)
        results = probe.evaluate()
        self.assertFalse(
            any(level == "FAIL" and check == "时间戳单调" for level, check, _ in results)
        )
        self.assertTrue(
            any(level == "WARN" and check == "多发布者" for level, check, _ in results)
        )

    def test_publisher_count_defaults_to_single_source_contract(self) -> None:
        self.assertEqual(self.make_probe().publisher_count, 1)

    def test_burst_at_window_end_does_not_pass_rate_admission(self) -> None:
        probe = self.make_probe(expect_hz=10.0)
        for index in range(5):
            probe.add_observation(
                arrival_mono_s=4.8 + index * 0.05,
                stamp_s=100.0 + index * 0.05,
                receipt_ros_s=100.01 + index * 0.05,
            )
        frequency = [
            item
            for item in probe.evaluate(observation_duration_s=5.0)
            if item[1] == "频率"
        ]
        self.assertEqual(frequency[0][0], "FAIL")
        self.assertIn("窗口", frequency[0][2])

    def test_single_cached_sample_cannot_satisfy_a_rate_threshold(self) -> None:
        probe = self.make_probe(expect_hz=1.0)
        probe.add_observation(
            arrival_mono_s=0.1,
            stamp_s=None,
            receipt_ros_s=100.0,
        )
        frequency = [
            item
            for item in probe.evaluate(observation_duration_s=1.0)
            if item[1] == "频率"
        ]
        self.assertEqual(frequency[0][0], "FAIL")
        self.assertIn("验收率 0.0 Hz", frequency[0][2])

    def test_single_sample_without_threshold_warns_rate_is_unobservable(self) -> None:
        probe = self.make_probe(expect_hz=None)
        probe.add_observation(
            arrival_mono_s=0.1,
            stamp_s=None,
            receipt_ros_s=100.0,
        )
        frequency = [
            item
            for item in probe.evaluate(observation_duration_s=1.0)
            if item[1] == "频率"
        ]
        self.assertEqual(frequency[0][0], "WARN")
        self.assertIn("不足以估计", frequency[0][2])

    def test_relative_topic_names_are_resolved_in_the_node_namespace(self) -> None:
        targets = self.module.resolve_topic_targets(
            {"scan": 10.0, "/imu/data": 100.0},
            lambda name: name if name.startswith("/") else f"/robot/{name}",
        )
        self.assertEqual(
            targets,
            {"/robot/scan": 10.0, "/imu/data": 100.0},
        )

    def test_ambiguous_topic_types_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "多个类型"):
            self.module.require_single_topic_type(
                "/ambiguous",
                ["example_msgs/msg/A", "example_msgs/msg/B"],
            )

    def test_ros_arguments_are_removed_only_for_application_parser(self) -> None:
        calls = []

        def fake_remove_ros_args(*, args):
            calls.append(args)
            return [args[0], "--duration", "0.1", "/scan"]

        application = self.module.application_args(
            ["--duration", "0.1", "/scan", "--ros-args", "-p", "use_sim_time:=true"],
            fake_remove_ros_args,
        )
        self.assertEqual(application, ["--duration", "0.1", "/scan"])
        self.assertEqual(calls[0][0], "check_topic_health.py")

    def test_node_does_not_shadow_rclpy_subscriptions_property(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("self.subscriptions", source)
        self.assertIn("self.subscription_handles", source)


if __name__ == "__main__":
    unittest.main()
