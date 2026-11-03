import argparse
from collections import Counter
from datetime import date
import json
import math
from pathlib import Path
import re

from approvals import eligible_topics, load_approvals
from passage_selection import parse_date, select_applicable_passages
from topic_passages import build_topic_passages


ROOT = Path(__file__).resolve().parent
STOP_WORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it my of on "
    "or should that the their this to was what when where which who with".split()
)


def tokenize(text):
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOP_WORDS]


def rank_passages(question, passages):
    """Local TF-IDF cosine ranking fitted only on eligible, applicable passages."""
    documents = [Counter(tokenize(passage["body"])) for passage in passages]
    document_frequency = Counter(word for document in documents for word in document)
    idf = {
        word: math.log((1 + len(documents)) / (1 + frequency)) + 1
        for word, frequency in document_frequency.items()
    }
    query = {
        word: count * idf[word]
        for word, count in Counter(tokenize(question)).items() if word in idf
    }
    query_norm = math.sqrt(sum(weight * weight for weight in query.values()))
    if not query_norm:
        return []

    ranked = []
    for passage, document in zip(passages, documents):
        weights = {word: count * idf[word] for word, count in document.items()}
        norm = math.sqrt(sum(weight * weight for weight in weights.values()))
        if not norm:
            continue
        score = sum(weight * query.get(word, 0) for word, weight in weights.items()) / (norm * query_norm)
        if score > 0:
            ranked.append({**passage, "score": score})
    return sorted(ranked, key=lambda passage: (-passage["score"], passage["id"]))


def retrieve(question, audience, reference_date=None, *, topics, facts, sources, approvals):
    """Retrieve evidence only. No model, gold answers, or expected citations."""
    resolved_date = date.today().isoformat() if reference_date is None else reference_date
    result = {
        "status": "empty",
        "reason": None,
        "reference_date": resolved_date,
        "audience": audience,
        "retrieved_source_ids": [],
        "passages": [],
        "conflicts": [],
    }
    try:
        if not isinstance(question, str) or not tokenize(question):
            raise ValueError("Question must contain searchable words")
        if audience not in ("Providers", "Patients"):
            raise ValueError("Audience must be Providers or Patients")
        parse_date(resolved_date)
    except (TypeError, ValueError) as error:
        return {**result, "status": "error", "reason": "invalid_request", "detail": str(error)}

    approved = eligible_topics(topics, facts, approvals)
    if not approved:
        return {**result, "reason": "no_approved_topics"}
    try:
        passages = []
        for topic_id, text in approved.items():
            for passage in build_topic_passages(topic_id, text, facts, sources):
                passages.append({
                    **passage,
                    "content_version": approvals[topic_id]["fingerprint"],
                })
        applicable = select_applicable_passages(passages, audience, resolved_date)
    except (KeyError, TypeError, ValueError) as error:
        return {**result, "status": "error", "reason": "invalid_content", "detail": str(error)}
    if not applicable:
        return {**result, "reason": "no_applicable_passages"}

    ranked = rank_passages(question, applicable)
    if not ranked:
        return {**result, "reason": "no_lexical_match"}

    # Explicit editorial flags, not automatic semantic contradiction detection.
    # Check before top-source truncation so a lower-ranked conflict cannot vanish.
    conflict_ids = sorted({
        conflict_id
        for passage in ranked
        for conflict_id in passage["unresolved_conflict_ids"]
    })
    if conflict_ids:
        return {
            **result,
            "status": "conflict",
            "reason": "unresolved_evidence_conflict",
            "conflicts": [
                {
                    "id": conflict_id,
                    "passages": sorted(
                        (passage for passage in applicable
                         if conflict_id in passage["unresolved_conflict_ids"]),
                        key=lambda passage: passage["id"],
                    ),
                }
                for conflict_id in conflict_ids
            ],
        }
    # Pick up to three distinct sources by their highest-scoring passage.
    source_ids = list(dict.fromkeys(passage["source_id"] for passage in ranked))[:3]
    # Bound context to at most three matching passages per selected source.
    selected = []
    counts = Counter()
    for passage in ranked:
        source_id = passage["source_id"]
        if source_id in source_ids and counts[source_id] < 3:
            selected.append(passage)
            counts[source_id] += 1
    return {
        **result,
        "status": "retrieved",
        "retrieved_source_ids": source_ids,
        "passages": selected,
    }


def load_workspace(root=ROOT):
    root = Path(root)
    return {
        "topics": {
            path.name: path.read_text(encoding="utf-8")
            for path in (root / "content").glob("*.md")
        },
        "facts": json.loads((root / "data/facts.json").read_text(encoding="utf-8")),
        "sources": json.loads((root / "data/sources.json").read_text(encoding="utf-8")),
        "approvals": load_approvals(root / "data/approvals.json"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieve local evidence without generating an answer")
    parser.add_argument("question")
    parser.add_argument("--audience", required=True, choices=("Providers", "Patients"))
    parser.add_argument("--date", dest="reference_date", help="YYYY-MM-DD; defaults to today's local date")
    args = parser.parse_args()
    result = retrieve(
        args.question, args.audience, args.reference_date, **load_workspace()
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
