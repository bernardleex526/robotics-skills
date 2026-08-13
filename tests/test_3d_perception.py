from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "robotics-3d-perception"
FIXTURES = ROOT / "assets/fixtures"
CLOUD = ROOT / "scripts/check_pointcloud_contract.py"
EVALUATE = ROOT / "scripts/evaluate_3d_results.py"


def run(script: Path, fixture: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), str(FIXTURES / fixture)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


class ThreeDPerceptionTests(unittest.TestCase):
    def test_valid_cloud_passes(self) -> None:
        result = run(CLOUD, "cloud_valid.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "pass")

    def test_truncated_cloud_fails(self) -> None:
        result = run(CLOUD, "cloud_truncated.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("data_length", result.stdout)

    def test_big_endian_xyz_is_decoded(self) -> None:
        result = run(CLOUD, "cloud_big_endian.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["metrics"]["finite_ratio"]["value"], 1.0)
        self.assertEqual(payload["metrics"]["decoded_point_count"]["value"], 2)

    def test_required_time_field_is_enforced(self) -> None:
        result = run(CLOUD, "cloud_missing_time.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("required_time_field", result.stdout)

    def test_known_3d_matching_metrics(self) -> None:
        result = run(EVALUATE, "objects_known.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["metrics"]["true_positive"]["value"], 1)
        self.assertEqual(payload["metrics"]["false_positive"]["value"], 1)
        self.assertEqual(payload["metrics"]["false_negative"]["value"], 1)
        self.assertAlmostEqual(
            payload["metrics"]["mean_translation_error_m"]["value"], 0.1
        )

    def test_frame_mismatch_fails_3d_evaluation(self) -> None:
        result = run(EVALUATE, "objects_bad_frame.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("object_frame", result.stdout)


if __name__ == "__main__":
    unittest.main()
