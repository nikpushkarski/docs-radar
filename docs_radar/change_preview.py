"""Read-only, escaped inline previews of supplied synthetic fact changes."""
from html import escape

from docs_radar.detect_impact import preview_change
from docs_radar.render_topic import FACT_REFERENCE_PATTERN, render_topic
from docs_radar.topic_metadata import split_topic


def highlighted_change(text, facts, change):
    """Return safe HTML, or None when the Markdown body has no changed reference.

    Only explicit fact references change; matching literal dates are untouched.
    No content, facts, metadata, or approvals are modified.
    """
    preview_change(change, facts, {"preview": text})  # Validate type and old version/value.
    render_topic(text, facts)  # Preserve the normal unknown-reference validation.
    _, body = split_topic(text)
    references = list(FACT_REFERENCE_PATTERN.finditer(body))
    if not any(match.group(1) == change["fact_id"] for match in references):
        return None
    values = {fact["id"]: fact["value"] for fact in facts}
    parts, position = [], 0
    for match in references:
        parts.append(escape(body[position:match.start()]))
        fact_id = match.group(1)
        if fact_id == change["fact_id"]:
            parts.append(
                '<del title="Current value" style="color:#8b1e1e;background-color:#ffe3e3;">'
                + escape(values[fact_id]) + '</del> '
                '<ins title="Simulated value" style="color:#14532d;background-color:#dcfce7;">'
                + escape(change["new_value"]) + '</ins>'
            )
        else:
            parts.append(escape(values[fact_id]))
        position = match.end()
    parts.append(escape(body[position:]))
    return '<pre style="white-space:pre-wrap;overflow-wrap:anywhere;">' + ''.join(parts) + '</pre>'
