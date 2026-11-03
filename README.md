> [!IMPORTANT]
> Docs Radar is an independent demo and is **not affiliated with, endorsed by, or sponsored by Fullscript**.

# Docs Radar

## What is it?

Docs Radar flags docs that need updating when shared facts change.
It answers questions with source-linked excerpts.

## Tech stack

- **Python + Streamlit** — application logic and web UI.
- **RAG / TF-IDF** — evidence retrieval is implemented; generation is planned.
- **Ollama + Qwen3** — local-model installer; app integration pending.
- **Markdown + JSON** — content, shared facts, approvals, and evaluation cases.
- **unittest + Streamlit AppTest** — automated checks.
- **LangChain, Promptfoo, GitHub Actions** — planned orchestration, evaluation, and CI.

## Easy way to start

Install [Python 3.11.8+](https://www.python.org/downloads/), then open a terminal in this project's folder.

| Step | Windows (cmd / cmder cmd) | macOS (zsh / Bash) |
| --- | --- | --- |
| Run the setup TUI | `py -m scripts.setup_local` | `python3 -m scripts.setup_local` |
| Launch the app after setup | `.\.venv\Scripts\python.exe -m streamlit run docs_radar/app.py` | `./.venv/bin/python -m streamlit run docs_radar/app.py` |

Choose **Install extractive app only (no model)** for the quickest start.
Use Up/Down and Enter to navigate, and review the download table before accepting.
Open http://localhost:8501 after launching the app.
The current app shows cited excerpts, not model-generated answers.

<details>
<summary>Need more? Expand setup details, current limitations, and verification checks</summary>

<details>
<summary><strong>Local installation — Windows and macOS</strong></summary>

The current extractive app needs Python 3.11+; Ollama is not required.
The app is tested on Windows with Python 3.15.1; macOS is not runtime-tested.
Application code lives in `docs_radar/`, setup tools and requirements in `scripts/`, and all tests in `tests/`.
Content, data, and frozen evaluation fixtures remain in `content/`, `data/`, and `evals/`.

</details>

<details>
<summary><strong>Interactive installer</strong></summary>

Install [Python 3.11.8+](https://www.python.org/downloads/) first; the bootstrap itself uses no third-party packages.
Run from the project folder in an interactive terminal:

| Windows (cmd / cmder cmd) | macOS (zsh / Bash) |
| --- | --- |
| `py -m scripts.setup_local` | `python3 -m scripts.setup_local` |

Use Up/Down and Enter to choose an existing model, request a hardware recommendation, or install only the extractive app.
The installer shows a paged download table, then asks `Start downloading? [Y/n]`; Enter defaults to Yes on the final page.
No network requests, package installations or model downloads occur before consent.
Yes creates/reuses `.venv`, installs `scripts/requirements.txt` and its dependencies, and optionally installs a pinned Ollama runtime and model.
N starts no downloads and shows the manual model folder and rerun instructions.
Esc or Ctrl+C cancels; existing model files are not deleted.

Installer checks are offline tests plus a real Windows hardware probe, not completed native installations or generation tests.
Neither Windows nor macOS end-to-end installation has been exercised yet.

</details>

<details>
<summary><strong>Manual extractive-only setup / launching after installation</strong></summary>

If you used the installer, skip environment creation and dependency installation below; activate the environment and launch the app.
Otherwise, use a fresh virtual environment on each machine.
From a local checkout of this repository, run the commands for your terminal:

| Step | Windows (cmd / cmder cmd) | macOS (zsh / Bash) |
| --- | --- | --- |
| Create once | `py -m venv .venv` | `python3 -m venv .venv` |
| Activate each new terminal | `.\scripts\start.cmd` | `source .venv/bin/activate` |
| Leave the environment | `deactivate` | `deactivate` |

Do not copy `.venv`, executables, or installed packages between operating systems.
`scripts/requirements.txt` pins the direct runtime dependency; transitive dependencies are not fully locked yet.

> On Windows, use `.\scripts\start.cmd`, not bare `start`, which opens a new window.

After activation, install the dependencies and launch the app; these commands are the same on both platforms:

```text
python -m pip install -r scripts/requirements.txt
python -m streamlit run docs_radar/app.py
```

Open http://localhost:8501 if the browser does not open automatically.
To see excerpts, choose Providers and reference date November 1, 2026, then ask where to place new lab orders.
Verify startup with `python -m unittest tests.test_app`.
Run all tests with `python -m unittest discover -s tests -q`.
Tests use separate synthetic approvals; they do not change real content approvals.

</details>

<details>
<summary><strong>Optional local-model setup</strong></summary>

The installer prepares the runtime for planned model integration; it does not enable generated answers in the app yet.
It uses official standalone archives so installation stays in the terminal, without administrator access, a GUI installer or global PATH changes.
It keeps a separate runtime rather than modifying an existing system-wide Ollama installation.

| | Windows | macOS |
| --- | --- | --- |
| Runtime requirements | Windows 10 22H2+ / Windows 11; x64 or ARM64 | macOS 14+; Apple silicon or Intel |
| Ollama 0.40.14 archive | Native Windows `.zip` | Universal macOS `.tgz` |
| Runtime directory | `%LOCALAPPDATA%\DocsRadar\ollama\0.40.14\<arch>` | `~/Library/Application Support/DocsRadar/ollama/0.40.14/<arch>` |
| Manual model folder | `models\` in this project | `models/` in this project |
| Managed model cache | `models\ollama\` | `models/ollama/` |

Recommendations range from Qwen3 0.6B to 8B, all Apache 2.0, using available RAM, NVIDIA free VRAM or Apple unified memory, and disk space.
CPU recommendations stop at 4B; Intel Macs and unverified/AMD Windows accelerators use CPU sizing.
This is a conservative heuristic, not a benchmark or proof of answer quality.
Archive sizes/checksums and model manifests are pinned; changed remote manifests stop setup rather than silently changing downloads.
Python's direct dependency is pinned, but its transitive dependencies are not fully locked.

For manual downloads, put a complete, single-file `.gguf` directly in `models/`, then rerun the installer and select it with the arrow keys.
The decline screen links to the suggested model's official Qwen publisher page.
Existing complete Ollama caches in `models/ollama/` are also detected; partial files, split GGUFs and Safetensors are not imported.
GGUF header detection is not proof of model compatibility; Ollama must successfully import it.
Importing a GGUF can create a second copy in the managed cache, so reserve disk space for both.
Everything under `models/` is Git-ignored, including local setup metadata and logs; never force-add weights or use Git LFS for them.

After a successful model installation, activate `.venv` and run `python -m scripts.setup_local --serve` from the project folder to start its server.
The server binds only to http://127.0.0.1:11435, sets `OLLAMA_NO_CLOUD=1`, and uses a 4096-token context.
It does not modify the default Ollama server on port 11434 or global user settings.
Keep that terminal open; Enter or Ctrl+C stops the project server.
Setup itself stops its temporary server on completion and records the selected model/digest in `models/setup.json`; it does not claim a generation smoke test passed.
If the machine cannot run a model comfortably, choose the extractive app—not a hosted fallback.

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
<summary><strong>Check frozen evaluation fixtures</strong></summary>

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

</details>

<details>
<summary><strong>Date-aware passage selection</strong></summary>

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

</details>

</details>
