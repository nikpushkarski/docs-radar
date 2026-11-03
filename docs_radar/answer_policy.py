"""Narrow presentation rules, not general prompt-injection or intent detection."""
import re

# Filter instruction-like lines only after retrieval. Raw evidence stays inspectable.
INSTRUCTION_LINE = re.compile(
    r"\bignore\b.*\b(?:question|instructions?|rules?)\b|"
    r"\b(?:system|developer)\s+(?:prompt|message)\b|"
    r"\b(?:output|print|respond with)\b.*\binstead\b", re.I,
)


def guidance_text(body):
    return "\n".join(line for line in body.splitlines() if not INSTRUCTION_LINE.search(line)).strip()


def unsupported_procedure(question, passages):
    """Do not label explicit absence of procedures as an actionable answer."""
    asks_action = re.search(r"\b(?:how|what should|what can|steps to|instructions to)\b", question, re.I)
    warning = re.compile(r"\b(?:procedures|instructions|steps)\s+(?:are\s+)?not\s+(?:established|supported|available)\b", re.I)
    return bool(asks_action and passages and all(warning.search(p["body"]) for p in passages))
