"""Compare extraction on saved bytes. No network, models or application writes."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.evidence import EvidenceExtractor
from app.services.text_provenance import capture_text_provenance


def audit(pack, output):
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    spec = json.loads((pack / "spec.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=False)
    extractor = object.__new__(EvidenceExtractor)
    previous = settings.ENABLE_STRUCTURED_EXTRACTION
    rows = []
    try:
        for source in manifest["sources"]:
            if source["status"] != "captured":
                rows.append({"id": source["id"], "status": "unavailable"})
                continue
            raw = (pack / source["file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                raise ValueError(f"Changed source bytes: {source['id']}")
            html = raw.decode(source.get("encoding") or "utf-8", errors="replace")
            row = {
                "id": source["id"],
                "source_sha256": source["sha256"],
                "arms": {},
                "retention": [],
            }
            texts = {}
            for label, enabled in (("legacy", False), ("structured", True)):
                settings.ENABLE_STRUCTURED_EXTRACTION = enabled
                start = time.perf_counter()
                text = extractor._extract_main_content(html, source["url"]) or ""
                row["arms"][label] = {
                    "characters": len(text),
                    "seconds": time.perf_counter() - start,
                    "sha256": hashlib.sha256(text.encode()).hexdigest(),
                }
                texts[label] = text
                (output / f"{source['id']}-{label}.txt").write_text(
                    text, encoding="utf-8"
                )
            row["narrative_preserved"] = texts["structured"].startswith(texts["legacy"])
            row["added_characters"] = len(texts["structured"]) - len(texts["legacy"])
            for case in spec["cases"]:
                if source["id"] not in case["source_ids"]:
                    continue
                item = {"url": source["url"], "_full_text": texts["structured"]}
                capture_text_provenance(item, case["claim"], case["elements"])
                passages = (item.get("text_provenance") or {}).get("passages", [])
                # Diagnostic only: overlap with the appended region is not
                # a claim of relevance, completeness or correct mapping.
                row["retention"].append(
                    {
                        "case_id": case["id"],
                        "retained_characters": sum(len(p["text"]) for p in passages),
                        "retains_added_region": row["added_characters"] > 0
                        and any(p["end"] > len(texts["legacy"]) for p in passages),
                    }
                )
            rows.append(row)
    finally:
        settings.ENABLE_STRUCTURED_EXTRACTION = previous
    result = {"model_evaluation": "not_run", "sources": rows}
    (output / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.pack, args.output)
