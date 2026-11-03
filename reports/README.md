# Evaluation records

## Current lightweight path

`verification-lightweight-windows-v1.json` records the current Windows checks and resource policy.
`live-selection-4b-v2.json` runs all 12 unchanged cases: six real 4B selection calls, six deterministic no-call cases, 10/12 passes.
The model selects source groups; Python renders complete excerpts, not generated prose.
The six calls took 2.3–3.3 seconds each on Nik's Windows machine; Ollama reported no model resident after the suite.
`extractive-lightweight-v2.json` retains 10/12 and a compatible comparison with the original baseline, with no new critical failures.
Q02/Q05 and Recall@3 still fail; human citation support remains unmeasured at 0/14 reviewed claims.
Actual Promptfoo smoke passed; its negative control failed as intended; its full suite retained Q02/Q05 failures.
Python 3.13 constraints cover the installed dependency closure; the npm lock pins the declared package tree.
The existing npm installation includes extraneous packages; a clean `npm ci` and native macOS execution remain unverified.
No model/package payload was downloaded for this lightweight change, and 8B was not executed.

## Historical evidence

`verification.json` preserves the earlier 203-test Windows checkpoint, loopback startup, and three-view Edge browser smoke.
`final-extractive-v2.json` preserves the earlier 10/12 run and its historical code hash.
`model-status.json` and `live-model-attempt-v2.json` predate authorized installation; their unavailable-dependency status is not current.
`model-smoke-windows-v1.json` records the subsequent real Ollama/4B smoke.
Historical reports are not rewritten into successes.
Human review, hosted CI, clean-checkout installation, and native macOS runtime remain unverified.

`baseline-extractive-v2.json` is the first recorded automated baseline, not a passing acceptance report.
It runs all 12 frozen cases through the real extractive pipeline: 8 pass, Q02/Q05/Q07/Q12 fail, and mean Source Recall@3 is 6/7 (0.8571), below 0.90.
Citation validity and structural coverage are 14/14; human citation accuracy is unmeasured with 0/14 claims reviewed.
A valid citation does not establish factual support.

`metrics-initial-diagnostic.json` preserves the first scorer run, which incorrectly rejected ISO dates in Q04/Q06.
The scorer was corrected to accept equivalent ISO/prose dates, with regression tests for both formats, before recording the baseline.
No frozen question, expected fact, corpus, or threshold changed.
Neither report is overwritten automatically.
`extractive-runtime-fixes-v2.json` records 10/12 deterministic passes after runtime fixes for Q07 and Q12, with the same frozen corpus and no newly failing critical cases.
Q02/Q05 and the Recall@3 threshold still fail; this is not a green release gate.
`gate-control-v2.json` records real subprocess exits 0 → 1 → 0 for an isolated missing-approval configuration regression and repair, not the full quality suite.
The full local gate is `python -m scripts.quality_gate`; `--demonstrate` runs that isolated control.
That historical gate was blocked on Promptfoo installation; the current full local gate executes Promptfoo and fails on the known quality cases.
Hosted CI has not been enabled or run.
One Windows temporary-directory rename test raised WinError 5 during the first gate invocation; the individual test and all 193 tests passed on rerun without changing the test.
Reports carry code hashes and Git dirty state because implementation was not yet committed when these checks ran.

Run `python -m evals.run --baseline reports/baseline-extractive-v2.json` on Windows or macOS after environment activation.
Exit 0 means the automated gate passed, 1 means quality failed, and 2 means setup/integrity was blocked.
The default report and raw outputs go to Git-ignored `reports/local/`.
Public-evidence and synthetic-adversarial metrics are separated.
Human review remains separate from all deterministic checks.

`live-model-attempt-v2.json` is an incomplete live-path attempt, not model performance evidence.
In that earlier run, all 12 cases traversed the actual pipeline, but no model call completed: optional dependencies were absent, every `model_called` was false, and model digests were empty.
Five deterministic pre-generation behaviors passed; none is a live-generation pass.
After consenting to local installation and starting the project server, rerun `python -m evals.run --mode live-model --model <installed-tag>` on either OS.
Record human support review separately, and rerun after code, corpus, prompt or model changes.

To record human citation-support review, inspect the matching raw outputs and provide a local JSON file to `--reviews`.
The current selection outputs are `reports/local/lightweight-live-outputs.json`; extractive outputs are `reports/local/lightweight-extractive-outputs.json`.
`reports/local/outputs.json` is overwritten by the latest default evaluator run, so always match its output hashes to the chosen report.
Each case entry needs its exact `output_hash` from the report, `reviewer`, `reviewed_on`, and `claims`, mapping zero-based cited claim indices to `true` (supported) or `false` (unsupported).
Changed outputs invalidate those decisions.
Do not record the assistant or test fixtures as Nik's human review.
