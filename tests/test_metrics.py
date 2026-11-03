from copy import deepcopy
import json
import unittest

from docs_radar.answers import answer
from evals.metrics import citation_metrics, fraction, manual_metrics, recall_at_three, score_case, summarize
from evals.run import compare_baseline, digest, evaluate
from evals.suite import load_suite, prepare_case
from evals.assertions import get_assert


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.case = load_suite()["cases"][0]
        inputs, self.workspace = prepare_case("Q01")
        self.output = answer(**inputs, workspace=self.workspace)

    def test_empty_denominators_are_not_perfect_scores(self):
        self.assertIsNone(fraction(0, 0)["value"])
        self.assertFalse(summarize([])["automated_gate_pass"])
        self.assertIsNone(recall_at_three([], ["x"])["value"])

    def test_recall_counts_distinct_first_three_sources(self):
        score = recall_at_three(["a", "d"], ["a", "a", "b", "c", "d"])
        self.assertEqual(score, {"numerator": 1, "denominator": 2, "value": .5})

    def test_wrong_abstention_keeps_answerable_denominator(self):
        result = deepcopy(self.output)
        result.update(status="abstain", retrieved_source_ids=[], citations=[], claims=[], passages=[])
        row = score_case(self.case, result, self.workspace)
        self.assertEqual(row["recall_at_3"]["value"], 0)
        self.assertFalse(row["automated_pass"])

    def test_forged_url_negative_control(self):
        result = deepcopy(self.output)
        result["citations"][0]["source_url"] = "https://example.invalid/forged-citation"
        row = score_case(self.case, result, self.workspace)
        self.assertFalse(row["citations"]["valid"])
        self.assertEqual(row["citations"]["invalid_citation_indices"], [0])

    def test_stale_version_not_valid(self):
        result = deepcopy(self.output)
        result["citations"][0]["content_version"] = "stale"
        self.assertFalse(score_case(self.case, result, self.workspace)["citations"]["valid"])

    def test_missing_required_citation_fails_even_without_denominator(self):
        result = deepcopy(self.output)
        result["citations"] = []
        row = score_case(self.case, result, self.workspace)
        self.assertTrue(row["citations"]["required_citation_missing"])
        self.assertIsNone(row["citations"]["validity"]["value"])
        self.assertFalse(row["automated_pass"])

    def test_valid_citation_is_not_semantic_support(self):
        result = deepcopy(self.output)
        result["claims"][0]["text"] = "An unsupported factual claim."
        metrics = citation_metrics(result, result["passages"], self.workspace["sources"], True)
        self.assertTrue(metrics["valid"])
        review = manual_metrics(result, {"reviewer": "Synthetic unit test", "reviewed_on": "2000-01-01", "claims": {"0": False}})
        self.assertEqual(review["accuracy"]["value"], 0)
        self.assertIsNone(manual_metrics(result)["accuracy"]["value"])

    def test_manual_review_requires_attribution_and_matching_output(self):
        with self.assertRaises(ValueError):
            manual_metrics(self.output, {"claims": {"0": True}})
        with self.assertRaises(ValueError):
            evaluate(reviews={"Q01": {"output_hash": "stale"}})

    def test_fixed_suite_records_existing_failures_without_relaxation(self):
        report, _ = evaluate()
        self.assertEqual(len(report["cases"]), 12)
        # Runtime fixes improve Q07/Q12; frozen corpus gaps still fail, not waived.
        self.assertEqual(set(report["summary"]["critical_failures"]), {"Q02", "Q05"})
        self.assertFalse(report["summary"]["automated_gate_pass"])
        self.assertIsNone(report["summary"]["manual_citation_accuracy"]["value"])
        self.assertEqual(report["summary"]["manual_review_coverage"]["value"], 0)

    def test_baseline_requires_matching_configuration_and_cases(self):
        report, _ = evaluate()
        same = compare_baseline(report, deepcopy(report))
        self.assertTrue(same["pass"])
        different = deepcopy(report)
        different["provenance"]["mode"] = "replay"
        self.assertFalse(compare_baseline(report, different)["compatible"])

    def test_equivalent_iso_and_prose_dates_are_accepted(self):
        for case_id in ("Q04", "Q06"):
            case = next(c for c in load_suite()["cases"] if c["id"] == case_id)
            inputs, workspace = prepare_case(case_id)
            output = answer(**inputs, workspace=workspace)
            self.assertTrue(score_case(case, output, workspace)["automated_pass"])
            output["answer_text"] = output["answer_text"].replace("2027-01-20", "January 20, 2027")
            self.assertTrue(score_case(case, output, workspace)["automated_pass"])

    def test_promptfoo_assertion_calls_same_metrics(self):
        self.assertTrue(get_assert(json.dumps(self.output), {"vars": {"case_id": "Q01"}})["pass"])
        self.assertFalse(get_assert("{}", {"vars": {"case_id": "Q01"}})["pass"])
