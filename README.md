# Docs Radar

Documentation change-impact detection and a citation-grounded AI assistant, with automated evaluations and CI quality gates.

## Current status

Streamlit evidence interface, three attributed source summaries, and 12 reviewed evaluation cases frozen as v2.
The interface accepts a question, audience, and reference date, then shows cited excerpts or an explicit clarification, abstention, or error.
Source validation checks required provenance fields and allowed review states; three automated tests cover valid data, missing provenance, and an invalid review state.
CLI scripts also render shared facts, identify affected topics for a supplied synthetic change, and calculate content fingerprints.
A standalone approval gate excludes topics without a matching demo approval; Nik has approved the current provider migration topic and its referenced fact.
Initial CLI retrieval combines approval checks, audience/date selection, and local TF-IDF ranking.
Only the provider migration topic currently declares answer passages.
Explicit unresolved-conflict flags return a conflict result instead of answer context; contradictions are not detected automatically.
Extractive output uses the real retrieval pipeline; no LLM generates the displayed text.
Account-transfer status questions have limited explicit abstention rules, not a general intent classifier.
The frozen case set and five isolated fixtures are integrity-checked; no full graded baseline has been established.
Live-model answers, Promptfoo evaluation, complete evaluation assertions/metrics, and CI gates are not implemented yet.

## Local installation — Windows and macOS

The current extractive app needs Python 3.11+; Ollama is not required.
Windows is tested with Python 3.15.1; macOS instructions are documented but not runtime-tested.

Use a fresh virtual environment on each machine.
From a local checkout of this repository, run the commands for your terminal:

| Step | Windows (cmd / cmder cmd) | macOS (zsh / Bash) |
| --- | --- | --- |
| Create once | `py -m venv .venv` | `python3 -m venv .venv` |
| Activate each new terminal | `.\start.cmd` | `source .venv/bin/activate` |
| Leave the environment | `deactivate` | `deactivate` |

Do not copy `.venv`, executables, or installed packages between operating systems.
`requirements.txt` pins the direct runtime dependency; transitive dependencies are not fully locked yet.

> On Windows, use `.\start.cmd`, not bare `start`, which opens a new window.

After activation, install the dependencies and launch the app; these commands are the same on both platforms:

```text
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501 if the browser does not open automatically.
To see excerpts, choose Providers and reference date November 1, 2026, then ask where to place new lab orders.
Verify startup with `python -m unittest test_app.py`.
Tests use separate synthetic approvals; they do not change real content approvals.

## Optional local-model installation

This prepares the runtime for the planned model integration; installing it does not enable generative answers in the app yet.
Use the native installer for each OS, never the Windows `.exe` on macOS.

| | Windows | macOS |
| --- | --- | --- |
| Official installer | [Windows `.exe`](https://ollama.com/download/windows) | [macOS `.dmg`](https://ollama.com/download/mac) |
| Requirements | Windows 10 22H2+; supported GPU/driver or CPU | macOS 14 Sonoma+; Apple silicon CPU/GPU, Intel CPU-only |
| App location | `%LOCALAPPDATA%\Programs\Ollama` | `/Applications/Ollama.app` |
| Model location | `%USERPROFILE%\.ollama\models` | `~/.ollama/models` |
| Server configuration | `%USERPROFILE%\.ollama\server.json` | `~/.ollama/server.json` |

Download installers to a temporary or Downloads folder outside this repository.
Install Ollama with the native installer; on macOS, drag the app to Applications and allow its CLI setup when prompted.
Before running a model, add `"disable_ollama_cloud": true` to the server configuration file, preserving any existing settings, then quit and restart Ollama.
Create the directory/file if absent; a new file can contain just `{"disable_ollama_cloud": true}`.
Keep the server on its default loopback address, http://127.0.0.1:11434; do not expose it to the network or configure a cloud fallback.

The initial candidate is [qwen3:4b](https://ollama.com/library/qwen3:4b), Q4_K_M, about 2.5 GB, Apache 2.0.
Check available memory and disk first; Windows Ollama installation additionally requires at least 4 GB of disk space.
After installation and local-only configuration, these commands are the same on both platforms:

```text
ollama --version
ollama pull qwen3:4b
ollama list
```

The pull command downloads the model; none of these installation steps has been executed for this project yet.
Model files stay outside Git, and `.gitignore` also guards against accidentally placed installers or weights.
If the machine cannot run the model comfortably, use the extractive app above—not an automatic paid fallback.
Native setup requirements: [Windows](https://docs.ollama.com/windows), [macOS](https://docs.ollama.com/macos), [local-only configuration](https://docs.ollama.com/faq).

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
The approved provider migration topic can supply dated excerpts; other topics remain ineligible.
