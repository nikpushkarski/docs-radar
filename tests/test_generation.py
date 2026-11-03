import io
import json
import unittest
from unittest.mock import patch

from docs_radar.answers import answer
from docs_radar.generation import (
    BASE_URL, RESPONSE_SCHEMA, SETTINGS, evidence_groups, model_digest, parse_output,
)
from docs_radar.model_policy import MAX_PROMPT_BYTES, ModelBudgetError
from evals.suite import prepare_case


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.inputs, self.workspace = prepare_case("Q01")
        self.base = answer(**self.inputs, workspace=self.workspace)

    def ask(self, **overrides):
        return answer(**{**self.inputs, **overrides}, workspace=self.workspace,
                      mode="live-model", model="local:test")

    def test_optional_adapter_contract_not_live_execution(self):
        output = json.dumps({"status": "answered", "source_indices": [0]})
        with patch("docs_radar.generation.invoke_local", return_value=(output, "a" * 64)) as invoke:
            result = self.ask()
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"], self.base["citations"])
        self.assertEqual(result["claims"], self.base["claims"])
        payload = invoke.call_args.args[0]
        self.assertEqual(set(payload), {"question", "audience", "reference_date", "untrusted_evidence"})
        self.assertNotIn("expected", json.dumps(payload))
        self.assertEqual(result["run"]["model_digest"], "a" * 64)
        self.assertEqual(result["run"]["answer_style"], "model_selected_excerpts")
        self.assertEqual(result["run"]["selection_attempts"], 1)
        self.assertIn("not generated prose", result["answer_text"])
        invoke.assert_called_once()

    def test_unavailable_is_error_not_extractive_fallback(self):
        with patch("docs_radar.generation.invoke_local", side_effect=ImportError) as invoke:
            result = self.ask()
        self.assertEqual(result["reason"], "model_unavailable")
        self.assertFalse(result["run"]["model_called"])
        self.assertEqual(result["claims"], [])
        invoke.assert_called_once()

    def test_malformed_output_is_explicit_error_without_retry(self):
        with patch("docs_radar.generation.invoke_local", return_value=("not json", "a" * 64)) as invoke:
            result = self.ask()
        self.assertEqual(result["reason"], "malformed_model_output")
        self.assertEqual(result["citations"], [])
        invoke.assert_called_once()

    def test_abstention_does_not_render_an_answer(self):
        with patch("docs_radar.generation.invoke_local", return_value=(json.dumps({
                "status": "abstain", "source_indices": []}), "a" * 64)):
            result = self.ask()
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["claims"], [])
        self.assertEqual(result["citations"], [])

    def test_no_evidence_never_calls_model(self):
        self.workspace["approvals"] = {}
        with patch("docs_radar.generation.invoke_local") as invoke:
            self.assertEqual(self.ask()["status"], "abstain")
        invoke.assert_not_called()

    def test_parser_rejects_forged_prose_ids_urls_and_invalid_indices(self):
        for value in [
            {"status": "answered", "source_indices": []},
            {"status": "abstain", "source_indices": [0]},
            {"status": "answered", "source_indices": [1]},
            {"status": "answered", "source_indices": [-1]},
            {"status": "answered", "source_indices": [True]},
            {"status": "answered", "source_indices": [0.0]},
            {"status": "answered", "source_indices": ["https://example.invalid/forged"]},
            {"status": "answered", "source_indices": [0, 0]},
            {"status": "answered", "source_indices": [0], "text": "invented guidance"},
            {"status": "answered", "claims": self.base["claims"]},
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_output(json.dumps(value), ["registered-source"])

    def test_schema_only_allows_bounded_selection_without_gold(self):
        self.assertEqual(set(RESPONSE_SCHEMA["properties"]), {"status", "source_indices"})
        self.assertFalse(RESPONSE_SCHEMA["additionalProperties"])
        self.assertEqual(RESPONSE_SCHEMA["properties"]["source_indices"]["maxItems"], 3)
        self.assertEqual(SETTINGS["num_ctx"], 2048)
        self.assertEqual(SETTINGS["num_predict"], 64)
        self.assertEqual(SETTINGS["keep_alive"], 0)
        self.assertEqual(SETTINGS["num_thread"], 2)
        self.assertFalse(SETTINGS["reasoning"])
        self.assertNotIn("Fullscript", json.dumps(RESPONSE_SCHEMA))

    def test_large_context_is_rejected_not_silently_truncated(self):
        with patch("docs_radar.generation.invoke_local") as invoke:
            result = self.ask(question=self.inputs["question"] + " x" * MAX_PROMPT_BYTES)
        self.assertEqual(result["reason"], "model_context_limit")
        self.assertEqual(result["run"]["selection_attempts"], 0)
        self.assertEqual(result["claims"], [])
        invoke.assert_not_called()

    def test_resource_failure_is_explicit_without_fallback(self):
        with patch("docs_radar.generation.invoke_local", side_effect=ModelBudgetError("too large")) as invoke:
            result = self.ask()
        self.assertEqual(result["reason"], "model_resource_limit")
        self.assertEqual(result["claims"], [])
        self.assertFalse(result["run"]["model_called"])
        invoke.assert_called_once()

    def test_cloud_models_rejected_before_network(self):
        self.assertEqual(BASE_URL, "http://127.0.0.1:11435")
        with patch("urllib.request.build_opener") as opener:
            with self.assertRaises(ValueError):
                model_digest("model:cloud")
        opener.assert_not_called()

    def test_large_installed_model_rejected_before_hardware_probe_or_inference(self):
        tags = {"models": [{"name": "qwen3:8b", "digest": "a" * 64,
                           "size": 5_225_389_023, "details": {"parameter_size": "8.2B"}}]}
        with patch("urllib.request.build_opener") as opener, patch("scripts.setup_support.detect_hardware") as probe:
            opener.return_value.open.return_value = io.BytesIO(json.dumps(tags).encode())
            with self.assertRaises(ModelBudgetError):
                model_digest("qwen3:8b")
        probe.assert_not_called()

    def test_replay_cannot_be_mislabeled_as_live_call(self):
        with self.assertRaises(ValueError):
            answer(**self.inputs, mode="replay")
