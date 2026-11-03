from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from docs_radar.answers import answer
from docs_radar.approvals import load_approvals, record_approval
from docs_radar.retrieval import load_workspace
from docs_radar.topic_metadata import split_topic


ROOT = Path(__file__).resolve().parents[1]
TOPIC_ID = "provider-migration-checklist.md"
QUESTION = "Where should I place new lab orders?"


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = Path(temporary.name) / "approvals.json"
        self.workspace = load_workspace()
        self.workspace["approvals"] = {}

    def approve(self):
        record_approval(
            self.store, TOPIC_ID, self.workspace["topics"][TOPIC_ID],
            self.workspace["facts"], "Synthetic test reviewer", "2000-01-01",
        )
        self.workspace["approvals"] = load_approvals(self.store)

    def ask(self, question=QUESTION, audience="Providers", reference_date="2026-11-01"):
        return answer(question, audience, reference_date, workspace=self.workspace)


class AnswerPipelineTest(WorkspaceTestCase):
    def test_returns_exact_excerpts_and_registered_citations(self):
        self.approve()
        result = self.ask()
        self.assertEqual(result["status"], "answered")
        self.assertIn("not a generated answer", result["answer_text"])
        self.assertIn("place new lab orders through Fullscript", result["answer_text"])
        source = self.workspace["sources"][0]
        for passage, claim, citation in zip(result["passages"], result["claims"], result["citations"]):
            self.assertEqual(claim["text"], passage["body"])
            self.assertEqual(claim["supporting_evidence_ids"], [passage["id"]])
            self.assertEqual(citation["evidence_id"], passage["id"])
            self.assertEqual(citation["source_url"], source["url"])
            self.assertEqual(citation["source_title"], source["title"])
            self.assertEqual(citation["evidence_type"], "demo_authored_topic")
        self.assertEqual(result["run"]["mode"], "extractive")
        self.assertIsNone(result["run"]["model_id_or_none"])
        self.assertIsNone(result["run"]["prompt_hash"])
        self.assertRegex(result["run"]["corpus_hash"], r"^[0-9a-f]{64}$")

    def test_missing_question_audience_or_date_requests_clarification(self):
        for arguments in ({"question": ""}, {"audience": None}, {"reference_date": "invalid"}):
            with self.subTest(arguments=arguments):
                result = self.ask(**arguments)
                self.assertEqual(result["status"], "clarify")
                self.assertEqual(result["citations"], [])

    def test_missing_approval_abstains_without_citations(self):
        result = self.ask()
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "no_approved_topics")
        self.assertEqual(result["citations"], [])

    def test_unsupported_account_status_abstains_before_retrieval(self):
        self.approve()
        for question in (
            "Has my doctor already transferred my Rupa data to Fullscript?",
            "Did our provider migrate our data?",
            "Is my transfer complete?",
        ):
            with self.subTest(question=question), patch("docs_radar.answers.retrieve") as retrieval:
                result = self.ask(question)
                self.assertEqual(result["status"], "abstain")
                self.assertEqual(result["reason"], "account_status_unavailable")
                self.assertEqual(result["citations"], [])
                retrieval.assert_not_called()

    def test_patient_workflow_question_is_not_mistaken_for_status_lookup(self):
        self.approve()
        result = self.ask(
            "My doctor didn't move to Fullscript; can I still pay an existing order?",
            audience="Patients",
        )
        self.assertEqual(result["reason"], "no_applicable_passages")
        # Patient corpus coverage is absent, not a passing answer evaluation.

    def test_no_matching_evidence_abstains(self):
        self.approve()
        result = self.ask("astronomy volcano")
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "no_lexical_match")

    def test_conflict_is_not_converted_into_an_answer(self):
        metadata, body = split_topic(self.workspace["topics"][TOPIC_ID])
        metadata["passages"][0]["unresolved_conflict_ids"] = ["synthetic-test-conflict"]
        self.workspace["topics"][TOPIC_ID] = "---\n" + json.dumps(metadata) + "\n---\n" + body
        self.approve()
        result = self.ask()
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "unresolved_evidence_conflict")
        self.assertTrue(result["conflicts"])
        self.assertEqual(result["passages"], [])
        self.assertEqual(result["claims"], [])
        self.assertEqual(result["citations"], [])

    def test_changed_evidence_is_an_error_not_a_fallback_answer(self):
        self.approve()
        self.workspace["sources"][0]["summary_sha256"] = "changed"
        result = self.ask()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "invalid_content")
        self.assertEqual(result["citations"], [])

    def test_invalid_registered_url_cannot_become_a_citation(self):
        self.approve()
        self.workspace["sources"][0]["url"] = "javascript:invalid"
        result = self.ask()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "invalid_citation")
        self.assertEqual(result["citations"], [])

    def test_load_failure_is_reported(self):
        with patch("docs_radar.answers.load_workspace", side_effect=OSError("test-only load failure")):
            result = answer(QUESTION, "Providers", "2026-11-01")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "workspace_error")

    def test_corpus_changes_change_run_identifier(self):
        self.approve()
        before = self.ask()["run"]["corpus_hash"]
        self.workspace["topics"]["about-demo.md"] += "\nTest-only edit."
        self.assertNotEqual(self.ask()["run"]["corpus_hash"], before)


class AnswerUiTest(WorkspaceTestCase):
    def submit(self, question=QUESTION, audience="Providers"):
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=10).run()
        app.text_input[0].input(question)
        app.selectbox[0].select(audience)
        app.date_input[0].set_value(date(2026, 11, 1))
        app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        return app

    def test_ui_displays_extracts_and_source_links(self):
        self.approve()
        with patch("docs_radar.answers.load_workspace", return_value=self.workspace):
            app = self.submit()
        self.assertTrue(any("Extractive mode" in element.value for element in app.info))
        self.assertTrue(any("place new lab orders through Fullscript" in element.value for element in app.text))
        self.assertGreater(len(app.get("link_button")), 0)

    def test_ui_explains_no_approval(self):
        with patch("docs_radar.answers.load_workspace", return_value=self.workspace):
            app = self.submit()
        self.assertTrue(any("No demo-approved content" in element.value for element in app.warning))
        self.assertEqual(len(app.get("link_button")), 0)

    def test_ui_asks_for_audience(self):
        with patch("docs_radar.answers.load_workspace", return_value=self.workspace):
            app = self.submit(audience="Choose audience")
        self.assertTrue(any("Choose Providers or Patients" in element.value for element in app.info))
