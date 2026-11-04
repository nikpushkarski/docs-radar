from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from docs_radar.support_review import build_review, load_review_outputs
from evals.run import evaluate, save_evaluation

ROOT = Path(__file__).resolve().parents[1]


class SupportReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.outputs = evaluate()

    def test_review_requires_confirmation_name_and_actual_decision(self):
        for reviewer, confirmed, decisions in (("Synthetic reviewer", False, {"Q01":{"0":True}}),
                ("", True, {"Q01":{"0":True}}), ("Synthetic reviewer", True, {})):
            with self.subTest(reviewer=reviewer, confirmed=confirmed), self.assertRaises(ValueError):
                build_review(self.report, self.outputs, decisions, reviewer, "2000-01-01", confirmed)

    def test_partial_and_negative_decisions_are_not_automatically_approved(self):
        review = build_review(self.report, self.outputs, {"Q01":{"0":False}}, "Synthetic reviewer", "2000-01-01", True)
        self.assertEqual(set(review), {"Q01"})
        self.assertEqual(review["Q01"]["claims"], {"0":False})
        self.assertEqual(review["Q01"]["output_hash"], self.report["cases"][0]["output_hash"])
        self.assertFalse(self.report["summary"]["human_review_complete"])

    def test_stale_outputs_and_invented_claims_fail_closed(self):
        changed = deepcopy(self.outputs)
        changed["Q01"]["claims"][0]["text"] = "Changed after review"
        for outputs, decisions in ((changed, {"Q01":{"0":True}}),
                (self.outputs, {"Q01":{"99":True}}), (self.outputs, {"Q01":{"0":None}}),
                (self.outputs, {"unknown":{"0":True}})):
            with self.subTest(decisions=decisions), self.assertRaises(ValueError):
                build_review(self.report, outputs, decisions, "Synthetic reviewer", "2000-01-01", True)

    def test_report_specific_artifact_round_trip_and_path_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            report=deepcopy(self.report)
            with patch("evals.run.ROOT", root):
                save_evaluation(root / "reports/test.json", report, self.outputs)
                with self.assertRaises(ValueError):
                    save_evaluation(root / "reports/test.json", report, self.outputs)
            self.assertEqual(load_review_outputs(root, report), self.outputs)
            report["output_artifact"] = "data/approvals.json"
            with self.assertRaises(ValueError):
                load_review_outputs(root, report)

    def test_ui_starts_unreviewed_and_exports_only_explicit_synthetic_choices(self):
        approvals = (ROOT / "data/approvals.json").read_bytes()
        with patch("docs_radar.quality_view.available_reports", return_value={"test-report":self.report}), \
             patch("docs_radar.support_review.load_review_outputs", return_value=self.outputs):
            app=AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=20).run()
            self.assertFalse(app.exception)
            choices=[r for r in app.radio if "supported by its cited evidence" in r.label]
            self.assertEqual(len(choices), 15)
            self.assertTrue(all(r.value == "Unreviewed" for r in choices))
            next(t for t in app.text_input if t.label == "Citation-support reviewer name").input("Synthetic UI reviewer")
            choices[0].set_value("Not supported")
            next(c for c in app.checkbox if c.label.startswith("I personally reviewed")).check()
            next(b for b in app.button if b.label == "Prepare review file").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Explicit decisions prepared" in s.value for s in app.success))
            self.assertEqual(len(app.get("download_button")), 1)
        self.assertEqual((ROOT / "data/approvals.json").read_bytes(), approvals)
