from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from docs_radar.approvals import load_approvals, record_approval
from docs_radar.retrieval import retrieve


ROOT = Path(__file__).resolve().parents[1]


class RetrievalConflictTest(unittest.TestCase):
    def setUp(self):
        fixture = json.loads(
            (ROOT / "tests/fixtures/conflicting_passages.json").read_text(encoding="utf-8")
        )
        self.assertEqual(fixture["evidence_type"], "synthetic")
        self.records = fixture["passages"]
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = Path(temporary.name) / "approvals.json"
        self.topics = {}
        self.sources = []
        self.approvals = {}

    def add_topic(self, record, approve=True):
        source_id = record["source_id"]
        self.sources.append({
            "id": source_id, "summary_sha256": "synthetic",
            "url": f"https://example.invalid/{source_id}", "retrieved_on": "2026-11-01",
        })
        metadata = {
            "source_id": source_id, "source_summary_sha256": "synthetic",
            "audience": record["audience"],
            "passages": [{
                "id": "ordering", "heading": "Ordering",
                "valid_from": record["valid_from"], "valid_until": record["valid_until"],
                "unresolved_conflict_ids": record["unresolved_conflict_ids"],
            }],
        }
        topic_id = record["topic_id"]
        text = "---\n" + json.dumps(metadata) + "\n---\n## Ordering\n" + record["body"]
        self.topics[topic_id] = text
        if approve:
            record_approval(self.store, topic_id, text, [], "Synthetic test reviewer", "2000-01-01")
            self.approvals = load_approvals(self.store)

    def ask(self, question="new lab orders"):
        return retrieve(
            question, "Providers", "2026-11-01",
            topics=self.topics, facts=[], sources=self.sources, approvals=self.approvals,
        )

    def test_conflict_returns_both_sides_without_answer_context(self):
        for record in self.records:
            self.add_topic(record)
        result = self.ask()
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["reason"], "unresolved_evidence_conflict")
        self.assertEqual(result["passages"], [])
        self.assertEqual(result["retrieved_source_ids"], [])
        self.assertEqual(len(result["conflicts"]), 1)
        conflict = result["conflicts"][0]
        self.assertEqual(conflict["id"], "synthetic-ordering-destination")
        self.assertEqual(
            {passage["topic_id"] for passage in conflict["passages"]},
            {record["topic_id"] for record in self.records},
        )
        self.assertTrue(all(p["content_version"] for p in conflict["passages"]))

    def test_lower_ranked_conflict_is_not_hidden_by_source_limit(self):
        for index in range(3):
            distractor = deepcopy(self.records[0])
            distractor.update(
                topic_id=f"synthetic-distractor-{index}.md",
                source_id=f"synthetic-distractor-{index}",
                body="new lab orders", unresolved_conflict_ids=[],
            )
            self.add_topic(distractor)
        for record in self.records:
            self.add_topic(record)
        self.assertEqual(self.ask()["status"], "conflict")

    def test_unrelated_query_does_not_trigger_flagged_conflict(self):
        for record in self.records:
            self.add_topic(record)
        result = self.ask("astronomy volcano")
        self.assertEqual(result["reason"], "no_lexical_match")
        self.assertEqual(result["conflicts"], [])

    def test_other_audience_and_future_passages_do_not_trigger_conflict(self):
        for change in ({"audience": "Patients"}, {"valid_from": "2027-01-01"}):
            with self.subTest(change=change):
                record = deepcopy(self.records[0])
                record.update(change)
                self.add_topic(record)
                result = self.ask()
                self.assertEqual(result["reason"], "no_applicable_passages")
                self.assertEqual(result["conflicts"], [])

    def test_unapproved_evidence_is_not_exposed_or_treated_as_resolution(self):
        self.add_topic(self.records[0])
        self.add_topic(self.records[1], approve=False)
        result = self.ask()
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(
            [p["topic_id"] for p in result["conflicts"][0]["passages"]],
            [self.records[0]["topic_id"]],
        )

    def test_inspection_includes_flagged_peer_without_query_overlap(self):
        self.add_topic(self.records[0])
        peer = deepcopy(self.records[1])
        peer["body"] = "Disputed destination: B."
        self.add_topic(peer)
        result = self.ask()
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(len(result["conflicts"][0]["passages"]), 2)

    def test_changing_conflict_flags_invalidates_approval(self):
        self.add_topic(self.records[0])
        topic_id = self.records[0]["topic_id"]
        self.topics[topic_id] = self.topics[topic_id].replace(
            '["synthetic-ordering-destination"]', '[]'
        )
        result = self.ask()
        self.assertEqual(result["reason"], "no_approved_topics")
        self.assertEqual(result["passages"], [])

    def test_malformed_conflict_flag_is_an_explicit_content_error(self):
        record = deepcopy(self.records[0])
        record["unresolved_conflict_ids"] = "not-a-list"
        self.add_topic(record)
        result = self.ask()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "invalid_content")
        self.assertEqual(result["passages"], [])


if __name__ == "__main__":
    unittest.main()
