"""Live cache-busted scout for adapter-cluster probing.

Runs an ad-hoc claim string through the REAL pipeline (live network, cache-busted,
real extractor + classifier) and reports what an adapter cluster actually does:
extracted entities, classified domain/jurisdiction, which adapters were queried,
and per-adapter yield. Use to shape a claim so it routes to a target adapter
BEFORE committing a corpus entry + cassette.

⚠️ This is a SCOUT, not a verdict. The authoritative source of truth is the
deterministic replay bench (record the claim → inspect the cassette-replayed
observation). The NF-03 mis-diagnosis came from a probe that didn't bust caches;
this one does (mirrors the bench), but still: confirm any should-vs-is conclusion
on the bench before acting.

    python scripts/probe_cluster.py "UK CPI inflation rose to 11.1% in October 2022."
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from scripts.replay_bench.fixtures import DomainStatusFixture  # noqa: E402


async def _run(claim_text: str) -> dict:
    from app.core.database import async_session
    from app.models.user import User
    from app.models.check import Check, Claim
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import run_pipeline, run_pipeline_phase2
    from scripts.replay_bench.runner import _bust_pipeline_caches
    from sqlalchemy import select

    async with async_session() as s:
        u = await s.get(User, "bench-replay-user")
        if u is None:
            u = User(id="bench-replay-user", email="b@b.local", name="b", credits=10**9)
            s.add(u)
            await s.commit()
        check = Check(
            id=str(uuid.uuid4()),
            user_id=u.id,
            input_type="text",
            input_content=json.dumps({"content": claim_text}),
            input_url=None,
            status="processing",
            credits_used=0,
        )
        s.add(check)
        await s.commit()
        check_id, user_id = check.id, u.id

    pin = {
        "input_type": "text",
        "content": claim_text,
        "url": None,
        "file_path": None,
        "user_query": None,
    }

    await _bust_pipeline_caches()  # mirror the bench — no warm-cache short-circuit

    # LIVE (no cassette) — real network, real extractor/classifier.
    result = await run_pipeline(check_id, user_id, pin, ProgressReporter(check_id))
    if result is None:
        # multi-claim → select all positions and run phase 2
        async with async_session() as s2:
            claims = (
                (
                    await s2.execute(
                        select(Claim)
                        .where(Claim.check_id == check_id)
                        .order_by(Claim.position)
                    )
                )
                .scalars()
                .all()
            )
            for c in claims:
                c.is_selected = True
            await s2.commit()
        result = await run_pipeline_phase2(
            check_id=check_id,
            user_id=user_id,
            input_data=pin,
            progress_reporter=ProgressReporter(check_id),
        )
    return result


def _report(claim_text: str, result: dict) -> None:
    print(f"\n{'='*70}\nCLAIM: {claim_text}\n{'='*70}")

    print(f"\nartwide classification: {result.get('article_classification')}")
    claims = result.get("claims", [])
    print(f"\nextracted {len(claims)} claim(s):")
    for i, c in enumerate(claims):
        print(f"  [{i}] domain/juris: {c.get('article_classification')}")
        print(f"      text: {(c.get('text') or '')[:100]}")
        ents = c.get("key_entities") or []
        print(f"      key_entities (raw): {ents}")

    print("\nadapters queried (provider_status, API only):")
    ps = result.get("provider_status") or {}
    for name, v in ps.items():
        v = v or {}
        if v.get("type") == "web_search":
            continue
        print(f"  {name:32s} status={v.get('status')} count={v.get('count')}")

    api_stats = result.get("api_stats") or {}
    aq = api_stats.get("apis_queried", [])
    print("\napi_stats.apis_queried (the bench's source of truth):")
    for a in aq:
        print(f"  {a.get('name'):32s} results={a.get('results')}")
    yielded = [a.get("name") for a in aq if a.get("results", 0) > 0]
    print(f"\n>>> adapters_with_results = {len(yielded)} {yielded}")


async def main(claim_text: str) -> None:
    with DomainStatusFixture():  # protect data/domain_status.json from probe writes
        result = await _run(claim_text)
    _report(claim_text, result)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python scripts/probe_cluster.py "<claim text>"')
        sys.exit(2)
    asyncio.run(main(sys.argv[1]))
