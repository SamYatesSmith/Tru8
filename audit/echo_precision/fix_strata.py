"""Plan review M7 (2026-10-05): stratum corrections on key_heldout.json.

- gate_would_scope_v2: a copy the old echo gate already scoped is stored as
  `context`; read it back on its `was` side from basis.echo_scope.scoped.
- dev_url_pair: the local set excluded dev POOLS only; flag any pair whose
  (A url, B url) is a dev-set pair, so the scorer can drop it.
Run from backend/:  PYTHONPATH=. python ../audit/echo_precision/fix_strata.py PROD_RAW
"""

import asyncio, base64, gzip, json, os, sys
from collections import Counter
from sqlalchemy import text
from app.core.database import engine

HERE = os.path.dirname(os.path.abspath(__file__))
load = lambda n: json.load(open(os.path.join(HERE, n), encoding="utf-8"))


def sides(cm):
    out = {}
    for el in (cm or {}).get("elements") or []:
        eid = el.get("element_id")
        for r in el.get("evidence_refs") or []:
            if r.get("relationship") in ("supports", "challenges"):
                out.setdefault(r.get("evidence_id"), set()).add(
                    (eid, r["relationship"])
                )
        for entry in ((el.get("basis") or {}).get("echo_scope") or {}).get(
            "scoped"
        ) or []:
            if entry.get("was") in ("supports", "challenges"):
                out.setdefault(entry.get("evidence_id"), set()).add((eid, entry["was"]))
    return out


async def local_maps(ids):
    async with engine.connect() as c:
        rows = (
            await c.execute(
                text(
                    "select id::text, claim_map::text from claim where id::text = any(:i)"
                ),
                {"i": list(ids)},
            )
        ).fetchall()
    return {r[0]: json.loads(r[1]) if r[1] else None for r in rows}


def prod_maps(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    pools = json.loads(
        gzip.decompress(
            base64.b64decode(raw.split("@@BEGIN@@", 1)[1].split("@@END@@", 1)[0])
        )
    )
    return {cid: json.loads(p["map"]) if p["map"] else None for cid, p in pools.items()}


key = load("key_heldout.json")
batches = {
    r["id"]: r for b in range(1, 7) for r in load(f"heldout_batches/batch{b}.json")
}
dev = {
    (r["A"]["url"], r["B"]["url"])
    for f in ("blind.json", "blind2.json")
    for r in load(f)
}
maps = {
    **prod_maps(sys.argv[1]),
    **asyncio.run(local_maps({k["claim_id"] for k in key})),
}
c = Counter()
for k in key:
    sd = sides(maps.get(k["claim_id"]))
    k["gate_would_scope_v2"] = bool(sd.get(k["A_id"], set()) & sd.get(k["B_id"], set()))
    r = batches[k["id"]]
    k["dev_url_pair"] = (r["A"]["url"], r["B"]["url"]) in dev
    c[(k["gate_would_scope"], k["gate_would_scope_v2"])] += 1
    c["dev_url_pair"] += k["dev_url_pair"]
json.dump(
    key, open(os.path.join(HERE, "key_heldout.json"), "w", encoding="utf-8"), indent=1
)
print(dict(c))
