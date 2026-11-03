from copy import deepcopy
import json
from pathlib import Path
import unittest

from content_fingerprint import content_fingerprint


ROOT = Path(__file__).resolve().parents[1]


class ContentFingerprintTest(unittest.TestCase):
    def setUp(self):
        self.text = (
            ROOT / "content/provider-migration-checklist.md"
        ).read_text(encoding="utf-8")
        self.facts = json.loads(
            (ROOT / "data/facts.json").read_text(encoding="utf-8")
        )
        self.original = content_fingerprint(self.text, self.facts)

    def test_fingerprint_is_stable_across_json_ordering(self):
        # A second, synthetic reference tests fact-list ordering as well.
        facts = self.facts + [{"id": "test-only", "value": "example", "version": 1}]
        text = self.text + "\n{{fact:test-only}}"
        reordered = [dict(reversed(list(fact.items()))) for fact in reversed(facts)]
        fingerprint = content_fingerprint(text, facts)
        self.assertEqual(fingerprint, content_fingerprint(text, reordered))
        self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")

    def test_topic_edit_changes_fingerprint(self):
        self.assertNotEqual(
            self.original,
            content_fingerprint(self.text + "\nExtra instruction.", self.facts),
        )

    def test_value_edit_changes_fingerprint_without_version_bump(self):
        # Synthetic value in memory only, not a Fullscript date change.
        changed = deepcopy(self.facts)
        changed[0]["value"] = "2099-01-01"
        self.assertNotEqual(self.original, content_fingerprint(self.text, changed))

    def test_version_edit_changes_fingerprint_without_value_change(self):
        changed = deepcopy(self.facts)
        changed[0]["version"] += 1
        self.assertNotEqual(self.original, content_fingerprint(self.text, changed))

    def test_referenced_evidence_or_audience_edit_changes_fingerprint(self):
        for field, value in (("source_id", "test-source"), ("audience", "Patients")):
            with self.subTest(field=field):
                changed = deepcopy(self.facts)
                changed[0][field] = value
                self.assertNotEqual(
                    self.original, content_fingerprint(self.text, changed)
                )

    def test_unrelated_fact_addition_and_edit_do_not_change_fingerprint(self):
        facts = deepcopy(self.facts)
        facts.append({"id": "unrelated", "value": "before", "version": 1})
        self.assertEqual(self.original, content_fingerprint(self.text, facts))
        facts[-1].update(value="after", version=2)
        self.assertEqual(self.original, content_fingerprint(self.text, facts))

    def test_unknown_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown fact ID: missing"):
            content_fingerprint("{{fact:missing}}", self.facts)

    def test_duplicate_referenced_fact_is_rejected(self):
        facts = self.facts + [deepcopy(self.facts[0])]
        with self.assertRaisesRegex(ValueError, "Duplicate referenced fact ID"):
            content_fingerprint(self.text, facts)

    def test_topic_without_references_does_not_depend_on_facts(self):
        text = (ROOT / "content/about-demo.md").read_text(encoding="utf-8")
        self.assertEqual(
            content_fingerprint(text, self.facts), content_fingerprint(text, [])
        )


if __name__ == "__main__":
    unittest.main()
