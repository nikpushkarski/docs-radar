"""Generate Promptfoo routing from frozen runtime inputs, not expected answers."""
import json
from pathlib import Path

from evals.suite import load_suite

ROOT = Path(__file__).resolve().parents[1]


def build_config():
    return {"description": "Frozen 12-case extractive checks; deterministic checks are not human review",
        "prompts": ["{{request}}"],
        "providers": [{"id": "file://provider.py", "config": {"mode": "extractive"}}],
        "tests": [{"description": case["id"],
            "vars": {"case_id": case["id"], "request": json.dumps({"inputs": case["inputs"], "fixture_id": case["fixture_id"]})},
            "assert": [{"type": "python", "value": "file://assertions.py"}]}
            for case in load_suite()["cases"]]}


if __name__ == "__main__":
    (ROOT / "evals/promptfooconfig.json").write_text(json.dumps(build_config(), indent=2) + "\n", encoding="utf-8")
