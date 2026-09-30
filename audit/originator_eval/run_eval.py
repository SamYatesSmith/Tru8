"""Offline eval of the originator review on the held-out Astra candidates.

PAID (Google API). Ask the founder before every run, with the cost.
Runs the production review code (`originator_review.review_originators`
through `EvidenceClassifier._call_originator_review`) over
`heldout_inputs.json`, `--runs` times on identical inputs, and scores it
against `eval_labels.json` (design §7.3).

Run from backend/:
    python ../audit/originator_eval/run_eval.py --runs 1 --limit 15   # cost probe
    python ../audit/originator_eval/run_eval.py --runs 2              # full eval
"""

import argparse
import asyncio
import collections
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")
from app.core.config import settings  # noqa: E402
from app.core.cost_constants import _rate  # noqa: E402
from app.pipeline.evidence_classifier import EvidenceClassifier  # noqa: E402
from app.services import originator_review as orv  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# Design §6, named before any run. Matched on the URL; an Astra-pool gate only.
MUST_SURVIVE = [
    (
        "sqlite.org own docs",
        lambda u: "sqlite.org/" in u
        and "/forum" not in u
        and "narkive" not in u
        and "system.data" not in u,
    ),
    ("ESA", lambda u: "esa.int/" in u),
    ("NAO", lambda u: "nao.org.uk" in u),
    ("FCA", lambda u: "fca.org.uk" in u),
    ("IEA", lambda u: "iea.org" in u),
    ("ICCT", lambda u: "theicct.org" in u),
    ("EuroMOMO", lambda u: "euromomo.eu" in u),
    ("IHME", lambda u: "healthdata.org" in u),
    ("NICE", lambda u: "nice.org.uk" in u),
    ("NEJM SELECT PDF", lambda u: "nejmgroup-production.org" in u),
    ("CBP-7960", lambda u: "brexitlegal.ie" in u and "7960" in u),
    ("Uganda guidelines", lambda u: "nms.go.ug" in u),
]


def _items(rows):
    """One eval item per candidate, carrying exactly the stored text as the
    review input (offline there is no `_full_text`; design §4.2)."""
    return [
        {
            "id": r["id"],
            "url": r["url"],
            "title": r["title"],
            "snippet": r["text"],
            "tier": "primary",
            "evidence_type": r["stored_type"],
            "classification_method": "llm",
        }
        for r in rows
    ]


async def _one_run(rows):
    classifier = EvidenceClassifier()
    items = _items(rows)
    stats = await orv.review_originators(items, classifier._call_originator_review)
    usage = classifier.get_token_usage()
    return items, stats, usage


def _score(rows, labels, runs):
    by_id = {r["id"]: r for r in rows}
    out = {}
    for n, items in enumerate(runs, 1):
        lowered = {i["id"] for i in items if i["tier"] == "reporting"}
        receipts = {i["id"]: i["metadata"]["originator_review"] for i in items}
        held = [i for i in by_id if not by_id[i]["overlap"]]
        orig = [i for i in held if labels[i] == "originator"]
        non = [i for i in held if labels[i] == "not_originator"]
        per_record = collections.defaultdict(lambda: [0, 0, 0, 0])
        for i in held:
            rec = by_id[i]["records"][0]
            if labels[i] == "originator":
                per_record[rec][0] += 1
                per_record[rec][1] += i in lowered
            elif labels[i] == "not_originator":
                per_record[rec][2] += 1
                per_record[rec][3] += i in lowered
        must = [
            (name, i, by_id[i]["url"])
            for name, match in MUST_SURVIVE
            for i in by_id
            if match(by_id[i]["url"]) and i in lowered
        ]
        out[f"run{n}"] = {
            "originators_lowered": f"{sum(i in lowered for i in orig)}/{len(orig)}",
            "non_originators_lowered": f"{sum(i in lowered for i in non)}/{len(non)}",
            "unclear_rate": f"{sum(receipts[i].get('role') == 'unclear' for i in held)}/{len(held)}",
            "invalid_or_failed": f"{sum(receipts[i].get('status') != 'reviewed' for i in held)}/{len(held)}",
            "must_survive_lowered": must,
            "by_input_kind": {
                kind: f"{sum(i in lowered for i in orig if by_id[i]['input_kind'] == kind)}/"
                f"{sum(by_id[i]['input_kind'] == kind for i in orig)} orig, "
                f"{sum(i in lowered for i in non if by_id[i]['input_kind'] == kind)}/"
                f"{sum(by_id[i]['input_kind'] == kind for i in non)} non"
                for kind in ("start0_window", "original_snippet", "stored_snippet")
            },
            "per_record_orig_lowered_non_lowered": {
                k: f"{v[1]}/{v[0]} orig, {v[3]}/{v[2]} non"
                for k, v in sorted(per_record.items())
            },
            "overlap_lowered": f"{sum(i in lowered for i in by_id if by_id[i]['overlap'])}/"
            f"{sum(by_id[i]['overlap'] for i in by_id)}",
        }
    if len(runs) >= 2:
        a = {i["id"]: i["tier"] for i in runs[0]}
        b = {i["id"]: i["tier"] for i in runs[1]}
        out["flip_rate"] = f"{sum(a[i] != b[i] for i in a)}/{len(a)}"
    return out


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument(
        "--limit", type=int, default=0, help="first N items only (cost probe)"
    )
    parser.add_argument("--inputs", default="heldout_inputs.json")
    parser.add_argument("--labels", default="eval_labels.json")
    parser.add_argument(
        "--exclude", default="", help="JSON file whose 'read' list is left out"
    )
    args = parser.parse_args()

    def _load(name):
        return json.load(open(os.path.join(HERE, name), encoding="utf-8"))

    settings.ENABLE_ORIGINATOR_REVIEW = True
    rows = _load(args.inputs)
    if args.exclude:
        read = set(_load(args.exclude)["read"])
        rows = [r for r in rows if r["id"] not in read and not r["overlap"]]
    if args.limit:
        rows = rows[: args.limit]
    labels = {r["id"]: r["label"] for r in _load(args.labels)}

    model = settings.ORIGINATOR_REVIEW_MODEL or settings.GOOGLE_LLM_MODEL
    rate = _rate(model)
    runs, cost = [], 0.0
    for _ in range(args.runs):
        items, stats, usage = await _one_run(rows)
        runs.append(items)
        # Thinking tokens bill at the output rate (Gemini 3.x).
        billed_out = usage["output_tokens"] + usage.get("thinking_tokens", 0)
        cost += (
            usage["input_tokens"] * rate["input"] + billed_out * rate["output"]
        ) / 1e6
        print("run", len(runs), stats, usage)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = {
        "model": model,
        "contract": orv.CONTRACT,
        "items": len(rows),
        "runs": args.runs,
        "cost_usd": round(cost, 4),
        "score": _score(rows, labels, runs),
        "receipts": [
            {i["id"]: i["metadata"]["originator_review"] for i in items}
            for items in runs
        ],
    }
    path = os.path.join(HERE, f"eval_result_{stamp}.json")
    json.dump(result, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(
        json.dumps(
            {k: result[k] for k in ("model", "items", "runs", "cost_usd", "score")},
            indent=1,
        )
    )
    print("->", path)


if __name__ == "__main__":
    asyncio.run(main())
