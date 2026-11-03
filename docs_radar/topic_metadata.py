import json


def split_topic(text):
    """Read optional JSON front matter; leave ordinary Markdown supported."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, text
    metadata_text, separator, body = normalized[4:].partition("\n---\n")
    if not separator:
        raise ValueError("Topic metadata is missing its closing --- delimiter")
    metadata = json.loads(metadata_text)
    if not isinstance(metadata, dict):
        raise ValueError("Topic metadata must be a JSON object")
    return metadata, body


def section_body(body, heading):
    """Extract exactly one named level-two section, excluding later sections."""
    lines = body.splitlines()
    starts = [index for index, line in enumerate(lines) if line == f"## {heading}"]
    if len(starts) != 1:
        raise ValueError(f"Expected one section named: {heading}")
    start = starts[0] + 1
    end = next(
        (index for index in range(start, len(lines))
         if lines[index].startswith(("# ", "## "))),
        len(lines),
    )
    content = "\n".join(lines[start:end]).strip()
    if not content:
        raise ValueError(f"Empty section: {heading}")
    return content
