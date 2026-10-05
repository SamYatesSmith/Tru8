"""Model inputs built the way production builds them (plan review H2, 2026-10-05).

The labels stay as they are (labellers read fact-centred windows). The MODEL must
read what the shipped stage would read: the claim-independent page opening
(`elc.copy_page_opening`), the original snippet, and passages chosen by the
production selector (`capture_text_provenance` with the check's own claim and
elements), cut by the module's own `build_prompt`.

- Stored side (verbatim text saved at check time): original_snippet + passages
  as stored, plus the page opening from a fresh fetch when one succeeds.
- Re-fetched side: the full page text is fetched again and run through
  `capture_text_provenance`. No original search snippet exists for these, so it
  is left empty (less text than production, the conservative direction).
A side with no text at all drops the pair, counted.

Run from backend/:
  PYTHONPATH=. python ../audit/echo_precision/build_model_inputs.py PROD_RAW
"""

import asyncio, base64, gzip, json, os, sys
from collections import Counter

import httpx, trafilatura
from sqlalchemy import text

from app.core.database import engine
from app.services import echo_link_confirmation as elc
from app.services.text_provenance import capture_text_provenance

HERE = os.path.dirname(os.path.abspath(__file__))
PROD_RAW = sys.argv[1]
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
}
PAGES = os.path.join(HERE, "page_texts.json")
BROWSER = os.path.join(HERE, "browser_texts.json")
MISSING = os.path.join(HERE, "page_missing.json")


def load(name):
    return json.load(open(os.path.join(HERE, name), encoding="utf-8"))


async def fetch(client, url, sem):
    async with sem:
        try:
            r = await client.get(url, timeout=20)
            if r.status_code != 200:
                return None
            if "pdf" in r.headers.get("content-type", "") or r.content[:5] == b"%PDF-":
                import io, pypdf

                rd = pypdf.PdfReader(io.BytesIO(r.content))
                t = "\n".join((pg.extract_text() or "") for pg in rd.pages[:15])
            else:
                t = trafilatura.extract(r.text) or ""
            return t if len(t) >= 200 else None
        except Exception:
            return None


async def claims_local(ids):
    async with engine.connect() as c:
        rows = (
            await c.execute(
                text(
                    "select id::text, text, claim_map::text from claim where id::text = any(:ids)"
                ),
                {"ids": list(ids)},
            )
        ).fetchall()
    return {
        r[0]: (r[1], (json.loads(r[2]) or {}).get("elements", []) if r[2] else [])
        for r in rows
    }


def claims_prod():
    raw = open(PROD_RAW, encoding="utf-8", errors="replace").read()
    pools = json.loads(
        gzip.decompress(
            base64.b64decode(raw.split("@@BEGIN@@", 1)[1].split("@@END@@", 1)[0])
        )
    )
    return {
        cid: (
            p["claim"],
            (json.loads(p["map"]) or {}).get("elements", []) if p["map"] else [],
        )
        for cid, p in pools.items()
    }


async def main():
    allp = {
        (p["claim_id"], p["A"]["evidence_id"], p["B"]["evidence_id"]): p
        for p in load("heldout_all.json")
    }
    # Which sides had verbatim text saved at check time: the pre-refetch files.
    for f in ("heldout_candidates.json", "heldout_prod.json"):
        for c in load(f):
            k = (c["claim_id"], c["A"]["evidence_id"], c["B"]["evidence_id"])
            if k in allp:
                allp[k]["stored_sides"] = [s for s in "AB" if c[s]["verbatim"]]
    key = load("key_heldout.json")
    pairs = {k["id"]: allp[(k["claim_id"], k["A_id"], k["B_id"])] for k in key}

    urls = {p[s]["url"] for p in pairs.values() for s in "AB"}
    pages = json.load(open(PAGES, encoding="utf-8")) if os.path.exists(PAGES) else {}
    todo = [u for u in urls if not pages.get(u)]
    sem = asyncio.Semaphore(12)
    async with httpx.AsyncClient(headers=UA, follow_redirects=True) as c:
        got = await asyncio.gather(*(fetch(c, u, sem) for u in todo))
    for u, t in zip(todo, got):
        if t:
            pages[u] = t
    browser = (
        json.load(open(BROWSER, encoding="utf-8")) if os.path.exists(BROWSER) else {}
    )
    for u in urls:
        if not pages.get(u) and browser.get(u):
            pages[u] = browser[u]
    json.dump(pages, open(PAGES, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(
        sorted(u for u in urls if not pages.get(u)),
        open(MISSING, "w", encoding="utf-8"),
        indent=0,
    )

    cids = {p["claim_id"] for p in pairs.values()}
    claims = {**claims_prod(), **(await claims_local(cids))}

    out, stats = {}, Counter()
    for pid, p in pairs.items():
        claim_text, elements = claims.get(p["claim_id"], ("", []))
        if not elements:
            stats["no_elements"] += 1
        sides, ok = {}, True
        for s in "AB":
            src = p[s]
            item = {
                k: src.get(k)
                for k in ("evidence_id", "url", "source", "title", "published_date")
            }
            full = pages.get(src["url"])
            if p["verbatim_source"] == "stored" or (
                p["verbatim_source"] == "refetched" and _was_stored(p, s)
            ):
                item["text_provenance"] = {
                    "original_snippet": src["verbatim"],
                    "passages": [],
                }
                if full:
                    item["_full_text"] = full
                    elc.copy_page_opening(item)
                    stats["stored_with_opening"] += 1
                else:
                    stats["stored_no_opening"] += 1
            else:
                if not full:
                    ok = False
                    stats["dropped_no_page_text"] += 1
                    break
                item["_full_text"] = full
                item["snippet"] = ""
                elc.copy_page_opening(item)
                capture_text_provenance(item, claim_text or "", elements)
                stats["rebuilt"] += 1
            item.pop("_full_text", None)
            item.pop("snippet", None)
            sides[s] = item
        if ok:
            out[pid] = sides
    json.dump(
        out,
        open(os.path.join(HERE, "model_inputs.json"), "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=1,
    )
    print("pairs", len(pairs), "| inputs", len(out), dict(stats))


def _was_stored(p, side):
    # In a re-fetched pair, a side whose verbatim text was stored at check time
    # is marked by `stored_sides` (refetch_verbatim.py); older files lack it.
    return side in (p.get("stored_sides") or [])


asyncio.run(main())
