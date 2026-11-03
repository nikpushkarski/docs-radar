import json
from pathlib import Path
import unittest
from unittest.mock import patch

from evals.provider import call_api
from evals.suite import prepare_case

ROOT = Path(__file__).resolve().parents[1]


class ProviderTests(unittest.TestCase):
    def request(self):
        inputs, _ = prepare_case("Q01")
        return json.dumps({"inputs": inputs, "fixture_id": "public-corpus-v1"})

    def test_calls_real_pipeline_and_ignores_assertion_context(self):
        result = call_api(self.request(), {}, {"expected": "DO NOT FORWARD", "vars": {"gold": "secret"}})
        output = json.loads(result["output"])
        self.assertEqual(output["status"], "answered")
        self.assertTrue(output["citations"])
        self.assertNotIn("DO NOT FORWARD", result["output"])

    def test_answer_receives_runtime_fields_only(self):
        with patch("evals.provider.answer", return_value={}) as function:
            call_api(self.request(), {}, {"expected": "secret"})
        self.assertEqual(set(function.call_args.kwargs), {"question", "audience", "reference_date", "workspace", "mode", "model"})

    def test_extra_fields_rejected(self):
        request = json.loads(self.request())
        request["expected"] = "answered"
        self.assertIn("error", call_api(json.dumps(request), {}, {}))
        del request["expected"]
        request["inputs"]["gold_source_ids"] = []
        self.assertIn("error", call_api(json.dumps(request), {}, {}))

    def test_frozen_fixture_routing_only(self):
        request = json.loads(self.request())
        request["fixture_id"] = "../../data/approvals.json"
        self.assertIn("error", call_api(json.dumps(request), {}, {}))

    def test_smoke_and_negative_provider_outputs_without_promptfoo(self):
        statuses = []
        for name in ("promptfoo-smoke.json", "promptfoo-negative.json"):
            config = json.loads((ROOT / "evals" / name).read_text())
            response = call_api(config["tests"][0]["vars"]["request"], config["providers"][0], {})
            statuses.append(json.loads(response["output"])["status"])
        self.assertEqual(statuses, ["answered", "abstain"])
        # These direct Python calls do not constitute a Promptfoo CLI execution.
