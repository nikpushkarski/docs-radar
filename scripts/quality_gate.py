"""Local gate; does not provision packages, cloud CI or hosted model services."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from evals.run import code_hash, git_provenance, save_report

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
    parser.add_argument("--demonstrate", action="store_true", help="Separate control: clean, injected failure, repaired")
    args = parser.parse_args()
    if args.demonstrate:
        steps = [run_step("clean", ["-m", "evals.control"]),
                 run_step("injected", ["-m", "evals.control", "--inject-regression"]),
                 run_step("repaired", ["-m", "evals.control"])]
        passed = [s["exit_code"] for s in steps] == [0, 1, 0]
        report = {"scope": "Isolated Q01 configuration control; not a full-suite pass",
                  "provenance": {**git_provenance(), "code_hash": code_hash()},
                  "steps": steps, "demonstration_pass": passed}
        save_report(ROOT / "reports/local/gate-demonstration.json", report)
        return 0 if passed else 1
    steps = [run_step("unit_tests", ["-m", "unittest", "discover", "-s", "tests", "-q"]),
             run_step("frozen_integrity", ["-m", "evals.suite"]),
             run_step("quality", ["-m", "evals.run", "--baseline", "reports/baseline-extractive-v2.json"]),
             run_step("promptfoo", ["-m", "scripts.run_promptfoo", "--suite"])]
    save_report(ROOT / "reports/local/gate.json", {"steps": steps, "pass": all(s["exit_code"] == 0 for s in steps),
        "live_model": "not_run", "human_review": "not_run", "hosted_ci": "not_run"})
    if any(s["exit_code"] == 2 for s in steps):
        return 2
    return 0 if all(s["exit_code"] == 0 for s in steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
