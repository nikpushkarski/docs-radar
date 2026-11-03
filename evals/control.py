"""Isolated missing-approval regression control; NOT the full quality gate."""
import argparse
import json

from docs_radar.answers import answer
from evals.metrics import score_case
from evals.suite import load_suite, prepare_case


def run_control(inject_regression=False):
    case = load_suite()["cases"][0]
    inputs, workspace = prepare_case(case["id"])
    if inject_regression:
        workspace["approvals"] = {}  # In-memory configuration regression only.
    result = answer(**inputs, workspace=workspace)
    score = score_case(case, result, workspace)
    return {"scope": "single-case synthetic missing-approval control, not full-suite acceptance",
            "injected": inject_regression, "case": case["id"],
            "status": result["status"], "checks": score["checks"], "pass": score["automated_pass"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inject-regression", action="store_true")
    args = parser.parse_args()
    result = run_control(args.inject_regression)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["pass"] else 1)
