"""Cited-source probe (2026-10-05, founder-approved, ~10 Serper calls).

Question: when the pool's copies NAME the missing original ("a new Bloomberg
analysis", "NHS England announced", "revealed in the Telegraph", "EFFIS data"),
does a query built from that name plus the claim's key terms return the
original? Queries combine the cited name (as found in the pool text) with the
claim's own key terms; no knowledge of the original's URL is used.

Run from backend/:  PYTHONPATH=. python ../audit/cited_source/probe.py
"""

import asyncio, json, os
import httpx
from app.core.config import settings

HERE = os.path.dirname(os.path.abspath(__file__))
# (record, cited name as the pool states it, query, what the original is)
PROBES = [
    (
        "#6",
        "Bloomberg analysis",
        "Bloomberg analysis Trump securities trades 28,700",
        "bloomberg.com Trump trades analysis / OGE 278e",
    ),
    (
        "#6",
        "Bloomberg analysis",
        "Bloomberg Trump made 29,000 securities trades more than all of Congress",
        "bloomberg.com graphics page",
    ),
    (
        "#15",
        "NHS England",
        "NHS England AI triage NHS App 29% reduction phone queues",
        "england.nhs.uk release",
    ),
    (
        "#15",
        "NHS England",
        "NHS England announces AI triage rollout NHS App GP practices",
        "england.nhs.uk release",
    ),
    (
        "#1",
        "Daily Telegraph",
        "Ben Delo Daily Telegraph Reform UK donation £36 million",
        "Delo's Telegraph piece",
    ),
    (
        "#1",
        "Daily Telegraph",
        "Christopher Harborne Telegraph Reform UK £36 million donation",
        "Harborne's statement",
    ),
    (
        "#17",
        "EFFIS",
        "EFFIS burned area 2026 EU estimates",
        "EFFIS statistics/estimates",
    ),
    (
        "#17",
        "EFFIS",
        "European Forest Fire Information System 2026 hectares burned EU",
        "EFFIS / JRC current situation",
    ),
    (
        "#4",
        "preliminary official results",
        "Saxony-Anhalt state election 2026 preliminary official results",
        "Landeswahlleiterin results page",
    ),
    (
        "#4",
        "preliminary official results",
        "Landtagswahl Sachsen-Anhalt 2026 vorläufiges amtliches Endergebnis",
        "Landeswahlleiterin results page (native language)",
    ),
]


async def main():
    out = []
    async with httpx.AsyncClient(timeout=30) as c:
        for rec, name, q, target in PROBES:
            r = await c.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": settings.SERPER_API_KEY,
                    "Content-Type": "application/json",
                },
                json={"q": q, "num": 10},
            )
            items = [
                {
                    "rank": i + 1,
                    "link": o.get("link"),
                    "title": o.get("title"),
                    "date": o.get("date"),
                }
                for i, o in enumerate(r.json().get("organic") or [])
            ]
            out.append(
                {
                    "record": rec,
                    "cited": name,
                    "query": q,
                    "target": target,
                    "results": items,
                }
            )
            print(f"\n{rec} [{name}] {q}\n   target: {target}")
            for it in items:
                print(f"   {it['rank']:>2} {it['link'][:110]}")
    json.dump(
        out,
        open(os.path.join(HERE, "probe_results.json"), "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=1,
    )


asyncio.run(main())
