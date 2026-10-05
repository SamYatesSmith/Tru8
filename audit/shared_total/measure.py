"""How often does decomposition attach a claim's shared total to a subset? (free)

Candidate rule (deliberately loose, for measurement only): the claim states a
number N, the claim text after N contains " and " joining further material, and
an element repeats N while omitting a content word that the claim has after the
" and ". Candidates are read by a blind labeller; nothing here is a detector.

Sources: local DB claim maps + the production export (pools since 2026-09-09).
Run from backend/:  PYTHONPATH=. python ../audit/shared_total/measure.py PROD_RAW OUT.json
"""

import asyncio, base64, gzip, json, re, sys
from sqlalchemy import text
from app.core.database import engine

NUM = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(?!\w)")
WORD = re.compile(r"[A-Za-z][A-Za-z'-]{3,}")
STOP = set(
    "that with from this were have been their they them into over under about after before which while where when also than more most such only both each other same team".split()
)


def content_words(s):
    return {w.lower() for w in WORD.findall(s or "")} - STOP


def candidates(claim, elements):
    out = []
    for m in NUM.finditer(claim):
        n = m.group(1)
        if len(n) == 4 and n.startswith(("19", "20")):
            continue  # a year, not a quantity
        tail = claim[m.end() :]
        if " and " not in tail:
            continue
        after_and = tail.split(" and ", 1)[1]
        need = content_words(after_and[:120])
        if not need:
            continue
        for el in elements:
            d = el.get("description") or ""
            if not re.search(r"(?<![\w.])" + re.escape(n) + r"(?!\w)", d):
                continue
            missing = need - content_words(d)
            if len(missing) >= max(1, len(need) // 2):
                out.append({"number": n, "element": d, "missing": sorted(missing)[:8]})
    return out


async def local():
    async with engine.connect() as c:
        rows = (
            await c.execute(
                text(
                    "select id::text, text, claim_map::text from claim where claim_map is not null"
                )
            )
        ).fetchall()
    return {r[0]: (r[1], json.loads(r[2]) or {}) for r in rows}


def prod(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    pools = json.loads(
        gzip.decompress(
            base64.b64decode(raw.split("@@BEGIN@@", 1)[1].split("@@END@@", 1)[0])
        )
    )
    return {
        cid: (p["claim"], json.loads(p["map"]) if p["map"] else {})
        for cid, p in pools.items()
    }


claims = {**asyncio.run(local()), **prod(sys.argv[1])}
seen, found = set(), []
for cid, (ctext, cm) in claims.items():
    key = (ctext or "").strip().lower()
    if not key or key in seen:
        continue
    seen.add(key)
    els = (cm or {}).get("elements") or []
    hits = candidates(ctext, els)
    if hits:
        found.append(
            {
                "claim_id": cid,
                "claim": ctext,
                "elements": [e.get("description") for e in els],
                "hits": hits,
            }
        )
json.dump(found, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("distinct claims", len(seen), "| candidate claims", len(found))
