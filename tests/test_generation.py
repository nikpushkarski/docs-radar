import json
import unittest
from unittest.mock import patch

from docs_radar.answers import answer
from docs_radar.generation import BASE_URL, parse_output, model_digest
from evals.suite import prepare_case


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.inputs, self.workspace = prepare_case("Q01")
        self.base = answer(**self.inputs, workspace=self.workspace)
        self.claim = self.base["claims"][0]

    def ask(self):
        return answer(**self.inputs, workspace=self.workspace, mode="live-model", model="local:test")

    def test_optional_adapter_contract_not_live_execution(self):
        output = json.dumps({"status": "answered", "claims": [self.claim]})
        with patch("docs_radar.generation.invoke_local", return_value=(output, "a" * 64)) as invoke:
            result = self.ask()
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"][0], self.base["citations"][0])
        payload = invoke.call_args.args[0]
        self.assertEqual(set(payload), {"question", "audience", "reference_date", "untrusted_evidence"})
        self.assertNotIn("expected", json.dumps(payload))
        self.assertEqual(result["run"]["model_digest"], "a" * 64)

    def test_unavailable_is_error_not_extractive_fallback(self):
        with patch("docs_radar.generation.invoke_local", side_effect=ImportError):
            result = self.ask()
        self.assertEqual(result["reason"], "model_unavailable")
        self.assertFalse(result["run"]["model_called"])
        self.assertEqual(result["claims"], [])

    def test_malformed_output_is_explicit_error(self):
        with patch("docs_radar.generation.invoke_local", return_value=("not json", "a" * 64)):
            result = self.ask()
        self.assertEqual(result["reason"], "malformed_model_output")
        self.assertEqual(result["citations"], [])

    def test_no_evidence_never_calls_model(self):
        self.workspace["approvals"] = {}
        with patch("docs_radar.generation.invoke_local") as invoke:
            self.assertEqual(self.ask()["status"], "abstain")
        invoke.assert_not_called()

    def test_parser_rejects_missing_claims_forged_ids_and_urls(self):
        for value in [
            {"status": "answered", "claims": []},
            {"status": "abstain", "claims": [self.claim]},
            {"status": "answered", "claims": [{"text": "invented", "supporting_evidence_ids": ["fake"]}]},
            {"status": "answered", "claims": [{**self.claim, "text": "https://example.invalid/forged"}]},
            {"status": "answered", "claims": [{**self.claim, "supporting_evidence_ids": []}]},
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_output(json.dumps(value), self.base["citations"])

    def test_cloud_models_rejected_before_network(self):
        self.assertEqual(BASE_URL, "http://127.0.0.1:11435")
        with patch("urllib.request.build_opener") as opener:
            with self.assertRaises(ValueError):
                model_digest("model:cloud")
        opener.assert_not_called()

    def test_replay_cannot_be_mislabeled_as_live_call(self):
        with self.assertRaises(ValueError):
            answer(**self.inputs, mode="replay")
