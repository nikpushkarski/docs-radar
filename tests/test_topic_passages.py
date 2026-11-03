from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from docs_radar.approvals import approval_status, load_approvals, record_approval
from docs_radar.passage_selection import select_applicable_passages
from docs_radar.render_topic import render_topic
from docs_radar.topic_metadata import section_body, split_topic
from docs_radar.topic_passages import build_topic_passages


ROOT = Path(__file__).resolve().parents[1]
TOPIC_ID = "provider-migration-checklist.md"


class TopicPassagesTest(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "content" / TOPIC_ID).read_text(encoding="utf-8")
        self.facts = json.loads((ROOT / "data/facts.json").read_text(encoding="utf-8"))
        self.sources = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))
        self.passages = build_topic_passages(TOPIC_ID, self.text, self.facts, self.sources)

    def test_real_passages_are_attributed_and_rendered(self):
        self.assertEqual(len(self.passages), 5)
        for passage in self.passages:
            self.assertEqual(passage["source_id"], "rupa-transition-schedule")
            self.assertEqual(passage["source_url"], self.sources[0]["url"])
            self.assertEqual(passage["evidence_type"], "demo_authored_topic")
            self.assertEqual(passage["captured_on"], "2026-11-01")
            self.assertNotIn("{{fact:", passage["body"])
            self.assertTrue(passage["body"])

    def test_actual_guidance_changes_on_both_boundaries(self):
        before = {"provider-ordering", "recommended-transfer", "transfer-before-closure"}
        between = {"provider-ordering", "transfer-before-closure", "recommendation-date-passed"}
        cases = {
            "2026-12-03": before, "2026-12-04": between,
            "2027-01-19": between, "2027-01-20": {"closure-warning"},
        }
        for reference_date, expected in cases.items():
            with self.subTest(reference_date=reference_date):
                selected = select_applicable_passages(self.passages, "Providers", reference_date)
                self.assertEqual(
                    {passage["id"].split("#", 1)[1] for passage in selected}, expected
                )
        closed = select_applicable_passages(self.passages, "Providers", "2027-01-20")
        self.assertIn("do not assume", closed[0]["body"])
        self.assertIn("Recovery procedures are not established", closed[0]["body"])
        self.assertNotIn("Transfer your Rupa data before", closed[0]["body"])

    def test_provider_passages_are_not_used_for_patients(self):
        self.assertEqual(select_applicable_passages(self.passages, "Patients", "2026-11-01"), [])

    def test_date_rule_or_audience_change_invalidates_approval(self):
        # Synthetic approval only; no real review is implied by this test.
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "approvals.json"
            record_approval(path, TOPIC_ID, self.text, self.facts, "Test reviewer", "2000-01-01")
            approvals = load_approvals(path)
            self.assertEqual(approval_status(TOPIC_ID, self.text, self.facts, approvals), "eligible")
            changes = (
                self.text.replace('"audience": "Providers"', '"audience": "Patients"'),
                self.text.replace('"valid_until": "2026-12-04"', '"valid_until": "2026-12-05"'),
            )
            for changed in changes:
                with self.subTest(changed=changed[:100]):
                    self.assertNotEqual(changed, self.text)
                    self.assertEqual(approval_status(TOPIC_ID, changed, self.facts, approvals), "changed")

    def test_shared_date_controls_routing_bounds_as_well_as_text(self):
        # Deliberately fictional change in memory, not a revised public date.
        facts = deepcopy(self.facts)
        facts[0].update(value="2099-01-01", version=2)
        passages = build_topic_passages(TOPIC_ID, self.text, facts, self.sources)
        closure = next(p for p in passages if p["id"].endswith("#closure-warning"))
        transfer = next(p for p in passages if p["id"].endswith("#transfer-before-closure"))
        self.assertEqual(closure["valid_from"], "2099-01-01")
        self.assertEqual(transfer["valid_until"], "2099-01-01")
        self.assertIn("2099-01-01", transfer["body"])

    def test_changed_source_evidence_is_rejected(self):
        sources = deepcopy(self.sources)
        sources[0]["summary_sha256"] = "different-version"
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            build_topic_passages(TOPIC_ID, self.text, self.facts, sources)
        with self.assertRaisesRegex(ValueError, "Unknown passage source"):
            build_topic_passages(TOPIC_ID, self.text, self.facts, [])

    def test_metadata_is_not_displayed_as_answer_text(self):
        rendered = render_topic(self.text, self.facts)
        self.assertNotIn('"passages"', rendered)
        self.assertNotIn('"valid_from"', rendered)
        self.assertIn("# Before Rupa login access closes", rendered)

    def test_unregistered_topics_produce_no_passages(self):
        text = (ROOT / "content/about-demo.md").read_text(encoding="utf-8")
        self.assertEqual(build_topic_passages("about-demo.md", text, self.facts, self.sources), [])

    def test_malformed_metadata_and_ambiguous_sections_are_rejected(self):
        for text in ("---\n{}", "---\n[]\n---\nBody", "---\nnot-json\n---\nBody"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    split_topic(text)
        for body in ("# No section", "## Name\n", "## Name\nOne\n## Name\nTwo"):
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    section_body(body, "Name")


if __name__ == "__main__":
    unittest.main()
