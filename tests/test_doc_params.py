from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "tools/check_doc_params.py"
MANIFEST_PATH = REPO / "tools/param_manifest.yaml"


def load_module():
    spec = importlib.util.spec_from_file_location("check_doc_params", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DocParameterTests(unittest.TestCase):
    def test_humble_manifest_uses_singular_progress_checker_parameter(self) -> None:
        manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
        nav2 = manifest["projects"]["nav2_humble"]
        self.assertIn("progress_checker_plugin", nav2["known"])
        self.assertNotIn("progress_checker_plugins", nav2["known"])

    def test_external_file_can_be_checked_without_mutating_global_root(self) -> None:
        module = load_module()
        manifest = module.load_manifest(MANIFEST_PATH)
        owns = module.compile_owns(manifest)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outside.md"
            path.write_text("Use `loop_search_maximum_distance`.\n", encoding="utf-8")
            problems = module.check_file(
                path,
                owns,
                manifest["forbidden"],
                display_root=Path(directory),
            )
        self.assertEqual(problems, [])

    def test_forbidden_parameter_is_reported(self) -> None:
        module = load_module()
        manifest = module.load_manifest(MANIFEST_PATH)
        owns = module.compile_owns(manifest)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.md"
            path.write_text("Tune `sm_search_window`.\n", encoding="utf-8")
            problems = module.check_file(
                path,
                owns,
                manifest["forbidden"],
                display_root=Path(directory),
            )
        self.assertTrue(any("sm_search_window" in item for item in problems))


if __name__ == "__main__":
    unittest.main()
