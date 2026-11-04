"""Read-only quality report inspection shared with UI tests."""
import json
from pathlib import Path

from docs_radar.generation import PROMPT_HASH
from evals.run import code_hash, digest
from evals.provider import fixture_workspace
from evals.suite import DEFAULT_VERSION, suite_root, verify_manifest


def report_freshness(report):
    provenance = report["provenance"]
    version = provenance.get("test_set_version", "v2")
    manifest = verify_manifest(suite_root(version))
    reasons = []
    if version != DEFAULT_VERSION:
        reasons.append(f"Historical suite {version}; the current default is {DEFAULT_VERSION}")
    if provenance.get("code_hash") != code_hash():
        reasons.append("Application/evaluation code differs from this recorded run")
    if provenance.get("test_set_hash") != manifest["bundle_sha256"]:
        reasons.append("Frozen test-set version differs")
    corpus_hashes = sorted({digest(fixture_workspace(name, version)) for name in manifest["fixtures"]})
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
    # A fresh checkout should show the current corpus, not the first old failing baseline.
    return dict(sorted(reports.items(), key=lambda item: (
        item[1]["provenance"].get("test_set_version") == DEFAULT_VERSION,
        item[0] == "reports/local/latest.json", item[1].get("created_at", "")), reverse=True))
