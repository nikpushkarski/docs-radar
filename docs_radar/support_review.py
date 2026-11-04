"""Human review export for exact recorded outputs; never infer review decisions."""
import json
from pathlib import Path

from docs_radar.passage_selection import parse_date
from evals.metrics import manual_metrics
from evals.run import digest


def validate_outputs(report, outputs):
    expected = {row["id"]:row["output_hash"] for row in report["cases"]}
    if set(outputs) != set(expected) or any(digest(outputs[key]) != value for key, value in expected.items()):
        raise ValueError("Recorded outputs do not match this report's hashes; no review can be attached.")


def load_review_outputs(root, report):
    root = Path(root).resolve()
    relative = report.get("output_artifact")
    if not relative:
        raise ValueError("This historical report has no review artifact. Run a new evaluation to create one.")
    path = (root / relative).resolve()
    if not path.is_relative_to(root / "reports/local") or path.suffix != ".json":
        raise ValueError("Review artifacts must stay in reports/local/.")
    outputs = json.loads(path.read_text(encoding="utf-8"))
    validate_outputs(report, outputs)
    return outputs


def build_review(report, outputs, decisions, reviewer, reviewed_on, confirmed=False):
    if not confirmed or not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("Enter your reviewer name and explicitly confirm your own support review.")
    parse_date(reviewed_on)
    validate_outputs(report, outputs)
    if not isinstance(decisions, dict) or not set(decisions) <= set(outputs):
        raise ValueError("Review decisions must refer to cases in this report.")
    records = {}
    for row in report["cases"]:
        claims = decisions.get(row["id"], {})
        if not claims:
            continue
        record = {"output_hash":row["output_hash"], "reviewer":reviewer.strip(),
                  "reviewed_on":reviewed_on, "claims":claims}
        manual_metrics(outputs[row["id"]], record)  # Reject invented indices and non-Boolean decisions.
        records[row["id"]] = record
    if not records:
        raise ValueError("Review at least one cited claim; Unreviewed is not approval.")
    return records
