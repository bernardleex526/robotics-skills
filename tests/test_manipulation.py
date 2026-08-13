from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "robotics-manipulation"
FIXTURES = ROOT / "assets/fixtures"
SCRIPT = ROOT / "scripts/check_moveit_config.py"


def run_fixture(name: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURES / name), *extra],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


class ManipulationTests(unittest.TestCase):
    def test_valid_moveit_snapshot_passes(self) -> None:
        result = run_fixture("moveit_valid")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["metrics"]["movable_joint_count"]["value"], 2)

    def test_controller_joint_mismatch_fails(self) -> None:
        result = run_fixture("moveit_bad_controller")
        self.assertEqual(result.returncode, 1)
        self.assertIn("controller_joint_set", result.stdout)

    def test_unknown_kinematics_group_fails(self) -> None:
        result = run_fixture("moveit_bad_kinematics")
        self.assertEqual(result.returncode, 1)
        self.assertIn("kinematics_group", result.stdout)

    def test_malformed_required_yaml_is_invalid_input(self) -> None:
        result = run_fixture("moveit_malformed")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid_input", result.stdout)

    def test_optional_ros_discovery_is_pass_or_skip(self) -> None:
        result = run_fixture("moveit_valid", "--ros-check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(json.loads(result.stdout)["status"], {"pass", "skip"})


if __name__ == "__main__":
    unittest.main()
