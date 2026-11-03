from copy import deepcopy
import unittest

from docs_radar.passage_selection import select_applicable_passages


class PassageSelectionTest(unittest.TestCase):
    def setUp(self):
        # Routing fixtures only, not approved answer content or live evidence.
        self.passages = [
            {
                "id": "recommended-transfer",
                "audience": "Providers",
                "valid_from": "2026-11-01",
                "valid_until": "2026-12-04",
            },
            {
                "id": "transfer-before-closure",
                "audience": "Providers",
                "valid_from": "2026-12-04",
                "valid_until": "2027-01-20",
            },
            {
                "id": "closure-warning",
                "audience": "Providers",
                "valid_from": "2027-01-20",
                "valid_until": None,
            },
            {
                "id": "ordering-guidance",
                "audience": "Providers",
                "valid_from": "2026-11-01",
                "valid_until": "2027-01-20",
            },
            {
                "id": "patient-only",
                "audience": "Patients",
                "valid_from": "2026-11-01",
                "valid_until": "2027-01-20",
            },
        ]

    def selected_ids(self, reference_date, audience="Providers"):
        return {
            passage["id"] for passage in select_applicable_passages(
                self.passages, audience, reference_date
            )
        }

    def test_date_boundaries_select_guidance_without_a_gap(self):
        cases = {
            "2026-11-01": {"recommended-transfer", "ordering-guidance"},
            "2026-12-03": {"recommended-transfer", "ordering-guidance"},
            "2026-12-04": {"transfer-before-closure", "ordering-guidance"},
            "2027-01-19": {"transfer-before-closure", "ordering-guidance"},
            "2027-01-20": {"closure-warning"},
            "2027-01-21": {"closure-warning"},
        }
        for reference_date, expected in cases.items():
            with self.subTest(reference_date=reference_date):
                self.assertEqual(self.selected_ids(reference_date), expected)

    def test_snapshot_does_not_establish_earlier_history(self):
        self.assertEqual(self.selected_ids("2026-10-31"), set())

    def test_audiences_are_not_mixed(self):
        self.assertEqual(
            self.selected_ids("2026-11-01", "Patients"), {"patient-only"}
        )

    def test_unknown_audience_is_not_universal(self):
        with self.assertRaisesRegex(ValueError, "Audience must"):
            self.selected_ids("2026-11-01", "unknown")
        self.passages[0]["audience"] = "unknown"
        with self.assertRaisesRegex(ValueError, "known audience"):
            self.selected_ids("2026-11-01")

    def test_missing_bounds_are_rejected(self):
        for field in ("valid_from", "valid_until"):
            with self.subTest(field=field):
                passage = dict(self.passages[0])
                del passage[field]
                with self.assertRaisesRegex(ValueError, "explicit validity bounds"):
                    select_applicable_passages([passage], "Providers", "2026-11-01")

    def test_invalid_dates_are_rejected(self):
        for value in (None, "tomorrow", "20261101", "2026-02-30"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.selected_ids(value)
        self.passages[0]["valid_from"] = "invalid"
        with self.assertRaises(ValueError):
            self.selected_ids("2026-11-01")

    def test_empty_and_reversed_intervals_are_rejected(self):
        for end in ("2026-11-01", "2026-10-31"):
            with self.subTest(end=end):
                self.passages[0]["valid_until"] = end
                with self.assertRaisesRegex(ValueError, "later than valid_from"):
                    self.selected_ids("2026-11-01")

    def test_selection_does_not_modify_passages(self):
        original = deepcopy(self.passages)
        self.selected_ids("2026-12-04")
        self.assertEqual(self.passages, original)


if __name__ == "__main__":
    unittest.main()
