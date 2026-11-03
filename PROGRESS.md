Current task: T16 — Complete: distinct metrics and recorded failing baseline implemented.
Completed tasks: T01–T12 at recorded scope; T13 fallback; T16 metrics. T14 live integration and T15 Promptfoo CLI acceptance remain incomplete; optional adapters/configurations implemented.
Acceptance evidence / tests: 187 tests passed on Windows. All 12 frozen cases evaluated through the actual extractive pipeline: 8 deterministic passes; Q02/Q05/Q07/Q12 fail. Mean Source Recall@3 = 6/7 = 0.8571 (<0.90); citation validity and structural coverage = 14/14. Human support review = 0/14, accuracy N/A. Quality CLI correctly exited 1. Initial date-format scorer bug and its original report are preserved and explained in reports/README.md; equivalent ISO/prose dates now tested. No frozen inputs/expectations/fixtures changed. No live-model or Promptfoo CLI run.
Implemented by: Codex
Active mode: takeover (remaining queue through T21; commit/push each increment)
Run mode: extractive
Key decision or blocker: Baseline is an observed failing baseline, not waived acceptance. Metrics distinguish missing sources, forged citations, claim coverage and human support decisions. Output hashes bind manual review to exact outputs; baseline compatibility checks preserve dataset/corpus/mode/configuration. Q02/Q05 require reviewed corpus improvements, not injected gold answers or silent fixture changes.
Next smallest action: Demonstrate a fail/recover local gate, address feasible runtime hygiene/abstention regressions, and keep unresolved frozen-corpus failures visible.
