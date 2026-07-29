from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "robotics-research-reproduction"
SCRIPT = ROOT / "scripts/validate_reproduction_manifest.py"
FIXTURES = ROOT / "assets/fixtures"


def run_fixture(name: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), str(FIXTURES / name), *extra],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


class ResearchReproductionTests(unittest.TestCase):
    def test_valid_manifest_passes(self) -> None:
        result = run_fixture("reproduction_valid.yaml")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["skill"], "robotics-research-reproduction")

    def test_floating_revision_fails(self) -> None:
        result = run_fixture("reproduction_floating_ref.yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("immutable_revision", result.stdout)

    def test_unhashed_dataset_fails(self) -> None:
        result = run_fixture("reproduction_unhashed_data.yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("dataset_sha256", result.stdout)

    def test_malformed_yaml_is_invalid_input(self) -> None:
        result = run_fixture("reproduction_malformed.yaml")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid_input", result.stdout)

    def test_output_matches_stdout_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            result = run_fixture(
                "reproduction_valid.yaml", "--output", str(output)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), json.loads(output.read_text()))


if __name__ == "__main__":
    unittest.main()
