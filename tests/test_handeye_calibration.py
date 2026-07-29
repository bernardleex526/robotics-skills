from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "robotics-hand-eye-calibration"
FIXTURES = ROOT / "assets/fixtures"
SCRIPT = ROOT / "scripts/validate_handeye.py"


def run_fixture(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), str(FIXTURES / name)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


class HandEyeCalibrationTests(unittest.TestCase):
    def test_valid_candidate_passes_holdout(self) -> None:
        result = run_fixture("handeye_valid.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertIn("holdout_rotation_rmse_deg", payload["metrics"])
        self.assertEqual(
            payload["metrics"]["holdout_translation_rmse_m"]["value"], 0.0
        )

    def test_single_axis_dataset_fails(self) -> None:
        result = run_fixture("handeye_single_axis.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("rotation_axis_diversity", result.stdout)

    def test_bad_candidate_fails_holdout(self) -> None:
        result = run_fixture("handeye_bad_candidate.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("holdout_translation_residual", result.stdout)

    def test_pairing_skew_is_enforced(self) -> None:
        result = run_fixture("handeye_bad_skew.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pairing_skew", result.stdout)

    def test_malformed_quaternion_fails_admission(self) -> None:
        result = run_fixture("handeye_bad_quaternion.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("quaternion_norm", result.stdout)


if __name__ == "__main__":
    unittest.main()
