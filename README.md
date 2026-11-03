# Docs Radar

Documentation change-impact detection and a citation-grounded AI assistant, with automated evaluations and CI quality gates.

## Current status

Basic Streamlit page, three attributed source summaries, and three written question cases.
Source validation checks required provenance fields and allowed review states; three automated tests cover valid data, missing provenance, and an invalid review state.
Change detection, AI answers, answer evaluations, and CI gates are not implemented yet.

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
