from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalSettingsTests(unittest.TestCase):
    def test_streamlit_defaults_to_loopback_and_no_usage_telemetry(self):
        settings = tomllib.loads((ROOT / ".streamlit/config.toml").read_text(encoding="utf-8"))
        self.assertEqual(settings["server"]["address"], "127.0.0.1")
        self.assertIs(settings["browser"]["gatherUsageStats"], False)
