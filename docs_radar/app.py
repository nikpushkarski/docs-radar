from datetime import date

import streamlit as st

from docs_radar.answers import answer


st.title("Docs Radar")
st.caption(
    "Independent demo using public Fullscript documentation. "
    "Not affiliated with or endorsed by Fullscript."
)
st.info("Extractive mode — cited excerpts, not model-generated answers.")
st.caption("Evidence is based on captured documentation, not live policy verification.")

with st.form("ask"):
    question = st.text_input("Question")
    audience = st.selectbox("Audience", ["Choose audience", "Providers", "Patients"])
    reference_date = st.date_input("Reference date", value=date.today())
    submitted = st.form_submit_button("Find evidence")

if submitted:
    result = answer(question, audience, reference_date.isoformat() if reference_date else "")
    st.caption(f"Status: {result['status']} | Reference date: {result['run']['reference_date']}")
    if result["status"] == "answered":
        st.subheader("Relevant excerpts")
        st.caption("Text matches are evidence candidates, not proof that every part of your question is answered.")
        citations = {citation["evidence_id"]: citation for citation in result["citations"]}
        passages = {p["id"]: p for p in result["passages"]}
        for claim in result["claims"]:
            evidence_id = claim["supporting_evidence_ids"][0]
            passage = passages[evidence_id]
            citation = citations[evidence_id]
            st.text(claim["text"])
            st.link_button(citation["source_title"], citation["source_url"])
            st.caption(
                f"Evidence: {passage['id']} | Type: {citation['evidence_type']} | "
                f"Captured: {passage['captured_on']}"
            )
    elif result["status"] == "error":
        st.error(result["answer_text"])
    elif result["status"] == "clarify":
        st.info(result["answer_text"])
    else:
        st.warning(result["answer_text"])

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
