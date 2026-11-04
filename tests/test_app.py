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
        self.assertEqual(app.selectbox[1].value, "test:latest")
        self.assertEqual(app.selectbox[1].options, ["test:latest", "Other…"])
        self.assertFalse(any(item.label == "Other local model tag" for item in app.text_input))
        self.assertEqual(app.radio[0].value, "Extractive")
        app.button(key="toggle_notes").click().run()
        self.assertEqual(app.selectbox[1].value, "test:latest")
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
        self.assertEqual(app.selectbox[1].value, "test:latest")
        self.assertFalse(any("Local model unavailable" in item.value for item in app.warning))

    def test_dropdown_lists_installed_tags_with_configured_model_first(self):
        self.runtime_start.return_value = RuntimeStatus(model="z:latest")
        self.installed_tags.return_value = ("a:latest", "z:latest")
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        self.assertEqual(app.selectbox[1].label, "Installed local model")
        self.assertEqual(app.selectbox[1].options, ["z:latest", "a:latest", "Other…"])
        app.selectbox[1].select("a:latest").run()
        app.button(key="toggle_notes").click().run()
        self.assertEqual(app.selectbox[1].value, "a:latest")

    def test_other_reveals_input_immediately_and_only_submit_calls_answer(self):
        from docs_radar.answers import answer
        result = answer("", "Providers", "2026-11-01")
        self.runtime_start.return_value = RuntimeStatus(model="test:latest")
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        with patch("docs_radar.answers.answer", return_value=result) as call:
            app.text_input[0].input("Where should I place new lab orders?").run()
            app.selectbox[0].select("Providers").run()
            app.radio[0].set_value("Model-selected excerpts (optional)").run()
            app.selectbox[1].select("Other…").run()
            self.assertFalse(app.exception)
            custom = next(item for item in app.text_input if item.label == "Other local model tag")
            custom.input("  custom:latest  ").run()
            self.assertEqual(app.text_input[0].value, "Where should I place new lab orders?")
            self.assertEqual(app.selectbox[0].value, "Providers")
            call.assert_not_called()
            app.button[0].click().run()
            self.assertEqual(call.call_args.kwargs["model"], "custom:latest")
            self.assertEqual(call.call_args.kwargs["mode"], "live-model")
            call.assert_called_once()

    def test_no_installed_models_offers_other_and_blank_tag_blocks_only_live_mode(self):
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        self.assertEqual(app.selectbox[1].options, ["Other…"])
        self.assertTrue(any(item.label == "Other local model tag" for item in app.text_input))
        app.radio[0].set_value("Model-selected excerpts (optional)").run()
        with patch("docs_radar.answers.answer") as call:
            app.button[0].click().run()
        call.assert_not_called()
        self.assertTrue(any("enter a local model tag" in item.value for item in app.error))
        app.radio[0].set_value("Extractive").run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Enter a question" in item.value for item in app.info))

    def test_switching_back_from_other_uses_dropdown_not_old_custom_value(self):
        from docs_radar.answers import answer
        result = answer("", "Providers", "2026-11-01")
        self.runtime_start.return_value = RuntimeStatus(model="test:latest")
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py"), default_timeout=15).run()
        app.selectbox[1].select("Other…").run()
        next(item for item in app.text_input if item.label == "Other local model tag").input("custom:latest").run()
        app.selectbox[1].select("test:latest").run()
        self.assertFalse(any(item.label == "Other local model tag" for item in app.text_input))
        app.radio[0].set_value("Model-selected excerpts (optional)").run()
        with patch("docs_radar.answers.answer", return_value=result) as call:
            app.button[0].click().run()
        self.assertEqual(call.call_args.kwargs["model"], "test:latest")


if __name__ == "__main__":
    unittest.main()
