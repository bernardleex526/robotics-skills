from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "robotics-benchmarking"
FIXTURES = ROOT / "assets/fixtures"
VALIDATOR = ROOT / "scripts/validate_benchmark_manifest.py"
RUNNER = ROOT / "scripts/run_benchmark.py"
AGGREGATOR = ROOT / "scripts/aggregate_results.py"


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


class BenchmarkingTests(unittest.TestCase):
    def test_valid_manifest_passes(self) -> None:
        result = run(VALIDATOR, str(FIXTURES / "benchmark_echo.yaml"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "pass")

    def test_scalar_shell_command_is_rejected(self) -> None:
        result = run(
            VALIDATOR, str(FIXTURES / "benchmark_shell_string.yaml")
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("argv_array_required", result.stdout)

    def test_runner_requires_explicit_execute(self) -> None:
        result = run(RUNNER, str(FIXTURES / "benchmark_echo.yaml"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "skip")

    def test_harmless_benchmark_executes_without_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            # The fixture documents a POSIX interpreter name; rewrite it to the
            # current interpreter so the runner can execute it cross-platform.
            manifest = yaml.safe_load(
                (FIXTURES / "benchmark_echo.yaml").read_text(encoding="utf-8")
            )
            manifest["command"][0] = sys.executable
            manifest_path = Path(temporary) / "benchmark_echo.yaml"
            manifest_path.write_text(
                yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8"
            )
            output_dir = Path(temporary) / "fresh"
            result = run(
                RUNNER,
                str(manifest_path),
                "--execute",
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["metrics"]["successful_runs"]["value"], 3)
            self.assertEqual(len(list(output_dir.glob("run-*.json"))), 3)

    def test_nonempty_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "occupied"
            output_dir.mkdir()
            (output_dir / "keep.txt").write_text("do not overwrite")
            result = run(
                RUNNER,
                str(FIXTURES / "benchmark_echo.yaml"),
                "--execute",
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("output_directory_not_empty", result.stdout)

    def test_failures_remain_in_denominator(self) -> None:
        result = run(AGGREGATOR, str(FIXTURES / "mixed_results"))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertAlmostEqual(
            payload["metrics"]["failure_rate"]["value"], 1 / 3
        )
        self.assertEqual(payload["metrics"]["total_runs"]["value"], 3)
        self.assertEqual(payload["metrics"]["score_sample_count"]["value"], 2)


if __name__ == "__main__":
    unittest.main()
