import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
FACT_REFERENCE_PATTERN = re.compile(r"\{\{fact:([^{}]+)\}\}")


def render_topic(text, facts):
    facts_by_id = {fact["id"]: fact for fact in facts}

    def replace_fact(match):
        fact_id = match.group(1)
        if fact_id not in facts_by_id:
            raise ValueError(f"Unknown fact ID: {fact_id}")
        return facts_by_id[fact_id]["value"]

    return FACT_REFERENCE_PATTERN.sub(replace_fact, text)


if __name__ == "__main__":
    facts = json.loads(
        (ROOT / "data/facts.json").read_text(encoding="utf-8")
    )
    print("Demo-authored draft preview — not approved for answers.\n")
    for topic_path in sorted((ROOT / "content").glob("*.md")):
        topic = topic_path.read_text(encoding="utf-8")
        print(f"--- {topic_path.name} ---")
        print(render_topic(topic, facts))
        print()
