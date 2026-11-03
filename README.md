> [!IMPORTANT]
> Docs Radar is an independent demo and is **not affiliated with, endorsed by, or sponsored by Fullscript**.

# Docs Radar

## What is it?

Docs Radar flags docs that need updating when shared facts change.
It answers questions with source-linked excerpts.
Use **Content and changes** to inspect dependencies and review drafts, **Ask and inspect** for answers and evidence, and **Quality** for recorded results.

## Tech stack

- **Python + Streamlit** — application logic and web UI.
- **TF-IDF** — local, approval-aware evidence retrieval.
- **Ollama + LangChain** — optional small-model evidence selection; Python renders excerpts, not generated prose.
- **Markdown + JSON** — content, shared facts, approvals, and evaluation cases.
- **unittest + Streamlit AppTest** — automated checks; browser smoke-tested on Windows.
- **Promptfoo** — installed, locked, real-pipeline checks; smoke and negative control verified.
- **Local quality gate** — no hosted GitHub Actions enabled.

## Easy way to start

Install [Python 3.13](https://www.python.org/downloads/), the tested dependency-lock path, then open a terminal in this project's folder.

| Step | Windows (cmd / cmder cmd) | macOS (zsh / Bash) |
| --- | --- | --- |
| Run the setup TUI | `py -3.13 -m scripts.setup_local` | `python3.13 -m scripts.setup_local` |
| Launch the app after setup | `.\.venv\Scripts\python.exe -m streamlit run docs_radar/app.py` | `./.venv/bin/python -m streamlit run docs_radar/app.py` |

Keep the default **Install extractive app only (no model)** for the quickest start; no GPU, Ollama, or model weights are needed.
Use Up/Down and Enter to navigate, and review the download table before accepting.
Open http://localhost:8501 after launching the app.
The default app shows cited excerpts, not model-generated answers.
The frozen quality suite currently passes 10/12 deterministic checks; Q02 patient coverage and Q05 post-recommendation guidance still fail.
The optional 4B model-selected-excerpt path also passes 10/12; it is not free-form generation or a complete quality pass.
Human citation-support review remains incomplete.

<details>
<summary>Need more? Expand setup details, current limitations, and verification checks</summary>

<details>
<summary><strong>Local installation — Windows and macOS</strong></summary>

Use Python 3.13; the terminal bootstrap accepts 3.11.8+, but other minors are not the locked installation path.
Windows validation uses Python 3.13.17; earlier browser smoke evidence used 3.15.1.
macOS ARM64/Intel wheel-resolution dry runs passed, but native installation and runtime are not tested.
Application code lives in `docs_radar/`, setup tools and requirements in `scripts/`, and all tests in `tests/`.
Content, data, and frozen evaluation fixtures remain in `content/`, `data/`, and `evals/`.

</details>

<details>
<summary><strong>Interactive installer</strong></summary>

Install [Python 3.13](https://www.python.org/downloads/) first; the bootstrap itself uses no third-party packages.
Run from the project folder in an interactive terminal:

| Windows (cmd / cmder cmd) | macOS (zsh / Bash) |
| --- | --- |
| `py -3.13 -m scripts.setup_local` | `python3.13 -m scripts.setup_local` |

Use Up/Down and Enter to choose an existing model, request a hardware recommendation, or install only the extractive app.
The installer shows a paged download table, then asks `Start downloading? [Y/n]`; Enter defaults to Yes on the final page.
No network requests, package installations or model downloads occur before consent.
Yes creates/reuses `.venv`, installs `scripts/requirements.txt` and its dependencies, and optionally installs a pinned Ollama runtime and model.
N starts no downloads and shows the manual model folder and rerun instructions.
Esc or Ctrl+C cancels; existing model files are not deleted.

Ollama 0.40.14, the pinned 4B model, Python dependencies, and real local calls were installed/executed on Windows with consent.
A clean-checkout end-to-end installer run and native macOS execution remain unverified.

</details>

<details>
<summary><strong>Manual extractive-only setup / launching after installation</strong></summary>

If you used the installer, skip environment creation and dependency installation below; activate the environment and launch the app.
Otherwise, use a fresh virtual environment on each machine.
From a local checkout of this repository, run the commands for your terminal:

| Step | Windows (cmd / cmder cmd) | macOS (zsh / Bash) |
| --- | --- | --- |
| Create once | `py -3.13 -m venv .venv` | `python3.13 -m venv .venv` |
| Activate each new terminal | `.\scripts\start.cmd` | `source .venv/bin/activate` |
| Leave the environment | `deactivate` | `deactivate` |

Do not copy `.venv`, executables, or installed packages between operating systems.
`scripts/requirements.txt` includes the Python 3.13 transitive constraints; OS markers exclude dependencies not needed on macOS.

> On Windows, use `.\scripts\start.cmd`, not bare `start`, which opens a new window.

After activation, install the dependencies and launch the app; these commands are the same on both platforms:

```text
python -m pip install -r scripts/requirements.txt
python -m streamlit run docs_radar/app.py
```

Open http://localhost:8501 if the browser does not open automatically.
Run from the repository root: `.streamlit/config.toml` binds the UI to `127.0.0.1` and disables usage telemetry.
The content-review controls have no authentication; do not expose this server to the network.
To see excerpts, choose Providers and reference date November 1, 2026, then ask where to place new lab orders.
Verify startup with `python -m unittest tests.test_app`.
Run all tests with `python -m unittest discover -s tests -q`.
Tests use separate synthetic approvals; they do not change real content approvals.

</details>

<details>
<summary><strong>Optional local-model setup</strong></summary>

The no-model path is the recommended demo default, including on a hiring manager's machine.
Optional model selection uses `docs_radar/generation.py`: approved retrieval → LangChain/Ollama → source indices → complete excerpts.
Python retains the source wording and registered citations; the model cannot write or shorten guidance.
Selection can still be irrelevant or incomplete; this is not semantic-entailment verification or free-form generation.
The original pinned `qwen3:4b` was tested; no custom template or larger model is required.
After explicitly choosing to download optional dependencies, run `python -m pip install -r scripts/requirements-model.txt` in the activated environment on either Windows or macOS.
The LangChain integration and its Python 3.13 dependency closure are pinned; `pip check` passed on Windows.
The installer uses official standalone archives so installation stays in the terminal, without administrator access, a GUI installer or global PATH changes.
It keeps a separate runtime rather than modifying an existing system-wide Ollama installation.

| | Windows | macOS |
| --- | --- | --- |
| Runtime requirements | Windows 10 22H2+ / Windows 11; x64 or ARM64 | macOS 14+; Apple silicon or Intel |
| Ollama 0.40.14 archive | Native Windows `.zip` | Universal macOS `.tgz` |
| Runtime directory | `%LOCALAPPDATA%\DocsRadar\ollama\0.40.14\<arch>` | `~/Library/Application Support/DocsRadar/ollama/0.40.14/<arch>` |
| Manual model folder | `models\` in this project | `models/` in this project |
| Managed model cache | `models\ollama\` | `models/ollama/` |

Recommendations stop at Qwen3 4B on every machine; smaller 0.6B/1.7B options remain hardware-dependent and are not quality-validated here.
All three use Apache 2.0 licences.
The adapter rejects models above 4B class or 3 GiB of weights, unknown size/memory, and insufficient measured RAM/VRAM headroom before inference.
Large files already on disk are left alone, not offered or loaded by the app.
These conservative checks reduce resource risk; they do not guarantee peak memory, latency, or comfort on another device.
Archive sizes/checksums and model manifests are pinned; changed remote manifests stop setup rather than silently changing downloads.

For manual downloads, put a complete, single-file `.gguf` directly in `models/`, then rerun the installer and select it with the arrow keys.
The decline screen links to the suggested model's official Qwen publisher page.
Existing complete Ollama caches in `models/ollama/` are also detected; partial files, split GGUFs and Safetensors are not imported.
GGUF header detection is not proof of model compatibility; Ollama must successfully import it.
Importing a GGUF can create a second copy in the managed cache, so reserve disk space for both.
Everything under `models/` is Git-ignored, including local setup metadata and logs; never force-add weights or use Git LFS for them.

After a successful model installation, activate `.venv` and run `python -m scripts.setup_local --serve` from the project folder to start its server.
The server binds only to http://127.0.0.1:11435 with cloud disabled, one loaded model, and one request at a time.
Selection uses a 2,048-token context, at most 64 output tokens, two CPU threads, a 30-second response timeout, and no repair retries.
Oversized evidence is rejected rather than truncated.
`keep_alive=0` unloads the model after each request; repeated calls reload it.
It does not modify the default Ollama server on port 11434 or global user settings.
Keep that terminal open; Enter or Ctrl+C stops the project server.
Setup itself stops its temporary server on completion and records the selected model/digest in `models/setup.json`; it does not claim a generation smoke test passed.
In **Ask and inspect**, choose **Model-selected excerpts (optional)** and enter the installed tag from `models/setup.json`.
The adapter never pulls models; resource limits, missing dependencies/runtime, or invalid selections return explicit errors, not silent fallback.
For all 12 evaluation cases, run `python -m evals.run --mode live-model --model <installed-tag>` in another activated terminal on either OS.
This saves local provenance and outputs; human support review remains separate.
The current Windows run completed six actual selection calls in 2.3–3.3 seconds each; eligibility/clarification/abstention gates skipped the other six.
Both modes retain Q02/Q05 failures; human support review is still missing.
The older zero-call report remains historical, not current installation status.
If the machine cannot run a model comfortably, choose the extractive app—not a larger model or hosted fallback.

Official references: [pinned runtime release](https://github.com/ollama/ollama/releases/tag/v0.40.14), [Windows](https://docs.ollama.com/windows), [macOS](https://docs.ollama.com/macos), [GGUF import](https://docs.ollama.com/import), [local-only configuration](https://docs.ollama.com/faq).

</details>

<details>
<summary><strong>Check source validation</strong></summary>

After activation, run from the project folder on either platform:

```text
python -m unittest discover -s tests -p test_validate_source.py -v
```

Expected: three passing tests.
These check metadata validation, not answer quality or factual accuracy.

</details>

<details>
<summary><strong>Quality checks and frozen evaluation fixtures</strong></summary>

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

Run these commands on either OS after activation:

```text
python -m evals.run --baseline reports/baseline-extractive-v2.json
python -m scripts.quality_gate --demonstrate
python -m scripts.quality_gate
```

The evaluator currently exits **1**: 10/12 deterministic passes, Source Recall@3 **6/7 (0.8571)** below 0.90, and Q02/Q05 failures.
Citation validity/structural coverage are 14/14; factual support is unmeasured with 0/14 claims human-reviewed.
The demonstration records an isolated control's exits **0 → 1 → 0**, not a full-suite pass.
The full gate returns **1** for the known quality failures; installed Promptfoo runs the actual suite rather than being skipped.
Reports identify code, corpus, dataset and mode; `reports/README.md` explains review and comparison.
Raw outputs and fresh local reports stay in Git-ignored `reports/local/`.

Optional Promptfoo requires Node 24 LTS.
After explicitly choosing to install its pinned package, run from the repository root on either OS:

```text
npm ci --prefix evals
python -m scripts.run_promptfoo
python -m scripts.run_promptfoo --negative-control
python -m scripts.run_promptfoo --suite
```

The smoke should pass, the deliberately incorrect negative control should fail, and the full suite retains known quality failures.
These CLI checks were executed on Windows: smoke exit 0, negative-control exit 100, full suite 10/12 with Q02/Q05 failing.
The launcher never downloads packages automatically and disables telemetry/update checks.
`evals/package-lock.json` pins the declared Promptfoo dependency tree.
A clean `npm ci` remains unverified; the existing installation includes extraneous packages.
No hosted model, paid judge, report upload or hosted CI is configured.

</details>

<details>
<summary><strong>Fingerprint changes reasoning</strong></summary>

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

</details>

<details>
<summary><strong>Approval reasoning</strong></summary>

| Situation | Result |
| --- | --- |
| No approval | Excluded |
| Current fingerprint matches the approved version | Eligible |
| Topic or referenced fact changes | Excluded until reapproved |
| Unrelated fact changes | Still eligible |
| Approval is deprecated, invalid, or incomplete | Excluded |

Eligible here means passing the approval gate, not guaranteed relevance to a question.
Approvals apply only to this independent demo, not Fullscript.
In **Content and changes**, inspect the rendered topic and facts before entering your reviewer name and confirming the exact version.
**Save draft** validates metadata and invalidates an old approval when the content changes; it never reapproves it.
**Remove answer eligibility** returns the topic to draft.
If a topic or referenced fact changes during review, reload before approving.
The two files in `content/drafts/` propose the missing patient guidance and the provider boundary-date correction; they are intentionally outside the answer corpus.
Review their wording and routing against the linked source before authorizing promotion and an explicitly versioned evaluation-corpus update.
No real approval, frozen v2 fixture, expectation, threshold, or baseline was changed.

</details>

<details>
<summary><strong>Date-aware passage selection</strong></summary>

Select guidance by audience and reference date rather than expiring an entire topic when one deadline passes.
Retrieval defaults to today's local date and records it; tests use explicit dates.

| Reference date | Applicable guidance |
| --- | --- |
| Before December 4, 2026 | Explain the recommended transfer date, its patient-impact rationale, and the final login closure |
| December 4, 2026–January 19, 2027 | The window to follow the “before December 4” recommendation has passed; retain its rationale and supported transfer guidance |
| January 20, 2027 onward | Do not promise continued login access; abstain from recovery instructions without supporting evidence |

These are demo selection rules based on evidence captured November 1, 2026, not live verification of Fullscript's policies.
The first interval starts on that capture date; earlier historical answers are not established by this snapshot.
The audience/date filter is tested against routing fixtures and the migration topic's actual passages, including both date boundaries.
Passage rules live in the topic's JSON metadata block, so changing them invalidates its approval fingerprint.
Default retrieval connects approval filtering, passage selection, and text ranking, returning excerpts rather than generated prose.
The approved provider migration topic can supply dated excerpts; other topics remain ineligible.
The frozen corpus still lacks patient payment passages and the required rationale after the recommended transfer date; those failures are not waived.
Instruction-like lines are filtered from excerpt guidance after retrieval, with raw text available only in labelled inspection.
This narrow rule is not general prompt-injection protection.

</details>

</details>
