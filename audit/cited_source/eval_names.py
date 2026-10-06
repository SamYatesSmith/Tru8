"""Eval step 1 (design rev 2 §11.9): name precision on HELD-OUT local pools.

PAID: one model call per pool (cost measured from the call's own usage).
Prompt and guards are frozen in app/services/cited_source.py at the commit
that runs this. Pools come from build_heldout.py: local pools whose claim is
not among the 41 production pools read during design, with stored text in
production shape (kept, or rebuilt by production's own capture).

Run from backend/:
  PYTHONPATH=. python ../audit/cited_source/eval_names.py POOLS.json OUT.json [--offset N] [--limit N]
"""

import asyncio, json, sys
from app.services import cited_source as cs

POOLS, OUT = sys.argv[1], sys.argv[2]
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
OFFSET = int(sys.argv[sys.argv.index("--offset") + 1]) if "--offset" in sys.argv else 0


async def main():
    pools = json.load(open(POOLS, encoding="utf-8"))
    pools = [
        p
        for p in pools
        if cs.select_items([{"position": 0, "text": p["text"]}], {"0": p["items"]})
    ]
    pools.sort(key=lambda p: p["claim_id"])
    pools = pools[OFFSET:]
    if LIMIT:
        pools = pools[:LIMIT]
    print("pools that send a name call:", len(pools))
    out, usage = [], {}
    for p in pools:
        res = await cs.name_cited_sources_default(
            [{"position": 0, "text": p["text"]}], {"0": p["items"]}
        )
        st = res.get("_stats") or {}
        for k, v in (st.get("usage") or {}).items():
            usage[k] = usage.get(k, 0) + v
        e = res.get("0") or {}
        out.append(
            {
                "claim_id": p["claim_id"],
                "claim": p["text"],
                "status": st.get("status"),
                "seconds": st.get("seconds"),
                "accepted": e.get("accepted") or [],
                "receipts": e.get("receipts") or [],
            }
        )
    json.dump(
        {"pools": out, "usage": usage},
        open(OUT, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=1,
    )
    cost = (
        usage.get("input_tokens", 0) * 0.75
        + (usage.get("output_tokens", 0) + usage.get("thinking_tokens", 0)) * 3.75
    ) / 1e6
    print(
        "accepted names:",
        sum(len(o["accepted"]) for o in out),
        "| pools with >=1:",
        sum(1 for o in out if o["accepted"]),
        "| statuses:",
        {
            s: sum(1 for o in out if o["status"] == s)
            for s in {o["status"] for o in out}
        },
        f"| cost ${cost:.4f} (3.7-flash intro price)",
    )


asyncio.run(main())
