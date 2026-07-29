from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "robotics-vision-perception"
FIXTURES = ROOT / "assets/fixtures"
CAMERA = ROOT / "scripts/check_camera_contract.py"
EVALUATE = ROOT / "scripts/evaluate_vision_results.py"


def run(script: Path, fixture: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(script), str(FIXTURES / fixture)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


class VisionPerceptionTests(unittest.TestCase):
    def test_valid_camera_contract_passes(self) -> None:
        result = run(CAMERA, "camera_valid.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "pass")

    def test_bad_row_stride_fails(self) -> None:
        result = run(CAMERA, "camera_bad_stride.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("image_data_length", result.stdout)

    def test_nonmonotonic_acquisition_stamps_fail(self) -> None:
        result = run(CAMERA, "camera_nonmonotonic.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("acquisition_stamp_monotonic", result.stdout)

    def test_pairing_skew_gate_fails(self) -> None:
        result = run(CAMERA, "camera_bad_pairing.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pairing_skew", result.stdout)

    def test_known_detection_metrics(self) -> None:
        result = run(EVALUATE, "detections_known.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["metrics"]["true_positive"]["value"], 1)
        self.assertEqual(payload["metrics"]["false_positive"]["value"], 1)
        self.assertEqual(payload["metrics"]["false_negative"]["value"], 1)
        self.assertEqual(payload["metrics"]["precision"]["value"], 0.5)
        self.assertEqual(payload["metrics"]["recall"]["value"], 0.5)

    def test_invalid_detection_box_fails(self) -> None:
        result = run(EVALUATE, "detections_bad_box.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("box_geometry", result.stdout)


if __name__ == "__main__":
    unittest.main()
