"""Probe: what does the pipeline's final_result actually carry for api_stats?

Runs one corpus claim under the deterministic cassette and dumps where adapter
contribution is (or isn't) observable, so the NF-03 counter can read the right
field. Deterministic + free (replay).

    python scripts/probe_nf03.py TRU-82CF-2F81
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from scripts.replay_bench.cassette import HttpxCassette  # noqa: E402
from scripts.replay_bench.fixtures import DomainStatusFixture  # noqa: E402

CORPUS = BACKEND / "tests" / "replay_corpus"


async def main(claim_id: str) -> None:
    from app.core.database import async_session
    from app.models.user import User
    from app.models.check import Check
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import run_pipeline, run_pipeline_phase2

    input_data = json.loads(
        (CORPUS / claim_id / "input.json").read_text(encoding="utf-8")
    )
    cassette = HttpxCassette(CORPUS / claim_id / "cassette.json.gz", "replay")

    async with async_session() as s:
        u = await s.get(User, "bench-replay-user")
        if u is None:
            u = User(id="bench-replay-user", email="b@b.local", name="b", credits=10**9)
            s.add(u)
            await s.commit()
        check = Check(
            id=str(uuid.uuid4()),
            user_id=u.id,
            input_type=input_data["input_type"],
            input_content=json.dumps({"content": input_data.get("content")}),
            input_url=input_data.get("url"),
            status="processing",
            credits_used=0,
            user_query=input_data.get("user_query"),
        )
        s.add(check)
        await s.commit()
        check_id, user_id = check.id, u.id

    pin = {
        "input_type": input_data["input_type"],
        "content": input_data.get("content"),
        "url": input_data.get("url"),
        "file_path": None,
        "user_query": input_data.get("user_query"),
    }

    with cassette:
        result = await run_pipeline(check_id, user_id, pin, ProgressReporter(check_id))
        if result is None:
            async with async_session() as s2:
                from sqlalchemy import select
                from app.models.check import Claim

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
                sel = set(input_data.get("selected_positions") or [0])
                for c in claims:
                    c.is_selected = c.position in sel
                await s2.commit()
            result = await run_pipeline_phase2(
                check_id=check_id,
                user_id=user_id,
                input_data=pin,
                progress_reporter=ProgressReporter(check_id),
            )

    print("=== final_result top-level keys ===")
    print(sorted(result.keys()))
    print("\n=== top-level api_stats ===")
    print(json.dumps(result.get("api_stats"), indent=2, default=str)[:1500])
    print("\n=== has top-level api_stats? ===", "api_stats" in result)
    claims = result.get("claims", [])
    print(f"\n=== per-claim api_stats ({len(claims)} claims) ===")
    for i, c in enumerate(claims):
        ast = c.get("api_stats")
        if ast is None:
            print(f"  claim[{i}]: NO api_stats key  (keys={sorted(c.keys())[:8]}...)")
        else:
            aq = ast.get("apis_queried", [])
            with_results = [a for a in aq if a.get("results", 0) > 0]
            print(
                f"  claim[{i}]: apis_queried={len(aq)}  "
                f"with_results={[(a.get('name'), a.get('results')) for a in with_results]}"
            )


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "TRU-82CF-2F81"))
