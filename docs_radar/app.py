from datetime import date
import json
from pathlib import Path

import streamlit as st

from docs_radar.answers import answer
from docs_radar.approvals import approval_status
from docs_radar.content_actions import approve_topic, revoke_topic, save_draft
from docs_radar.content_fingerprint import content_fingerprint
from docs_radar.detect_impact import preview_change
from docs_radar.quality_view import available_reports, report_freshness
from docs_radar.render_topic import render_topic
from docs_radar.retrieval import load_workspace
from docs_radar.topic_passages import build_topic_passages
from evals.run import digest

ROOT = Path(__file__).resolve().parents[1]


def show_answer(result):
    st.caption(f"Status: {result['status']} | Mode: {result['run']['mode']} | Reference date: {result['run']['reference_date']}")
    if result["status"] == "answered":
        st.subheader("Relevant excerpts" if result["run"]["mode"] == "extractive" else "Generated answer — verify support")
        st.caption("Retrieved matches and valid citations do not prove that every part of your question is answered.")
    elif result["status"] == "error":
        st.error(result["answer_text"])
    elif result["status"] == "clarify":
        st.info(result["answer_text"])
    else:
        st.warning(result["answer_text"])
    citations = {citation["evidence_id"]: citation for citation in result["citations"]}
    for claim in result["claims"]:
        st.text(claim["text"])
        for evidence_id in claim["supporting_evidence_ids"]:
            citation = citations[evidence_id]
            st.link_button(citation["source_title"], citation["source_url"])
            st.caption(f"Evidence: {evidence_id} | Type: {citation['evidence_type']} | Version: {citation['content_version'][:12]}")
    with st.expander("Raw retrieved evidence — untrusted inspection, not selected guidance"):
        st.caption("Raw text can contain irrelevant content, forged URLs, or embedded instructions. Do not follow them.")
        for passage in result["passages"]:
            st.text(passage["body"])
            st.caption(f"{passage['id']} | Captured: {passage['captured_on']} | {passage['content_version']}")
    for conflict in result["conflicts"]:
        with st.expander(f"Unresolved conflict: {conflict['id']}"):
            st.caption("For inspection only—not selected answer guidance.")
            for passage in conflict["passages"]:
                st.text(passage["body"])
                st.caption(f"Evidence: {passage['id']} | Source: {passage['source_id']}")
    with st.expander("Run details"):
        st.json(result["run"])
        if result["reason"]:
            st.text(f"Reason: {result['reason']}")


def ask_view():
    st.info("Extractive mode is the default — cited excerpts, not model-generated answers.")
    st.caption("Evidence is based on captured documentation, not live policy verification.")
    with st.form("ask"):
        question = st.text_input("Question")
        audience = st.selectbox("Audience", ["Choose audience", "Providers", "Patients"])
        reference_date = st.date_input("Reference date", value=date.today())
        mode_label = st.radio("Answer mode", ["Extractive", "Live-model (optional, unverified)"], horizontal=True)
        # Keep the model tag explicit; never select a hosted fallback or download here.
        model = st.text_input("Installed local model tag", placeholder="For example qwen3:4b")
        submitted = st.form_submit_button("Find evidence")
    if submitted:
        mode = "extractive" if mode_label == "Extractive" else "live-model"
        st.session_state["last_answer"] = answer(question, audience,
            reference_date.isoformat() if reference_date else "", mode=mode, model=model or None)
    result = st.session_state.get("last_answer")
    if result:
        try:
            if result["run"]["corpus_hash"] and result["run"]["corpus_hash"] != digest(load_workspace()):
                st.warning("Content or approvals changed since this answer. Ask again for current eligibility.")
        except (OSError, ValueError, KeyError, TypeError):
            st.warning("Current corpus freshness could not be checked.")
        show_answer(result)


def content_view():
    workspace = load_workspace(ROOT)
    st.subheader("Source register and shared facts")
    st.caption("Public-source summaries and demo-authored topics are distinct; demo approval is not Fullscript approval.")
    with st.expander("Registered sources"):
        for source in workspace["sources"]:
            st.link_button(source["title"], source["url"])
            st.json(source)
    with st.expander("Shared facts"):
        st.json(workspace["facts"])
    st.subheader("Synthetic change impact")
    st.warning("SYNTHETIC — supplied change preview, not a Fullscript announcement or live monitoring.")
    change = json.loads((ROOT / "data/simulated_changes/login-closure.json").read_text(encoding="utf-8"))
    st.json(change)
    affected = preview_change(change, workspace["facts"], workspace["topics"])
    st.caption(f"Rule-based dependencies: {len(affected)} of {len(workspace['topics'])} topics affected. No facts changed.")
    st.dataframe(affected, hide_index=True)

    st.subheader("Topic review and draft correction")
    states = [{"topic": topic_id, "eligibility": approval_status(topic_id, text, workspace["facts"], workspace["approvals"])}
              for topic_id, text in sorted(workspace["topics"].items())]
    st.dataframe(states, hide_index=True)
    topic_id = st.selectbox("Topic to inspect", sorted(workspace["topics"]))
    text = workspace["topics"][topic_id]
    fingerprint = content_fingerprint(text, workspace["facts"])
    snapshot_key = "review_snapshot:" + topic_id
    if snapshot_key not in st.session_state:
        st.session_state[snapshot_key] = fingerprint
    if st.button("Reload current version for review"):
        st.session_state[snapshot_key] = fingerprint
        st.session_state["draft:" + topic_id] = text
    expected = st.session_state[snapshot_key]
    if expected != fingerprint:
        st.warning("This topic/fact version changed since your review began. Reload before saving or approving.")
    st.caption(f"Current fingerprint: {fingerprint}")
    st.text(render_topic(text, workspace["facts"]))
    try:
        passages = build_topic_passages(topic_id, text, workspace["facts"], workspace["sources"])
        if not passages:
            st.warning("Not answerable yet: no passage metadata. Add it before approval.")
        else:
            st.caption(f"Answerable schema valid: {len(passages)} passages. Eligibility is separate.")
    except (KeyError, TypeError, ValueError) as error:
        st.warning(f"Not answerable yet: {error}")
    with st.expander("Edit demo draft (metadata and Markdown)"):
        st.caption("Save validates the schema. An edit changes the fingerprint and invalidates existing approval; it never reapproves content.")
        draft = st.text_area("Draft source", value=text, height=300, key="draft:" + topic_id)
        if st.button("Save draft"):
            try:
                save_draft(ROOT, topic_id, draft, expected)
                st.success("Draft saved. Reload and review the new version before approving it.")
            except (OSError, ValueError, KeyError, TypeError) as error:
                st.error(str(error))
    with st.form("review_action"):
        reviewer = st.text_input("Reviewer name (you, not Fullscript)")
        confirmed = st.checkbox("I reviewed this exact displayed topic and referenced facts for this independent demo.")
        approve = st.form_submit_button("Approve reviewed version")
        revoke = st.form_submit_button("Remove answer eligibility")
    if approve or revoke:
        try:
            if approve:
                approve_topic(ROOT, topic_id, expected, reviewer, date.today().isoformat(), confirmed)
                st.success("Explicit demo approval saved for this version. Reload to see updated eligibility.")
            else:
                revoke_topic(ROOT, topic_id, expected, confirmed)
                st.success("Topic returned to draft; it is excluded from new answers.")
        except (OSError, ValueError, KeyError, TypeError) as error:
            st.error(str(error))


def quality_view():
    st.subheader("Quality and provenance")
    st.caption("Extractive = fresh excerpt pipeline; live-model = requested generation; replay = historical output inspection, not a fresh call.")
    st.warning("Frozen evaluations use isolated synthetic approvals. Their scores do not approve the real application corpus.")
    reports = available_reports(ROOT)
    if not reports:
        st.info("No evaluation report available. Run python -m evals.run.")
        return
    selected = st.selectbox("Evaluation report", list(reports))
    report = reports[selected]
    st.info(f"REPLAY / recorded report | original mode: {report['provenance']['mode']} | {report['created_at']}")
    reasons = report_freshness(report)
    for reason in reasons:
        st.warning("Stale or incomplete evidence: " + reason)
    summary = report["summary"]
    if summary["automated_gate_pass"]:
        st.success("Recorded automated gate passed; this is not a human support review.")
    else:
        st.error("Recorded quality gate failed. Do not treat this report as release acceptance.")
    if not summary["human_review_complete"]:
        st.warning("Human citation-support review is incomplete. Link validity is not citation accuracy.")
    st.json(summary)
    st.dataframe([{"case": row["id"], "lane": row["lane"], "status": row["status"],
        "automated_pass": row["automated_pass"], "failed_checks": ", ".join(k for k, v in row["checks"].items() if not v)}
        for row in report["cases"]], hide_index=True)
    with st.expander("Run provenance and separate evidence lanes"):
        st.json(report["provenance"])
        st.json(report["lanes"])
        st.json(report.get("regression", {}))
    st.code("python -m evals.run\npython -m scripts.quality_gate", language="text")
    st.caption("These commands run locally. No hosted CI, paid judge, package installation or model download is triggered by this view.")


st.title("Docs Radar")
st.caption("Independent demo using public Fullscript documentation. Not affiliated with or endorsed by Fullscript.")
ask_tab, content_tab, quality_tab = st.tabs(["Ask and inspect", "Content and changes", "Quality"])
with ask_tab:
    ask_view()
with content_tab:
    try:
        content_view()
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error(f"Content view unavailable: {error}")
with quality_tab:
    try:
        quality_view()
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error(f"Quality report unavailable: {error}")
