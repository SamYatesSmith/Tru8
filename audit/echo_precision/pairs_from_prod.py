"""Held-out candidate pairs from a production pool export (checks since 2026-09-09).

Same candidate rule as extract_heldout.py (detector at >= 1 derivative, on the stored
snippet), verbatim text only (review H1). Any pair whose (A url, B url) appears in the
dev set (blind.json / blind2.json) is dropped, and so is every pool that holds one.
Pairs are deduplicated by URL pair against each other and against heldout_candidates.json.
Run from backend/:  PYTHONPATH=. python ../audit/echo_precision/pairs_from_prod.py RAW OUT
"""

import base64, gzip, json, os, sys
from collections import Counter
from app.utils import corroboration as C

HERE = os.path.dirname(os.path.abspath(__file__))
RAW, OUT = sys.argv[1], sys.argv[2]

raw = open(RAW, encoding="utf-8", errors="replace").read()
blob = raw.split("@@BEGIN@@", 1)[1].split("@@END@@", 1)[0]
pools = json.loads(gzip.decompress(base64.b64decode(blob)))

dev_urls = set()
for f in ("blind.json", "blind2.json"):
    for r in json.load(open(os.path.join(HERE, f), encoding="utf-8")):
        dev_urls.add((r["A"]["url"], r["B"]["url"]))
seen = {
    (p["A"]["url"], p["B"]["url"])
    for p in json.load(
        open(os.path.join(HERE, "heldout_candidates.json"), encoding="utf-8")
    )
}


def sides(claim_map):
    out = {}
    cm = json.loads(claim_map) if claim_map else None
    for el in (cm or {}).get("elements") or []:
        for r in el.get("evidence_refs") or []:
            if r.get("relationship") in ("supports", "challenges"):
                out.setdefault(r.get("evidence_id"), set()).add(
                    (el.get("element_id"), r["relationship"])
                )
    return out


# latest pool per claim text
latest = {}
for cid, p in sorted(pools.items(), key=lambda kv: kv[1]["created"], reverse=True):
    latest.setdefault((p["claim"] or "").strip().lower(), cid)
keep = set(latest.values())

pairs, drop = [], Counter()
for cid, p in pools.items():
    if cid not in keep:
        drop["older_duplicate_pool"] += 1
        continue
    items, sd = p["items"], sides(p["map"])
    cmap = C.find_corroborating_sources(items)
    facts = [C._extract_key_facts(i["text"] or "") for i in items]
    pool_pairs, dev_hit = [], False
    for i, js in cmap.items():
        if items[i]["tier"] != "primary":
            continue
        for j in js:
            if items[j]["tier"] not in ("reporting", "commentary"):
                continue
            A, B = items[i], items[j]
            if (A["url"], B["url"]) in dev_urls:
                dev_hit = True
                continue
            if not (A["verbatim"] and B["verbatim"]):
                drop["no_verbatim"] += 1  # kept, flagged: refetch_verbatim.py fills it
            if (A["url"], B["url"]) in seen:
                drop["duplicate_url_pair"] += 1
                continue
            seen.add((A["url"], B["url"]))
            sim = C._text_similarity(A["text"] or "", B["text"] or "")
            shared = sorted(facts[i] & facts[j])
            strong = [f for f in shared if not (f.isdigit() and len(f) in (1, 4))]
            pool_pairs.append(
                {
                    "claim_id": cid,
                    "source": "prod",
                    "needs_fetch": not (A["verbatim"] and B["verbatim"]),
                    "rule": (
                        "text" if sim >= C.MIN_CORROBORATION_SIMILARITY else "facts"
                    ),
                    "text_sim": round(sim, 3),
                    "shared_facts": shared,
                    "strong_facts": len(strong),
                    "gate_would_scope": bool(
                        sd.get(A["evidence_id"], set())
                        & sd.get(B["evidence_id"], set())
                    ),
                    "A": {
                        k: A[k]
                        for k in (
                            "evidence_id",
                            "url",
                            "source",
                            "title",
                            "published_date",
                            "verbatim",
                        )
                    },
                    "B": {
                        k: B[k]
                        for k in (
                            "evidence_id",
                            "url",
                            "source",
                            "title",
                            "published_date",
                            "verbatim",
                            "tier",
                        )
                    },
                }
            )
    if dev_hit:
        drop["dev_pool"] += 1
        continue
    pairs += pool_pairs

json.dump(pairs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
per_pool = Counter(p["claim_id"] for p in pairs)
print("prod pools", len(pools), "| kept", len(keep), "| dropped", dict(drop))
print("pairs", len(pairs), "in pools", len(per_pool))
print(
    "rule",
    Counter(p["rule"] for p in pairs),
    "| gate_would_scope",
    Counter(p["gate_would_scope"] for p in pairs),
)
v = sorted(per_pool.values())
print("pairs per pool: median", v[len(v) // 2] if v else 0, "max", max(v) if v else 0)
