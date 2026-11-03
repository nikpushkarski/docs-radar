# Docs Radar

Documentation change-impact detection and a citation-grounded AI assistant, with automated evaluations and CI quality gates.

## Current status

Basic Streamlit page, three attributed source summaries, and three written question cases.
Source validation checks required provenance fields and allowed review states; three automated tests cover valid data, missing provenance, and an invalid review state.
CLI scripts also render shared facts, identify affected topics for a supplied synthetic change, and calculate content fingerprints.
A standalone approval gate excludes topics without a matching demo approval; no real approvals have been recorded.
Retrieval, AI answers, answer evaluations, and CI gates are not implemented yet.

## Use

**Developers:** Use a virtual environment to keep this project's Python packages separate.
With Python installed, run the commands for your terminal from the project folder:

| Step | Windows (cmd / cmder cmd) | macOS (zsh / Bash) |
| --- | --- | --- |
| Create once | `py -m venv .venv` | `python3 -m venv .venv` |
| Activate each new terminal | `.\start.cmd` | `source .venv/bin/activate` |
| Leave the environment | `deactivate` | `deactivate` |

After activation, use `python -m pip` for package installation on either platform.
Create `.venv` locally on each machine; do not copy it between operating systems.

> On Windows, use `.\start.cmd`, not bare `start`, which opens a new window.

## Check source validation

After activation, run from the project folder on either platform:

```text
python -m unittest discover -s tests -p test_validate_source.py -v
```

Expected: three passing tests.
These check metadata validation, not answer quality or factual accuracy.

## Fingerprint changes reasoning

A topic needs a new review when its text or referenced facts change.
Its fingerprint tracks those changes without reacting to unrelated facts or JSON field order.

| Change | Fingerprint changes? |
| --- | --- |
| Edit the topic's text | Yes |
| Change a referenced fact's value or version | Yes |
| Change its evidence or audience | Yes |
| Change an unrelated fact | No |
| Reorder JSON fields | No |

Unknown or duplicate referenced fact IDs produce an error.
Fingerprints identify content versions; they do not approve content by themselves.
The approval gate admits a topic only when its current fingerprint matches its stored demo approval.

## Approval reasoning

| Situation | Result |
| --- | --- |
| No approval | Excluded |
| Current fingerprint matches the approved version | Eligible |
| Topic or referenced fact changes | Excluded until reapproved |
| Unrelated fact changes | Still eligible |
| Approval is deprecated, invalid, or incomplete | Excluded |

Eligible here means passing the approval gate, not guaranteed relevance to a question.
Approvals apply only to this independent demo, not Fullscript.
