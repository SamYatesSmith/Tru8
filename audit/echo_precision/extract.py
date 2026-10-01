import asyncio, json, random, sys
from sqlalchemy import text
from app.core.database import engine
from app.utils import corroboration as C

OUT = sys.argv[1]

async def load():
    async with engine.connect() as c:
        rows = (await c.execute(text("""
          select cl.id, cl.text, ch.created_at, e.evidence_id, e.url, e.source, e.title,
                 e.snippet, e.tier, e.receipt_status
          from claim cl join "check" ch on ch.id=cl.check_id
          join evidence e on e.claim_id=cl.id
          where ch.status='completed' and e.tier is not null
          order by ch.created_at desc"""))).fetchall()
    return rows

rows = asyncio.run(load())
pools, latest = {}, {}
for cid, ctext, created, *ev in rows:
    key = (ctext or "").strip().lower()
    if key in latest and latest[key] != cid:
        continue  # keep the most recent claim per text
    latest[key] = cid
    pools.setdefault(cid, {"claim": ctext, "created": str(created), "items": []})["items"].append(
        dict(zip(["evidence_id", "url", "source", "title", "text", "tier", "receipt_status"], ev)))

pairs, chains = [], 0
for cid, p in pools.items():
    items = p["items"]
    cmap = C.find_corroborating_sources(items)
    facts = [C._extract_key_facts(i["text"] or "") for i in items]
    ch = C._detect_derivation_chains(items, cmap)
    chains += len(ch)
    for i, js in cmap.items():
        if items[i]["tier"] != "primary":
            continue
        for j in js:
            if items[j]["tier"] not in ("reporting", "commentary"):
                continue
            sim = C._text_similarity(items[i]["text"] or "", items[j]["text"] or "")
            ov = C._check_fact_overlap(facts[i], facts[j])
            pairs.append({
                "claim_id": str(cid), "claim": p["claim"], "in_chain": i in ch,
                "text_sim": round(sim, 3), "fact_overlap": round(ov, 3),
                "rule": "text" if sim >= C.MIN_CORROBORATION_SIMILARITY else "facts",
                "shared_facts": sorted(facts[i] & facts[j]),
                "A": {k: items[i][k] for k in ("url", "source", "title", "text")},
                "B": {k: items[j][k] for k in ("url", "source", "title", "text", "tier")},
            })
json.dump(pairs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("pools", len(pools), "chains", chains, "primary-derivative pairs", len(pairs))
print("rule", Counter(p["rule"] for p in pairs))
print("pairs in a chain", sum(p["in_chain"] for p in pairs))
print("pools with >=1 pair", len({p["claim_id"] for p in pairs}))
