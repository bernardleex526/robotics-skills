from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "robotics-legged-wbc"
FIXTURES = ROOT / "assets/fixtures"
SCRIPT = ROOT / "scripts/check_wbc_contract.py"


def run_fixture(name: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURES / name), *extra],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


class LeggedWbcTests(unittest.TestCase):
    def test_valid_wbc_contract_passes(self) -> None:
        result = run_fixture("wbc_valid.yaml")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["metrics"]["actuated_joint_count"]["value"], 4)

    def test_joint_order_mismatch_fails(self) -> None:
        result = run_fixture("wbc_bad_joint_order.yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("actuated_joint_order", result.stdout)

    def test_missing_fallback_fails(self) -> None:
        result = run_fixture("wbc_missing_fallback.yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("degraded_state", result.stdout)

    def test_unknown_contact_frame_fails(self) -> None:
        result = run_fixture("wbc_bad_contact.yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("contact_frames", result.stdout)

    def test_optional_pinocchio_check_is_pass_or_skip(self) -> None:
        result = run_fixture("wbc_valid.yaml", "--pinocchio-check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(json.loads(result.stdout)["status"], {"pass", "skip"})

    def test_runtime_script_is_read_only(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "create_publisher",
            "ros2 topic pub",
            "switch_controller",
            "activate_controller",
            "motor_command",
            "subprocess",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
