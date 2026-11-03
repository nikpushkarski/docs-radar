from datetime import date


def parse_date(value):
    if not isinstance(value, str):
        raise ValueError("Date must use YYYY-MM-DD")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Date must use YYYY-MM-DD")
    return parsed


def select_applicable_passages(passages, audience, reference_date):
    """Select by audience and [valid_from, valid_until), not by approval/relevance.

    The caller supplies an explicit reference date so runs are reproducible.
    A null valid_until means no declared upper boundary, not live verification.
    """
    if audience not in ("Providers", "Patients"):
        raise ValueError("Audience must be Providers or Patients")
    reference = parse_date(reference_date)
    selected = []
    for passage in passages:
        if passage.get("audience") not in ("Providers", "Patients"):
            raise ValueError("Passage requires a known audience")
        if "valid_from" not in passage or "valid_until" not in passage:
            raise ValueError("Passage requires explicit validity bounds")
        start = parse_date(passage["valid_from"])
        end = (
            None if passage["valid_until"] is None
            else parse_date(passage["valid_until"])
        )
        if end is not None and start >= end:
            raise ValueError("valid_until must be later than valid_from")
        if passage["audience"] != audience:
            continue
        if reference >= start and (end is None or reference < end):
            selected.append(passage)
    return selected
