import json
from pathlib import Path
import unittest

from docs_radar.validate_source import validate_source


ROOT = Path(__file__).resolve().parents[1]


class SourceValidationTest(unittest.TestCase):
    def setUp(self):
        sources = json.loads(
            (ROOT / "data/sources.json").read_text(encoding="utf-8")
        )
        self.source = sources[0]

    def test_valid_source_passes(self):
        validate_source(self.source)

    def test_invalid_review_state_is_rejected(self):
        # Deliberately invalid local test data, not a public-source change.
        sources = json.loads(
            (ROOT / "tests/fixtures/invalid_sources.json").read_text(
                encoding="utf-8"
            )
        )
        with self.assertRaisesRegex(ValueError, "Invalid review_state: 'published'"):
            validate_source(sources[0])

    def test_missing_provenance_is_rejected(self):
        for field in (
            "id", "url", "retrieved_on", "evidence_type", "summary_sha256"
        ):
            with self.subTest(field=field):
                source = self.source.copy()
                del source[field]
                with self.assertRaisesRegex(
                    ValueError, f"Missing or empty provenance field: {field}"
                ):
                    validate_source(source)


if __name__ == "__main__":
    unittest.main()
