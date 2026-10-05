"""Fill verbatim text for candidate pairs that lack it, by fetching the live page (free).

For each side with no stored verbatim text: fetch the URL, extract main text with
trafilatura, and keep the page opening (900 chars) plus up to two 900-char windows
around the pair's shared non-year facts. That mirrors what the confirmer will read in
production (page opening + retained passages). Marked `verbatim_source: refetched`.
A side that fails to fetch leaves the pair dropped, with the reason counted.

Usage: python refetch_verbatim.py IN.json [IN2.json ...] OUT.json
"""

import asyncio, json, os, re, sys
from collections import Counter
import httpx, trafilatura

INS, OUT = sys.argv[1:-1], sys.argv[-1]
HERE = os.path.dirname(os.path.abspath(__file__))
BROWSER = os.path.join(HERE, "browser_texts.json")
FAILED = os.path.join(HERE, "fetch_failed.json")
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
}
W = 900


def windows(text, facts):
    out = [text[:W]]
    for f in facts:
        if len(out) >= 3:
            break
        m = re.search(r"(?<![\w.])" + re.escape(f) + r"(?![\w])", text[W:])
        if m:
            s = max(W, W + m.start() - W // 2)
            out.append(text[s : s + W])
    return "\n\n".join(out)


async def fetch(client, url, sem):
    async with sem:
        try:
            r = await client.get(url, timeout=20)
            if r.status_code != 200:
                return None, f"http_{r.status_code}"
            if "pdf" in r.headers.get("content-type", "") or r.content[:5] == b"%PDF-":
                import io, pypdf

                rd = pypdf.PdfReader(io.BytesIO(r.content))
                t = "\n".join((pg.extract_text() or "") for pg in rd.pages[:15])
                return (t, None) if len(t) >= 200 else (None, "pdf_no_text")
            t = trafilatura.extract(r.text) or ""
            return (t, None) if len(t) >= 200 else (None, "too_short")
        except Exception as e:
            return None, type(e).__name__


async def main():
    pairs = [p for f in INS for p in json.load(open(f, encoding="utf-8"))]
    urls = {
        p[s]["url"]
        for p in pairs
        if p.get("needs_fetch")
        for s in "AB"
        if not p[s]["verbatim"]
    }
    sem = asyncio.Semaphore(12)
    async with httpx.AsyncClient(headers=UA, follow_redirects=True) as c:
        got = dict(zip(urls, await asyncio.gather(*(fetch(c, u, sem) for u in urls))))
    # second pass: real-browser texts (refetch_browser.mjs) for pages a plain fetch could not read
    if os.path.exists(BROWSER):
        for u, t in json.load(open(BROWSER, encoding="utf-8")).items():
            if u in got and got[u][0] is None and t:
                got[u] = (t, None)
    failed = sorted(u for u, v in got.items() if v[0] is None)
    json.dump(failed, open(FAILED, "w", encoding="utf-8"), indent=0)
    stats, out = Counter(), []
    for p in pairs:
        if not p.get("needs_fetch"):
            p["verbatim_source"] = "stored"
            out.append(p)
            stats["stored"] += 1
            continue
        strong = [
            f for f in p["shared_facts"] if not (f.isdigit() and len(f) in (1, 4))
        ]
        ok = True
        for s in "AB":
            if p[s]["verbatim"]:
                continue
            text, err = got[p[s]["url"]]
            if text is None:
                stats[f"fail_{err}"] += 1
                ok = False
                break
            p[s]["verbatim"] = windows(text, strong)
        if ok:
            p["verbatim_source"] = "refetched"
            out.append(p)
            stats["refetched"] += 1
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("urls fetched", len(urls), "| ok", sum(1 for v in got.values() if v[0]))
    print("pairs usable", len(out), dict(stats))
    print(
        "pools",
        len({p["claim_id"] for p in out}),
        "| gate_would_scope",
        Counter(p["gate_would_scope"] for p in out),
        "| rule",
        Counter(p["rule"] for p in out),
    )


asyncio.run(main())
