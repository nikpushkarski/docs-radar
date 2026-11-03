"""Run installed Promptfoo only. Never use npx or install packages implicitly."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--negative-control", action="store_true")
    parser.add_argument("--suite", action="store_true")
    args = parser.parse_args()
    if args.suite and args.negative_control:
        parser.error("Choose either the suite or the negative control")
    node = shutil.which("node")
    cli = ROOT / "evals/node_modules/promptfoo/dist/src/entrypoint.js"
    if not node or not cli.is_file():
        print("Promptfoo not installed; no download attempted. Review evals/package.json, then explicitly install the lock with npm ci --prefix evals.")
        return 2
    name = "promptfooconfig.json" if args.suite else "promptfoo-negative.json" if args.negative_control else "promptfoo-smoke.json"
    env = dict(os.environ, PROMPTFOO_DISABLE_TELEMETRY="1", PROMPTFOO_DISABLE_UPDATE="1",
               PROMPTFOO_PYTHON=sys.executable, PROMPTFOO_DISABLE_REMOTE_GENERATION="true",
               PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
               PROMPTFOO_CONFIG_DIR=str(ROOT / "evals/.promptfoo"))
    # Promptfoo children must resolve the shared package from any worker cwd.
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([node, str(cli), "eval", "--config", str(ROOT / "evals" / name),
        "--no-cache", "--max-concurrency", "1", "--output", str(ROOT / "reports/local/promptfoo.json")],
        cwd=ROOT, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
