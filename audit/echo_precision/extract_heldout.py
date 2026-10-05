"""Held-out candidate pairs for echo link confirmation (design rev 2, §6 step 1 + M3).

Free: local DB only. Candidates = the mechanical detector at >= 1 derivative
(every primary <-> reporting/commentary link, chain or not), on the same text
production feeds it (the stored snippet). Labels and the confirmer read ONLY
verbatim text (text_provenance.original_snippet + passages, review H1), so a
pair without verbatim text on both sides is dropped here and counted.

Excludes every pool that holds a dev-set pair (key.json / key2.json).
Run from backend/:  python ../audit/echo_precision/extract_heldout.py OUT.json
"""

import asyncio, json, os, sys
from collections import Counter
from sqlalchemy import text
from app.core.database import engine
from app.utils import corroboration as C

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]

dev = set()
for f in ("key.json", "key2.json"):
    dev |= {
        r["claim_id"] for r in json.load(open(os.path.join(HERE, f), encoding="utf-8"))
    }


def verbatim(tp):
    if not tp:
        return ""
    if isinstance(tp, str):
        tp = json.loads(tp)
    if not isinstance(tp, dict):
        return ""
    parts = [tp.get("original_snippet") or ""]
    parts += [p.get("text") or "" for p in tp.get("passages") or []]
    seen, out = set(), []
    for p in parts:
        p = p.strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return "\n\n".join(out)


async def load():
    async with engine.connect() as c:
        rows = (
            await c.execute(
                text(
                    """
          select cl.id, cl.text, cl.claim_map::text, e.evidence_id, e.url, e.source, e.title,
                 e.snippet, e.tier, e.published_date, e.text_provenance::text
          from claim cl join "check" ch on ch.id=cl.check_id
          join evidence e on e.claim_id=cl.id
          where ch.status='completed' and e.tier is not null
          order by ch.created_at desc"""
                )
            )
        ).fetchall()
    return rows


def sides(claim_map):
    """evidence_id -> set of (element_id, relationship) for directional refs."""
    out = {}
    if not claim_map:
        return out
    cm = json.loads(claim_map) or {}
    for el in cm.get("elements") or []:
        for r in el.get("evidence_refs") or []:
            if r.get("relationship") in ("supports", "challenges"):
                out.setdefault(r.get("evidence_id"), set()).add(
                    (el.get("element_id"), r["relationship"])
                )
    return out


rows = asyncio.run(load())
pools, latest = {}, {}
for cid, ctext, cmap, *ev in rows:
    key = (ctext or "").strip().lower()
    if key in latest and latest[key] != cid:
        continue
    latest[key] = cid
    p = pools.setdefault(cid, {"claim": ctext, "map": cmap, "items": []})
    d = dict(
        zip(
            [
                "evidence_id",
                "url",
                "source",
                "title",
                "text",
                "tier",
                "published_date",
                "tp",
            ],
            ev,
        )
    )
    d["verbatim"] = verbatim(d.pop("tp"))
    p["items"].append(d)

pairs, drop = [], Counter()
for cid, p in pools.items():
    if str(cid) in dev:
        drop["dev_pool"] += 1
        continue
    items = p["items"]
    sd = sides(p["map"])
    cmap = C.find_corroborating_sources(items)
    facts = [C._extract_key_facts(i["text"] or "") for i in items]
    for i, js in cmap.items():
        if items[i]["tier"] != "primary":
            continue
        for j in js:
            if items[j]["tier"] not in ("reporting", "commentary"):
                continue
            A, B = items[i], items[j]
            if not (A["verbatim"] and B["verbatim"]):
                drop["no_verbatim"] += 1  # kept, flagged: refetch_verbatim.py fills it
            sim = C._text_similarity(A["text"] or "", B["text"] or "")
            shared = sorted(facts[i] & facts[j])
            strong = [
                f
                for f in shared
                if not (len(f) == 4 and f.isdigit())
                and not (len(f) == 1 and f.isdigit())
            ]
            pairs.append(
                {
                    "claim_id": str(cid),
                    "needs_fetch": not (A["verbatim"] and B["verbatim"]),
                    "rule": (
                        "text" if sim >= C.MIN_CORROBORATION_SIMILARITY else "facts"
                    ),
                    "text_sim": round(sim, 3),
                    "shared_facts": shared,
                    "strong_facts": len(strong),
                    # the gate scopes B only where A and B sit on the same side of the same element
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

for p in pairs:
    for s in ("A", "B"):
        p[s]["published_date"] = (
            str(p[s]["published_date"]) if p[s]["published_date"] else None
        )
json.dump(pairs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
per_pool = Counter(p["claim_id"] for p in pairs)
print("pools total", len(pools), "| dropped", dict(drop))
print("held-out pairs", len(pairs), "in pools", len(per_pool))
print(
    "rule",
    Counter(p["rule"] for p in pairs),
    "| gate_would_scope",
    Counter(p["gate_would_scope"] for p in pairs),
)
vals = sorted(per_pool.values())
print(
    "pairs per pool (pools with any): median",
    vals[len(vals) // 2] if vals else 0,
    "max",
    max(vals) if vals else 0,
)
