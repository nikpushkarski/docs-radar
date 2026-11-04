"""Corpus-only v3 update: preserve every v2 requirement and prove the new coverage."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from tests.app_helpers import OfflineModelMixin

from docs_radar.answers import answer
from docs_radar.approvals import approval_status
from docs_radar.content_fingerprint import content_fingerprint
from docs_radar.retrieval import load_workspace
from evals.assertions import get_assert
from evals.provider import call_api
from evals.run import compare_baseline, evaluate
from evals.suite import load_suite, prepare_case, suite_root, verify_manifest
from scripts.build_eval_config import build_config

ROOT = Path(__file__).resolve().parents[1]


class CorpusVersionTests(OfflineModelMixin, unittest.TestCase):
    def test_v2_remains_frozen_and_v3_changes_no_expectation(self):
        self.assertEqual(verify_manifest(suite_root("v2"))["bundle_sha256"],
                         "eeb5c8943255702dcc405bfac4854f9c9d7d8f7f90508af2482cf284024e3405")
        old, new = (load_suite(suite_root(v)) for v in ("v2", "v3"))
        for a, b in zip(old["cases"], new["cases"]):
            self.assertEqual({k:v for k,v in a.items() if k != "fixture_id"},
                             {k:v for k,v in b.items() if k != "fixture_id"})
        self.assertEqual(old["acceptance_rules_markdown"], new["acceptance_rules_markdown"])

    def test_adversarial_fixtures_are_unchanged(self):
        a, b = (verify_manifest(suite_root(v)) for v in ("v2", "v3"))
        for name in ("draft-only-v1", "conflict-v1", "forged-citation-v1", "injected-instruction-v1"):
            self.assertEqual(a["files"][a["fixtures"][name]], b["files"][b["fixtures"][name]])

    def test_corpus_change_is_exactly_the_two_reviewed_topics(self):
        _, old = prepare_case("Q01", suite_root("v2"))
        _, new = prepare_case("Q01", suite_root("v3"))
        self.assertEqual(old["sources"], new["sources"])
        self.assertEqual(old["facts"], new["facts"])
        changed = {name for name in old["topics"].keys() | new["topics"].keys()
                   if old["topics"].get(name) != new["topics"].get(name)}
        self.assertEqual(changed, {"provider-migration-checklist.md", "patient-unpaid-orders.md"})
        pins = verify_manifest(suite_root("v3"))["approved_topic_fingerprints"]
        for name in changed:
            self.assertEqual(content_fingerprint(new["topics"][name], new["facts"]), pins[name])
        self.assertTrue(all(record["reviewer"] == "Synthetic evaluation reviewer" for record in new["approvals"].values()))

    def test_v3_passes_all_existing_deterministic_requirements_not_human_review(self):
        report, _ = evaluate(version="v3")
        self.assertEqual(report["summary"]["automated_passes"], 12)
        self.assertEqual(report["summary"]["source_recall_at_3_mean"], 1)
        self.assertTrue(report["summary"]["automated_gate_pass"])
        self.assertFalse(report["summary"]["human_review_complete"])
        self.assertIsNone(report["summary"]["manual_citation_accuracy"]["value"])
        old, _ = evaluate(version="v2")
        self.assertFalse(compare_baseline(report, old)["compatible"])

    def test_full_suite_regression_fails_then_recovers_without_mutations(self):
        before = (ROOT / "data/approvals.json").read_bytes()
        hashes = {v:verify_manifest(suite_root(v))["bundle_sha256"] for v in ("v2", "v3")}
        for injected in (False, True, False):
            report, _ = evaluate(inject_regression=injected)
            self.assertEqual(report["summary"]["automated_gate_pass"], not injected)
            self.assertEqual(len(report["cases"]), 12)
        self.assertEqual((ROOT / "data/approvals.json").read_bytes(), before)
        self.assertEqual(hashes, {v:verify_manifest(suite_root(v))["bundle_sha256"] for v in hashes})

    def test_promptfoo_runs_same_v3_pipeline_and_negative_control(self):
        for injected in (False, True):
            config = build_config("v3", injected)
            case = config["tests"][1]  # Patient payment, previously missing from v2.
            response = call_api(case["vars"]["request"], config["providers"][0], {"gold": "not forwarded"})
            self.assertEqual(get_assert(response["output"], {"vars":case["vars"]})["pass"], not injected)
        with patch("evals.provider.answer", return_value={}) as called:
            call_api(case["vars"]["request"], config["providers"][0], {"expected": "not forwarded"})
        self.assertEqual(set(called.call_args.kwargs), {"question", "audience", "reference_date", "workspace", "mode", "model"})

    def test_unknown_version_is_rejected(self):
        with self.assertRaises(ValueError):
            suite_root("../../data")


class ApprovedContentTests(unittest.TestCase):
    def test_real_topics_match_explicitly_approved_fingerprints(self):
        workspace = load_workspace()
        for name, expected in verify_manifest(suite_root("v3"))["approved_topic_fingerprints"].items():
            text = workspace["topics"][name]
            self.assertEqual(content_fingerprint(text, workspace["facts"]), expected)
            self.assertEqual(approval_status(name, text, workspace["facts"], workspace["approvals"]), "eligible")
            self.assertEqual(workspace["approvals"][name]["reviewer"], "Nik")

    def test_patient_payment_date_boundaries_and_explicit_account_status_abstention(self):
        inputs, workspace = prepare_case("Q02", suite_root("v3"))
        for reference_date in ("2026-12-22", "2026-12-23"):
            output = answer(**{**inputs, "reference_date":reference_date}, workspace=workspace)
            self.assertEqual(output["status"], "answered")
            self.assertIn("If your provider has not transferred", output["answer_text"])
        output = answer(**{**inputs, "reference_date":"2026-12-24"}, workspace=workspace)
        self.assertEqual(output["reason"], "no_applicable_passages")
        output = answer("Has my doctor transferred my data?", "Patients", "2026-11-01", workspace=workspace)
        self.assertEqual(output["reason"], "account_status_unavailable")

    def test_ui_patient_question_now_returns_evidence(self):
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        app.text_input[0].input("My doctor didn't move to Fullscript; can I pay an existing unpaid Rupa order?")
        app.selectbox[0].select("Patients")
        app.date_input[0].set_value(date(2026, 11, 1))
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("December 23, 2026" in t.value for t in app.tabs[0].text))
        self.assertTrue(app.tabs[0].get("link_button"))
