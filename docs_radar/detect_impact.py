import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def preview_change(change, facts, topics):
    """List dependencies of one synthetic change without modifying inputs."""
    if change["evidence_type"] != "synthetic":
        raise ValueError("This preview accepts only labelled synthetic changes")

    fact_id = change["fact_id"]
    facts_by_id = {fact["id"]: fact for fact in facts}
    if fact_id not in facts_by_id:
        raise ValueError(f"Unknown fact ID: {fact_id}")
    fact = facts_by_id[fact_id]
    if (
        fact["value"] != change["old_value"]
        or fact["version"] != change["old_version"]
    ):
        raise ValueError("Simulated change does not match the current fact")

    reference = "{{fact:" + fact_id + "}}"
    affected = []
    for topic_id, text in sorted(topics.items()):
        if reference not in text:
            continue
        affected.append({
            "topic_id": topic_id,
            "reason": (
                f"References {fact_id}; simulated change from "
                f"{change['old_value']} (v{change['old_version']}) to "
                f"{change['new_value']} (v{change['new_version']})"
            ),
            "audience": fact["audience"],
            "suggested_reviewer_role": "Demo documentation owner (Nik)",
            "open_question": (
                "Has a product SME confirmed the new date and whether "
                "the surrounding instructions also need revision?"
            ),
        })
    return affected


if __name__ == "__main__":
    facts = json.loads(
        (ROOT / "data/facts.json").read_text(encoding="utf-8")
    )
    change = json.loads(
        (ROOT / "data/simulated_changes/login-closure.json").read_text(
            encoding="utf-8"
        )
    )
    topics = {
        path.name: path.read_text(encoding="utf-8")
        for path in (ROOT / "content").glob("*.md")
    }
    print("SYNTHETIC CHANGE — not a Fullscript announcement.")
    print("Rule-based dependency preview; no files changed.\n")
    affected = preview_change(change, facts, topics)
    print(f"Topics needing review: {len(affected)} of {len(topics)}\n")
    for item in affected:
        print(item["topic_id"])
        print(f"  Reason: {item['reason']}")
        print(f"  Audience: {item['audience']}")
        print(f"  Suggested reviewer: {item['suggested_reviewer_role']}")
        print(f"  Open question: {item['open_question']}\n")
