from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from docs_radar.quality_view import available_reports, report_freshness
from evals.run import evaluate

ROOT = Path(__file__).resolve().parents[1]


class ViewTests(unittest.TestCase):
    def test_three_views_and_no_implicit_approval(self):
        approvals = (ROOT / "data/approvals.json").read_bytes()
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        self.assertEqual([tab.label for tab in app.tabs], ["Ask and inspect", "Content and changes", "Quality"])
        self.assertTrue(any("SYNTHETIC" in item.value for item in app.warning))
        self.assertTrue(any("Human citation-support review is incomplete" in item.value for item in app.warning))
        self.assertEqual((ROOT / "data/approvals.json").read_bytes(), approvals)

    def test_default_requires_no_model_and_model_output_is_labelled_extractive(self):
        import json
        from datetime import date
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        self.assertEqual(app.radio[0].value, "Extractive")
        app.text_input[0].input("Where should I place new lab orders?")
        app.selectbox[0].select("Providers")
        app.date_input[0].set_value(date(2026, 11, 1))
        app.radio[0].set_value("Model-selected excerpts (optional)")
        with patch("docs_radar.generation.invoke_local", return_value=(json.dumps({
                "status": "answered", "source_indices": [0]}), "a" * 64)):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(x.value == "Model-selected excerpts" for x in app.tabs[0].subheader))
        self.assertTrue(any("not generated prose" in x.value for x in app.tabs[0].caption))

    def test_report_freshness_checks_code_and_dataset(self):
        report, _ = evaluate()
        self.assertEqual(report_freshness(report), [])
        report["provenance"]["code_hash"] = "old"
        self.assertTrue(any("code differs" in reason for reason in report_freshness(report)))
        report["provenance"]["test_set_hash"] = "old"
        self.assertTrue(any("test-set" in reason for reason in report_freshness(report)))

    def test_fresh_checkout_prefers_current_suite_over_historical_baseline(self):
        import tempfile
        from evals.run import save_report
        current, _ = evaluate()
        historical = deepcopy(current)
        historical["provenance"]["test_set_version"] = "v2"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save_report(root / "reports/a-old.json", historical)
            save_report(root / "reports/z-current.json", current)
            self.assertEqual(next(iter(available_reports(root))), "reports/z-current.json")

    def test_recorded_live_attempt_is_not_current_live_evidence(self):
        report = available_reports(ROOT)["reports/live-model-attempt-v2.json"]
        self.assertIn("No complete live-model evidence", report_freshness(report))

    def test_live_request_shows_error_without_fallback(self):
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        from datetime import date
        app.text_input[0].input("Where should I place new lab orders?")
        app.selectbox[0].select("Providers")
        app.date_input[0].set_value(date(2026, 11, 1))
        app.radio[0].set_value("Model-selected excerpts (optional)")
        app.text_input[1].input("qwen3:4b")
        with patch("docs_radar.generation.invoke_local", side_effect=ImportError):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Local model selection is unavailable" in item.value for item in app.tabs[0].error))
        self.assertFalse(app.tabs[0].get("link_button"))
