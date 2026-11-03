import unittest

from evals.control import run_control
from scripts.build_eval_config import build_config
from evals.suite import load_suite, verify_manifest


class GateTests(unittest.TestCase):
    def test_regression_control_recovers_without_editing_frozen_data(self):
        before = verify_manifest()["bundle_sha256"]
        self.assertTrue(run_control()["pass"])
        self.assertFalse(run_control(True)["pass"])
        self.assertTrue(run_control()["pass"])
        self.assertEqual(verify_manifest()["bundle_sha256"], before)

    def test_promptfoo_routes_all_frozen_cases_without_gold_in_request(self):
        import json
        config = build_config()
        self.assertEqual(len(config["tests"]), 12)
        for test, case in zip(config["tests"], load_suite()["cases"]):
            request = json.loads(test["vars"]["request"])
            self.assertEqual(set(request), {"inputs", "fixture_id"})
            self.assertEqual(request["inputs"], case["inputs"])
            self.assertEqual(test["vars"]["case_id"], case["id"])
