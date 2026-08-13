from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "robotics-force-control"
FIXTURES = ROOT / "assets/fixtures"
ANALYZE = ROOT / "scripts/analyze_wrench_log.py"
CHECK = ROOT / "scripts/check_force_config.py"


def run(script: Path, fixture: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), str(FIXTURES / fixture)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


class ForceControlTests(unittest.TestCase):
    def test_nominal_wrench_log_passes(self) -> None:
        result = run(ANALYZE, "wrench_nominal.yaml")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertAlmostEqual(
            payload["metrics"]["sample_rate_hz"]["value"], 100.0
        )

    def test_saturated_wrench_log_fails(self) -> None:
        result = run(ANALYZE, "wrench_saturated.yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("saturation_fraction", result.stdout)

    def test_nonmonotonic_wrench_log_fails(self) -> None:
        result = run(ANALYZE, "wrench_nonmonotonic.yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("timestamp_monotonic", result.stdout)

    def test_valid_force_config_passes(self) -> None:
        result = run(CHECK, "force_config_valid.yaml")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "pass")

    def test_missing_timeout_safe_state_fails(self) -> None:
        result = run(CHECK, "force_config_unsafe.yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("timeout_safe_state", result.stdout)

    def test_read_only_scripts_contain_no_actuation_path(self) -> None:
        forbidden = (
            "rclpy.create_publisher",
            "ros2 topic pub",
            "switch_controller",
            "activate_controller",
            "subprocess",
        )
        for name in ("analyze_wrench_log.py", "check_force_config.py"):
            text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            for pattern in forbidden:
                self.assertNotIn(pattern, text, (name, pattern))


if __name__ == "__main__":
    unittest.main()
