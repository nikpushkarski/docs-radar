import json
from pathlib import Path
import shutil
import tempfile
import unittest

from docs_radar.approvals import approval_status
from docs_radar.content_actions import approve_topic, revoke_topic, save_draft
from docs_radar.content_fingerprint import content_fingerprint
from docs_radar.retrieval import load_workspace

ROOT = Path(__file__).resolve().parents[1]
TOPIC = "provider-migration-checklist.md"


class ContentActionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for folder in ("content", "data"):
            shutil.copytree(ROOT / folder, self.root / folder)
        self.workspace = load_workspace(self.root)
        self.text = self.workspace["topics"][TOPIC]
        self.fingerprint = content_fingerprint(self.text, self.workspace["facts"])

    def test_approval_requires_confirmation_and_identified_reviewer(self):
        for confirmed, reviewer in ((False, "Test reviewer"), (True, "")):
            with self.assertRaises(ValueError):
                approve_topic(self.root, TOPIC, self.fingerprint, reviewer, "2000-01-01", confirmed)

    def test_explicit_approval_and_revocation(self):
        approve_topic(self.root, TOPIC, self.fingerprint, "Synthetic UI test", "2000-01-01", True)
        workspace = load_workspace(self.root)
        self.assertEqual(approval_status(TOPIC, self.text, workspace["facts"], workspace["approvals"]), "eligible")
        revoke_topic(self.root, TOPIC, self.fingerprint, True)
        self.assertEqual(load_workspace(self.root)["approvals"][TOPIC]["state"], "draft")

    def test_saved_draft_invalidates_not_refreshes_approval(self):
        before = (self.root / "data/approvals.json").read_bytes()
        edited = self.text + "\nDraft correction for a synthetic unit test.\n"
        save_draft(self.root, TOPIC, edited, self.fingerprint)
        self.assertEqual((self.root / "data/approvals.json").read_bytes(), before)
        workspace = load_workspace(self.root)
        self.assertEqual(approval_status(TOPIC, edited, workspace["facts"], workspace["approvals"]), "changed")

    def test_stale_version_rejected(self):
        (self.root / "content" / TOPIC).write_text(self.text + "\nchanged", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed since preview"):
            approve_topic(self.root, TOPIC, self.fingerprint, "Synthetic UI test", "2000-01-01", True)
        with self.assertRaises(ValueError):
            save_draft(self.root, TOPIC, self.text, self.fingerprint)

    def test_invalid_schema_and_traversal_do_not_write(self):
        with self.assertRaises(ValueError):
            save_draft(self.root, TOPIC, "Missing metadata", self.fingerprint)
        with self.assertRaises(ValueError):
            save_draft(self.root, "../README.md", self.text, self.fingerprint)
        self.assertEqual((self.root / "content" / TOPIC).read_text(encoding="utf-8"), self.text)
