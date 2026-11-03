from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from answers import answer
from approvals import load_approvals, record_approval
from content_fingerprint import content_fingerprint
from passage_selection import parse_date
from topic_passages import build_topic_passages


ROOT = Path(__file__).resolve().parent
INPUT_FIELDS = {"question", "audience", "reference_date"}
WORKSPACE_FIELDS = {"topics", "facts", "sources", "approvals"}


def text_sha256(path):
    # Universal newline reading makes Git's LF/CRLF conversion irrelevant.
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def checked_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Evaluation file must stay inside the suite directory")
    return path


def verify_manifest(root=ROOT):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    files = manifest["files"]
    if not files or not {"cases.json", "cases.md"} <= files.keys():
        raise ValueError("Frozen manifest requires both case specifications")
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != manifest["bundle_sha256"]:
        raise ValueError("Evaluation manifest bundle hash mismatch")
    for relative, expected_hash in files.items():
        path = checked_path(root, relative)
        if text_sha256(path) != expected_hash:
            raise ValueError(f"Frozen evaluation file changed: {relative}")
    if not set(manifest["fixtures"].values()) <= files.keys():
        raise ValueError("Every fixture must be covered by the frozen manifest")
    return manifest


def validate_inputs(inputs):
    if not isinstance(inputs, dict) or set(inputs) != INPUT_FIELDS:
        raise ValueError("Runtime inputs must contain only question, audience, and reference_date")
    if not isinstance(inputs["question"], str) or not inputs["question"].strip():
        raise ValueError("Evaluation question must be nonempty")
    if inputs["audience"] not in (None, "Providers", "Patients"):
        raise ValueError("Evaluation audience must be Providers, Patients, or null")
    parse_date(inputs["reference_date"])


def load_suite(root=ROOT):
    root = Path(root)
    manifest = verify_manifest(root)
    suite = json.loads((root / "cases.json").read_text(encoding="utf-8"))
    if suite["version"] != manifest["test_set_version"] or suite["state"] != "frozen":
        raise ValueError("Case version/state does not match the frozen manifest")
    cases = suite["cases"]
    if [case["id"] for case in cases] != [f"Q{number:02}" for number in range(1, 13)]:
        raise ValueError("The frozen suite must contain exactly Q01–Q12 in order")
    for case in cases:
        validate_inputs(case["inputs"])
        if case["fixture_id"] not in manifest["fixtures"]:
            raise ValueError(f"Unknown fixture for {case['id']}")
        if case["expected"]["status"] not in ("answered", "clarify", "abstain", "error"):
            raise ValueError(f"Invalid expected status for {case['id']}")
        if not case["reviewed_specification"].strip():
            raise ValueError(f"Missing reviewed criteria for {case['id']}")
    return suite


def materialize_fixture(fixture):
    """Build an isolated workspace with pinned, synthetic test approvals."""
    workspace = deepcopy(fixture["workspace"])
    if set(workspace) != WORKSPACE_FIELDS or workspace["approvals"]:
        raise ValueError("Fixture workspace must have four runtime fields and no real approvals")
    sources = workspace["sources"]
    if len({source["id"] for source in sources}) != len(sources):
        raise ValueError("Fixture source IDs must be unique")
    for source in sources:
        actual_hash = hashlib.sha256(source["summary"].encode("utf-8")).hexdigest()
        if actual_hash != source["summary_sha256"]:
            raise ValueError(f"Fixture source hash mismatch: {source['id']}")
    for topic_id, text in workspace["topics"].items():
        build_topic_passages(topic_id, text, workspace["facts"], sources)

    seen = set()
    with TemporaryDirectory() as temporary:
        store = Path(temporary) / "approvals.json"
        for setup in fixture["approval_setup"]:
            topic_id = setup["topic_id"]
            if topic_id in seen or topic_id not in workspace["topics"]:
                raise ValueError("Fixture approval IDs must be unique and resolve to topics")
            seen.add(topic_id)
            if setup["state"] not in ("draft", "demo_approved"):
                raise ValueError("Fixture approval state must be draft or demo_approved")
            if setup["reviewer"] != "Synthetic evaluation reviewer":
                raise ValueError("Fixture must not impersonate a real reviewer")
            text = workspace["topics"][topic_id]
            if content_fingerprint(text, workspace["facts"]) != setup["fingerprint"]:
                raise ValueError(f"Fixture approval fingerprint mismatch: {topic_id}")
            record_approval(
                store, topic_id, text, workspace["facts"],
                setup["reviewer"], setup["approved_on"],
            )
        workspace["approvals"] = load_approvals(store)
    for setup in fixture["approval_setup"]:
        workspace["approvals"][setup["topic_id"]]["state"] = setup["state"]
    return workspace


def prepare_case(case_id, root=ROOT):
    """Return only runtime inputs and ordinary evidence, never gold fields."""
    root = Path(root)
    suite = load_suite(root)
    case = next((case for case in suite["cases"] if case["id"] == case_id), None)
    if case is None:
        raise ValueError(f"Unknown evaluation case: {case_id}")
    manifest = verify_manifest(root)
    path = checked_path(root, manifest["fixtures"][case["fixture_id"]])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if fixture["id"] != case["fixture_id"]:
        raise ValueError("Fixture ID does not match its manifest entry")
    return dict(case["inputs"]), materialize_fixture(fixture)


def run_case(case_id, root=ROOT):
    """Call the real answer pipeline; evaluation assertions stay outside it."""
    inputs, workspace = prepare_case(case_id, root)
    return answer(**inputs, workspace=workspace)


if __name__ == "__main__":
    suite = load_suite()
    manifest = verify_manifest()
    for fixture_id, relative in manifest["fixtures"].items():
        fixture = json.loads(checked_path(ROOT, relative).read_text(encoding="utf-8"))
        materialize_fixture(fixture)
        print(f"Fixture valid: {fixture_id}")
    print(f"Frozen {suite['version']}: {len(suite['cases'])} cases; bundle {manifest['bundle_sha256']}")
    print("Fixture/integrity checks only — no answer evaluation or baseline score produced.")
