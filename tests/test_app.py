from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class AppSmokeTest(unittest.TestCase):
    def test_page_loads(self):
        app = AppTest.from_file(str(ROOT / "docs_radar/app.py")).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.title[0].value, "Docs Radar")
        self.assertIn("Independent demo", app.caption[0].value)


if __name__ == "__main__":
    unittest.main()
