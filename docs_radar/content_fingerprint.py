import hashlib
import json
from pathlib import Path

from docs_radar.render_topic import FACT_REFERENCE_PATTERN


ROOT = Path(__file__).resolve().parents[1]


def content_fingerprint(text, facts):
    """Hash the topic and its referenced fact records, not the entire corpus."""
    referenced_ids = set(FACT_REFERENCE_PATTERN.findall(text))
    referenced_facts = {}
    for fact in facts:
        fact_id = fact["id"]
        if fact_id not in referenced_ids:
            continue
        if fact_id in referenced_facts:
            raise ValueError(f"Duplicate referenced fact ID: {fact_id}")
        referenced_facts[fact_id] = fact

    missing = referenced_ids - referenced_facts.keys()
    if missing:
        raise ValueError(f"Unknown fact ID: {sorted(missing)[0]}")

    # Include evidence/applicability metadata as well as value and version.
    # JSON key order and fact-list order must not affect the fingerprint.
    payload = {
        "fingerprint_schema": 1,
        "topic_text": text,
        "referenced_facts": [
            referenced_facts[fact_id] for fact_id in sorted(referenced_ids)
        ],
    }
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    facts = json.loads(
        (ROOT / "data/facts.json").read_text(encoding="utf-8")
    )
    print("Content fingerprints only — no approval recorded.\n")
    for path in sorted((ROOT / "content").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        print(f"{path.name}: {content_fingerprint(text, facts)}")
