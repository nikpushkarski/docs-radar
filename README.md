# Docs Radar

Docs Radar is a demo app that:

- flags docs that need updating when shared facts change

- answers questions with source-linked excerpts.

There are 3 tabs in the app:

| **Ask and inspect**  | **Content and changes** | **Quality**  |
|---|---|---|
| check answers and evidence  | inspect dependencies and review drafts  |  see the recorded results |

Explanatory captions are hidden by default; the floating **Show notes / Hide notes** button toggles them across all tabs.
In **Content and changes**, highlighted **Review needed** cells identify simulated proposals, and the first affected topic opens automatically.
Saved-document approval is separate and never approves a simulated proposal.

> [!IMPORTANT]
> Docs Radar is an independent demo and is **not affiliated with, endorsed by, or sponsored by Fullscript**.

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

<details>
<summary>Need more? Expand setup details, current limitations, and verification checks</summary>

## Local installation — Windows and macOS

<details>

Use Python 3.13; the terminal bootstrap accepts 3.11.8+, but other minors are not the locked installation path.
Windows validation uses Python 3.13.17: 238 tests, a clean model-free checkout, full local gate, and a real Edge browser workflow passed.
macOS ARM64/Intel wheel-resolution dry runs passed, but native installation and runtime are not tested.
Application code lives in `docs_radar/`, setup tools and requirements in `scripts/`, and all tests in `tests/`.
Content, data, and frozen evaluation fixtures remain in `content/`, `data/`, and `evals/`.

</details>

## Interactive installer

<details>

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
Clean Windows manual setup was verified with a newly created virtual environment and no model packages or weights.
The complete interactive TUI download flow and native macOS execution have not been tested end to end.

</details>

## Manual extractive-only setup / launching after installation

<details>

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

## Optional local-model setup
<details>

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
The Windows v3 run passed 12/12: seven actual selection calls took 2.38–3.60 seconds each; deterministic gates skipped the other five.
No model remained resident afterward.
These timings are not a performance guarantee for another machine, and human support review is still missing.
The older zero-call report remains historical, not current installation status.
If the machine cannot run a model comfortably, choose the extractive app—not a larger model or hosted fallback.

Official references: [pinned runtime release](https://github.com/ollama/ollama/releases/tag/v0.40.14), [Windows](https://docs.ollama.com/windows), [macOS](https://docs.ollama.com/macos), [GGUF import](https://docs.ollama.com/import), [local-only configuration](https://docs.ollama.com/faq).

</details>

## Check source validation

<details>

After activation, run from the project folder on either platform:

```text
python -m unittest discover -s tests -p test_validate_source.py -v
```

Expected: three passing tests.
These check metadata validation, not answer quality or factual accuracy.

</details>

## Quality checks and frozen evaluation fixtures

<details>

- `evals/v3/` — current frozen cases, five fixtures, and their manifest.
- `evals/cases.json`, `evals/fixtures/`, `evals/manifest.json` — preserved historical v2.
- `evals/suite.py` — integrity checks and a wrapper for the real answer pipeline.

V3 changes only the reviewed public corpus: the approved patient passage and provider boundary correction.
All 12 questions, expectations, thresholds, and adversarial fixtures are unchanged.

After activation, run from the project folder on either platform:

```text
python -m evals.suite
```

This checks the 12-case specification, frozen file hashes, and five fixture workspaces—not whether all 12 answers pass.
Fixture approvals use a synthetic reviewer and temporary storage, never the real approval file.
Changes to frozen expectations or fixture content need review and a new version; do not silently refresh hashes.

Run these commands on either OS after activation:

```text
python -m evals.run --baseline reports/baseline-extractive-v3.json
python -m scripts.quality_gate
python -m scripts.quality_gate --demonstrate
```

The v3 evaluator and full gate exit **0**: 12/12, Source Recall@3 **7/7**, and citation validity/structural coverage **15/15**.
Factual support is unmeasured with **0/15** claims human-reviewed per mode.
`--demonstrate` runs the full model-free gate three times: clean **0**, in-memory missing approvals **1**, repaired **0**.
It neither edits real approvals nor alters frozen fixtures.
The separate v3 baseline records the approved corpus update, not a same-corpus comparison with v2.
Historical v2 still returns 10/12 and exit 1: `python -m evals.run --version v2 --baseline reports/baseline-extractive-v2.json`.
Reports identify code, corpus, dataset and mode; `reports/README.md` explains review and comparison.
Raw outputs stay in Git-ignored, report-specific files under `reports/local/`.

Optional Promptfoo requires Node 24 LTS.
After explicitly choosing to install its pinned package, run from the repository root on either OS:

```text
npm ci --ignore-scripts --prefix evals
python -m scripts.run_promptfoo
python -m scripts.run_promptfoo --negative-control
python -m scripts.run_promptfoo --suite
```

Verified on Windows, including a clean checkout: smoke exit **0**, deliberate negative-control exit **100**, full v3 suite **12/12**, exit **0**.
The locked install also succeeded offline from the local npm cache, with install scripts disabled; no model or browser payload is needed for these checks.
Npm still labels several packages extraneous after a clean locked install; the checks pass without pruning or changing the lock.
The launcher never downloads packages automatically and disables telemetry/update checks.
No hosted model, paid judge, report upload or hosted CI is configured.

</details>

## Human citation-support review

<details>

Open **Quality**, select `reports/final-extractive-v3.json` or `reports/live-selection-4b-v3.json`, then expand **Review recorded citation support**.
Read each claim beside its cited passage and source link, keeping synthetic cases separate from public evidence.
Choose **Supported** or **Not supported**, enter your reviewer name, confirm your own review, and prepare/download the review file.
All 15 claims start **Unreviewed**; content approval does not fill these decisions.
On a fresh checkout, first run the evaluator, then select `reports/local/latest.json` to review your newly recorded outputs; historical raw artifacts are not shipped.

Save the downloaded file as `reports/local/citation-review.json` and rerun the same mode/version with a new report path:

```text
python -m evals.run --reviews reports/local/citation-review.json --output reports/reviewed-extractive-v3.json
```

For the live report, also supply `--mode live-model --model qwen3:4b` with the project server running.
Review is bound to exact output hashes; changed outputs are rejected instead of inheriting approval.
Refresh Quality and select the new report under `reports/`.
It is separate from the immutable original, and no content approval is changed.

</details>

## Fingerprint changes reasoning

<details>

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

## Approval reasoning

<details>

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
Expand **Current saved document and approval—not the proposal** to manage the real document.
**Approve current saved version only** does not apply or approve simulated changes.
**Remove saved version from answers** returns the topic to draft.
If a topic or referenced fact changes during review, reload before approving.
Nik approved the exact revisions now in `content/patient-unpaid-orders.md` and `content/provider-migration-checklist.md`.
Their matching fingerprints are recorded in `data/approvals.json`.
The separately approved v3 evaluation corpus incorporates those revisions; frozen v2, its expectations, thresholds, and baseline remain intact.

</details>

## Date-aware passage selection

<details>

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
The provider migration and patient-payment topics are eligible; other topics remain ineligible.
Patient guidance includes the provider-not-transferred condition and applies through December 23, with no invented cutoff hour.
The v3 corpus fixes the former Q02/Q05 gaps through reviewed content changes, not relaxed checks.
Instruction-like lines are filtered from excerpt guidance after retrieval, with raw text available only in labelled inspection.
This narrow rule is not general prompt-injection protection.

</details>

</details>
