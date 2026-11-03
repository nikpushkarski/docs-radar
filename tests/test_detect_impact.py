from copy import deepcopy
import json
from pathlib import Path
import unittest

from docs_radar.detect_impact import preview_change


ROOT = Path(__file__).resolve().parents[1]


class ImpactDetectionTest(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads(
            (ROOT / "data/facts.json").read_text(encoding="utf-8")
        )
        self.change = json.loads(
            (ROOT / "data/simulated_changes/login-closure.json").read_text(
                encoding="utf-8"
            )
        )
        self.topics = {
            path.name: path.read_text(encoding="utf-8")
            for path in (ROOT / "content").glob("*.md")
        }

    def test_only_dependents_are_flagged_with_review_context(self):
        self.assertIn("about-demo.md", self.topics)
        affected = preview_change(self.change, self.facts, self.topics)
        self.assertEqual(
            [item["topic_id"] for item in affected],
            ["provider-migration-checklist.md", "rupa-view-only.md"],
        )
        for item in affected:
            with self.subTest(topic=item["topic_id"]):
                self.assertIn(self.change["fact_id"], item["reason"])
                self.assertIn("simulated", item["reason"])
                self.assertEqual(item["audience"], "Providers")
                self.assertTrue(item["suggested_reviewer_role"])
                self.assertTrue(item["open_question"])

    def test_preview_does_not_change_inputs(self):
        before = deepcopy((self.change, self.facts, self.topics))
        preview_change(self.change, self.facts, self.topics)
        self.assertEqual((self.change, self.facts, self.topics), before)

    def test_unknown_fact_is_rejected(self):
        self.change["fact_id"] = "missing"
        with self.assertRaisesRegex(ValueError, "Unknown fact ID: missing"):
            preview_change(self.change, self.facts, self.topics)

    def test_stale_change_is_rejected(self):
        for field, value in (("old_version", 0), ("old_value", "2000-01-01")):
            with self.subTest(field=field):
                change = dict(self.change, **{field: value})
                with self.assertRaisesRegex(ValueError, "does not match"):
                    preview_change(change, self.facts, self.topics)

    def test_unlabelled_simulation_is_rejected(self):
        self.change["evidence_type"] = "public_source"
        with self.assertRaisesRegex(ValueError, "only labelled synthetic"):
            preview_change(self.change, self.facts, self.topics)


if __name__ == "__main__":
    unittest.main()
