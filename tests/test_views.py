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

    def test_synthetic_preview_is_visible_and_does_not_write_files(self):
        paths = [ROOT / "data/approvals.json", ROOT / "data/facts.json",
                 *sorted((ROOT / "content").glob("*.md"))]
        before = {path: path.read_bytes() for path in paths}
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        topic = next(widget for widget in app.selectbox if widget.label == "Topic to inspect")
        topic.select("rupa-view-only.md").run()
        self.assertFalse(app.exception)
        self.assertTrue(any(item.label == "Simulated preview—not saved" for item in app.expander))
        previews = [item.value for item in app.markdown if '<del ' in item.value]
        self.assertEqual(len(previews), 1)
        self.assertIn('2027-01-20</del>', previews[0])
        self.assertIn('2099-01-01</ins>', previews[0])
        self.assertTrue(any('2027-01-20' in item.value and '2099-01-01' not in item.value for item in app.text))
        next(widget for widget in app.selectbox if widget.label == "Topic to inspect").select("patient-unpaid-orders.md").run()
        self.assertFalse(app.exception)
        self.assertTrue(any('no simulated edits to show' in item.value for item in app.info))
        self.assertFalse(any('<del ' in item.value for item in app.markdown))
        self.assertEqual({path: path.read_bytes() for path in paths}, before)

    def test_approval_and_simulated_impact_are_separate_and_explained(self):
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        table = next(item.value for item in app.dataframe if "Approval for answers" in item.value.columns)
        rows = {row['Document']: row for row in table.to_dict('records')}
        expected = {
            'patient-unpaid-orders.md': ('Approved', 'No'),
            'provider-migration-checklist.md': ('Approved', 'Yes'),
            'rupa-view-only.md': ('Not approved — no review recorded', 'Yes'),
        }
        for name, (approval, impact) in expected.items():
            with self.subTest(topic=name):
                self.assertEqual(rows[name]['Approval for answers'], approval)
                self.assertEqual(rows[name]['Affected by simulated change?'], impact)
                next(widget for widget in app.selectbox if widget.label == 'Topic to inspect').select(name).run()
                self.assertFalse(app.exception)
                self.assertTrue(any(f'Approval for answers: {approval}. Affected by simulated change: {impact}.' == item.value for item in app.info))
        self.assertTrue(any('A simulated preview does not change approval' in item.value for item in app.caption))

    def test_nonapproved_states_keep_useful_plain_language_reasons(self):
        labels = {
            'changed': 'Needs reapproval — content or facts changed',
            'not_approved': 'Not approved — approval inactive',
            'invalid_approval': 'Not approved — invalid approval record',
            'invalid_content': 'Not approved — invalid content or fact references',
        }
        for status, label in labels.items():
            with self.subTest(status=status), patch('docs_radar.approvals.approval_status', return_value=status):
                app = AppTest.from_file(str(ROOT / 'docs_radar/app.py'), default_timeout=15).run()
                self.assertFalse(app.exception)
                table = next(item.value for item in app.dataframe if 'Approval for answers' in item.value.columns)
                self.assertEqual(set(table['Approval for answers']), {label})
                self.assertEqual(set(table['Affected by simulated change?']), {'Yes', 'No'})

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
