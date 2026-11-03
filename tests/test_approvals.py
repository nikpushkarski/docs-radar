from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from docs_radar.approvals import approval_status, eligible_topics, load_approvals, record_approval


ROOT = Path(__file__).resolve().parents[1]
TOPIC_ID = "provider-migration-checklist.md"


class ApprovalTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = Path(temporary.name) / "approvals.json"
        self.topics = {
            path.name: path.read_text(encoding="utf-8")
            for path in (ROOT / "content").glob("*.md")
        }
        self.text = self.topics[TOPIC_ID]
        self.facts = json.loads(
            (ROOT / "data/facts.json").read_text(encoding="utf-8")
        )

    def approve_test_topic(self, text=None, facts=None):
        # Synthetic test approval in a temporary file, never Nik's approval.
        record_approval(
            self.store, TOPIC_ID,
            self.text if text is None else text,
            self.facts if facts is None else facts,
            reviewer="Synthetic test reviewer", approved_on="2000-01-01",
        )
        return load_approvals(self.store)

    def test_no_approval_excludes_all_topics(self):
        approvals = load_approvals(self.store)
        self.assertEqual(eligible_topics(self.topics, self.facts, approvals), {})
        self.assertEqual(
            approval_status(TOPIC_ID, self.text, self.facts, approvals),
            "no_approval",
        )

    def test_persisted_approval_admits_only_the_exact_topic(self):
        approvals = self.approve_test_topic()
        self.assertTrue(self.store.exists())
        self.assertEqual(approvals[TOPIC_ID]["reviewer"], "Synthetic test reviewer")
        self.assertEqual(
            eligible_topics(self.topics, self.facts, approvals),
            {TOPIC_ID: self.text},
        )

    def test_topic_edit_invalidates_approval(self):
        approvals = self.approve_test_topic()
        changed = self.text + "\nAdditional instruction."
        self.assertEqual(
            approval_status(TOPIC_ID, changed, self.facts, approvals), "changed"
        )
        self.assertEqual(eligible_topics({TOPIC_ID: changed}, self.facts, approvals), {})

    def test_fact_value_or_version_edit_invalidates_approval(self):
        approvals = self.approve_test_topic()
        for field, value in (("value", "2099-01-01"), ("version", 2)):
            with self.subTest(field=field):
                changed = deepcopy(self.facts)
                changed[0][field] = value
                self.assertEqual(
                    approval_status(TOPIC_ID, self.text, changed, approvals),
                    "changed",
                )
                self.assertEqual(eligible_topics(self.topics, changed, approvals), {})

    def test_unrelated_fact_does_not_invalidate_approval(self):
        approvals = self.approve_test_topic()
        facts = self.facts + [{"id": "unrelated", "value": "test", "version": 1}]
        self.assertEqual(
            eligible_topics(self.topics, facts, approvals), {TOPIC_ID: self.text}
        )

    def test_nonapproved_states_are_excluded(self):
        approvals = self.approve_test_topic()
        for state in ("captured", "draft", "deprecated", "archived", "published"):
            with self.subTest(state=state):
                approvals[TOPIC_ID]["state"] = state
                self.assertEqual(eligible_topics(self.topics, self.facts, approvals), {})

    def test_reapproval_admits_new_version_and_excludes_old_one(self):
        self.approve_test_topic()
        changed = self.text + "\nRevised instruction."
        approvals = self.approve_test_topic(text=changed)
        self.assertEqual(
            eligible_topics({TOPIC_ID: changed}, self.facts, approvals),
            {TOPIC_ID: changed},
        )
        self.assertEqual(eligible_topics(self.topics, self.facts, approvals), {})

    def test_missing_fact_is_excluded(self):
        approvals = self.approve_test_topic()
        self.assertEqual(approval_status(TOPIC_ID, self.text, [], approvals), "invalid_content")
        self.assertEqual(eligible_topics(self.topics, [], approvals), {})

    def test_malformed_approval_is_excluded(self):
        original = self.approve_test_topic()
        for field, value in (
            ("topic_id", "different-topic"), ("reviewer", ""),
            ("approved_on", "not-a-date"), ("fingerprint", "wrong-hash"),
        ):
            with self.subTest(field=field):
                approvals = deepcopy(original)
                approvals[TOPIC_ID][field] = value
                self.assertEqual(eligible_topics(self.topics, self.facts, approvals), {})

    def test_approval_requires_reviewer_and_date(self):
        for reviewer, approved_on in (("", "2000-01-01"), ("Test", "invalid")):
            with self.subTest(reviewer=reviewer, approved_on=approved_on):
                with self.assertRaises(ValueError):
                    record_approval(
                        self.store, TOPIC_ID, self.text, self.facts,
                        reviewer, approved_on,
                    )
        self.assertFalse(self.store.exists())

    def test_corrupt_store_is_not_silently_overwritten(self):
        for contents in ("not-json", "[]"):
            with self.subTest(contents=contents):
                self.store.write_text(contents, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.approve_test_topic()
                self.assertEqual(self.store.read_text(encoding="utf-8"), contents)


if __name__ == "__main__":
    unittest.main()
