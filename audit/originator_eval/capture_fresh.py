"""Capture a FRESH candidate set from the replay corpus (free, offline).

Replays every corpus claim from its cassette (no network, no spend) with the
originator review OFF, and snapshots what `classify_batch` produced: each item
the model itself called PRIMARY on a host whose identity does not settle the
tier, with the page's first 1,200 chars exactly as the runtime review would
read them (`_page_opening`). None of these claims is an Astra or A− record, so
the set was never read while the review was designed (design §17).

Run from backend/ (Docker up):  python ../audit/originator_eval/capture_fresh.py
"""

import json
import os
import runpy
import sys

sys.path.insert(0, ".")

import scripts.replay_bench.runner as bench_runner  # noqa: E402
from app.pipeline import evidence_classifier as ec  # noqa: E402
from app.services import originator_review as orv  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "corpus_inputs.json")

current = {"claim": None}
captured = {}

_run_one = bench_runner.run_one_async


async def _tagged_run_one(corpus_dir, claim_id, *args, **kwargs):
    current["claim"] = claim_id
    return await _run_one(corpus_dir, claim_id, *args, **kwargs)


_classify = ec.EvidenceClassifier.classify_batch


async def _capturing_classify(self, evidence_items, review_originators=True):
    # Snapshot the opening at entry: the distiller pops `_full_text` once
    # classify yields to it (they run concurrently).
    openings = {
        id(item): (item.get("_full_text") or "")[: orv.TEXT_CHARS]
        for item in evidence_items
    }
    result = await _classify(self, evidence_items, review_originators)
    for item in result:
        if not orv.is_candidate(item):
            continue
        opening = openings.get(id(item), "")
        row = captured.setdefault(
            item.get("url"),
            {
                "url": item.get("url"),
                "host": ec._url_host(item.get("url") or ""),
                "title": item.get("title") or "",
                "text": opening or (item.get("snippet") or "")[: orv.TEXT_CHARS],
                "input_kind": "page_opening" if opening else "snippet",
                "records": [],
                "overlap": False,
                "stored_type": item.get("evidence_type"),
            },
        )
        if current["claim"] not in row["records"]:
            row["records"].append(current["claim"])
    return result


def main():
    # Patch BEFORE the bench script runs: it binds `run_one_async` at import.
    bench_runner.run_one_async = _tagged_run_one
    ec.EvidenceClassifier.classify_batch = _capturing_classify
    sys.argv = ["replay_bench.py", "--all"]
    try:
        runpy.run_path("scripts/replay_bench.py", run_name="__main__")
    except SystemExit:
        pass
    finally:
        rows = [dict(r, id=f"f{n:03d}") for n, r in enumerate(captured.values())]
        json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"captured {len(rows)} fresh candidates -> {OUT}")


if __name__ == "__main__":
    main()
