from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from approvals import load_approvals, record_approval
from retrieval import retrieve


ROOT = Path(__file__).resolve().parents[1]
TOPIC_ID = "provider-migration-checklist.md"


class RetrievalTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = Path(temporary.name) / "approvals.json"
        self.topics = {
            path.name: path.read_text(encoding="utf-8")
            for path in (ROOT / "content").glob("*.md")
        }
        self.facts = json.loads((ROOT / "data/facts.json").read_text(encoding="utf-8"))
        self.sources = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))
        self.approvals = {}

    def approve(self, topic_id=TOPIC_ID):
        # Test-only consent and temporary persistence; not a real demo approval.
        record_approval(
            self.store, topic_id, self.topics[topic_id], self.facts,
            "Synthetic test reviewer", "2000-01-01",
        )
        self.approvals = load_approvals(self.store)

    def ask(self, question="Where should I put lab orders after October 2026?",
            audience="Providers", reference_date="2026-11-01"):
        return retrieve(
            question, audience, reference_date,
            topics=self.topics, facts=self.facts, sources=self.sources,
            approvals=self.approvals,
        )

    def test_provider_question_retrieves_registered_evidence(self):
        self.approve()
        result = self.ask()
        self.assertEqual(result["status"], "retrieved")
        self.assertEqual(result["retrieved_source_ids"], ["rupa-transition-schedule"])
        self.assertTrue(result["passages"][0]["id"].endswith("#provider-ordering"))
        self.assertIn("place new lab orders through Fullscript", result["passages"][0]["body"])
        for passage in result["passages"]:
            self.assertEqual(passage["source_url"], self.sources[0]["url"])
            self.assertEqual(passage["content_version"], self.approvals[TOPIC_ID]["fingerprint"])
        self.assertNotIn("answer_text", result)

    def test_unapproved_and_edited_topics_cannot_be_retrieved(self):
        self.assertEqual(self.ask()["reason"], "no_approved_topics")
        self.approve()
        self.topics[TOPIC_ID] += "\nEdited after approval."
        result = self.ask()
        self.assertEqual(result["status"], "empty")
        self.assertEqual(result["passages"], [])

    def test_fact_edit_invalidates_retrieval(self):
        self.approve()
        self.facts[0]["version"] += 1
        self.assertEqual(self.ask()["reason"], "no_approved_topics")

    def test_audience_and_pre_capture_date_are_filtered(self):
        self.approve()
        for audience, reference_date in (("Patients", "2026-11-01"), ("Providers", "2026-10-31")):
            with self.subTest(audience=audience, reference_date=reference_date):
                result = self.ask(audience=audience, reference_date=reference_date)
                self.assertEqual(result["reason"], "no_applicable_passages")
                self.assertEqual(result["passages"], [])

    def test_boundary_rules_apply_before_ranking(self):
        self.approve()
        for reference_date, forbidden in (
            ("2026-12-04", "recommended-transfer"),
            ("2027-01-20", "transfer-before-closure"),
        ):
            with self.subTest(reference_date=reference_date):
                result = self.ask("recommended transfer date Rupa login closure", reference_date=reference_date)
                self.assertEqual(result["status"], "retrieved")
                ids = {passage["id"].split("#", 1)[1] for passage in result["passages"]}
                self.assertNotIn(forbidden, ids)
                if reference_date == "2027-01-20":
                    self.assertEqual(ids, {"closure-warning"})

    def test_no_overlap_returns_empty_not_arbitrary_evidence(self):
        self.approve()
        result = self.ask("volcano astronomy")
        self.assertEqual(result["reason"], "no_lexical_match")
        self.assertEqual(result["retrieved_source_ids"], [])

    def test_today_default_is_resolved_and_recorded(self):
        self.approve()
        with patch("retrieval.date") as clock:
            clock.today.return_value = date(2026, 11, 1)
            result = self.ask(reference_date=None)
        self.assertEqual(result["reference_date"], "2026-11-01")
        self.assertEqual(result["status"], "retrieved")

    def test_invalid_requests_are_explicit_errors(self):
        for arguments in (
            {"question": ""}, {"audience": "unknown"},
            {"reference_date": "tomorrow"}, {"reference_date": "20261101"},
        ):
            with self.subTest(arguments=arguments):
                result = self.ask(**arguments)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["reason"], "invalid_request")
                self.assertEqual(result["passages"], [])

    def test_changed_source_is_not_silently_used(self):
        self.approve()
        self.sources[0]["summary_sha256"] = "changed-source"
        result = self.ask()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "invalid_content")
        self.assertEqual(result["passages"], [])

    def test_results_use_three_distinct_sources_not_three_chunks(self):
        # Entirely synthetic corpus for source deduplication and context limits.
        self.topics = {}
        self.sources = []
        for number in range(4):
            source_id = f"synthetic-source-{number}"
            self.sources.append({
                "id": source_id, "url": f"https://example.invalid/{number}",
                "summary_sha256": "synthetic", "retrieved_on": "2026-11-01",
            })
            rules = [
                {"id": f"passage-{index}", "heading": f"Section {index}",
                 "valid_from": "2026-11-01", "valid_until": None}
                for index in range(4)
            ]
            metadata = {
                "source_id": source_id, "source_summary_sha256": "synthetic",
                "audience": "Providers", "passages": rules,
            }
            topic_id = f"synthetic-{number}.md"
            self.topics[topic_id] = "---\n" + json.dumps(metadata) + "\n---\n" + "\n".join(
                f"## Section {index}\nLab orders use Fullscript.\n" for index in range(4)
            )
            self.approve(topic_id)
        result = self.ask("lab orders")
        self.assertEqual(result["status"], "retrieved")
        self.assertEqual(result["retrieved_source_ids"], [f"synthetic-source-{n}" for n in range(3)])
        self.assertEqual(len(result["passages"]), 9)
        self.assertEqual({p["source_id"] for p in result["passages"]}, set(result["retrieved_source_ids"]))

    def test_retrieval_does_not_mutate_inputs(self):
        self.approve()
        before = deepcopy((self.topics, self.facts, self.sources, self.approvals))
        self.ask()
        self.assertEqual((self.topics, self.facts, self.sources, self.approvals), before)


if __name__ == "__main__":
    unittest.main()
