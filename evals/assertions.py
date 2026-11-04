"""Promptfoo assertion entry point. Gold data is read here, never by answer()."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.metrics import score_case
from evals.provider import fixture_workspace
from evals.suite import load_suite, suite_root


def get_assert(output, context):
    try:
        case_id = context["vars"]["case_id"]
        version = context["vars"].get("suite_version", "v2")
        case = next(c for c in load_suite(suite_root(version))["cases"] if c["id"] == case_id)
        result = json.loads(output) if isinstance(output, str) else output
        row = score_case(case, result, fixture_workspace(case["fixture_id"], version))
        failed = [name for name, passed in row["checks"].items() if not passed]
        return {"pass": row["automated_pass"], "score": 1 if row["automated_pass"] else 0,
                "reason": ", ".join(failed) if failed else "Deterministic checks passed; human support review remains separate."}
    except (ValueError, KeyError, TypeError, StopIteration) as error:
        return {"pass": False, "score": 0, "reason": f"Invalid evaluation output: {error}"}
