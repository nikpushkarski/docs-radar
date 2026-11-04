"""Local full-suite gate; never provisions packages, models or hosted services."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from evals.run import code_hash, git_provenance, save_report
from evals.suite import DEFAULT_VERSION, VERSIONS

ROOT = Path(__file__).resolve().parents[1]


def run_step(name, arguments):
    process = subprocess.run([sys.executable, *arguments], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8", check=False,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    print(f"{name}: exit {process.returncode}")
    print(process.stdout)
    if process.stderr:
        print(process.stderr, file=sys.stderr)
    return {"name": name, "exit_code": process.returncode,
            "status": "passed" if process.returncode == 0 else "blocked" if process.returncode == 2 else "failed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=VERSIONS, default=DEFAULT_VERSION)
    parser.add_argument("--demonstrate", action="store_true", help="Full gate: clean, in-memory missing approvals, repaired")
    parser.add_argument("--inject-regression", action="store_true", help="Control only; does not alter files or real approvals")
    args = parser.parse_args()
    if args.demonstrate and args.inject_regression:
        parser.error("Choose the demonstration or a single injected run")
    if args.demonstrate:
        steps = []
        for name, extra in (("clean", []), ("injected", ["--inject-regression"]), ("repaired", [])):
            step = run_step(name, ["-m", "scripts.quality_gate", "--version", args.version, *extra])
            step["gate"] = json.loads((ROOT / "reports/local/gate.json").read_text(encoding="utf-8"))
            steps.append(step)
        passed = [s["exit_code"] for s in steps] == [0, 1, 0]
        save_report(ROOT / "reports/local/gate-demonstration.json", {
            "scope": "Full model-free gate, including all 12 cases and actual Promptfoo; in-memory approval regression only",
            "version": args.version, "provenance": {**git_provenance(), "code_hash": code_hash()},
            "steps": steps, "demonstration_pass": passed})
        return 0 if passed else 1
    extra = ["--inject-regression"] if args.inject_regression else []
    steps = [run_step("unit_tests", ["-m", "unittest", "discover", "-s", "tests", "-q"]),
             run_step("frozen_v2_integrity", ["-m", "evals.suite", "--version", "v2"]),
             run_step("selected_frozen_integrity", ["-m", "evals.suite", "--version", args.version]),
             run_step("quality", ["-m", "evals.run", "--version", args.version,
                 "--baseline", f"reports/baseline-extractive-{args.version}.json", *extra]),
             run_step("promptfoo", ["-m", "scripts.run_promptfoo", "--suite", "--version", args.version, *extra])]
    report = {"version": args.version, "regression_injected": args.inject_regression,
        "provenance": {**git_provenance(), "code_hash": code_hash()},
        "steps": steps, "pass": all(s["exit_code"] == 0 for s in steps),
        "live_model": "not_run", "human_review": "not_run", "hosted_ci": "not_run"}
    latest = ROOT / "reports/local/latest.json"
    if latest.exists():
        result = json.loads(latest.read_text(encoding="utf-8"))
        provenance = result["provenance"]
        if (provenance["code_hash"] == code_hash() and provenance["test_set_version"] == args.version
                and provenance.get("regression_injected") == args.inject_regression):
            report["evaluation_summary"] = result["summary"]
            report["regression"] = result.get("regression")
    save_report(ROOT / "reports/local/gate.json", report)
    if any(s["exit_code"] == 2 for s in steps):
        return 2
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
