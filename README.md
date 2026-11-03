# Docs Radar

Documentation change-impact detection and a citation-grounded AI assistant, with automated evaluations and CI quality gates.

## Current status

Streamlit evidence interface, three attributed source summaries, and 12 reviewed evaluation cases frozen as v2.
The interface accepts a question, audience, and reference date, then shows cited excerpts or an explicit clarification, abstention, or error.
Source validation checks required provenance fields and allowed review states; three automated tests cover valid data, missing provenance, and an invalid review state.
CLI scripts also render shared facts, identify affected topics for a supplied synthetic change, and calculate content fingerprints.
A standalone approval gate excludes topics without a matching demo approval; no real approvals have been recorded.
Initial CLI retrieval combines approval checks, audience/date selection, and local TF-IDF ranking.
Only the provider migration topic currently declares answer passages.
Explicit unresolved-conflict flags return a conflict result instead of answer context; contradictions are not detected automatically.
Extractive output uses the real retrieval pipeline; no LLM generates the displayed text.
Account-transfer status questions have limited explicit abstention rules, not a general intent classifier.
The frozen case set and five isolated fixtures are integrity-checked; no full graded baseline has been established.
Live-model answers, Promptfoo evaluation, complete evaluation assertions/metrics, and CI gates are not implemented yet.

## Use

**Developers:** Use a virtual environment to keep this project's Python packages separate.
With Python installed, run the commands for your terminal from the project folder:

| Step | Windows (cmd / cmder cmd) | macOS (zsh / Bash) |
| --- | --- | --- |
| Create once | `py -m venv .venv` | `python3 -m venv .venv` |
| Activate each new terminal | `.\start.cmd` | `source .venv/bin/activate` |
| Leave the environment | `deactivate` | `deactivate` |

After activation, use `python -m pip` for package installation on either platform.
Create `.venv` locally on each machine; do not copy it between operating systems.

> On Windows, use `.\start.cmd`, not bare `start`, which opens a new window.

After activation, launch the app from the project folder:

```text
python -m streamlit run app.py
```

With the current empty approval store, the app explains that no demo-approved content is available.
Tests use temporary synthetic approvals; they do not approve the real corpus.

## Check source validation

After activation, run from the project folder on either platform:

```text
python -m unittest discover -s tests -p test_validate_source.py -v
```

Expected: three passing tests.
These check metadata validation, not answer quality or factual accuracy.

## Check frozen evaluation fixtures

- `evals/cases.json` — 12 cases, with inputs separate from expectations.
- `evals/fixtures/` — five isolated test workspaces.
- `evals/manifest.json` — hashes of the frozen cases and fixtures.
- `evals/suite.py` — integrity checks and a wrapper for the real answer pipeline.

After activation, run from the project folder on either platform:

```text
python -m evals.suite
```

This checks the 12-case specification, frozen file hashes, and five fixture workspaces—not whether all 12 answers pass.
Fixture approvals use a synthetic reviewer and temporary storage, never the real approval file.
Changes to frozen expectations or fixture content need review and a new version; do not silently refresh hashes.

## Fingerprint changes reasoning

A topic needs a new review when its text or referenced facts change.
Its fingerprint tracks those changes without reacting to unrelated facts or JSON field order.

| Change | Fingerprint changes? |
| --- | --- |
| Edit the topic's text | Yes |
| Change a referenced fact's value or version | Yes |
| Change its evidence or audience | Yes |
| Change an unrelated fact | No |
| Reorder JSON fields | No |

Unknown or duplicate referenced fact IDs produce an error.
Fingerprints identify content versions; they do not approve content by themselves.
The approval gate admits a topic only when its current fingerprint matches its stored demo approval.

## Approval reasoning

| Situation | Result |
| --- | --- |
| No approval | Excluded |
| Current fingerprint matches the approved version | Eligible |
| Topic or referenced fact changes | Excluded until reapproved |
| Unrelated fact changes | Still eligible |
| Approval is deprecated, invalid, or incomplete | Excluded |

Eligible here means passing the approval gate, not guaranteed relevance to a question.
Approvals apply only to this independent demo, not Fullscript.

## Date-aware passage selection

Select guidance by audience and reference date rather than expiring an entire topic when one deadline passes.
Retrieval defaults to today's local date and records it; tests use explicit dates.

| Reference date | Applicable guidance |
| --- | --- |
| Before December 4, 2026 | Explain the recommended transfer date, its patient-impact rationale, and the final login closure |
| December 4, 2026–January 19, 2027 | Acknowledge that the recommended date has passed; retain supported guidance to transfer before login closes |
| January 20, 2027 onward | Do not promise continued login access; abstain from recovery instructions without supporting evidence |

These are demo selection rules based on evidence captured November 1, 2026, not live verification of Fullscript's policies.
The first interval starts on that capture date; earlier historical answers are not established by this snapshot.
The audience/date filter is tested against routing fixtures and the migration topic's actual passages, including both date boundaries.
Passage rules live in the topic's JSON metadata block, so changing them invalidates its approval fingerprint.
Initial retrieval connects approval filtering, passage selection, and text ranking, returning evidence rather than a generated answer.
With no real approvals recorded, a normal retrieval run currently returns `no_approved_topics`.
