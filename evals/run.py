"""Evaluate the unchanged frozen set; exit 1 on quality failure, 2 on setup error."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

from docs_radar.answers import answer
from evals.metrics import score_case, summarize
from evals.suite import DEFAULT_VERSION, VERSIONS, load_suite, prepare_case, suite_root, verify_manifest

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def code_hash():
    files = {}
    for folder in ("docs_radar", "evals", "scripts"):
        for path in sorted((ROOT / folder).glob("*.py")):
            files[path.relative_to(ROOT).as_posix()] = path.read_text(encoding="utf-8")
    for name in ("scripts/requirements.txt", "scripts/requirements-model.txt",
                 "scripts/constraints-python313.txt", "evals/package.json", "evals/package-lock.json"):
        files[name] = (ROOT / name).read_text(encoding="utf-8")
    return digest(files)


def git_provenance():
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        return {"commit": revision, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def compare_baseline(report, baseline):
    # Code can change for a regression comparison; dataset, corpus and configuration cannot.
    keys = ("test_set_hash", "mode", "corpus_hashes", "prompt_hash", "model_id", "model_digests")
    compatible = all(report["provenance"].get(k) == baseline["provenance"].get(k) for k in keys)
    old_ids = [r["id"] for r in baseline["cases"]]
    compatible = compatible and old_ids == [r["id"] for r in report["cases"]]
    old_failed = set(baseline["summary"]["critical_failures"])
    new_failed = sorted(set(report["summary"]["critical_failures"]) - old_failed)
    return {"compatible": compatible, "new_critical_failures": new_failed if compatible else None,
            "pass": compatible and not new_failed}


def evaluate(mode="extractive", model=None, reviews=None, *, version=DEFAULT_VERSION, inject_regression=False):
    root = suite_root(version)
    suite = load_suite(root)
    manifest = verify_manifest(root)
    rows, outputs = [], {}
    for case in suite["cases"]:
        inputs, workspace = prepare_case(case["id"], root)
        if inject_regression:
            workspace["approvals"] = {}  # In-memory control only; never edit frozen/live approvals.
        started = time.perf_counter()
        output = answer(**inputs, workspace=workspace, mode=mode, model=model)
        elapsed = time.perf_counter() - started
        output_hash = digest(output)
        review = (reviews or {}).get(case["id"])
        if review and review.get("output_hash") != output_hash:
            raise ValueError(f"Stale human review for {case['id']}")
        row = score_case(case, output, workspace, review)
        row.update(output_hash=output_hash, run=output["run"], elapsed_seconds=round(elapsed, 4))
        rows.append(row)
        outputs[case["id"]] = output
    from docs_radar.generation import PROMPT_HASH
    report = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {**git_provenance(), "code_hash": code_hash(),
            "test_set_version": suite["version"], "test_set_hash": manifest["bundle_sha256"],
            "regression_injected": inject_regression,
            "mode": mode, "answer_style": "model_selected_excerpts" if mode == "live-model" else "extractive_excerpts",
            "model_id": model, "prompt_hash": PROMPT_HASH if mode == "live-model" else None,
            "corpus_hashes": sorted({r["run"]["corpus_hash"] for r in rows if r["run"]["corpus_hash"]}),
            "model_digests": sorted({r["run"]["model_digest"] for r in rows if r["run"].get("model_digest")})},
        "summary": summarize(rows),
        "lanes": {lane: summarize([r for r in rows if r["lane"] == lane]) for lane in ("public_evidence", "synthetic_adversarial")},
        "cases": rows,
        "limitations": ["Current live-model output is model-selected excerpts, not generated prose.",
            "Deterministic checks do not establish semantic support or general injection resistance.",
            "Synthetic fixture approvals do not approve the real corpus.",
            "Human review is incomplete unless explicitly recorded against each output hash.",
            "A failing baseline records observed failures; it does not waive thresholds."]}
    if mode == "live-model":
        report["successful_model_responses"] = sum(
            bool(o["run"].get("model_called")) and o["status"] != "error" for o in outputs.values())
        report["live_evidence_complete"] = bool(report["provenance"]["model_digests"]) and all(
            o["status"] != "error" for o in outputs.values())
    return report, outputs


def save_report(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_evaluation(path, report, outputs):
    """Keep raw outputs local and tied to this report, not a mutable global slot."""
    path = Path(path)
    if path.exists() and not path.resolve().is_relative_to((ROOT / "reports/local").resolve()):
        raise ValueError("Recorded reports are immutable; choose a new path")
    artifact = ROOT / "reports/local" / (path.stem + "-outputs.json")
    report["output_artifact"] = artifact.relative_to(ROOT).as_posix()
    save_report(artifact, outputs)
    save_report(path, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("extractive", "live-model"), default="extractive")
    parser.add_argument("--model")
    parser.add_argument("--version", choices=VERSIONS, default=DEFAULT_VERSION)
    parser.add_argument("--inject-regression", action="store_true", help="Isolated in-memory missing-approval control across the full suite")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/local/latest.json")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    if args.mode == "live-model" and not args.model:
        parser.error("--model is required for live-model mode")
    if args.baseline and args.output.resolve() == args.baseline.resolve():
        parser.error("Never overwrite the baseline with a comparison run")
    if args.output.exists() and not args.output.resolve().is_relative_to((ROOT / "reports/local").resolve()):
        parser.error("Recorded reports are immutable; choose a new path or reports/local/")
    try:
        reviews = json.loads(args.reviews.read_text(encoding="utf-8")) if args.reviews else None
        report, outputs = evaluate(args.mode, args.model, reviews, version=args.version, inject_regression=args.inject_regression)
        if args.baseline:
            report["regression"] = compare_baseline(report, json.loads(args.baseline.read_text(encoding="utf-8")))
        save_evaluation(args.output, report, outputs)
        # Legacy convenience copy; review uses the report-specific, hash-checked artifact.
        save_report(ROOT / "reports/local/outputs.json", outputs)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Evaluation blocked: {error}")
        return 2
    print(json.dumps(report["summary"], indent=2))
    print(f"Report: {args.output}")
    passed = report["summary"]["automated_gate_pass"] and report.get("regression", {}).get("pass", True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
