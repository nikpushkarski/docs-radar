# Fullscript Docs Radar — Implementation Plan

**Owner:** Nik Pushkarski
**Prepared:** November 1, 2026
**Target:** A working local app with change-impact detection and evidence-grounded answers.
**Status:** T01–T08 implemented at their recorded scope; see `PROGRESS.md` for actual checks and limitations.

**Companion:** `AGENTS.md` governs how Codex teaches and implements this plan.

## 1. The project in one paragraph

Build a local app using selected public Fullscript support material for two functions:

1. Identify which topics need updating when a tracked fact changes.
2. Retrieve eligible evidence and answer freeform questions with citations, or abstain when the evidence is insufficient.

Validation, content eligibility, and evaluations support those functions.
The deliverable is working software, not a writing portfolio or an interview-preparation package.
Initial impact detection uses explicit fact references and supplied change records, including clearly labelled simulations; it is not live website monitoring.

**Budget rule:** No additional paid services, subscriptions, API usage, or hardware purchases without Nik's explicit approval. Local operation is the default. A hosted application is not required.

## 2. Functional scope

| Component | Runtime purpose |
| --- | --- |
| Source register and topic metadata | Trace evidence and filter by applicability |
| Shared facts and topic references | Reuse values and identify dependencies |
| Impact report | List affected topics and the changed facts that caused the alert |
| Machine-readable approval record | Restrict answers to the exact reviewed content version |
| Retrieval and answers | Select supporting passages and return cited answers or abstentions |
| Tests and evaluations | Detect invalid content, retrieval errors, and answer regressions |

A prose editorial rationale is not an application dependency.
Writer discussions and revision reasoning can remain outside the app; no Jira-like review documents or separate before/after essays are required.

**Do not claim this is Fullscript's internal technology stack.** LangChain and Promptfoo are our implementation choices. This uses their public content and product context; it is not an integration with private Fullscript systems.

## 3. Case study and evidence boundaries

Use the Rupa-to-Fullscript transition, limited initially to ordering access and account migration.

The published transition schedule states that practitioners become view-only on October 30, 2026, while existing patient-order workflows have separate conditions. It also identifies January 20, 2027 as the login-closure date. These distinctions make a useful audience-and-date test case. [2]

**Correction to the earlier discussion:** The view-only article now shows an October 30, 2026 update and reflects the universal transition. Do not present it as a currently outdated article. [3]

The acquisition FAQ still contains earlier workflow language as of this research. Treat it as a **candidate for contextual review**, not proof of a product defect or a failure by Fullscript's team. [4]

Use two clearly separated datasets:

- **Verified snapshot:** Captured, dated public evidence plus our own attributed summaries and proposed rewrites.
- **Simulated regression:** A deliberately altered local copy, visibly labelled synthetic. Use it to demonstrate a reliable failure-and-fix sequence. It is not an alleged historical Fullscript version.

A page's modification date is not proof that every statement supersedes another page. Record a specific evidence-backed supersession decision or leave the conflict unresolved.

### Corpus size and publication

Start with **three sources**: the transition schedule, view-only article, and acquisition FAQ. Expand to six only after the full workflow works. Eight is the ceiling before the interview.

Keep source URLs, retrieval dates, selected passage identifiers, and checksums. Prefer original paraphrases and small necessary excerpts. Do not publish a scraped copy of the Support Center or any confidential material. Keep fuller working snapshots local and excluded from Git where appropriate; public tests must remain reproducible using distributable fixtures.

“Approved” always means **reviewed for this independent demo by Nik**, not approved by Fullscript. Public availability and internal editorial approval are different concepts.

## 4. Scope and stopping rules

### Target deliverable

A local Streamlit app with three views:

1. **Content and changes:** Source register, shared facts, affected articles, draft correction, and review state.
2. **Ask and inspect:** Question, audience, reference date, answer, and the exact supporting passages.
3. **Quality:** Evaluation results, failures, and run provenance for the actual pipeline.

### Keep these even when simplifying

One change scenario; one shared fact; one dependency-based impact report; usable source-backed topics; approval-aware retrieval; traceable citations; a fixed test set; and a demonstrated failing-then-passing quality gate.

### Scope gate for every next step

Before assigning work, identify the runtime behavior, test, or essential setup instruction it enables.
If it enables none of those, do not make it a task or a prerequisite.
Do not reintroduce optional presentation work without Nik explicitly requesting it.
Existing Git history is sufficient for examining earlier content; no separate editorial review files are required.

### Out of scope unless explicitly requested

Editorial-rationale documents, portfolio writing samples, interview rehearsals, pitch scripts, demo recordings, screenshots for presentation, feedback instrumentation, and business-measurement specifications.
Evaluation reports remain in scope because they record actual pipeline results, not promotional claims.

Also exclude hosting, visual polish, extra articles before the core works, semantic embeddings, and automated claim extraction.
Do not add authentication, multi-agent orchestration, a full CMS, OAuth, a vector database, or live patient data.

**Hardware fallback:** If a local model is impractical, ship an explicitly labelled extractive evidence assistant. Continue testing retrieval, governance, citations, and CI. Do not describe extractive output, mocks, or recordings as live generative AI. A working LangChain-to-model integration remains an unfinished feature until actually run.

## 5. Architecture and technology

```text
Public source register ──> reviewed content + versioned shared facts
                                      │
Release change ──> fact dependencies ──┴──> affected-article review queue
                                                    │
                                  topic update + eligibility approval
                                                    │
Question + audience + date ──> eligible-content filter ──> retrieval
                                                             │
                              ┌──────────────────────────────┴────────────┐
                              │                                           │
                     Extractive answer                         LangChain + local model
                              │                                           │
                              └──────────> answer + evidence <────────────┘
                                                  │
                                    Promptfoo + custom checks
                                                  │
                       offline CI gates / separate live-model report
```

| Layer | Choice and reason |
| --- | --- |
| Interface | Streamlit: one local Python application |
| Content | Markdown and JSON: inspectable, versionable, no database service |
| Validation | Python tests and a small explicit schema |
| Retrieval | Local lexical ranking, initially TF-IDF; no embedding API |
| Orchestration | LangChain components around our actual retrieval and answer functions |
| Generative answers | `ChatOllama` through `langchain-ollama`; local model selected after a hardware check [5] |
| Evaluations | Promptfoo calling the same Python pipeline through a custom provider; custom Python assertions [6][7] |
| Automation | GitHub Actions on a standard Linux runner; model-free checks by default [8] |

Use existing compatible Python where possible. Install Promptfoo locally and lock its version; verify its current Node requirement before installation. Current documentation recommends Node 24 LTS. [9] Do not build a separate HTTP service merely to connect Promptfoo.

### Cost safeguards

Local generation avoids a metered cloud-model dependency, but performance depends on the machine. No model tag is selected yet. Check RAM, available GPU memory, disk space, model download size, and licence before choosing one.

Standard GitHub-hosted runners in public repositories are free; larger runners are not. Private-repository compute and storage allowances need checking. [8] Publishing a repository is a separate decision requiring Nik's approval. Until then, run the same checks locally; do not change repository visibility to obtain free compute.

Do not rely on assumed promotional API credits or unlimited Codex access. Use existing access within its actual allowance. Keep hosted tracing, paid judges, cloud fallback, public report sharing, and automatic top-ups off. Electricity, downloads, and existing subscriptions are not new service fees, but are not literally costless resources.

## 6. Minimal data contracts

Implement only fields needed for this scenario; add complexity when a test requires it.

| Record | Required information |
| --- | --- |
| Source | Stable ID, title, URL, captured date, published/modified date if available, evidence type, content hash |
| Topic/passage | Stable ID, source ID, content version, audience, region or `unknown`, topic, body, fact references |
| Fact | Stable ID, value, version, applicable audience/conditions, effective interval, supporting passage, supersession relation when established |
| Approval | Content ID, hash covering topic and referenced fact values/versions, state, reviewer, approval date |
| Release/change | ID, effective date, changed fact IDs, evidence, affected audiences |
| Evaluation case | ID, question, audience, reference date, optional migration state, expected behavior, gold source IDs, criticality |

Review states: `captured → draft → demo_approved → deprecated → archived`. A source can remain available for audit without being eligible to answer a question.

Approval is a machine-readable eligibility record, not a prose review note.
Its hash must cover the topic and the referenced fact values/versions used to render it.
Editing either invalidates approval.
Unknown audience/region applicability must not silently become universal.
Validity dates and capture dates are separate fields; use date-level examples rather than inventing an unspecified cutover time.

A shared fact must actually render into at least two demo-authored topics. A manually curated `fact_id → article_ids` dependency map is enough for impact detection; label it rule-based, not semantic AI detection.

The answer function should return structured output containing:

```text
status: answered | clarify | abstain | error
answer_text
claims: [{text, supporting_evidence_ids}]
citations: [{evidence_id, source_id, source_url, content_version, evidence_type}]
retrieved_source_ids
run: {mode, corpus_hash, prompt_hash, model_id_or_none, reference_date}
```

Resolve citation links from the source register, not from model-invented URLs. Display whether evidence is a public excerpt or our demo rewrite. A valid link alone does not prove that a claim is supported.

## 7. Build queue: one task per interaction

There are 20 active tasks.
Existing IDs are preserved for progress history; T20 (feedback instrumentation) and T22 (interview rehearsal) have been removed from scope, not completed.
Every task must enable runtime behavior, a verification check, or essential reproducibility.
Subdivide tasks when needed, but do not add editorial exercises or presentation artifacts as prerequisites.
Dependencies follow numerical order unless a fallback is explicitly recorded.

### Foundation and evidence

#### T01 — Check the workspace

**Learn:** The coding assistant and the application's model are different tools.
**Do:** Inspect the repository, active shell, Python/Node/Git availability, and local model feasibility. Record constraints in `PROGRESS.md`.
**Done:** We know which commands work and whether local generation is plausible. Nothing paid, published, or downloaded without permission.

#### T02 — Run the smallest application

**Learn:** A running shell provides a checkpoint before any AI complexity.
**Do:** Create a minimal Streamlit page with the project name and an independent-demo notice. Add one smoke test.
**Done:** The page opens locally and the test passes.

#### T03 — Register three sources

**Learn:** Provenance lets another person check a claim.
**Do:** Capture the three starter references and write short, attributed summaries with IDs and dates.
**Done:** Each summary can be traced to a currently checked source. The synthetic dataset is separate.

#### T04 — Write the first three questions

**Learn:** Expected behavior should exist before a model starts answering.
**Do:** Write one practitioner question, one patient question, and one unsupported question. Record the required distinctions and evidence.
**Done:** A human can explain what a correct answer must include or why it should abstain.

### Documentation operations

#### T05 — Validate one content record

**Learn:** Metadata makes routing and governance executable.
**Do:** Implement the smallest content schema and validate one record. Add one intentionally invalid fixture.
**Done:** Valid data passes; missing provenance or invalid review state fails with a useful message.

#### T06 — Reuse one fact

**Learn:** Single-sourcing removes repeated maintenance.
**Do:** Store one evidenced fact once and reference it in two demo-authored topics. Render both.
**Done:** Changing its version updates both rendered topics without manual duplication.

#### T07 — Detect an affected article

**Learn:** A release impact report explains dependencies, not just text differences.
**Do:** Apply one simulated fact change and list dependent articles with a reason, audience, suggested reviewer role, and open question.
**Done:** All known dependents are flagged; an unrelated article is not.

#### T08 — Prepare one answerable topic

**Learn:** Retrieved content must preserve the conditions needed for a correct answer.
**Do:** Make one source-backed topic usable by the answer pipeline: include audience, relevant dates, next action, source attribution, and demo-authored labelling.
Retain shared fact references and verify the rendered result.
**Done:** The topic renders with the supported ordering and transfer guidance, distinguishes recommendations from hard cutoffs, and identifies its evidence.
No editorial-rationale file, before/after essay, or standalone writing sample is required.
This remains a proposed demo topic, not a Fullscript-approved correction.

#### T09 — Add the approval boundary

**Learn:** A draft should not become answerable merely because it exists.
**Do:** Persist a minimal approval record covering the topic and referenced fact values/versions; reject unapproved or superseded versions in the answer corpus.
This is runtime eligibility data, not a narrative review document.
**Done:** A draft is excluded, approval admits the exact reviewed version, and a later topic or referenced-fact edit invalidates that approval.

#### T10 — Retrieve the right sources

**Learn:** Retrieval chooses evidence; generation writes from it.
**Do:** Filter approved passages by audience and reference date, then rank applicable content lexically.
The application defaults to today's date and records the resolved date; tests supply explicit dates.
Use passage-level intervals with inclusive starts and exclusive ends rather than expiring an entire topic when one recommendation passes its date.
Keep supported instructions available between the recommended transfer date and final closure; do not invent post-closure recovery procedures.
Include passage routing metadata in approval fingerprints before connecting the filter to retrieval.
Return the top three distinct source IDs with their relevant passages.
**Done:** A known question retrieves its expected source; unapproved or inapplicable passages cannot appear.
Boundary tests cover December 3/4 and January 19/20, with appropriate guidance on either side and no assumption of access on the closure date.
Empty or conflicting evidence is represented explicitly.
Routing fixtures alone do not establish answer quality or live verification.

### Answers and the local model

#### T11 — Answer without a model first

**Learn:** A useful evidence interface can exist before generative AI.
**Do:** Show retrieved passages with registered citations and clear extractive-mode labelling. Add clarification/abstention for the defined unsupported cases.
**Done:** The app never fabricates a source or pretends that excerpts are newly generated prose.

#### T12 — Freeze the regression set

**Learn:** A stable test set makes before/after comparisons meaningful.
**Do:** Expand to 12 cases, including role differences, date boundaries, missing context, draft exclusion, a conflicting source, a forged citation, and an instruction embedded in retrieved text. Version the cases and expected evidence.
**Done:** Expectations are human-reviewed and hidden from the answering pipeline.

#### T13 — Run one local-model smoke test

**Learn:** Model capability and speed are empirical, not assumed.
**Do:** With approval, install/download an appropriate local model and test one short grounded response. Record the exact model and settings.
**Done:** A real response is produced locally, or the extractive fallback is recorded without purchasing a workaround.

#### T14 — Connect LangChain

**Learn:** The chain composes retrieval, context, prompt, model, and parsing.
**Do:** Connect our retriever to the local model and return the structured answer contract. Treat retrieved text as data, not instructions.
**Done:** One answer is grounded in approved evidence; malformed output, missing evidence, and model unavailability produce explicit states rather than silent fallback.

### Evaluation and automation

#### T15 — Call the application from Promptfoo

**Learn:** Evaluation must exercise the real pipeline, not a second imitation.
**Do:** Add a Python provider that calls our answer function and supplies only runtime inputs. Run one passing and one deliberately failing case. [6]
**Done:** Promptfoo receives real pipeline outputs. Gold answers and expected citations are used only by assertions.

#### T16 — Calculate the metrics

**Learn:** Retrieval, citation validity, and factual support are different measurements.
**Do:** Implement the metrics and thresholds in Section 8, with small unit tests for denominators and empty cases. Add a manual citation-support review field.
**Done:** A missing relevant source, forged citation, and unsupported factual claim are not all collapsed into one vague quality score.

#### T17 — Make the quality gate fail and recover

**Learn:** A gate matters only when a regression can stop the check.
**Do:** Run validation, retrieval tests, and model-free Promptfoo checks in CI when an approved repository setup permits it; otherwise verify the same gate locally. Inject a regression, observe failure, repair it, and rerun. [9]
**Done:** Exit codes and reports demonstrate both states. No skipped live-model tests are reported as passes.

#### T18 — Record live-model evidence

**Learn:** Offline CI does not establish live-model answer quality.
**Do:** Run all 12 cases locally against the actual model, inspect citations, and save a report with corpus, prompt, test-set, code, and model identifiers.
**Done:** The report separates automated checks from human review. Missing or stale live-model evidence remains visibly incomplete.

### Interface and reproducibility

#### T19 — Assemble the three views

**Learn:** The interface exposes the app's behavior and evidence.
**Do:** Connect the content/change view, answer/evidence view, and evaluation view.
Add obvious badges for extractive, live-model, replay, and synthetic modes.
**Done:** Users can inspect an impact report, manage content eligibility, ask a question, and inspect the answer evidence and test results without editing code.

#### T21 — Document setup and checks

**Learn:** Setup instructions must reproduce the working application.
**Do:** Keep a short README with setup, run/test commands, provenance, and current limitations.
Verify the documented commands on available platforms and label untested platforms honestly.
**Done:** The app and its checks can be run from the documented instructions without a paid service or public hosting.
No recording, slide deck, screenshots, or rehearsal is required.

## 8. Evaluation specification

### Fixed set

Use 12 cases, not a growing collection selected to flatter the system. Include answerable, conditional, ambiguous, unsupported, and adversarial cases. For historical questions, use only dates backed by captured evidence or explicitly labelled synthetic fixtures. Do not reconstruct earlier product behavior from a current article without evidence.

### Metrics and initial project thresholds

These are chosen acceptance criteria for this demo, not Fullscript standards or achieved results.

| Metric | Definition | Gate or reporting rule |
| --- | --- | --- |
| Source Recall@3 | For each answerable case: relevant gold source IDs found among the first three distinct retrieved sources, divided by all gold source IDs | Mean at least 0.90; report numerator/denominator per case |
| Citation validity | References resolve to eligible, retrieved evidence in the recorded content version | 100%; a required missing citation fails |
| Citation accuracy | Human-reviewed cited factual claims actually supported by their cited passages, divided by cited factual claims reviewed | 100% for reviewed demo answers; report review coverage separately |
| Citation coverage | Factual claims requiring evidence that have citations, divided by factual claims requiring evidence | 100% for the reviewed demonstration set |
| Critical behavior | Correct handling of predefined audience/date conditions, unapproved evidence, unsupported requests, and injected instructions | All critical cases pass |
| Regression | Same dataset, corpus, mode, and configuration compared with a recorded baseline | No newly failing critical cases; do not silently rewrite the baseline |

Source Recall@3 is deliberately source-level, not chunk-level. Cases with no relevant source are excluded from its mean and evaluated for abstention instead. Empty denominators are `N/A`, not an automatic perfect score. An empty evaluation run is a failed gate.

For free-text answers, deterministic assertions can verify selected dates, structured fields, evidence IDs, and forbidden claims. They do **not** establish general semantic entailment. Do not relabel citation validity as citation accuracy or use a paid LLM judge by default.

### Two execution lanes

**Offline CI:** Run schema checks, approval and expiry logic, retrieval against fixtures, citation validation, extractive outputs, and Promptfoo assertions. An optional replay checks stored model outputs but is labelled replay. It does not test a fresh model call.

**Local live evaluation:** Run the same questions through LangChain and the local model, then review factual support. Save run identifiers and reviewed results. A prompt, corpus, model, or code change invalidates the relevant earlier evidence until rerun. Deterministic settings reduce variability; they do not guarantee identical output.

GitHub-hosted CI cannot reach a model listening only on Nik's laptop. Do not solve this by exposing the laptop, adding secrets, or purchasing hosting. A future self-hosted runner is out of scope for this homework.

### No business-impact claims

Support-ticket deflection is unmeasured.
Business instrumentation and measurement-plan documents are outside this build's scope.
Do not claim production impact from offline tests or synthetic scenarios.

## 9. Proposed repository layout

Create files incrementally, not all at once.

```text
AGENTS.md
IMPLEMENTATION_PLAN.md
PROGRESS.md
README.md
app.py
docs_radar/             # schema, rendering, impact, retrieval, answers, metrics
content/                # demo-authored Markdown topics
data/                   # source register, facts, changes, runtime approvals
evals/                  # fixed cases, Python provider, assertions, two mode configs
tests/                  # fixtures and unit/integration tests
reports/                # small, attributable evaluation outputs
.github/workflows/      # quality checks, once repository use is approved
```

Keep private snapshots, credentials, virtual environments, model weights, and sensitive logs out of Git. Lock working Python and Node dependencies. The README must contain tested commands for the user's actual shell; do not prescribe Bash syntax to a Windows cmd session.

## 10. Functional completion checklist

Before claiming completion, verify:

- [ ] A supplied fact change flags dependent topics and leaves unrelated topics unflagged.
- [ ] Questions retrieve eligible evidence and produce cited answers or explicit clarification/abstention.
- [ ] Approval, source attribution, audience, and date behavior are demonstrated.
- [ ] The same runtime functions serve the UI and evaluations.
- [ ] Measured results identify the exact run; unrun checks remain unrun.
- [ ] Any LangChain/local-model claim is backed by an actual successful execution.
- [ ] No confidential material, real patient data, fabricated approvals, or invented business impact appears.
- [ ] The app, README, and evaluation outputs distinguish real, synthetic, replayed, and planned capabilities.

## References

Public sources checked November 1, 2026. Technical details and public articles may change; recheck when implementing or presenting.

[1] Fullscript, **Senior Technical Writer, Support Documentation**.
https://jobs.lever.co/fullscript/da672c0a-c946-4a6c-a4ed-97aa7ca9bca0

[2] Fullscript, **Rupa closes January 20, 2027: key dates and next steps**; page marked modified October 27, 2026.
https://support.fullscript.com/articles/rupa-closes-january-20-2027-key-dates-and-next-steps

[3] Fullscript, **What it means to be view-only on Rupa**; page marked modified October 30, 2026.
https://support.fullscript.com/articles/what-it-means-to-be-view-only-on-rupa

[4] Fullscript, **Rupa Health Acquisition FAQs**; page marked modified July 17, 2026.
https://support.fullscript.com/articles/rupa-health-acquisition-faqs

[5] LangChain, **ChatOllama integration**.
https://docs.langchain.com/oss/python/integrations/chat/ollama

[6] Promptfoo, **Python provider**.
https://www.promptfoo.dev/docs/providers/python/

[7] Promptfoo, **Python assertions**.
https://www.promptfoo.dev/docs/configuration/expected-outputs/python/

[8] GitHub, **GitHub Actions billing**.
https://docs.github.com/en/billing/concepts/product-billing/github-actions

[9] Promptfoo, **CI/CD integration**.
https://www.promptfoo.dev/docs/integrations/ci-cd/
