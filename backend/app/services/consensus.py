"""M-06: Convergence layer — cross-user consensus from independent Full checks.

Daily batch job finds claims checked ≥3 times by distinct users, aggregates
element states via description-hash canonicalisation, and computes stability.

Key decisions (from Track M plan, all LOCKED):
- KD5: MVP uses description hashing only — no embeddings
- KD8: Requires k≥3 independent Full checks from distinct users
- Only Full-tier checks count (Quick has insufficient depth)
- Individual evidence items never returned in consensus responses (privacy)
"""

import asyncio
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.manifest_signer import canonical_element_id
from app.models.claim_consensus import ClaimConsensus

logger = logging.getLogger(__name__)

# Minimum independent Full checks required for consensus
MIN_INDEPENDENT_CHECKS = 3

# Consensus staleness — recomputed if older than 7 days in smart endpoint
CONSENSUS_MAX_AGE_DAYS = 7


def compute_stability(element_votes: dict) -> str:
    """Classify consensus stability from element vote distribution.

    stable:   ≥80% agreement on each element's majority state
    mixed:    60-80% agreement
    shifting: <60% agreement
    """
    if not element_votes:
        return "stable"
    agreements = []
    for _ceid, votes in element_votes.items():
        if isinstance(votes, dict):
            total = sum(votes.values())
            majority = max(votes.values()) if votes else 0
        else:
            # Counter object
            total = sum(votes.values())
            majority = max(votes.values()) if votes else 0
        agreements.append(majority / total if total > 0 else 1.0)
    avg_agreement = sum(agreements) / len(agreements)
    if avg_agreement >= 0.8:
        return "stable"
    elif avg_agreement >= 0.6:
        return "mixed"
    else:
        return "shifting"


async def compute_consensus(session: AsyncSession) -> int:
    """Batch job: find qualifying claims and compute/upsert consensus.

    Returns count of consensus rows created/updated.
    """
    # Find claim_text_hashes with ≥3 distinct user_ids on completed Full checks
    qualifying = await session.execute(
        text(
            """
        SELECT cl.claim_text_hash, COUNT(DISTINCT ch.user_id) as user_count
        FROM claim cl
        JOIN "check" ch ON cl.check_id = ch.id
        WHERE ch.status = 'completed'
          AND ch.executed_tier = 'full'
          AND ch.initiated_via IN (
              'api_key', 'agent_x402', 'agent_skyfire', 'agent_credit', 'dashboard'
          )
          AND cl.claim_map IS NOT NULL
          AND cl.claim_text_hash IS NOT NULL
        GROUP BY cl.claim_text_hash
        HAVING COUNT(DISTINCT ch.user_id) >= :min_checks
    """
        ),
        {"min_checks": MIN_INDEPENDENT_CHECKS},
    )

    rows = qualifying.fetchall()
    logger.info(f"[CONSENSUS] Found {len(rows)} qualifying claim hashes")
    updated = 0

    for row in rows:
        claim_hash = row[0]
        try:
            await _compute_consensus_for_hash(session, claim_hash)
            updated += 1
        except Exception:
            logger.exception(f"[CONSENSUS] Failed for hash {claim_hash[:16]}...")

    await session.commit()
    logger.info(f"[CONSENSUS] Updated {updated} consensus rows")
    return updated


async def _compute_consensus_for_hash(session: AsyncSession, claim_hash: str) -> None:
    """Compute consensus for a single claim_text_hash."""
    # Load all ClaimMaps for this hash (Full-tier only)
    claims_result = await session.execute(
        text(
            """
        SELECT cl.claim_map, ch.user_id, ch.completed_at
        FROM claim cl
        JOIN "check" ch ON cl.check_id = ch.id
        WHERE cl.claim_text_hash = :claim_hash
          AND ch.status = 'completed'
          AND ch.executed_tier = 'full'
          AND cl.claim_map IS NOT NULL
    """
        ),
        {"claim_hash": claim_hash},
    )

    claim_rows = claims_result.fetchall()
    if not claim_rows:
        return

    # Canonicalise elements by description hash
    element_votes: dict[str, Counter] = defaultdict(Counter)
    user_ids = set()
    latest_check_at = None

    for claim_map_raw, user_id, completed_at in claim_rows:
        user_ids.add(user_id)
        if completed_at and (latest_check_at is None or completed_at > latest_check_at):
            latest_check_at = completed_at

        cm = claim_map_raw if isinstance(claim_map_raw, dict) else {}
        for elem in cm.get("elements") or []:
            desc = elem.get("description", "")
            if not desc:
                continue
            ceid = canonical_element_id(desc)
            state = elem.get("state")
            if state:
                element_votes[ceid][state] += 1

    # Count evidence from Evidence table (Full-tier checks only)
    ev_result = await session.execute(
        text(
            """
        SELECT e.url, e.tier
        FROM evidence e
        JOIN claim cl ON e.claim_id = cl.id
        JOIN "check" ch ON cl.check_id = ch.id
        WHERE cl.claim_text_hash = :claim_hash
          AND ch.status = 'completed'
          AND ch.executed_tier = 'full'
    """
        ),
        {"claim_hash": claim_hash},
    )

    ev_rows = ev_result.fetchall()
    unique_urls = set()
    tier_counts: Counter = Counter()
    for url, tier in ev_rows:
        if url:
            unique_urls.add(url)
        if tier:
            tier_counts[tier] += 1

    # Compute stability
    stability = compute_stability(dict(element_votes))

    # Serialise element_votes for JSONB (Counter → dict)
    esd = {k: dict(v) for k, v in element_votes.items()}

    # Upsert
    now = datetime.now(timezone.utc)
    existing = await session.get(ClaimConsensus, claim_hash)
    if existing:
        existing.independent_checks = len(user_ids)
        existing.stability = stability
        existing.element_state_distribution = esd
        existing.unique_sources = len(unique_urls)
        existing.total_evidence = len(ev_rows)
        existing.tier_spread = dict(tier_counts)
        existing.last_full_check_at = latest_check_at or now
        existing.computed_at = now
    else:
        consensus = ClaimConsensus(
            claim_text_hash=claim_hash,
            independent_checks=len(user_ids),
            stability=stability,
            element_state_distribution=esd,
            unique_sources=len(unique_urls),
            total_evidence=len(ev_rows),
            tier_spread=dict(tier_counts),
            last_full_check_at=latest_check_at or now,
            computed_at=now,
        )
        session.add(consensus)


def build_consensus_response(consensus: ClaimConsensus) -> dict:
    """Build agent response from consensus row.

    Individual evidence items are NEVER returned (privacy).
    Several landscape fields are null (per-check concepts).
    """
    return {
        "id": None,
        "status": "consensus",
        "claims": [],
        "_meta": {
            "executedTier": "consensus",
            "chargedPence": 3,
            "limitations": ["no_individual_evidence", "aggregated_landscape"],
            "landscape": {
                "elementCount": len(consensus.element_state_distribution),
                "elementStates": _aggregate_element_states(
                    consensus.element_state_distribution
                ),
                "evidenceDensity": consensus.total_evidence,
                "sourcesConsidered": None,
                "sourceDiversity": {
                    "tierSpread": consensus.tier_spread,
                    "uniqueDomains": None,
                    "typeCoverage": None,
                },
                "freshness": None,
                "gaps": [],
                "providerStatus": None,
            },
            "consensus": {
                "independentChecks": consensus.independent_checks,
                "stability": consensus.stability,
                "elementStateDistribution": consensus.element_state_distribution,
                "uniqueSourcesAcrossChecks": consensus.unique_sources,
                "lastFullCheck": (
                    consensus.last_full_check_at.isoformat()
                    if consensus.last_full_check_at
                    else None
                ),
                "computedAt": (
                    consensus.computed_at.isoformat() if consensus.computed_at else None
                ),
            },
        },
        "_manifest": None,  # Consensus is unsigned in MVP (deliberate — KD plan note)
    }


def _aggregate_element_states(esd: dict) -> dict:
    """Majority-vote element states from distribution."""
    totals: Counter = Counter()
    for _ceid, votes in esd.items():
        if isinstance(votes, dict) and votes:
            majority_state = max(votes, key=lambda k: votes[k])
            totals[majority_state] += 1
    return dict(totals)


# ---------------------------------------------------------------------------
# Background loop (lifespan integration)
# ---------------------------------------------------------------------------


async def _consensus_loop():
    """Daily consensus computation at 02:00 UTC."""
    while True:
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        sleep_seconds = (next_run - now).total_seconds()
        logger.info(
            f"[CONSENSUS] Next batch run in {sleep_seconds / 3600:.1f}h "
            f"at {next_run.isoformat()}"
        )
        await asyncio.sleep(sleep_seconds)
        try:
            # Use async_session() directly (it IS an async context
            # manager). get_session() is an async generator intended
            # for FastAPI dependency injection and cannot be entered
            # via `async with` — that was the PYTHON-FASTAPI-20
            # regression: TypeError 'async_generator' object does not
            # support the asynchronous context manager protocol.
            async with async_session() as session:
                count = await compute_consensus(session)
                logger.info(f"[CONSENSUS] Batch complete: {count} rows updated")
        except Exception:
            logger.exception("[CONSENSUS] Batch job failed")


def start_consensus_loop():
    """Launch consensus batch loop as fire-and-forget background task."""
    asyncio.create_task(_consensus_loop())
    logger.info("[CONSENSUS] Background loop started")
