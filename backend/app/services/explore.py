"""Seeker Explore Mode — surface related claims when no gaps remain.

Finds claims from other users that share key entities with the target claim,
returning normalised claim text + element descriptions (no individual evidence,
no user attribution — privacy-safe).

Relatedness signal: key_entities JSONB overlap (deterministic, no embeddings —
consistent with KD5 consensus design decision).
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Minimum shared entities for a claim to be considered related
MIN_ENTITY_OVERLAP = 2

# Maximum related claims to return
MAX_RELATED_CLAIMS = 5

# Minimum non-stopword tokens for subject_context fallback
MIN_CONTEXT_TOKENS = 2


def _extract_context_tokens(subject_context: str | None) -> list[str]:
    """Extract meaningful tokens from subject_context for fallback matching."""
    if not subject_context:
        return []
    stopwords = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "of",
        "in",
        "to",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "and",
        "or",
        "that",
        "this",
        "it",
        "its",
        "has",
        "have",
        "had",
        "be",
        "been",
        "being",
    }
    tokens = [
        t.lower().strip()
        for t in subject_context.split()
        if t.lower().strip() not in stopwords and len(t.strip()) > 2
    ]
    return tokens[:5]


async def find_related_claims(
    claim_id: str,
    user_id: str,
    session: AsyncSession,
    limit: int = MAX_RELATED_CLAIMS,
) -> list[dict]:
    """Find claims from other users that share key entities with the target claim.

    Returns list of related claim dicts with normalised claim text, elements,
    and optional consensus metadata. Never returns user IDs, check IDs, or
    individual evidence items.

    Two-pass strategy:
    1. Entity overlap (preferred): claims sharing >=2 key_entities
    2. Subject context fallback: ILIKE match on subject_context tokens
    """
    # Load target claim's entities and context
    target_result = await session.execute(
        text(
            """
        SELECT cl.key_entities, cl.subject_context, cl.claim_text_hash
        FROM claim cl
        JOIN "check" ch ON cl.check_id = ch.id
        WHERE cl.id = :claim_id
          AND ch.user_id = :user_id
    """
        ),
        {"claim_id": claim_id, "user_id": user_id},
    )
    target_row = target_result.fetchone()
    if not target_row:
        return []

    target_entities = target_row[0] or []
    target_context = target_row[1]
    target_hash = target_row[2]

    if isinstance(target_entities, str):
        import json

        try:
            target_entities = json.loads(target_entities)
        except (json.JSONDecodeError, TypeError):
            target_entities = []

    if not isinstance(target_entities, list):
        target_entities = []

    # Normalise entities for comparison
    normalised_entities = [str(e).lower().strip() for e in target_entities if e]

    results: list[dict] = []

    # --- Pass 1: Entity overlap ---
    if len(normalised_entities) >= MIN_ENTITY_OVERLAP:
        results = await _find_by_entity_overlap(
            session, normalised_entities, user_id, target_hash, limit
        )

    # --- Pass 2: Subject context fallback ---
    if len(results) < 3:
        context_tokens = _extract_context_tokens(target_context)
        if len(context_tokens) >= MIN_CONTEXT_TOKENS:
            existing_hashes = {r["claimTextHash"] for r in results}
            fallback = await _find_by_subject_context(
                session,
                context_tokens,
                user_id,
                target_hash,
                existing_hashes,
                limit - len(results),
            )
            results.extend(fallback)

    # --- Enrich with consensus data ---
    if results:
        await _enrich_with_consensus(session, results)

    return results[:limit]


async def _find_by_entity_overlap(
    session: AsyncSession,
    normalised_entities: list[str],
    user_id: str,
    target_hash: str | None,
    limit: int,
) -> list[dict]:
    """Find claims sharing >=2 key entities with the target."""
    # Use a CTE approach: for each candidate claim, count how many of its
    # entities match the target's entity list. PostgreSQL JSONB array overlap.
    #
    # We extract each candidate's key_entities as text, lowercase them,
    # and count matches against our normalised entity list.
    entity_array = normalised_entities

    query = text(
        """
        WITH candidate_claims AS (
            SELECT DISTINCT ON (cl.claim_text_hash)
                cl.claim_text_hash,
                cl.claim_map,
                cl.claim_type,
                cl.key_entities
            FROM claim cl
            JOIN "check" ch ON cl.check_id = ch.id
            WHERE ch.status = 'completed'
              AND ch.executed_tier = 'full'
              AND ch.user_id != :user_id
              AND cl.claim_map IS NOT NULL
              AND cl.claim_text_hash IS NOT NULL
              AND (:target_hash IS NULL OR cl.claim_text_hash != :target_hash)
              AND cl.key_entities IS NOT NULL
        )
        SELECT
            cc.claim_text_hash,
            cc.claim_map,
            cc.claim_type,
            cc.key_entities,
            (
                SELECT COUNT(*)
                FROM jsonb_array_elements_text(cc.key_entities) AS entity
                WHERE LOWER(TRIM(entity)) = ANY(:entities)
            ) AS overlap_count
        FROM candidate_claims cc
        WHERE (
            SELECT COUNT(*)
            FROM jsonb_array_elements_text(cc.key_entities) AS entity
            WHERE LOWER(TRIM(entity)) = ANY(:entities)
        ) >= :min_overlap
        ORDER BY overlap_count DESC
        LIMIT :limit
    """
    )

    result = await session.execute(
        query,
        {
            "user_id": user_id,
            "target_hash": target_hash,
            "entities": entity_array,
            "min_overlap": MIN_ENTITY_OVERLAP,
            "limit": limit,
        },
    )
    rows = result.fetchall()

    claims = []
    for row in rows:
        claim_hash, claim_map_raw, claim_type, key_entities, overlap_count = row
        cm = claim_map_raw if isinstance(claim_map_raw, dict) else {}

        # Extract shared entities for transparency
        candidate_entities = []
        if isinstance(key_entities, list):
            candidate_entities = [str(e).lower().strip() for e in key_entities if e]
        entity_set = set(normalised_entities)
        shared = [e for e in candidate_entities if e in entity_set]

        claims.append(_build_related_claim(cm, claim_type, claim_hash, shared))

    return claims


async def _find_by_subject_context(
    session: AsyncSession,
    context_tokens: list[str],
    user_id: str,
    target_hash: str | None,
    existing_hashes: set[str],
    limit: int,
) -> list[dict]:
    """Fallback: find claims with similar subject_context."""
    if limit <= 0 or not context_tokens:
        return []

    # Build ILIKE conditions for each token
    conditions = []
    params: dict = {
        "user_id": user_id,
        "target_hash": target_hash,
        "limit": limit,
    }
    for i, token in enumerate(context_tokens[:3]):
        param_name = f"token_{i}"
        conditions.append(f"LOWER(cl.subject_context) LIKE :{param_name}")
        params[param_name] = f"%{token}%"

    # Require at least 2 tokens to match
    where_clause = (
        " AND ".join(conditions[:2]) if len(conditions) >= 2 else conditions[0]
    )

    # Exclude already-found hashes
    hash_exclusion = ""
    if existing_hashes:
        hash_list = list(existing_hashes)
        for i, h in enumerate(hash_list):
            params[f"excl_{i}"] = h
        hash_placeholders = ", ".join(f":excl_{i}" for i in range(len(hash_list)))
        hash_exclusion = f"AND cl.claim_text_hash NOT IN ({hash_placeholders})"

    query = text(
        f"""
        SELECT DISTINCT ON (cl.claim_text_hash)
            cl.claim_text_hash,
            cl.claim_map,
            cl.claim_type,
            cl.key_entities
        FROM claim cl
        JOIN "check" ch ON cl.check_id = ch.id
        WHERE ch.status = 'completed'
          AND ch.executed_tier = 'full'
          AND ch.user_id != :user_id
          AND cl.claim_map IS NOT NULL
          AND cl.claim_text_hash IS NOT NULL
          AND (:target_hash IS NULL OR cl.claim_text_hash != :target_hash)
          AND cl.subject_context IS NOT NULL
          AND ({where_clause})
          {hash_exclusion}
        LIMIT :limit
    """
    )

    result = await session.execute(query, params)
    rows = result.fetchall()

    claims = []
    for row in rows:
        claim_hash, claim_map_raw, claim_type, _key_entities = row
        cm = claim_map_raw if isinstance(claim_map_raw, dict) else {}
        claims.append(_build_related_claim(cm, claim_type, claim_hash, []))

    return claims


def _build_related_claim(
    claim_map: dict,
    claim_type: str | None,
    claim_hash: str,
    entity_overlap: list[str],
) -> dict:
    """Build a privacy-safe related claim dict from raw DB data."""
    elements = []
    for elem in claim_map.get("elements") or []:
        elements.append(
            {
                "description": elem.get("description", ""),
                "state": elem.get("state"),
            }
        )

    return {
        "normalisedClaim": claim_map.get("normalised_claim", ""),
        "claimType": claim_type,
        "elements": elements,
        "consensus": None,  # Enriched later
        "entityOverlap": list(set(entity_overlap)),  # Deduplicate
        "claimTextHash": claim_hash,  # Internal — stripped before response
    }


async def _enrich_with_consensus(
    session: AsyncSession,
    claims: list[dict],
) -> None:
    """Attach consensus metadata to related claims where available."""
    hashes = [c["claimTextHash"] for c in claims if c.get("claimTextHash")]
    if not hashes:
        return

    # Batch fetch consensus rows
    placeholders = ", ".join(f":h{i}" for i in range(len(hashes)))
    params = {f"h{i}": h for i, h in enumerate(hashes)}

    result = await session.execute(
        text(
            f"""
        SELECT claim_text_hash, independent_checks, stability
        FROM claim_consensus
        WHERE claim_text_hash IN ({placeholders})
    """
        ),
        params,
    )

    consensus_map = {}
    for row in result.fetchall():
        consensus_map[row[0]] = {
            "independentChecks": row[1],
            "stability": row[2],
        }

    for claim in claims:
        claim_hash = claim.get("claimTextHash")
        if claim_hash and claim_hash in consensus_map:
            claim["consensus"] = consensus_map[claim_hash]


def build_explore_response(
    related_claims: list[dict],
    exploration_basis: str = "key_entities",
) -> dict:
    """Build the final API response, stripping internal fields."""
    sanitised = []
    for claim in related_claims:
        sanitised.append(
            {
                "normalisedClaim": claim["normalisedClaim"],
                "claimType": claim.get("claimType"),
                "elements": claim["elements"],
                "consensus": claim.get("consensus"),
                "entityOverlap": claim.get("entityOverlap", []),
            }
        )

    return {
        "relatedClaims": sanitised,
        "mode": "explore" if sanitised else "gaps",
        "explorationBasis": exploration_basis,
    }
