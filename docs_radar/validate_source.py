import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def validate_source(source):
    required_fields = (
        "id", "url", "retrieved_on", "evidence_type", "summary_sha256"
    )
    for field in required_fields:
        value = source.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or empty provenance field: {field}")

    allowed_states = (
        "captured", "draft", "demo_approved", "deprecated", "archived"
    )
    if source.get("review_state") not in allowed_states:
        raise ValueError(
            f"Invalid review_state: {source.get('review_state')!r}"
        )


if __name__ == "__main__":
    sources = json.loads(
        (ROOT / "data/sources.json").read_text(encoding="utf-8")
    )
    validate_source(sources[0])
    print("First source passed validation.")
