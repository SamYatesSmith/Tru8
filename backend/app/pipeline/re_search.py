"""Element Re-Search — targeted evidence retrieval for a single element.

G02: Re-search mechanism. Runs query planner + retrieval + classification + mapping
for a single element, appending new evidence to the existing claim.
"""

import asyncio
import copy
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.core.database import async_session
from app.models import Claim, Evidence
from app.utils.date_utils import parse_date

logger = logging.getLogger(__name__)


def _get_redis() -> redis.Redis:
    """Get Redis client for status tracking."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _update_status(
    check_id: str,
    claim_id: str,
    element_id: str,
    status: str,
    message: str,
    **extra,
):
    """Update re-search status in Redis."""
    key = f"element-research:{check_id}:{claim_id}:{element_id}"
    data = {"status": status, "message": message, **extra}
    try:
        r = _get_redis()
        r.set(key, json.dumps(data), ex=600)
    except Exception as e:
        logger.warning(f"Failed to update research status: {e}")


def get_research_status(
    check_id: str, claim_id: str, element_id: str
) -> Optional[Dict]:
    """Read current re-search status from Redis."""
    key = f"element-research:{check_id}:{claim_id}:{element_id}"
    try:
        r = _get_redis()
        data = r.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


async def run_element_re_search(
    check_id: str,
    claim_id: str,
    element_id: str,
) -> None:
    """
    Run targeted re-search for a single element.

    Flow:
    1. Load claim + existing evidence from DB
    2. Plan queries for target element (including bounty text as context)
    3. Retrieve new evidence via web search
    4. Classify new evidence (tier + type)
    5. Deduplicate against existing evidence by URL
    6. Re-map all evidence to all elements (mapper operates on full claim)
    7. Save updated claim_map + new evidence to DB
    """

    def update(status, message, **kw):
        _update_status(check_id, claim_id, element_id, status, message, **kw)

    try:
        update("planning", "Planning search queries...")

        async with async_session() as session:
            # 1. Load claim
            stmt = select(Claim).where(Claim.id == claim_id, Claim.check_id == check_id)
            result = await session.execute(stmt)
            db_claim = result.scalar_one_or_none()

            if not db_claim:
                update("error", "Claim not found")
                return

            claim_map = db_claim.claim_map
            if isinstance(claim_map, str):
                claim_map = json.loads(claim_map)

            if not claim_map or not isinstance(claim_map, dict):
                update("error", "Claim map not found")
                return

            # Find target element
            target_element = None
            for elem in claim_map.get("elements", []):
                if elem.get("element_id") == element_id:
                    target_element = elem
                    break

            if not target_element:
                update("error", f"Element {element_id} not found")
                return

            bounty_text = target_element.get("bounty_text", "")

            # Load existing evidence URLs for deduplication
            ev_stmt = select(Evidence).where(Evidence.claim_id == claim_id)
            ev_result = await session.execute(ev_stmt)
            existing_evidence = list(ev_result.scalars().all())
            existing_urls = {ev.url for ev in existing_evidence if ev.url}

            # 2. Plan queries for target element
            element_desc = target_element.get("description", "")
            # Append bounty text as research context for better queries
            if bounty_text:
                element_desc = f"{element_desc} (Research brief: {bounty_text})"

            from app.utils.query_planner import get_query_planner

            planner = get_query_planner()
            claims_with_elements = [
                {
                    "text": db_claim.text,
                    "claim_index": 0,
                    "elements": [
                        {
                            "element_id": element_id,
                            "description": element_desc,
                        }
                    ],
                }
            ]

            query_plans = await planner.plan_queries_batch(claims_with_elements)

            if not query_plans:
                update(
                    "completed",
                    "No search queries could be generated",
                    newEvidenceCount=0,
                )
                return

            # 3. Retrieve evidence
            update("retrieving", "Searching for new evidence...")

            from app.pipeline.retrieve import EvidenceRetriever

            retriever = EvidenceRetriever()

            # Build merged query plan for the retriever
            merged_query_plan = {
                "queries": [],
                "query_element_ids": [],
                "query_freshness": [],
                "claim_index": 0,
                "freshness": query_plans[0].get("freshness", "py"),
                "reasoning": query_plans[0].get("reasoning", ""),
            }
            for plan in query_plans:
                for q in plan.get("queries", []):
                    merged_query_plan["queries"].append(q)
                    merged_query_plan["query_element_ids"].append(
                        plan.get("element_id", element_id)
                    )
                    merged_query_plan["query_freshness"].append(
                        plan.get("freshness", "py")
                    )

            # Construct claim dict for the retriever
            fake_claim = {
                "text": db_claim.text,
                "position": 0,
                "elements": [
                    {
                        "element_id": element_id,
                        "description": target_element.get("description", ""),
                    }
                ],
                "query_plan": merged_query_plan,
            }

            retrieval_result = await retriever.retrieve_evidence_for_claims(
                [fake_claim]
            )
            evidence_by_claim = retrieval_result.get("evidence_by_claim", {})
            new_evidence_list = evidence_by_claim.get("0", [])

            if not new_evidence_list:
                update("completed", "No new evidence found", newEvidenceCount=0)
                return

            # 4. Classify new evidence
            update("classifying", "Classifying evidence...")

            from app.pipeline.evidence_classifier import EvidenceClassifier

            classifier = EvidenceClassifier()
            new_evidence_list = await classifier.classify_batch(new_evidence_list)
            for ev in new_evidence_list:
                ev["receipt_status"] = "classified"

            # 5. Deduplicate against existing evidence
            deduped = [
                ev
                for ev in new_evidence_list
                if ev.get("url", "") not in existing_urls and ev.get("url", "")
            ]

            if not deduped:
                update(
                    "completed",
                    "All found evidence already exists",
                    newEvidenceCount=0,
                )
                return

            # 6. Re-map all evidence to all elements
            update("mapping", "Mapping evidence to elements...")

            # Build evidence dicts from existing DB records
            existing_ev_dicts = []
            for ev in existing_evidence:
                existing_ev_dicts.append(
                    {
                        "evidence_id": ev.evidence_id,
                        "title": ev.title,
                        "snippet": ev.snippet,
                        "text": ev.snippet,
                        "url": ev.url,
                        "source": ev.source,
                    }
                )

            all_evidence_for_mapping = existing_ev_dicts + deduped

            # Deep copy claim_map — mapper mutates in place
            updated_claim_map = copy.deepcopy(claim_map)

            from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

            analyzer = ClaimMapAnalyzer()
            updated_claim_map = await analyzer.map_evidence_to_elements(
                updated_claim_map, all_evidence_for_mapping
            )

            # Restore bounty_text from original claim_map
            # (mapper sets evidence_refs, state, uncertainty but not bounty_text)
            for orig_elem in claim_map.get("elements", []):
                bt = orig_elem.get("bounty_text")
                if bt:
                    for new_elem in updated_claim_map.get("elements", []):
                        if new_elem.get("element_id") == orig_elem.get("element_id"):
                            new_elem["bounty_text"] = bt
                            break

            # 7. Save to DB
            # Save new evidence records
            for ev_data in deduped:
                evidence_id = ev_data.get("evidence_id")
                if not evidence_id:
                    url_hash = hashlib.sha256(
                        ev_data.get("url", "").encode()
                    ).hexdigest()[:12]
                    evidence_id = f"ev-{url_hash}"

                new_ev = Evidence(
                    claim_id=claim_id,
                    evidence_id=evidence_id,
                    source=ev_data.get("source", "Unknown"),
                    url=ev_data.get("url", ""),
                    title=ev_data.get("title", ""),
                    snippet=ev_data.get("snippet", ev_data.get("text", "")),
                    published_date=parse_date(ev_data.get("published_date")),
                    date_basis=ev_data.get("date_basis"),
                    relevance_score=float(ev_data.get("relevance_score", 0.0) or 0.0),
                    tier=ev_data.get("tier"),
                    evidence_type=ev_data.get("evidence_type"),
                    receipt_status=ev_data.get("receipt_status", "shown"),
                    external_source_provider=ev_data.get("external_source_provider"),
                )
                session.add(new_ev)

            # Update claim_map on claim
            db_claim.claim_map = updated_claim_map
            flag_modified(db_claim, "claim_map")

            await session.commit()

            update(
                "completed",
                f"Found {len(deduped)} new source{'s' if len(deduped) != 1 else ''}",
                newEvidenceCount=len(deduped),
            )
            logger.info(
                f"[RE-SEARCH] Element {element_id}: added {len(deduped)} new evidence items"
            )

    except Exception as e:
        logger.error(f"[RE-SEARCH] Error for element {element_id}: {e}")
        import traceback

        logger.error(f"[RE-SEARCH] Traceback: {traceback.format_exc()}")
        update("error", f"Research failed: {str(e)[:200]}")
