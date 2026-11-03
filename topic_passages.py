from passage_selection import parse_date
from render_topic import render_topic
from topic_metadata import section_body, split_topic


def build_topic_passages(topic_id, text, facts, sources):
    """Build attributed passages, without approving, filtering, or ranking them."""
    metadata, body = split_topic(text)
    if not metadata:
        return []  # No explicit routing rules means no answer passages yet.
    source_id = metadata.get("source_id")
    source = next((item for item in sources if item["id"] == source_id), None)
    if source is None:
        raise ValueError(f"Unknown passage source: {source_id}")
    if metadata.get("source_summary_sha256") != source["summary_sha256"]:
        raise ValueError("Topic evidence reference no longer matches the source summary")
    audience = metadata.get("audience")
    if audience not in ("Providers", "Patients"):
        raise ValueError("Topic passages require a known audience")
    rules = metadata.get("passages")
    if not isinstance(rules, list) or not rules:
        raise ValueError("Topic requires a nonempty passage list")

    passages = []
    seen = set()
    for rule in rules:
        passage_id = rule["id"]
        if not isinstance(passage_id, str) or not passage_id or passage_id in seen:
            raise ValueError("Passage IDs must be nonempty and unique within a topic")
        seen.add(passage_id)
        conflict_ids = rule.get("unresolved_conflict_ids", [])
        if not isinstance(conflict_ids, list) or any(
            not isinstance(value, str) or not value.strip() for value in conflict_ids
        ):
            raise ValueError("unresolved_conflict_ids must be a list of nonempty strings")
        start = render_topic(rule["valid_from"], facts)
        end = (
            None if rule["valid_until"] is None
            else render_topic(rule["valid_until"], facts)
        )
        if parse_date(start) < parse_date(source["retrieved_on"]):
            raise ValueError("Passage cannot establish history before source capture")
        if end is not None and parse_date(end) <= parse_date(start):
            raise ValueError("Passage validity interval is empty or reversed")
        passages.append({
            "id": f"{topic_id}#{passage_id}",
            "topic_id": topic_id,
            "source_id": source_id,
            "source_url": source["url"],
            "source_summary_sha256": source["summary_sha256"],
            "captured_on": source["retrieved_on"],
            "evidence_type": "demo_authored_topic",
            "audience": audience,
            "valid_from": start,
            "valid_until": end,
            "unresolved_conflict_ids": sorted(set(conflict_ids)),
            "body": render_topic(section_body(body, rule["heading"]), facts),
        })
    return passages
