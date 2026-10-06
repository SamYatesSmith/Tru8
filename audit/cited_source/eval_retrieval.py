"""Eval step 2 (design rev 2 §11.9): retrieval on HELD-OUT accepted names.

PAID: one web search per name plus page fetches. Each accepted name from an
eval_names.py run is followed ALONE through the production `follow_names`
path (exact query, host identity filter, submitted-page and pool checks,
production fetch). A hit = an item is kept AND its fetched text carries the
claim's figure or finding (`carries_claim`, the lane's own test).

Run from backend/:
  PYTHONPATH=. python ../audit/cited_source/eval_retrieval.py NAMES.json POOLS.json OUT.json [--labels LABELS.json KEY.json]
"""

import asyncio, json, sys
from app.services import cited_source as cs
from app.utils.url_identity import UrlKeySet

NAMES, POOLS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LABELS = None
if "--labels" in sys.argv:
    i = sys.argv.index("--labels")
    labels = json.load(open(sys.argv[i + 1], encoding="utf-8"))
    key = json.load(open(sys.argv[i + 2], encoding="utf-8"))
    by_row = {l["row"]: l["label"] for l in labels}
    LABELS = {(k["claim_id"], k["name"]): by_row.get(k["row"]) for k in key}


async def main():
    names = json.load(open(NAMES, encoding="utf-8"))
    pools = {p["claim_id"]: p for p in json.load(open(POOLS, encoding="utf-8"))}
    extract = cs._default_extract()
    out = []
    for x in names["pools"]:
        pool = pools[x["claim_id"]]
        for n in x["accepted"]:
            evidence = {"0": [dict(i) for i in pool["items"]]}
            before = len(evidence["0"])
            existing = UrlKeySet(i.get("url") for i in pool["items"] if i.get("url"))
            receipts = await cs.follow_names(
                [{"position": 0, "text": x["claim"]}],
                evidence,
                {"0": {"accepted": [n], "receipts": []}},
                cs._search_exact,
                extract,
                existing,
            )
            kept = evidence["0"][before:]
            item = kept[0] if kept else None
            text = (item.get("_full_text") or item.get("text") or "") if item else ""
            r = receipts.get("0") or {}
            out.append(
                {
                    "claim_id": x["claim_id"],
                    "claim": x["claim"],
                    "name": n["name"],
                    "label": LABELS.get((x["claim_id"], n["name"])) if LABELS else None,
                    "status": next(
                        (
                            s.get("status")
                            for s in r.get("names", [])
                            if s.get("name") == n["name"]
                        ),
                        None,
                    ),
                    "queries": r.get("queries"),
                    "kept_url": item.get("url") if item else None,
                    "carries_claim": bool(item)
                    and cs.carries_claim(text, x["claim"], n["name"]),
                }
            )
            print(
                f"{len(out):3d} {n['name'][:40]:40s} kept={bool(item)} hit={out[-1]['carries_claim']}"
            )
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def rate(rows):
        h = sum(1 for o in rows if o["carries_claim"])
        return f"{h}/{len(rows)}"

    print("all names: hit", rate(out), "| kept", sum(1 for o in out if o["kept_url"]))
    if LABELS:
        t = [o for o in out if o["label"] == "true_origin"]
        print("true_origin names: hit", rate(t))
    print("already_present:", sum(1 for o in out if o["status"] == "already_present"))


asyncio.run(main())
