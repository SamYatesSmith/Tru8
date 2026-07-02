"""Invoke the pipeline as a library against one corpus claim and return the
captured Observation.

Mirrors the synchronous /run endpoint pattern (checks.py:880-963) but skips
HTTP, skips persistence-of-final-results, and uses a known bench-user so test
rows can be cleaned up.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .capture import PipelineCaptureHandler, Observation
from .cassette import HttpxCassette
from .fixtures import DomainStatusFixture


BENCH_USER_ID = "bench-replay-user"
BENCH_USER_EMAIL = "bench-replay@trueight.local"


def _resolve_input_path(corpus_dir: Path, claim_id: str) -> Path:
    p = corpus_dir / claim_id / "input.json"
    if not p.exists():
        raise FileNotFoundError(f"input.json not found for {claim_id}: {p}")
    return p


async def _ensure_bench_user(session: Any) -> Any:
    """Idempotent get-or-create of the bench user."""
    from sqlalchemy import select
    from app.models.user import User

    stmt = select(User).where(User.id == BENCH_USER_ID)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    if user is None:
        user = User(
            id=BENCH_USER_ID,
            email=BENCH_USER_EMAIL,
            name="Bench Replay User",
            credits=10**9,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def _create_check(session: Any, user_id: str, input_data: Dict[str, Any]) -> Any:
    """Create a Check row for the bench run. Returns the Check."""
    from app.models.check import Check

    check = Check(
        id=str(uuid.uuid4()),
        user_id=user_id,
        input_type=input_data["input_type"],
        input_content=json.dumps(
            {
                "content": input_data.get("content"),
                "url": input_data.get("url"),
                "file_path": None,
            }
        ),
        input_url=input_data.get("url"),
        status="processing",
        credits_used=0,
        user_query=input_data.get("user_query"),
    )
    session.add(check)
    await session.commit()
    await session.refresh(check)
    return check


async def _apply_claim_selection(
    session: Any, check_id: str, selected_positions: list[int]
) -> int:
    """Mirror the /select-claims endpoint: set Claim.is_selected by position."""
    from sqlalchemy import select
    from app.models.check import Check, Claim

    claims_stmt = (
        select(Claim).where(Claim.check_id == check_id).order_by(Claim.position)
    )
    claims_res = await session.execute(claims_stmt)
    claims = list(claims_res.scalars().all())

    selected_set = set(selected_positions)
    for claim in claims:
        claim.is_selected = claim.position in selected_set

    check_stmt = select(Check).where(Check.id == check_id)
    check_res = await session.execute(check_stmt)
    check = check_res.scalar_one()
    check.selected_claims_count = len(selected_set)

    await session.commit()
    return len(selected_set)


async def _cleanup_check(session: Any, check_id: str) -> None:
    """Best-effort: drop the bench Check row and its claims/evidence."""
    from sqlalchemy import delete
    from app.models.check import Check, Claim, Evidence

    try:
        await session.execute(delete(Evidence).where(Evidence.check_id == check_id))
        await session.execute(delete(Claim).where(Claim.check_id == check_id))
        await session.execute(delete(Check).where(Check.id == check_id))
        await session.commit()
    except Exception:
        await session.rollback()


async def _bust_pipeline_caches() -> None:
    """Invalidate the Redis caches that would otherwise short-circuit retrieve.

    Without this, a second bench run on the same claim text hits the
    evidence_extract cache and skips emission of [API DEBUG], [FRESHNESS INJECT],
    [TIER CAP], [URL LEDGER] — which are exactly the signals we want to assert
    on. Cost of this bust is ~$0.05 per claim per bench run.
    """
    from app.services.cache import CacheService

    cache = CacheService()
    await cache.initialize()
    if not cache.redis_client:
        return
    for pattern in (
        "claim_extract:*",
        "evidence_extract:*",
        "search_results:*",
        "url_content:*",
        "relevance:*",
    ):
        try:
            await cache.invalidate_pattern(pattern)
        except Exception:
            pass


async def _run_one_claim_async(
    input_data: Dict[str, Any],
    selected_positions: Optional[list[int]],
    handler: PipelineCaptureHandler,
) -> str:
    """Run pipeline against one input. Returns the temporary check_id."""
    from app.core.database import async_session
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import run_pipeline, run_pipeline_phase2

    await _bust_pipeline_caches()

    async with async_session() as session:
        user = await _ensure_bench_user(session)
        check = await _create_check(session, user.id, input_data)
        check_id = check.id
        user_id = user.id

    pipeline_input = {
        "input_type": input_data["input_type"],
        "content": input_data.get("content"),
        "url": input_data.get("url"),
        "file_path": None,
        "user_query": input_data.get("user_query"),
    }

    reporter = ProgressReporter(check_id)
    result = await asyncio.wait_for(
        run_pipeline(check_id, user_id, pipeline_input, reporter),
        timeout=300,
    )

    # Article mode: result=None, must apply selection + run phase 2
    if result is None:
        if not selected_positions:
            raise RuntimeError(
                f"Article mode but selected_positions missing for {check_id}"
            )
        async with async_session() as sel_session:
            n = await _apply_claim_selection(sel_session, check_id, selected_positions)
            logging.info(f"[BENCH] Applied selection of {n} claims for {check_id}")

        phase2_reporter = ProgressReporter(check_id)
        result = await asyncio.wait_for(
            run_pipeline_phase2(
                check_id=check_id,
                user_id=user_id,
                input_data=pipeline_input,
                progress_reporter=phase2_reporter,
            ),
            timeout=300,
        )

    return check_id


def _cassette_path(corpus_dir: Path, claim_id: str) -> Path:
    return corpus_dir / claim_id / "cassette.json.gz"


async def run_one_async(
    corpus_dir: Path,
    claim_id: str,
    fixture: DomainStatusFixture,
    cassette_mode: str = "off",
) -> Observation:
    """Run the bench for a single claim_id and return the Observation.

    All DB / cache / pipeline I/O happens inside the *caller's* event loop —
    the caller (the CLI) wraps the whole bench session in a single asyncio.run()
    so the asyncpg engine doesn't span multiple closed loops.

    ``cassette_mode``:
      - ``"off"``    — live network (legacy behaviour; subject to provider drift).
      - ``"record"`` — live network, captured to the claim's cassette.json.
      - ``"replay"`` — served from cassette.json; deterministic, no network.
    """
    input_path = _resolve_input_path(corpus_dir, claim_id)
    input_data = json.loads(input_path.read_text(encoding="utf-8"))

    fixture.reset_between_claims()

    handler = PipelineCaptureHandler()
    root = logging.getLogger()
    root.addHandler(handler)
    prev_level = root.level
    root.setLevel(logging.INFO)

    cassette: Optional[HttpxCassette] = None
    if cassette_mode in ("record", "replay", "patch"):
        cassette = HttpxCassette(_cassette_path(corpus_dir, claim_id), cassette_mode)

    check_id: Optional[str] = None
    try:
        if cassette is not None:
            with cassette:
                check_id = await _run_one_claim_async(
                    input_data,
                    input_data.get("selected_positions"),
                    handler,
                )
            logging.info(
                f"[BENCH] cassette[{cassette_mode}] {claim_id}: {cassette.stats}"
            )
        else:
            check_id = await _run_one_claim_async(
                input_data,
                input_data.get("selected_positions"),
                handler,
            )
    finally:
        root.removeHandler(handler)
        root.setLevel(prev_level)
        if check_id:
            from app.core.database import async_session

            try:
                async with async_session() as session:
                    await _cleanup_check(session, check_id)
            except Exception:
                pass

    obs = handler.observation()
    # Surface cassette hit/miss stats to the CLI: replay-mode misses mean the
    # pipeline's requests no longer match the recording, so the observation
    # is NOT comparable to golden — the CLI must fail loudly, not diff it.
    obs.cassette_stats = cassette.stats if cassette is not None else None
    return obs


def run_one(
    corpus_dir: Path,
    claim_id: str,
    fixture: DomainStatusFixture,
    cassette_mode: str = "off",
) -> Observation:
    """Synchronous wrapper for one-shot single-claim use. The CLI's --all path
    avoids this and uses run_one_async directly inside a shared event loop."""
    return asyncio.run(run_one_async(corpus_dir, claim_id, fixture, cassette_mode))
