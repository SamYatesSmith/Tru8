"""Held-out pools for eval step 1, rebuilt in production shape (free).

Local pools (latest per claim text) whose claim is NOT among the 41 production
pools read during design. Pools with stored text keep it. For the rest, each
page is re-fetched (plain fetch, then the Chromium texts cache from the echo
work) and run through production's own `capture_text_provenance` with the
claim's text and elements, so `stored_text` is what production would store.
Items with no page text stay without stored text (as snippet fallbacks do).

Run from backend/:
  PYTHONPATH=. python ../audit/cited_source/build_heldout.py PROD_RAW OUT.json
"""

import asyncio, base64, gzip, json, os, sys
import httpx, trafilatura
from sqlalchemy import text
from app.core.database import engine
from app.services.text_provenance import capture_text_provenance

PROD_RAW, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_CACHE = os.path.join(HERE, "page_texts.json")
ECHO_CACHE = os.path.join(HERE, "..", "echo_precision", "page_texts.json")
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
}


def prod_claims():
    raw = open(PROD_RAW, encoding="utf-8", errors="replace").read()
    pools = json.loads(
        gzip.decompress(
            base64.b64decode(raw.split("@@BEGIN@@", 1)[1].split("@@END@@", 1)[0])
        )
    )
    return {(p["claim"] or "").strip().lower() for p in pools.values()}


async def fetch(client, url, sem):
    async with sem:
        try:
            r = await client.get(url, timeout=20)
            if r.status_code != 200 or "pdf" in r.headers.get("content-type", ""):
                return None
            t = trafilatura.extract(r.text) or ""
            return t if len(t) >= 200 else None
        except Exception:
            return None


async def main():
    prod = prod_claims()
    async with engine.connect() as c:
        rows = (
            await c.execute(
                text(
                    """
          select cl.id::text, cl.text, cl.claim_map::text, e.evidence_id, e.url, e.title, e.text_provenance::text
          from claim cl join "check" ch on ch.id=cl.check_id join evidence e on e.claim_id=cl.id
          where ch.status='completed' order by ch.created_at desc"""
                )
            )
        ).fetchall()
    latest, pools = {}, {}
    for cid, ct, cmap, eid, url, title, tp in rows:
        k = (ct or "").strip().lower()
        if not k or k in prod or (k in latest and latest[k] != cid):
            continue
        latest[k] = cid
        t = json.loads(tp) if tp else None
        els = ((json.loads(cmap) or {}).get("elements") if cmap else None) or []
        p = pools.setdefault(
            cid, {"claim_id": cid, "text": ct, "elements": els, "items": []}
        )
        p["items"].append(
            {
                "evidence_id": eid,
                "url": url,
                "title": title,
                "text_provenance": t if isinstance(t, dict) else None,
            }
        )

    cache = {}
    for f in (ECHO_CACHE, PAGE_CACHE):
        if os.path.exists(f):
            cache.update(json.load(open(f, encoding="utf-8")))
    need = sorted(
        {
            i["url"]
            for p in pools.values()
            for i in p["items"]
            if not i["text_provenance"] and i["url"] and i["url"] not in cache
        }
    )
    print("pools", len(pools), "| urls to fetch", len(need))
    sem = asyncio.Semaphore(16)
    async with httpx.AsyncClient(headers=UA, follow_redirects=True) as client:
        got = await asyncio.gather(*(fetch(client, u, sem) for u in need))
    for u, t in zip(need, got):
        cache[u] = t
    json.dump(
        {k: v for k, v in cache.items() if v},
        open(PAGE_CACHE, "w", encoding="utf-8"),
        ensure_ascii=False,
    )

    rebuilt = 0
    for p in pools.values():
        for it in p["items"]:
            if it["text_provenance"] or not cache.get(it["url"]):
                continue
            item = {"url": it["url"], "snippet": "", "_full_text": cache[it["url"]]}
            capture_text_provenance(item, p["text"] or "", p["elements"])
            it["text_provenance"] = item.get("text_provenance")
            rebuilt += 1
    keep = [p for p in pools.values() if any(i["text_provenance"] for i in p["items"])]
    json.dump(keep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print("items rebuilt", rebuilt, "| pools with stored text", len(keep))


asyncio.run(main())
