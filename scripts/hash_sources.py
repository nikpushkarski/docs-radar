import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "data/sources.json"
sources = json.loads(path.read_text(encoding="utf-8"))

for source in sources:
    source["summary_sha256"] = hashlib.sha256(
        source["summary"].encode("utf-8")
    ).hexdigest()

path.write_text(
    json.dumps(sources, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print(f"Hashed {len(sources)} summaries.")
