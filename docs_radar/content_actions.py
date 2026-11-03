"""Explicit local UI actions; never approve on page load or on draft save."""
import json
from pathlib import Path
import tempfile

from docs_radar.approvals import record_approval
from docs_radar.content_fingerprint import content_fingerprint
from docs_radar.retrieval import load_workspace
from docs_radar.topic_passages import build_topic_passages


def atomic_text(path, text):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(text)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def checked_topic(root, topic_id, expected_fingerprint):
    root = Path(root)
    workspace = load_workspace(root)
    if topic_id not in workspace["topics"] or Path(topic_id).name != topic_id:
        raise ValueError("Select an existing local topic")
    text = workspace["topics"][topic_id]
    if content_fingerprint(text, workspace["facts"]) != expected_fingerprint:
        raise ValueError("Topic or referenced facts changed since preview. Reload and review before saving.")
    return workspace, text


def save_draft(root, topic_id, text, expected_fingerprint):
    workspace, old = checked_topic(root, topic_id, expected_fingerprint)
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Draft must not be empty")
    # Require answerable schema for edited topics; incomplete topics remain inspectable.
    if not build_topic_passages(topic_id, text, workspace["facts"], workspace["sources"]):
        raise ValueError("Draft requires answerable passage metadata")
    content_fingerprint(text, workspace["facts"])
    if text != old:
        atomic_text(Path(root) / "content" / topic_id, text)
    # Existing approval is intentionally not refreshed; a changed hash is ineligible.
    return content_fingerprint(text, workspace["facts"])


def approve_topic(root, topic_id, expected_fingerprint, reviewer, approved_on, confirmed=False):
    if not confirmed:
        raise ValueError("Explicit confirmation of this exact demo version is required")
    workspace, text = checked_topic(root, topic_id, expected_fingerprint)
    if not build_topic_passages(topic_id, text, workspace["facts"], workspace["sources"]):
        raise ValueError("Approval requires answerable passage metadata")
    return record_approval(Path(root) / "data/approvals.json", topic_id, text,
                           workspace["facts"], reviewer, approved_on)


def revoke_topic(root, topic_id, expected_fingerprint, confirmed=False):
    if not confirmed:
        raise ValueError("Explicit confirmation is required to remove eligibility")
    workspace, _ = checked_topic(root, topic_id, expected_fingerprint)
    records = workspace["approvals"]
    records[topic_id] = {**records.get(topic_id, {}), "topic_id": topic_id, "state": "draft"}
    atomic_text(Path(root) / "data/approvals.json", json.dumps(records, indent=2, ensure_ascii=False) + "\n")
