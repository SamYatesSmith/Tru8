"""Build the originator-review eval inputs from the Astra regrade pools.

Free and local. Candidates = items still PRIMARY after today's caps, on the
model's own verdict (`llm`), host not identity-settled, no adapter. Text per
item follows design §4.2 (offline): the stored start==0 provenance window,
else `original_snippet`, else the stored snippet; cut to 1,200 chars.
Design: audit/2026-09-30_classify_originator_design.md.
Run from backend/:  python ../audit/originator_eval/build_inputs.py
"""

import glob
import json
import os
import sys

sys.path.insert(0, ".")
from app.pipeline.evidence_classifier import (  # noqa: E402
    _apply_quality_floor,
    _identity_settles_tier,
    _url_host,
)

# Same claims as A- records #18 (JWST) and #19 (Sweden): reported apart.
OVERLAP = {"t04_jwst", "t06_sweden_focus", "t13_sweden"}
TEXT_CHARS = 1200
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "heldout_inputs.json")


def _items(node, out):
    if isinstance(node, dict):
        if "tier" in node and "url" in node:
            out.append(node)
        for value in node.values():
            _items(value, out)
    elif isinstance(node, list):
        for value in node:
            _items(value, out)


def _text(item):
    prov = item.get("textProvenance") or {}
    for passage in prov.get("passages") or []:
        if passage.get("start") == 0 and passage.get("text"):
            return "start0_window", passage["text"][:TEXT_CHARS]
    if prov.get("original_snippet"):
        return "original_snippet", prov["original_snippet"][:TEXT_CHARS]
    return "stored_snippet", (item.get("snippet") or "")[:TEXT_CHARS]


def _still_primary(item):
    probe = {
        "url": item["url"],
        "source": item.get("source"),
        "title": item.get("title"),
        "snippet": item.get("snippet"),
        "tier": "primary",
        "evidence_type": item.get("evidenceType"),
    }
    _apply_quality_floor(probe)
    return probe["tier"] == "primary"


def main():
    by_url = {}
    for path in sorted(glob.glob("../tmp/astra-regrade-*/*/owner.json")):
        record = os.path.basename(os.path.dirname(path))
        found = []
        _items(json.load(open(path, encoding="utf-8")), found)
        for item in found:
            if (
                item.get("tier") != "primary"
                or item.get("classificationMethod") != "llm"
                or item.get("externalSourceProvider")
                or _identity_settles_tier(_url_host(item["url"]))
                or not _still_primary(item)
            ):
                continue
            entry = by_url.setdefault(item["url"], {"records": set(), "occ": []})
            entry["records"].add(record)
            entry["occ"].append(item)

    rows = []
    for url in sorted(by_url):
        entry = by_url[url]
        # Prefer the richest stored text across this URL's occurrences.
        rank = {"start0_window": 0, "original_snippet": 1, "stored_snippet": 2}
        kind, text = min((_text(i) for i in entry["occ"]), key=lambda kt: (rank[kt[0]], -len(kt[1])))
        first = entry["occ"][0]
        rows.append(
            {
                "id": f"h{len(rows):03d}",
                "url": url,
                "host": _url_host(url),
                "title": first.get("title") or "",
                "text": text,
                "input_kind": kind,
                "records": sorted(entry["records"]),
                "overlap": bool(entry["records"] & OVERLAP),
                "stored_type": first.get("evidenceType"),
            }
        )
    json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    held = [r for r in rows if not r["overlap"]]
    print(f"{len(rows)} candidates: {len(held)} held-out, {len(rows) - len(held)} overlap -> {OUT}")


if __name__ == "__main__":
    main()
