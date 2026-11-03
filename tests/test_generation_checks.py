"""Selection preserves whole excerpts; it is not free-text entailment checking."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from docs_radar.answers import answer
from docs_radar.generation import evidence_groups, model_selected_answer
from evals.suite import prepare_case


class SourceFidelityTests(unittest.TestCase):
    def test_selected_source_retains_conditions_dates_recommendation_and_rationale(self):
        inputs, workspace = prepare_case("Q01")
        base = answer(**inputs, workspace=workspace)
        base = deepcopy(base)
        # Independent wording: the renderer must not special-case the frozen answers.
        passage = base["passages"][0]
        text = ("The portal is read-only from March 2, 2030. If you have outstanding orders, "
                "we recommend exporting before that date to avoid disruption.")
        passage["body"] = text
        base["claims"][0]["text"] = text
        raw = json.dumps({"status": "answered", "source_indices": [0]})
        with patch("docs_radar.generation.invoke_local", return_value=(raw, "a" * 64)) as invoke:
            result = model_selected_answer(base, inputs["question"], inputs["audience"], "local:test")
        self.assertEqual(result["claims"], base["claims"])
        self.assertEqual(result["claims"][0]["text"], text)
        self.assertEqual(result["citations"], base["citations"])
        invoke.assert_called_once()

    def test_related_passages_travel_together_but_unselected_sources_do_not(self):
        inputs, workspace = prepare_case("Q04")
        base = deepcopy(answer(**inputs, workspace=workspace))
        additional = {**base["passages"][0], "id": "another-passage", "source_id": "another-source",
                      "body": "Unrelated context."}
        base["passages"].append(additional)
        base["retrieved_source_ids"].append("another-source")
        base["citations"].append({**base["citations"][0], "evidence_id": "another-passage", "source_id": "another-source"})
        base["claims"].append({"text": additional["body"], "supporting_evidence_ids": [additional["id"]]})
        source_ids, groups = evidence_groups(base)
        self.assertEqual(len(groups), 2)
        self.assertGreater(len(groups[0]["passages"]), 1)
        raw = json.dumps({"status": "answered", "source_indices": [0]})
        with patch("docs_radar.generation.invoke_local", return_value=(raw, "a" * 64)):
            result = model_selected_answer(base, inputs["question"], inputs["audience"], "local:test")
        self.assertEqual(result["claims"], base["claims"][:-1])
        self.assertNotIn("another-source", {c["source_id"] for c in result["citations"]})
        self.assertEqual(result["passages"], base["passages"])  # Preserve the full retrieval trace.

    def test_instruction_reaches_model_but_cannot_become_generated_guidance(self):
        inputs, workspace = prepare_case("Q12")
        raw = json.dumps({"status": "answered", "source_indices": [0]})
        with patch("docs_radar.generation.invoke_local", return_value=(raw, "a" * 64)) as invoke:
            result = answer(**inputs, workspace=workspace, mode="live-model", model="local:test")
        self.assertIn("INJECTION_EXECUTED", json.dumps(invoke.call_args.args[0]))
        self.assertNotIn("INJECTION_EXECUTED", result["answer_text"])
        self.assertIn("Demo Portal I", result["answer_text"])
        self.assertIn("INJECTION_EXECUTED", json.dumps(result["passages"]))
