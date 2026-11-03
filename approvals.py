from datetime import date
import json
from pathlib import Path

from content_fingerprint import content_fingerprint


ROOT = Path(__file__).resolve().parent


def load_approvals(path):
    path = Path(path)
    if not path.exists():
        return {}
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, dict):
        raise ValueError("Approval store must be a JSON object keyed by topic ID")
    return records


def record_approval(path, topic_id, text, facts, reviewer, approved_on):
    """Persist an explicit demo approval; callers must obtain reviewer consent."""
    if not isinstance(topic_id, str) or not topic_id.strip():
        raise ValueError("Approval requires a topic ID")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("Approval requires a reviewer")
    if not isinstance(approved_on, str):
        raise ValueError("Approval date must use YYYY-MM-DD")
    if date.fromisoformat(approved_on).isoformat() != approved_on:
        raise ValueError("Approval date must use YYYY-MM-DD")

    record = {
        "topic_id": topic_id,
        "fingerprint": content_fingerprint(text, facts),
        "state": "demo_approved",
        "reviewer": reviewer.strip(),
        "approved_on": approved_on,
    }
    records = load_approvals(path)
    records[topic_id] = record
    Path(path).write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return record


def approval_status(topic_id, text, facts, approvals):
    record = approvals.get(topic_id)
    if record is None:
        return "no_approval"
    if not isinstance(record, dict) or record.get("topic_id") != topic_id:
        return "invalid_approval"
    if record.get("state") != "demo_approved":
        return "not_approved"
    reviewer = record.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        return "invalid_approval"
    try:
        approved_on = record["approved_on"]
        if date.fromisoformat(approved_on).isoformat() != approved_on:
            return "invalid_approval"
    except (KeyError, TypeError, ValueError):
        return "invalid_approval"
    try:
        current = content_fingerprint(text, facts)
    except (KeyError, TypeError, ValueError):
        return "invalid_content"
    if record.get("fingerprint") != current:
        return "changed"
    return "eligible"


def eligible_topics(topics, facts, approvals):
    """Return only exact topic/fact versions admitted by the approval gate."""
    return {
        topic_id: text
        for topic_id, text in topics.items()
        if approval_status(topic_id, text, facts, approvals) == "eligible"
    }


if __name__ == "__main__":
    facts = json.loads(
        (ROOT / "data/facts.json").read_text(encoding="utf-8")
    )
    approvals = load_approvals(ROOT / "data/approvals.json")
    print("Demo eligibility check — this command does not approve content.\n")
    for path in sorted((ROOT / "content").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        print(f"{path.name}: {approval_status(path.name, text, facts, approvals)}")
