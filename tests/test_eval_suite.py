from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from answers import answer
from approvals import approval_status
from evals.suite import (
    ROOT, checked_path, load_suite, materialize_fixture, prepare_case,
    run_case, validate_inputs, verify_manifest,
)
from passage_selection import select_applicable_passages
from retrieval import retrieve
from topic_passages import build_topic_passages


class FrozenEvaluationSuiteTest(unittest.TestCase):
    def setUp(self):
        self.suite = load_suite()
        self.cases = {case["id"]: case for case in self.suite["cases"]}
        self.manifest = verify_manifest()

    def fixture(self, fixture_id):
        path = ROOT / self.manifest["fixtures"][fixture_id]
        return json.loads(path.read_text(encoding="utf-8"))

    def copied_bundle(self, directory):
        root = Path(directory)
        for relative in (*self.manifest["files"], "manifest.json"):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        return root

    def test_exactly_twelve_accepted_cases_and_unchanged_statuses(self):
        self.assertEqual(self.suite["version"], "v2")
        self.assertEqual(self.suite["state"], "frozen")
        self.assertEqual(self.suite["accepted_by"], "Nik")
        self.assertEqual(len(self.cases), 12)
        self.assertEqual(
            [case["expected"]["status"] for case in self.cases.values()],
            ["answered", "answered", "abstain", "answered", "answered", "answered",
             "abstain", "clarify", "abstain", "abstain", "answered", "answered"],
        )
        self.assertTrue(all(case["criticality"] == "critical" for case in self.cases.values()))
        self.assertIsNone(self.cases["Q08"]["inputs"]["audience"])
        self.assertEqual(sum(case["expected"]["source_recall_applicable"] for case in self.cases.values()), 7)

    def test_json_preserves_every_reviewed_case_and_global_rule(self):
        text = (ROOT / "cases.md").read_text(encoding="utf-8")
        parts = re.split(r"^## (Q\d+) — ([^\n]+)\n", text, flags=re.M)
        rules = parts[0][parts[0].index("## Execution boundaries"):].strip()
        self.assertEqual(self.suite["acceptance_rules_markdown"], rules)
        for index in range(1, len(parts), 3):
            case_id, title, block = parts[index:index + 3]
            with self.subTest(case=case_id):
                case = self.cases[case_id]
                self.assertEqual(case["title"], title)
                self.assertEqual(case["reviewed_specification"], block.strip())
                for name, field in (("Question", "question"), ("Reference date", "reference_date")):
                    value = re.search(r"^" + name + r": (.+)$", block, re.M).group(1)
                    self.assertEqual(case["inputs"][field], value)
                source = re.search(r"^Source ID: (.+)$", block, re.M)
                gold = [] if source is None or source.group(1).startswith("None") else [source.group(1)]
                self.assertEqual(case["expected"]["gold_source_ids"], gold)

    def test_boundary_pairs_change_only_date_and_reuse_identical_evidence(self):
        for first, second in (("Q04", "Q05"), ("Q06", "Q07")):
            with self.subTest(pair=(first, second)):
                inputs_a, workspace_a = prepare_case(first)
                inputs_b, workspace_b = prepare_case(second)
                self.assertNotEqual(inputs_a.pop("reference_date"), inputs_b.pop("reference_date"))
                self.assertEqual(inputs_a, inputs_b)
                self.assertEqual(workspace_a, workspace_b)

    def test_missing_patient_content_is_not_fabricated_by_fixture(self):
        _, workspace = prepare_case("Q02")
        passages = [
            passage for topic_id, text in workspace["topics"].items()
            for passage in build_topic_passages(topic_id, text, workspace["facts"], workspace["sources"])
        ]
        self.assertEqual(select_applicable_passages(passages, "Patients", "2026-11-01"), [])
        self.assertEqual(self.cases["Q02"]["expected"]["status"], "answered")
        self.assertTrue(self.cases["Q02"]["expected"]["source_recall_applicable"])

    def test_draft_fixture_has_valid_evidence_but_is_not_approved(self):
        _, workspace = prepare_case("Q09")
        topic_id, text = next(iter(workspace["topics"].items()))
        self.assertEqual(
            approval_status(topic_id, text, workspace["facts"], workspace["approvals"]),
            "not_approved",
        )
        passages = build_topic_passages(topic_id, text, workspace["facts"], workspace["sources"])
        self.assertEqual(len(select_applicable_passages(passages, "Providers", "2026-11-01")), 1)
        self.assertEqual(workspace["approvals"][topic_id]["state"], "draft")

    def test_conflict_fixture_preserves_existing_synthetic_body_text(self):
        original = json.loads(
            (ROOT.parent / "tests/fixtures/conflicting_passages.json").read_text(encoding="utf-8")
        )
        _, workspace = prepare_case("Q10")
        actual = {
            topic_id: build_topic_passages(topic_id, text, [], workspace["sources"])[0]
            for topic_id, text in workspace["topics"].items()
        }
        for record in original["passages"]:
            passage = actual[record["topic_id"]]
            self.assertEqual(passage["body"], record["body"])
            self.assertEqual(passage["unresolved_conflict_ids"], record["unresolved_conflict_ids"])

    def test_attack_fixtures_reach_real_retrieval_without_precleaning(self):
        # Exposure checks are NOT claims that the adversarial cases pass.
        for case_id in ("Q11", "Q12"):
            with self.subTest(case=case_id):
                observed = []
                def observe(*args, **kwargs):
                    result = retrieve(*args, **kwargs)
                    observed.append(deepcopy(result))
                    return result  # The real result, not a manufactured answer.
                with patch("answers.retrieve", side_effect=observe):
                    output = run_case(case_id)
                self.assertEqual(len(observed), 1)
                self.assertEqual(observed[0]["status"], "retrieved")
                body = "\n".join(passage["body"] for passage in observed[0]["passages"])
                for marker in self.cases[case_id]["expected"]["required_retrieval_markers"]:
                    self.assertIn(marker, body)
                self.assertEqual(output["run"]["mode"], "extractive")

    def test_only_runtime_inputs_and_workspace_reach_answer_function(self):
        with patch("evals.suite.answer", wraps=answer) as called:
            run_case("Q01")
        self.assertEqual(called.call_args.args, ())
        kwargs = called.call_args.kwargs
        self.assertEqual(set(kwargs), {"question", "audience", "reference_date", "workspace"})
        self.assertEqual(set(kwargs["workspace"]), {"topics", "facts", "sources", "approvals"})
        for forbidden in ("gold_source_ids", "reviewed_specification", "required_retrieval_markers"):
            self.assertNotIn(forbidden, json.dumps(kwargs))

    def test_extra_gold_input_is_rejected(self):
        inputs = dict(self.cases["Q01"]["inputs"], expected_answer="do not leak")
        with self.assertRaisesRegex(ValueError, "only question"):
            validate_inputs(inputs)

    def test_fixture_mutation_does_not_leak_and_live_approvals_are_untouched(self):
        live_path = ROOT.parent / "data/approvals.json"
        before = live_path.read_bytes()
        _, first = prepare_case("Q01")
        first["topics"].clear()
        first["approvals"].clear()
        with patch("answers.load_workspace", side_effect=AssertionError("Do not load live corpus")):
            run_case("Q03")
        _, second = prepare_case("Q01")
        self.assertTrue(second["topics"])
        self.assertTrue(second["approvals"])
        self.assertEqual(live_path.read_bytes(), before)

    def test_changed_frozen_file_is_rejected(self):
        for relative in ("cases.json", "fixtures/injected-instruction-v1.json"):
            with self.subTest(file=relative), tempfile.TemporaryDirectory() as temporary:
                root = self.copied_bundle(temporary)
                path = root / relative
                path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Frozen evaluation file changed"):
                    load_suite(root)

    def test_crlf_conversion_does_not_invalidate_frozen_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copied_bundle(temporary)
            path = root / "cases.md"
            path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
            self.assertEqual(load_suite(root)["version"], "v2")

    def test_stale_source_or_topic_approval_is_rejected(self):
        original = self.fixture("public-corpus-v1")
        bad_source = deepcopy(original)
        bad_source["workspace"]["sources"][0]["summary"] += " changed"
        with self.assertRaisesRegex(ValueError, "source hash mismatch"):
            materialize_fixture(bad_source)
        bad_approval = deepcopy(original)
        bad_approval["approval_setup"][0]["fingerprint"] = "wrong"
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            materialize_fixture(bad_approval)

    def test_fixture_cannot_impersonate_real_reviewer(self):
        fixture = self.fixture("public-corpus-v1")
        fixture["approval_setup"][0]["reviewer"] = "Nik"
        with self.assertRaisesRegex(ValueError, "real reviewer"):
            materialize_fixture(fixture)

    def test_unknown_case_and_external_path_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown evaluation case"):
            prepare_case("Q13")
        with self.assertRaisesRegex(ValueError, "inside the suite directory"):
            checked_path(ROOT, "../data/sources.json")
