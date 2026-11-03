"""Read-only quality report inspection shared with UI tests."""
import json
from pathlib import Path

from docs_radar.generation import PROMPT_HASH
from evals.run import code_hash, digest
from evals.provider import fixture_workspace
from evals.suite import verify_manifest


def report_freshness(report):
    provenance = report["provenance"]
    manifest = verify_manifest()
    reasons = []
    if provenance.get("code_hash") != code_hash():
        reasons.append("Application/evaluation code differs from this recorded run")
    if provenance.get("test_set_hash") != manifest["bundle_sha256"]:
        reasons.append("Frozen test-set version differs")
    corpus_hashes = sorted({digest(fixture_workspace(name)) for name in manifest["fixtures"]})
    if provenance.get("corpus_hashes") != corpus_hashes:
        reasons.append("Evaluation fixture corpus differs")
    if provenance.get("mode") == "live-model":
        if provenance.get("prompt_hash") != PROMPT_HASH:
            reasons.append("Model prompt/settings differ")
        if not report.get("live_evidence_complete"):
            reasons.append("No complete live-model evidence")
        reasons.append("Current installed model digest has not been verified by this read-only view")
    return reasons


def available_reports(root):
    root = Path(root)
    candidates = [root / "reports/local/latest.json", *sorted((root / "reports").glob("*.json"))]
    reports = {}
    for path in candidates:
        if not path.is_file():
            continue
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            if all(key in report for key in ("provenance", "summary", "cases")):
                reports[path.relative_to(root).as_posix()] = report
        except (OSError, ValueError, TypeError):
            continue
    return reports
