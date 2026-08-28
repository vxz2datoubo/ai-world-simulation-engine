from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = {
    "parent_version": "1.9.0-candidate",
    "authority_graph": "AF001-AUTHORITY-GRAPH-1.9-I2A008@1",
    "golden_version": "1.7.0-candidate",
    "decision_binding_version": "1.2.0-candidate",
}
TEXT_SUFFIXES = {".json", ".py", ".md", ".yaml", ".yml"}
EXCLUDED_DIRS = {".git", ".pytest_cache", "__pycache__"}


def classify(path: Path) -> str:
    p = path.as_posix()
    if p.startswith("contracts/"):
        return "contract"
    if p.startswith("evals/"):
        return "eval"
    if p.startswith("runtime/") or p.startswith("registries/"):
        return "runtime_or_registry"
    if p.startswith("tests/"):
        return "test"
    if p.startswith("docs/") or p == "ARCHITECTURE.md":
        return "documentation"
    return "other"


def json_key_hits(path: Path, value) -> list[dict]:
    hits: list[dict] = []
    if path.suffix != ".json":
        return hits
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return hits

    def walk(node, pointer=""):
        if isinstance(node, dict):
            for key, child in node.items():
                child_pointer = f"{pointer}/{key}"
                if child in TOKENS.values() if isinstance(child, str) else False:
                    hits.append({"pointer": child_pointer, "value": child})
                walk(child, child_pointer)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                child_pointer = f"{pointer}/{index}"
                if child in TOKENS.values() if isinstance(child, str) else False:
                    hits.append({"pointer": child_pointer, "value": child})
                walk(child, child_pointer)

    walk(data)
    return hits


def main() -> None:
    records: list[dict] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="replace")
        counts = {name: text.count(token) for name, token in TOKENS.items()}
        if not any(counts.values()):
            continue
        records.append(
            {
                "path": rel.as_posix(),
                "class": classify(rel),
                "counts": counts,
                "json_key_hits": json_key_hits(path, text),
            }
        )
    out = {
        "inventory_schema": "AWRSE-I8D-B1-VERSION-DEPENDENCY-INVENTORY-1",
        "tokens": TOKENS,
        "files": records,
        "file_count": len(records),
    }
    target = ROOT / "b1-inventory.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"file_count": len(records), "paths": [r["path"] for r in records]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
