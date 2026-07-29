from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "robotics-ros2-infra/scripts/check_tf_tree.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_tf_tree", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def levels_for(results, check_name: str) -> list[str]:
    return [level for level, check, _ in results if check == check_name]


class TfAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_empty_graph_fails_cleanly(self) -> None:
        results, tree = self.module.analyze({}, 10.0, 1.0, [])
        self.assertEqual(tree, [])
        self.assertIn("FAIL", levels_for(results, "TF 存在性"))

    def test_cycle_is_reported_without_recursing_or_indexing_empty_roots(self) -> None:
        frames = {
            "a": {"parent": "b", "rate": 10.0, "most_recent_transform": 9.9},
            "b": {"parent": "a", "rate": 10.0, "most_recent_transform": 9.9},
        }
        results, _ = self.module.analyze(frames, 10.0, 1.0, [])
        self.assertTrue(
            any(level == "FAIL" and "环" in detail for level, _, detail in results)
        )

    def test_multiple_roots_are_reported(self) -> None:
        frames = {
            "base_link": {"parent": "odom", "rate": 20.0, "most_recent_transform": 9.9},
            "camera": {"parent": "world", "rate": 0.0, "most_recent_transform": 0.0},
        }
        results, _ = self.module.analyze(frames, 10.0, 1.0, [])
        self.assertIn("FAIL", levels_for(results, "树连通性"))

    def test_future_transform_warns_about_clock_domain(self) -> None:
        frames = {
            "base_link": {
                "parent": "odom",
                "rate": 20.0,
                "most_recent_transform": 1000.0,
            }
        }
        results, _ = self.module.analyze(frames, 10.0, 1.0, [])
        self.assertTrue(
            any(
                level == "WARN" and "时钟" in detail
                for level, check, detail in results
                if check == "变换新鲜度"
            )
        )

    def test_zero_rate_yaml_is_not_claimed_to_prove_static_tf(self) -> None:
        frames = {
            "camera": {
                "parent": "base_link",
                "rate": 0.0,
                "most_recent_transform": 0.0,
            }
        }
        results, tree = self.module.analyze(frames, 10.0, 1.0, [])
        freshness = [detail for _, check, detail in results if check == "变换新鲜度"]
        self.assertTrue(any("不能可靠区分" in detail for detail in freshness))
        self.assertTrue(any("来源未判定" in line for line in tree))

    def test_tree_rendering_distinguishes_sibling_branches(self) -> None:
        frames = {
            "left": {
                "parent": "map",
                "rate": 0.0,
                "most_recent_transform": 0.0,
            },
            "right": {
                "parent": "map",
                "rate": 0.0,
                "most_recent_transform": 0.0,
            },
        }
        _, tree = self.module.analyze(
            frames,
            now_s=1.0,
            stale_s=1.0,
            chain=[],
        )
        self.assertTrue(any("├─ left" in line for line in tree))
        self.assertTrue(any("└─ right" in line for line in tree))

    def test_ros_arguments_are_removed_only_for_application_parser(self) -> None:
        calls = []

        def fake_remove_ros_args(*, args):
            calls.append(args)
            return [args[0], "--duration", "0.1"]

        application = self.module.application_args(
            ["--duration", "0.1", "--ros-args", "-p", "use_sim_time:=true"],
            fake_remove_ros_args,
        )
        self.assertEqual(application, ["--duration", "0.1"])
        self.assertEqual(calls[0][0], "check_tf_tree.py")


if __name__ == "__main__":
    unittest.main()
