"""Promptfoo Python provider: runtime inputs only, no expected answers."""
import json
from pathlib import Path
import sys

# Promptfoo loads providers by file path in a worker, not as a package module.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docs_radar.answers import answer
from evals.suite import checked_path, materialize_fixture, suite_root, validate_inputs, verify_manifest


def fixture_workspace(fixture_id, version="v2"):
    root = suite_root(version)
    manifest = verify_manifest(root)
    relative = manifest["fixtures"].get(fixture_id)
    if relative is None:
        raise ValueError("Unknown frozen fixture")
    fixture = json.loads(checked_path(root, relative).read_text(encoding="utf-8"))
    if fixture["id"] != fixture_id:
        raise ValueError("Fixture identifier mismatch")
    return materialize_fixture(fixture)


def call_api(prompt, options, context):
    """Ignore assertion context. Prompt contains ordinary inputs and fixture routing only."""
    try:
        request = json.loads(prompt)
        if not isinstance(request, dict) or set(request) != {"inputs", "fixture_id"}:
            raise ValueError("Provider request requires only inputs and fixture_id")
        validate_inputs(request["inputs"])
        config = options.get("config", {})
        workspace = fixture_workspace(request["fixture_id"], config.get("suite_version", "v2"))
        if config.get("inject_missing_approval"):
            workspace["approvals"] = {}  # Same isolated regression control as evals.run.
        output = answer(**request["inputs"], workspace=workspace,
                        mode=config.get("mode", "extractive"), model=config.get("model"))
        return {"output": json.dumps(output, ensure_ascii=False)}
    except (OSError, KeyError, TypeError, ValueError) as error:
        return {"error": f"Evaluation provider error: {error}"}
