from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from tests.app_helpers import OfflineModelMixin
from docs_radar.local_runtime import RuntimeStatus


ROOT = Path(__file__).resolve().parents[1]


class AppSmokeTest(OfflineModelMixin, unittest.TestCase):
    def test_page_loads(self):
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py")).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.title[0].value, "Docs Radar")
        self.assertIn("Independent demo", app.caption[0].value)

    def test_installed_model_is_prefilled_without_changing_extractive_default(self):
        self.runtime_start.return_value = RuntimeStatus(model="test:latest")
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input[1].value, "test:latest")
        self.assertEqual(app.radio[0].value, "Extractive")
        app.button(key="toggle_notes").click().run()
        self.assertEqual(app.text_input[1].value, "test:latest")
        self.assertTrue(any("Local model server ready" in item.value for item in app.caption))

    def test_model_startup_failure_keeps_app_usable_and_never_calls_other_listener(self):
        self.runtime_start.return_value = RuntimeStatus(error="Port 11435 is already in use")
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs), 3)
        self.assertTrue(any("Extractive mode still works" in item.value for item in app.warning))
        app.radio[0].set_value("Model-selected excerpts (optional)")
        with patch("docs_radar.answers.answer") as answer:
            app.button[0].click().run()
        answer.assert_not_called()
        self.assertTrue(any("Local model selection is unavailable" in item.value for item in app.error))
        app.radio[0].set_value("Extractive")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Enter a question" in item.value for item in app.info))

    def test_explicit_retry_refreshes_status_and_prefills_recovered_model(self):
        self.runtime_start.return_value = RuntimeStatus(error="Startup failed")
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        self.runtime_start.side_effect = [RuntimeStatus(error="Startup failed"),
                                          RuntimeStatus(model="test:latest"), RuntimeStatus(model="test:latest")]
        app.button(key="retry_model_server").click().run()
        self.assertFalse(app.exception)
        self.runtime_start.assert_any_call(ROOT, retry=True)
        self.assertEqual(app.text_input[1].value, "test:latest")
        self.assertFalse(any("Local model unavailable" in item.value for item in app.warning))


if __name__ == "__main__":
    unittest.main()
