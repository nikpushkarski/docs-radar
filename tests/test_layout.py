"""Regression checks for package imports, launch commands and repository paths."""

from contextlib import chdir
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from docs_radar import (
    approvals, content_fingerprint, detect_impact, render_topic, retrieval,
    validate_source,
)
from evals import suite
from scripts import setup_support


ROOT = Path(__file__).resolve().parents[1]


class RepositoryLayoutTest(unittest.TestCase):
    def run_python(self, *arguments, cwd=ROOT):
        return subprocess.run(
            [sys.executable, "-X", "utf8", *arguments], cwd=cwd, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )

    def test_workspace_roots_still_point_to_repository_not_package(self):
        for module in (approvals, content_fingerprint, detect_impact, render_topic,
                       retrieval, validate_source, setup_support):
            with self.subTest(module=module.__name__):
                self.assertEqual(module.ROOT, ROOT)
        self.assertEqual(suite.ROOT, ROOT / "evals")
        self.assertTrue((ROOT / "scripts/requirements.txt").is_file())

    def test_default_workspace_is_independent_of_current_directory(self):
        expected = retrieval.load_workspace(ROOT)
        self.assertTrue(expected["topics"])
        with tempfile.TemporaryDirectory() as temporary, chdir(temporary):
            self.assertEqual(retrieval.load_workspace(), expected)
            self.assertEqual(setup_support.ROOT, ROOT)
            self.assertEqual(suite.verify_manifest()["test_set_version"], "v2")

    def test_read_only_tools_run_as_package_modules(self):
        commands = (
            ("docs_radar.validate_source", "First source passed validation."),
            ("docs_radar.approvals", "Demo eligibility check"),
            ("docs_radar.content_fingerprint", "Content fingerprints only"),
            ("docs_radar.detect_impact", "SYNTHETIC CHANGE"),
            ("docs_radar.render_topic", "Demo-authored draft preview"),
        )
        for module, marker in commands:
            with self.subTest(module=module):
                result = self.run_python("-m", module)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(marker, result.stdout)
        result = self.run_python(
            "-m", "docs_radar.retrieval", "Where should I place new lab orders?",
            "--audience", "Providers", "--date", "2026-11-01",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertNotEqual(output["status"], "error")
        self.assertEqual(output["reference_date"], "2026-11-01")

    def test_setup_bootstraps_without_site_packages_and_rejects_noninteractive_input(self):
        # -S excludes Streamlit and all installed third-party packages.
        # Closed stdin must never be treated as consent to download anything.
        result = self.run_python("-S", "-m", "scripts.setup_local")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("interactive terminal", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_hash_maintenance_uses_its_repo_not_current_working_directory(self):
        real_sources_before = (ROOT / "data/sources.json").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            data = root / "data"
            data.mkdir()
            target = data / "sources.json"
            target.write_text(json.dumps([{"summary": "Synthetic relocation fixture"}]), encoding="utf-8")
            script = scripts / "hash_sources.py"
            shutil.copyfile(ROOT / "scripts/hash_sources.py", script)
            elsewhere = root / "unrelated"
            elsewhere.mkdir()
            # The utility only depends on the standard library and its __file__.
            result = self.run_python(str(script), cwd=elsewhere)
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(target.read_text(encoding="utf-8"))[0]
            expected = hashlib.sha256(record["summary"].encode("utf-8")).hexdigest()
            self.assertEqual(record["summary_sha256"], expected)
            self.assertFalse((elsewhere / "data").exists())
        self.assertEqual((ROOT / "data/sources.json").read_bytes(), real_sources_before)

    def test_root_contains_no_application_scripts_or_dependency_file(self):
        self.assertEqual(list(ROOT.glob("*.py")), [])
        self.assertFalse((ROOT / "requirements.txt").exists())
        self.assertFalse((ROOT / "start.cmd").exists())
        for name in ("README.md", "AGENTS.md", "IMPLEMENTATION_PLAN.md", "PROGRESS.md", ".gitignore"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
