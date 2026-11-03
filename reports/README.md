# Evaluation records

`baseline-extractive-v2.json` is the first recorded automated baseline, not a passing acceptance report.
It runs all 12 frozen cases through the real extractive pipeline: 8 pass, Q02/Q05/Q07/Q12 fail, and mean Source Recall@3 is 6/7 (0.8571), below 0.90.
Citation validity and structural coverage are 14/14; human citation accuracy is unmeasured with 0/14 claims reviewed.
A valid citation does not establish factual support.

`metrics-initial-diagnostic.json` preserves the first scorer run, which incorrectly rejected ISO dates in Q04/Q06.
The scorer was corrected to accept equivalent ISO/prose dates, with regression tests for both formats, before recording the baseline.
No frozen question, expected fact, corpus, or threshold changed.
Neither report is overwritten automatically.
Reports carry code hashes and Git dirty state because implementation was not yet committed when these checks ran.

Run `python -m evals.run --baseline reports/baseline-extractive-v2.json` on Windows or macOS after environment activation.
Exit 0 means the automated gate passed, 1 means quality failed, and 2 means setup/integrity was blocked.
The default report and raw outputs go to Git-ignored `reports/local/`.
Public-evidence and synthetic-adversarial metrics are separated.
Human review remains separate from all deterministic checks.

To record human citation-support review, inspect `reports/local/outputs.json` and provide a local JSON file to `--reviews`.
Each case entry needs its exact `output_hash` from the report, `reviewer`, `reviewed_on`, and `claims`, mapping zero-based cited claim indices to `true` (supported) or `false` (unsupported).
Changed outputs invalidate those decisions.
Do not record the assistant or test fixtures as Nik's human review.
