from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

import jsonschema
import yaml


REPO = Path(__file__).resolve().parents[1]
ENGINEERING_SKILLS = {
    "robotics-vision-perception",
    "robotics-3d-perception",
    "robotics-manipulation",
    "robotics-hand-eye-calibration",
    "robotics-force-control",
    "robotics-legged-wbc",
    "robotics-research-reproduction",
    "robotics-benchmarking",
}


def load_result_contract(skill: str):
    path = REPO / skill / "scripts/result_contract.py"
    spec = importlib.util.spec_from_file_location(
        f"{skill.replace('-', '_')}_result_contract", path
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EngineeringSkillContractTests(unittest.TestCase):
    def test_engineering_skills_have_portable_runtime_assets(self) -> None:
        for skill in sorted(ENGINEERING_SKILLS):
            root = REPO / skill
            self.assertTrue((root / "SKILL.md").is_file(), skill)
            self.assertTrue((root / "LICENSE.txt").is_file(), skill)
            self.assertTrue((root / "scripts").is_dir(), skill)
            self.assertTrue((root / "assets/fixtures").is_dir(), skill)
            self.assertTrue(
                (root / "assets/result.schema.json").is_file(), skill
            )
            self.assertTrue(
                (root / "assets/run_manifest.example.yaml").is_file(), skill
            )

    def test_manifest_declares_exact_engineering_skill_set(self) -> None:
        manifest = yaml.safe_load(
            (REPO / "tools/engineering_skills_manifest.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(set(manifest["skills"]), ENGINEERING_SKILLS)

    def test_manifest_paths_are_skill_relative(self) -> None:
        manifest = yaml.safe_load(
            (REPO / "tools/engineering_skills_manifest.yaml").read_text(
                encoding="utf-8"
            )
        )
        for skill, entry in manifest["skills"].items():
            paths = (
                list(entry["primary_scripts"])
                + [entry["valid_fixture"], entry["invalid_fixture"]]
            )
            for relative in paths:
                self.assertFalse(Path(relative).is_absolute(), (skill, relative))
                self.assertNotIn("..", Path(relative).parts, (skill, relative))

    def test_manifest_has_one_valid_and_invalid_case_per_primary_script(self) -> None:
        manifest = yaml.safe_load(
            (REPO / "tools/engineering_skills_manifest.yaml").read_text(
                encoding="utf-8"
            )
        )
        for skill, entry in manifest["skills"].items():
            cases = entry.get("cases")
            self.assertIsInstance(cases, list, skill)
            self.assertEqual(
                {case["script"] for case in cases},
                set(entry["primary_scripts"]),
                skill,
            )
            for case in cases:
                self.assertIn("valid_fixture", case, (skill, case))
                self.assertIn("invalid_fixture", case, (skill, case))
                self.assertEqual(case.get("valid_exit"), 0, (skill, case))
                self.assertTrue(case.get("invalid_exits"), (skill, case))

    def test_declared_cases_emit_the_common_result_contract(self) -> None:
        manifest = yaml.safe_load(
            (REPO / "tools/engineering_skills_manifest.yaml").read_text(
                encoding="utf-8"
            )
        )
        schema = json.loads(
            (REPO / "tools/result.schema.json").read_text(encoding="utf-8")
        )
        validator = jsonschema.Draft202012Validator(schema)
        required = {
            "schema_version",
            "skill",
            "check",
            "status",
            "summary",
            "inputs",
            "environment",
            "metrics",
            "gates",
            "findings",
            "evidence",
            "limitations",
        }
        for skill, entry in manifest["skills"].items():
            for case in entry["cases"]:
                script = REPO / skill / case["script"]
                for kind, expected in (
                    ("valid", {case["valid_exit"]}),
                    ("invalid", set(case["invalid_exits"])),
                ):
                    fixture = REPO / skill / case[f"{kind}_fixture"]
                    completed = subprocess.run(
                        ["python3", str(script), str(fixture)],
                        cwd=REPO,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertIn(
                        completed.returncode,
                        expected,
                        (skill, case["script"], kind, completed.stderr),
                    )
                    payload = json.loads(completed.stdout)
                    validator.validate(payload)
                    self.assertEqual(set(payload), required, (skill, case, kind))
                    self.assertEqual(payload["schema_version"], "1.0.0")
                    self.assertEqual(payload["skill"], skill)
                    self.assertIn(
                        payload["status"], {"pass", "warn", "fail", "skip"}
                    )
                    fail_items = [
                        item
                        for item in payload["findings"]
                        if item.get("level") == "fail"
                    ]
                    self.assertEqual(
                        payload["status"] == "fail",
                        bool(fail_items),
                        (skill, case["script"], kind),
                    )
                    for metric in payload["metrics"].values():
                        self.assertIn("value", metric)
                        self.assertIn("unit", metric)

    def test_result_schemas_are_byte_identical(self) -> None:
        payloads = {
            (REPO / skill / "assets/result.schema.json").read_bytes()
            for skill in ENGINEERING_SKILLS
        }
        self.assertEqual(len(payloads), 1)
        self.assertEqual(
            hashlib.sha256(next(iter(payloads))).hexdigest(),
            hashlib.sha256((REPO / "tools/result.schema.json").read_bytes()).hexdigest(),
        )

    def test_result_helpers_are_byte_identical(self) -> None:
        payloads = {
            (REPO / skill / "scripts/result_contract.py").read_bytes()
            for skill in ENGINEERING_SKILLS
        }
        self.assertEqual(len(payloads), 1)
        self.assertEqual(
            next(iter(payloads)),
            (REPO / "tools/result_contract_template.py").read_bytes(),
        )

    def test_fail_finding_controls_overall_status(self) -> None:
        module = load_result_contract("robotics-vision-perception")
        result = module.make_result(
            skill="robotics-vision-perception",
            check="camera",
            summary="bad",
            findings=[
                {"level": "fail", "code": "bad_stride", "message": "bad"}
            ],
        )
        self.assertEqual(result["status"], "fail")
        self.assertEqual(module.exit_code(result), 1)

    def test_skip_is_successful_but_not_pass(self) -> None:
        module = load_result_contract("robotics-vision-perception")
        result = module.make_result(
            skill="robotics-vision-perception",
            check="optional_dependency",
            summary="dependency unavailable",
            requested_status="skip",
            limitations=["Open3D was not installed"],
        )
        self.assertEqual(result["status"], "skip")
        self.assertEqual(module.exit_code(result), 0)


if __name__ == "__main__":
    unittest.main()
