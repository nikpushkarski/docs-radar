# Evaluation records

## Current v3 acceptance

`verification-windows-v3.json` records the final Windows checks: 238 tests, actual Edge workflow, clean model-free checkout, and explicit remaining limitations.
`baseline-extractive-v3.json` establishes the separately approved corpus baseline; `final-extractive-v3.json` compares compatibly with it.
Both record 12/12 deterministic passes, Source Recall@3 7/7, and citation validity/structural coverage 15/15.
`live-selection-4b-v3.json` also passes 12/12: seven actual 4B calls, five deterministic no-call cases.
Those calls took 2.38–3.60 seconds on Nik's Windows machine; no model remained resident afterward.
The model selects evidence; Python renders excerpts, not generated prose.
`gate-full-v3.json` records full model-free gate exits 0 → 1 → 0, including actual Promptfoo each time.
The injected missing-approval run falls to 3/12; neither real approvals nor frozen files change.
`clean-install-windows-v3.json` verifies a fresh local clone, new Python environment, no model package/weights, offline locked npm install with scripts disabled, full gate, smoke/negative control, and HTTP 200 startup.
Npm still reports 15 packages as extraneous even after that clean locked install; no pruning or lock rewrite was used to hide it.

Nik explicitly approved the two source-backed content revisions and the separate v3 corpus.
The 12 questions, expected behaviors, thresholds, source expectations, and four adversarial fixtures are unchanged from v2.
V3's corpus differs, so it is not presented as a same-corpus regression comparison with v2.
Human citation support remains **unmeasured: 0/15 reviewed claims per mode**.
Native macOS runtime, hosted CI, and the complete interactive TUI download flow remain unrun.
No larger model was downloaded or executed.

## Historical evidence

`verification.json` preserves the earlier 203-test Windows checkpoint, loopback startup, and three-view Edge browser smoke.
`final-extractive-v2.json` preserves the earlier 10/12 run and its historical code hash.
`model-status.json` and `live-model-attempt-v2.json` predate authorized installation; their unavailable-dependency status is not current.
`model-smoke-windows-v1.json` records the subsequent real Ollama/4B smoke.
Historical reports are not rewritten into successes.
`verification-lightweight-windows-v1.json`, `live-selection-4b-v2.json`, and `extractive-lightweight-v2.json` preserve the 222-test/10-of-12 checkpoint before the approved corpus update.
Their Q02/Q05 failures remain visible; v2 still reproduces 10/12 after the v3 work.

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
The old isolated control remains available as `python -m evals.control`.
The current `python -m scripts.quality_gate --demonstrate` exercises the entire v3 gate, not only Q01.
The older gate was blocked on Promptfoo installation; current v3 executes Promptfoo and passes.
Hosted CI has not been enabled or run.
One Windows temporary-directory rename test raised WinError 5 during the first gate invocation; the individual test and all 193 tests passed on rerun without changing the test.
Reports carry code hashes and Git dirty state because implementation was not yet committed when these checks ran.

Run `python -m evals.run --baseline reports/baseline-extractive-v3.json` after environment activation.
To reproduce historical failures, use `--version v2 --baseline reports/baseline-extractive-v2.json`.
Exit 0 means the automated gate passed, 1 means quality failed, and 2 means setup/integrity was blocked.
The default report and raw outputs go to Git-ignored `reports/local/`.
Public-evidence and synthetic-adversarial metrics are separated.
Human review remains separate from all deterministic checks.

`live-model-attempt-v2.json` is an incomplete live-path attempt, not model performance evidence.
In that earlier run, all 12 cases traversed the actual pipeline, but no model call completed: optional dependencies were absent, every `model_called` was false, and model digests were empty.
Five deterministic pre-generation behaviors passed; none is a live-generation pass.
After consenting to local installation and starting the project server, rerun `python -m evals.run --mode live-model --model <installed-tag>` on either OS.
Record human support review separately, and rerun after code, corpus, prompt or model changes.

## Human review handoff

In **Quality**, select `reports/final-extractive-v3.json` or `reports/live-selection-4b-v3.json` and expand **Review recorded citation support**.
Inspect the 15 claims beside their cited passages/links; mark Supported or Not supported, identify yourself, explicitly confirm, then prepare/download the review file.
Every choice defaults to Unreviewed, and synthetic cases remain labelled.
The UI neither submits decisions on page load nor changes content approvals.

Current raw artifacts are `reports/local/final-extractive-v3-outputs.json` and `reports/local/live-selection-4b-v3-outputs.json`.
Each report names its own artifact, and the UI validates every output hash before allowing review.
On a fresh checkout, run the evaluator and select `reports/local/latest.json` instead; raw artifacts are deliberately not published.
Save the downloaded file under `reports/local/` and rerun the same version/mode with `--reviews <file>` and a new `--output` path.
Each case entry needs its exact `output_hash` from the report, `reviewer`, `reviewed_on`, and `claims`, mapping zero-based cited claim indices to `true` (supported) or `false` (unsupported).
Changed outputs invalidate those decisions.
Do not record the assistant or test fixtures as Nik's human review.
