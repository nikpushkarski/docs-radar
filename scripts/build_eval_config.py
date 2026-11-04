"""Generate Promptfoo routing from frozen runtime inputs, not expected answers."""
import argparse
import json
from pathlib import Path

from evals.suite import DEFAULT_VERSION, VERSIONS, load_suite, suite_root

ROOT = Path(__file__).resolve().parents[1]


def build_config(version=DEFAULT_VERSION, inject_regression=False):
    return {"description": f"Frozen {version} 12-case extractive checks; deterministic checks are not human review",
        "prompts": ["{{request}}"],
        "providers": [{"id": "file://provider.py", "config": {"mode": "extractive",
            "suite_version": version, "inject_missing_approval": inject_regression}}],
        "tests": [{"description": case["id"],
            "vars": {"case_id": case["id"], "suite_version": version,
                "request": json.dumps({"inputs": case["inputs"], "fixture_id": case["fixture_id"]})},
            "assert": [{"type": "python", "value": "file://assertions.py"}]}
            for case in load_suite(suite_root(version))["cases"]]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=VERSIONS, default=DEFAULT_VERSION)
    version = parser.parse_args().version
    target = ROOT / f"evals/promptfooconfig-{version}.json"
    target.write_text(json.dumps(build_config(version), indent=2) + "\n", encoding="utf-8")
