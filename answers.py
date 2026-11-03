from datetime import date
import hashlib
import json
import re
from urllib.parse import urlparse

from passage_selection import parse_date
from retrieval import load_workspace, retrieve


# Narrow, explicit handling of account-specific transfer-status questions.
# This is not a general intent classifier or a guarantee of answerability.
ACCOUNT_STATUS_PATTERNS = (
    r"\b(?:has|have|did)\s+(?:my|our)\s+(?:doctor|provider|practitioner)\b"
    r".*\b(?:transfer(?:red)?|migrat(?:e|ed)|mov(?:e|ed))\b",
    r"\b(?:is|was|has)\s+(?:my|our)\s+(?:data|account|transfer|migration)\b"
    r".*\b(?:transfer(?:red)?|migrat(?:e|ed)|complete(?:d)?|finished)\b",
)


def registered_citation(passage, sources):
    source = sources[passage["source_id"]]
    url = source["url"]
    if not isinstance(url, str):
        raise ValueError("Source URL must be text")
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError("Source URL must be an HTTP(S) link")
    return {
        "evidence_id": passage["id"], "source_id": passage["source_id"],
        "source_url": url, "source_title": source["title"],
        "content_version": passage["content_version"],
        "evidence_type": passage["evidence_type"],
    }


def answer(question, audience=None, reference_date=None, *, workspace=None):
    """Return cited excerpts or an explicit non-answer; never call a model."""
    reference_date = date.today().isoformat() if reference_date is None else reference_date
    result = {
        "status": "abstain",
        "reason": None,
        "answer_text": "",
        "claims": [],
        "citations": [],
        "retrieved_source_ids": [],
        "passages": [],
        "conflicts": [],
        "run": {
            "mode": "extractive", "corpus_hash": None,
            "prompt_hash": None, "model_id_or_none": None,
            "reference_date": reference_date,
        },
    }
    if not isinstance(question, str) or not question.strip():
        return {**result, "status": "clarify", "reason": "missing_question",
                "answer_text": "Enter a question about the documentation."}
    if audience not in ("Providers", "Patients"):
        return {**result, "status": "clarify", "reason": "missing_audience",
                "answer_text": "Choose Providers or Patients so the evidence matches the reader."}
    try:
        parse_date(reference_date)
    except (TypeError, ValueError):
        return {**result, "status": "clarify", "reason": "invalid_date",
                "answer_text": "Choose a reference date using YYYY-MM-DD."}

    try:
        workspace = load_workspace() if workspace is None else workspace
        serialized = json.dumps(workspace, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        result["run"]["corpus_hash"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        if any(re.search(pattern, question, re.IGNORECASE | re.DOTALL) for pattern in ACCOUNT_STATUS_PATTERNS):
            return {**result, "reason": "account_status_unavailable",
                    "answer_text": "Public documentation cannot establish whether your provider has transferred your data. This demo has no access to account-specific transfer status."}
        evidence = retrieve(question, audience, reference_date, **workspace)
    except (OSError, KeyError, TypeError, ValueError):
        return {**result, "status": "error", "reason": "workspace_error",
                "answer_text": "The local content or approval data could not be loaded or validated."}

    if evidence["status"] == "conflict":
        return {**result, "reason": evidence["reason"], "conflicts": evidence["conflicts"],
                "answer_text": "Relevant evidence has a recorded unresolved conflict. I cannot select reliable guidance until that conflict is resolved."}
    if evidence["status"] == "error":
        return {**result, "status": "error", "reason": evidence["reason"],
                "answer_text": "The request or evidence could not be validated. No excerpts are being presented as an answer."}
    if evidence["status"] == "empty":
        messages = {
            "no_approved_topics": "No demo-approved content is available. Nothing has been approved on your behalf.",
            "no_applicable_passages": "No approved passages apply to this audience and reference date.",
            "no_lexical_match": "No matching approved evidence was found for this question.",
        }
        return {**result, "reason": evidence["reason"],
                "answer_text": messages[evidence["reason"]]}

    try:
        sources = {source["id"]: source for source in workspace["sources"]}
        citations = [registered_citation(passage, sources) for passage in evidence["passages"]]
    except (KeyError, TypeError, ValueError):
        return {**result, "status": "error", "reason": "invalid_citation",
                "answer_text": "A supporting citation could not be resolved to a valid registered source."}
    return {
        **result,
        "status": "answered",
        "answer_text": "Relevant evidence excerpts (not a generated answer):\n\n" + "\n\n".join(
            passage["body"] for passage in evidence["passages"]
        ),
        "claims": [
            {"text": passage["body"], "supporting_evidence_ids": [passage["id"]]}
            for passage in evidence["passages"]
        ],
        "citations": citations,
        "retrieved_source_ids": evidence["retrieved_source_ids"],
        "passages": evidence["passages"],
    }
