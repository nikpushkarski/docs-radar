# Fullscript Docs Radar — Implementation Plan

**Owner:** Nik Pushkarski  
**Prepared:** November 1, 2026  
**Target:** First screening on Wednesday, November 4, 2026, based on the interview timing discussed.  
**Status:** Planning only. No application, evaluations, or results have been implemented by creating this document.  
**Companion:** `AGENTS.md` governs how Codex teaches and implements this plan.

## 1. The project in one paragraph

Build a small documentation-quality workbench using selected public Fullscript support material. Demonstrate one complete story: a product change affects several articles; the system identifies the dependencies; a writer proposes and reviews a correction; an assistant answers from eligible content with citations; regression checks detect a deliberately introduced mistake. The main deliverable is evidence of editorial judgment, supported by working software—not a chatbot with a long tool list.

**Budget rule:** No additional paid services, subscriptions, API usage, or hardware purchases without Nik's explicit approval. Local operation is the default. A hosted application is not required.

## 2. Why this fits the role

The advertised position emphasizes support-content ownership, information architecture, reusable facts, release impact, AI-ready topics, governance, and effectiveness measurement. It also remains a hands-on writing role. [1]

| Evidence in the demo | What it demonstrates |
| --- | --- |
| A small content schema and controlled vocabulary | Information architecture and audience-aware content |
| One shared fact used in two articles | Single-sourcing rather than duplicated maintenance |
| An affected-article queue with reasons and owners | Release impact assessment |
| A before/after article and review history | Writing, editorial decisions, and governance |
| Grounded answers and a fixed evaluation set | AI readiness and quality assurance |
| A measurement specification with honest limitations | Outcome-oriented thinking |

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
3. **Quality:** Evaluation results, failures, run provenance, and unmeasured business outcomes.

### Keep these even when simplifying

One release scenario; one shared fact; one dependency-based impact alert; one substantial writing sample; approval-aware retrieval; traceable citations; a fixed test set; and a demonstrated failing-then-passing quality gate.

### Cut these first

Hosting, visual polish, extra articles, feedback instrumentation, semantic embeddings, and automated claim extraction. Do not add authentication, multi-agent orchestration, a full CMS, OAuth, a vector database, or live patient data.

**Hardware fallback:** If a local model is impractical, ship an explicitly labelled extractive evidence assistant. Continue testing retrieval, governance, citations, and CI. Do not describe extractive output, mocks, or recordings as live generative AI. A working LangChain-to-model integration remains an unfinished feature until actually run.

## 5. Architecture and technology

```text
Public source register ──> reviewed content + versioned shared facts
                                      │
Release change ──> fact dependencies ──┴──> affected-article review queue
                                                    │
                                  writer's revision + human approval
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
| Review | Content ID and hash, state, reviewer, review date, decision, reason, unresolved questions |
| Release/change | ID, effective date, changed fact IDs, evidence, affected audiences |
| Evaluation case | ID, question, audience, reference date, optional migration state, expected behavior, gold source IDs, criticality |

Review states: `captured → draft → demo_approved → deprecated → archived`. A source can remain available for audit without being eligible to answer a question.

Approval is tied to an exact content hash. Editing approved content invalidates approval. Unknown audience/region applicability must not silently become universal. Validity dates and capture dates are separate fields; use date-level examples rather than inventing an unspecified cutover time.

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

Every task has one observable outcome. Codex should subdivide any task that feels too large rather than hand over this whole queue. Dependencies follow numerical order unless a fallback is explicitly recorded.

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

#### T08 — Write the correction yourself

**Learn:** A strong support topic answers a specific reader question without losing important conditions.  
**Do:** Rewrite one selected passage as a short standalone answer. Include audience, date, next action, and evidence.  
**Done:** A before/after comparison explains the editorial choices and remaining SME questions. This is a proposed demo revision, not an approved Fullscript correction.

#### T09 — Add the approval boundary

**Learn:** A draft should not become answerable merely because it exists.  
**Do:** Persist a review decision tied to the content hash; reject unapproved or superseded versions in the answer corpus.  
**Done:** A draft is excluded, approval admits it, and a later edit invalidates that approval.

#### T10 — Retrieve the right sources

**Learn:** Retrieval chooses evidence; generation writes from it.  
**Do:** Filter by approval and applicable metadata, then rank eligible content lexically. Return the top three distinct source IDs with their relevant passages.  
**Done:** A known question retrieves its expected source; an ineligible source cannot appear. Empty or conflicting evidence is represented explicitly.

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

### Demonstration and handoff

#### T19 — Assemble the three views

**Learn:** The interface should expose the editorial story, not hide it.  
**Do:** Connect the content/change view, answer/evidence view, and evaluation view. Add obvious badges for extractive, live-model, replay, and synthetic modes.  
**Done:** One scenario can be followed from source change to review to answer to test result without editing code during the demonstration.

#### T20 — Add measurement hooks, only if the core works

**Learn:** Product instrumentation is not proof of a business outcome.  
**Do:** Log synthetic `answer_shown`, `helpful_yes`, `helpful_no`, and `support_link_clicked` events locally. Use case IDs rather than storing personal questions.  
**Done:** The dashboard displays event counts and labels ticket deflection “not measured.” This task is optional before the interview.

#### T21 — Package the demonstration

**Learn:** Reproducibility makes a small project credible.  
**Do:** Write a short README covering setup, one command per check, limitations, provenance, and a two-minute walkthrough. Record the working scenario and retain screenshots/reports as a backup.  
**Done:** The project can be demonstrated without depending on a fresh external API call or public hosting.

#### T22 — Rehearse and freeze scope

**Learn:** The explanation should be about the role, not the libraries.  
**Do:** Explain the problem, the writing decision, the guardrail, and the evidence. Name what is simulated, unmeasured, or unfinished.  
**Done:** Nik can explain every claimed capability and offer a concise demo without assuming the recruiter wants a technical walkthrough.

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

### Business measurement: no invented deflection rate

This project can implement instrumentation and a measurement plan, not establish actual support-ticket deflection without production users and linked ticket data.

A future controlled comparison could estimate relative ticket-rate reduction as:

```text
(control contact rate - assisted contact rate) / control contact rate
```

Define eligible sessions, topic, observation window, and linked ticket outcomes in advance; a zero control rate makes that ratio undefined. Feedback and support-link clicks are useful signals, not equivalent to ticket creation or causal deflection. Report no production percentage for this demo.

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
data/                   # source register, facts, releases, reviews
evals/                  # fixed cases, Python provider, assertions, two mode configs
tests/                  # fixtures and unit/integration tests
reports/                # small, attributable evaluation outputs
.github/workflows/      # quality checks, once repository use is approved
```

Keep private snapshots, credentials, virtual environments, model weights, and sensitive logs out of Git. Lock working Python and Node dependencies. The README must contain tested commands for the user's actual shell; do not prescribe Bash syntax to a Windows cmd session.

## 10. Interview story and completion checklist

Suggested opening:

> I built an independent proof of concept around a documentation transition. It connects shared facts to affected articles, keeps unreviewed content out of answers, and tests whether changes break retrieval or citations. The public sources are attributed; the injected regression is simulated.

Then show: one dependency alert → one writer-reviewed revision → one cited answer → one failing and repaired check.

Before claiming completion, verify:

- [ ] The writing sample is substantial enough to discuss, not just an AI-generated draft.
- [ ] Approval, source attribution, audience, and date behavior are demonstrated.
- [ ] The same runtime functions serve the UI and evaluations.
- [ ] Measured results identify the exact run; unrun checks remain unrun.
- [ ] Any LangChain/local-model claim is backed by an actual successful execution.
- [ ] No confidential material, real patient data, fabricated approvals, or invented business impact appears.
- [ ] The README and recording distinguish real, synthetic, replayed, and planned capabilities.

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
