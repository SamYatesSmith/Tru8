"""Response builder — shared between checks.py and agent.py.

Extracted from checks.py (L-03). Builds the camelCase API response dict
from a check with claims/evidence. Adds _meta block for agent responses.

Zero behaviour change to existing endpoints — checks.py imports these
functions instead of defining them locally.
"""

import json
import logging
from typing import List, Optional

import redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.check import Check, Claim, Evidence, RawEvidence
from app.utils.encoding import fix_mojibake

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Serialization helpers (moved from checks.py — zero behaviour change)
# ---------------------------------------------------------------------------


def _sanitize_strings(obj):
    """Recursively fix mojibake in all string values of a dict/list."""
    if isinstance(obj, str):
        return fix_mojibake(obj)
    elif isinstance(obj, dict):
        return {k: _sanitize_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_strings(item) for item in obj]
    return obj


def _claim_map_to_camel_case(claim_map: dict) -> dict:
    """Convert a ClaimMap dict from snake_case (DB/TypedDict) to camelCase (API)."""
    if not claim_map or not isinstance(claim_map, dict):
        return claim_map

    def _snake_to_camel(name: str) -> str:
        parts = name.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    result = {}
    for key, value in claim_map.items():
        camel_key = _snake_to_camel(key)
        if key == "elements" and isinstance(value, list):
            result[camel_key] = [_convert_element(elem) for elem in value]
        elif key == "metadata" and isinstance(value, dict):
            result[camel_key] = {_snake_to_camel(mk): mv for mk, mv in value.items()}
        else:
            result[camel_key] = value
    return result


def _convert_element(elem: dict) -> dict:
    """Convert a ClaimElement dict from snake_case to camelCase."""
    if not isinstance(elem, dict):
        return elem

    def _snake_to_camel(name: str) -> str:
        parts = name.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    result = {}
    for key, value in elem.items():
        camel_key = _snake_to_camel(key)
        if key == "evidence_refs" and isinstance(value, list):
            result[camel_key] = [
                (
                    {_snake_to_camel(rk): rv for rk, rv in ref.items()}
                    if isinstance(ref, dict)
                    else ref
                )
                for ref in value
            ]
        else:
            result[camel_key] = value
    return result


def _serialize_evidence(ev, include_factcheck_detail: bool = False) -> dict:
    """Serialize an Evidence model instance to camelCase API dict."""
    result = {
        "id": ev.id,
        "evidenceId": ev.evidence_id,
        "source": ev.source,
        "url": ev.url,
        "title": ev.title,
        "snippet": ev.snippet,
        "publishedDate": (ev.published_date.isoformat() if ev.published_date else None),
        "relevanceScore": ev.relevance_score,
        "tier": ev.tier,
        "evidenceType": ev.evidence_type,
        "receiptStatus": ev.receipt_status,
        "corroborationGroupId": ev.corroboration_group_id,
        "corroboratingEvidenceIds": ev.corroborating_evidence_ids,
        "isFactcheck": ev.is_factcheck,
        "externalSourceProvider": ev.external_source_provider,
        "sourceType": ev.source_type,
        "archivedUrl": ev.archived_url,
        # Provenance persistence (M-01)
        "llmRelevanceScore": ev.llm_relevance_score,
        "classificationMethod": ev.classification_method,
        "contentBasis": ev.content_basis,
    }
    if include_factcheck_detail:
        result["factcheckPublisher"] = ev.factcheck_publisher
        result["factcheckRating"] = ev.factcheck_rating
        result["contextBefore"] = ev.context_before
        result["contextAfter"] = ev.context_after
    return result


# ---------------------------------------------------------------------------
# Core response builder (moved from checks.py)
# ---------------------------------------------------------------------------


async def build_check_response(
    check_id: str,
    user_id: str,
    session: AsyncSession,
    computed: bool = False,
) -> dict:
    """Load a check with claims/evidence and build the camelCase API response.

    Shared by GET /{id} and POST /run. Returns the full response dict.
    Raises HTTPException 404 if the check doesn't exist or doesn't belong to user.
    """
    from fastapi import HTTPException

    stmt = select(Check).where(Check.id == check_id, Check.user_id == user_id)
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Get real-time progress from Redis when processing
    current_stage = None
    progress_percent = None
    progress_message = None

    if check.status in ("processing", "waiting_for_selection"):
        try:
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            progress_data = redis_client.get(f"inline-progress:{check_id}")
            if progress_data:
                data = json.loads(progress_data)
                current_stage = data.get("stage", "processing")
                progress_percent = data.get("progress", 0)
                progress_message = data.get("message", "Processing...")
            redis_client.close()
        except Exception as e:
            logger.warning(
                f"Failed to get progress from Redis for check {check_id}: {e}"
            )

    claims_data = await _load_claims_data(check.id, session)

    response = _build_response_dict(
        check, claims_data, current_stage, progress_percent, progress_message
    )

    if computed:
        from app.services.computed_analytics import compute_analytics

        response["_computed"] = compute_analytics(claims_data)

    response = _sanitize_strings(response)
    return response


# ---------------------------------------------------------------------------
# Agent response builder (L-03)
# ---------------------------------------------------------------------------


async def build_agent_response(
    check_id: str,
    session: AsyncSession,
    executed_tier: str,
    charged_cents: int,
    limitations: List[str],
    compact: bool = False,
    cached_from: Optional[str] = None,
) -> dict:
    """Build response for agent endpoints with _meta block.

    Same data as build_check_response but adds _meta and supports compact mode.
    Does NOT enforce user_id — caller must verify ownership before calling.
    """
    check_result = await session.execute(select(Check).where(Check.id == check_id))
    check = check_result.scalar_one_or_none()
    if not check:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Check not found")

    claims_data = await _load_claims_data(check.id, session)

    # Build landscape metrics from claims data (M-03: pass check for provider_status)
    landscape = _compute_landscape(claims_data, check=check)

    # Build _meta block
    meta = {
        "executedTier": executed_tier,
        "chargedCents": charged_cents,
        "limitations": limitations,
        "landscape": landscape,
    }
    if cached_from:
        meta["cachedFrom"] = cached_from

    if compact:
        # Compact mode: claims + claimMap + _meta only, no evidence arrays
        compact_claims = []
        for claim in claims_data:
            compact_claims.append(
                {
                    "id": claim["id"],
                    "text": claim["text"],
                    "position": claim["position"],
                    "claimMap": claim.get("claimMap"),
                    "claimType": claim.get("claimType"),
                    "isSelected": claim.get("isSelected"),
                }
            )
        response = {
            "id": check.id,
            "status": check.status,
            "claims": compact_claims,
            "_meta": meta,
        }
    else:
        response = _build_response_dict(check, claims_data, None, None, None)
        response["_meta"] = meta

    if not compact:
        from app.services.computed_analytics import compute_analytics

        response["_computed"] = compute_analytics(claims_data)

    # M-04: Include signed manifest for agent responses
    if check.manifest:
        response["_manifest"] = {
            "checkId": check.id,
            "landscapeHash": check.manifest.get("landscape_hash"),
            "signedAt": check.manifest.get("signed_at"),
            "signature": check.manifest.get("signature"),
            "kid": check.manifest.get("kid"),
            "verifyUrl": f"/verify/{check.id}",
        }
    else:
        response["_manifest"] = None

    response = _sanitize_strings(response)
    return response


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_claims_data(check_id: str, session: AsyncSession) -> list:
    """Load claims + evidence for a check, returning the standard claims_data list."""
    claims_stmt = (
        select(Claim).where(Claim.check_id == check_id).order_by(Claim.position)
    )
    claims_result = await session.execute(claims_stmt)
    claims = claims_result.scalars().all()

    raw_counts_stmt = (
        select(RawEvidence.claim_position, func.count(RawEvidence.id))
        .where(RawEvidence.check_id == check_id)
        .group_by(RawEvidence.claim_position)
    )
    raw_counts_result = await session.execute(raw_counts_stmt)
    raw_counts_by_position = dict(raw_counts_result.all())

    claims_data = []
    for claim in claims:
        evidence_stmt = select(Evidence).where(Evidence.claim_id == claim.id)
        evidence_result = await session.execute(evidence_stmt)
        evidence = evidence_result.scalars().all()

        claims_data.append(
            {
                "id": claim.id,
                "text": claim.text,
                "position": claim.position,
                "claimMap": (
                    _claim_map_to_camel_case(claim.claim_map)
                    if claim.claim_map
                    else None
                ),
                "claimType": claim.claim_type,
                "isSelected": claim.is_selected,
                "significanceRank": claim.significance_rank,
                "subjectContext": claim.subject_context,
                "keyEntities": (claim.key_entities if claim.key_entities else []),
                "sourceTitle": claim.source_title,
                "sourceUrl": claim.source_url,
                "sourcesReviewedCount": raw_counts_by_position.get(claim.position, 0),
                "evidence": [_serialize_evidence(ev) for ev in evidence],
            }
        )
    return claims_data


def _build_response_dict(
    check: Check,
    claims_data: list,
    current_stage: Optional[str],
    progress_percent: Optional[float],
    progress_message: Optional[str],
) -> dict:
    """Build the standard check response dict (shared shape)."""
    return {
        "id": check.id,
        "inputType": check.input_type,
        "inputContent": json.loads(check.input_content),
        "inputUrl": check.input_url,
        "status": check.status,
        "creditsUsed": check.credits_used,
        "processingTimeMs": check.processing_time_ms,
        "errorMessage": check.error_message,
        "entryMode": check.entry_mode,
        "selectedClaimsCount": check.selected_claims_count,
        "articleDomain": check.article_domain,
        "articleSecondaryDomains": check.article_secondary_domains,
        "articleJurisdiction": check.article_jurisdiction,
        "articleClassificationSource": check.article_classification_source,
        "userQuery": check.user_query,
        "queryResponse": check.query_response,
        "queryConfidence": check.query_confidence,
        "querySources": (
            check.query_sources.get("sources", []) if check.query_sources else None
        ),
        "queryRelatedClaims": (
            check.query_sources.get("related_claims", [])
            if check.query_sources
            else None
        ),
        "claims": claims_data,
        "createdAt": check.created_at.isoformat(),
        "completedAt": (check.completed_at.isoformat() if check.completed_at else None),
        "currentStage": current_stage,
        "progress": progress_percent,
        "progressMessage": progress_message,
    }


def _compute_landscape(claims_data: list, check=None) -> dict:
    """Compute landscape metrics from claims data for _meta block.

    Args:
        claims_data: Serialized claims with evidence.
        check: Optional Check model instance (for provider_status).
    """
    from datetime import datetime
    from urllib.parse import urlparse

    element_count = 0
    element_states = {}
    evidence_density = 0
    sources_considered = 0
    tier_spread = {}
    type_set = set()
    domains = set()
    dated_dts = []
    undated_count = 0
    gaps = []

    for claim in claims_data:
        claim_map = claim.get("claimMap")
        if claim_map and isinstance(claim_map, dict):
            elements = claim_map.get("elements", [])
            element_count += len(elements)
            for elem in elements:
                state = elem.get("state")
                if state:
                    element_states[state] = element_states.get(state, 0) + 1
                # M-03: element-level gaps
                refs = elem.get("evidenceRefs") or []
                state = elem.get("state")
                if not refs:
                    gaps.append(
                        {
                            "elementId": elem.get("elementId"),
                            "description": elem.get("description"),
                            "claimPosition": claim.get("position"),
                            "reason": "no_evidence",
                        }
                    )
                elif state == "unresolved":
                    gaps.append(
                        {
                            "elementId": elem.get("elementId"),
                            "description": elem.get("description"),
                            "claimPosition": claim.get("position"),
                            "reason": "unresolved",
                            "evidenceCount": len(refs),
                        }
                    )

        evidence_list = claim.get("evidence", [])
        evidence_density += len(evidence_list)
        for ev in evidence_list:
            sources_considered += 1
            tier = ev.get("tier")
            if tier:
                tier_spread[tier] = tier_spread.get(tier, 0) + 1
            etype = ev.get("evidenceType")
            if etype:
                type_set.add(etype)
            # Domain counting
            url = ev.get("url", "")
            if url:
                try:
                    host = urlparse(url).hostname
                    if host:
                        host = host.lower()
                        if host.startswith("www."):
                            host = host[4:]
                        domains.add(host)
                except (ValueError, TypeError):
                    pass
            # Freshness
            raw_date = ev.get("publishedDate")
            if raw_date:
                try:
                    dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    dated_dts.append(dt.replace(tzinfo=None) if dt.tzinfo else dt)
                except (ValueError, TypeError):
                    undated_count += 1
            else:
                undated_count += 1

    # Freshness computation
    freshness = {
        "freshestDaysAgo": None,
        "dateSpanDays": None,
        "undatedCount": undated_count,
    }
    if dated_dts:
        now = datetime.utcnow()
        dated_dts.sort()
        freshest = max(dated_dts)
        oldest = min(dated_dts)
        freshness["freshestDaysAgo"] = max(0, (now - freshest).days)
        freshness["dateSpanDays"] = max(0, (freshest - oldest).days)

    # M-02: Tier/type gap enrichment
    # Check-level gaps for missing source diversity
    if evidence_density > 0:
        if "primary" not in tier_spread:
            gaps.append({"reason": "no_primary_sources"})
        if "academic" not in type_set:
            gaps.append({"reason": "no_academic_sources"})

    # Provider status from Check model (M-02 JSONB column)
    # Records provider outcome, not evidence quality. Brave timeout is
    # structurally different from PubMed timeout.
    provider_status = None
    if check and hasattr(check, "provider_status") and check.provider_status:
        provider_status = check.provider_status

    return {
        "elementCount": element_count,
        "elementStates": element_states,
        "evidenceDensity": evidence_density,
        "sourcesConsidered": sources_considered,
        "sourceDiversity": {
            "tierSpread": tier_spread,
            "uniqueDomains": len(domains),
            "typeCoverage": len(type_set),
        },
        "freshness": freshness,
        "gaps": gaps,
        "providerStatus": provider_status,
    }
