"""One bounded claim-level strengthening pass; persistence belongs to its operation."""

import copy
import json
import uuid
import redis
from app.core.config import settings
from app.services.evidence_payload import prepare_new_evidence


def _update_status(check_id, claim_id, element_id, status, message, **extra):
    """Legacy watchdog compatibility; new operations use PostgreSQL."""
    try:
        redis.from_url(settings.REDIS_URL, decode_responses=True).set(
            f"element-research:{check_id}:{claim_id}:{element_id}",
            json.dumps({"status": status, "message": message, **extra}),
            ex=600,
        )
    except Exception:
        pass


def get_research_status(check_id, claim_id, element_id):
    """Read statuses of pre-migration tasks only."""
    try:
        raw = redis.from_url(settings.REDIS_URL, decode_responses=True).get(
            f"element-research:{check_id}:{claim_id}:{element_id}"
        )
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def research_claim(claim: dict, element_ids: list[str], progress):
    """Retrieve selected elements together, deduplicate and map exactly once.

    No database writes occur here. The caller owns rollback and refunds.
    """
    from app.utils.query_planner import get_query_planner
    from app.pipeline.retrieve import EvidenceRetriever
    from app.pipeline.evidence_classifier import EvidenceClassifier
    from app.pipeline.evidence_distiller import EvidenceDistiller
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    cm = copy.deepcopy(claim["claimMap"])
    targets = [e for e in cm["elements"] if e["element_id"] in element_ids]
    if {e["element_id"] for e in targets} != set(element_ids):
        raise ValueError("Research targets no longer match the claim")
    elements = [
        {
            "element_id": e["element_id"],
            "description": e["description"]
            + (
                f" (Research brief: {e['bounty_text']})" if e.get("bounty_text") else ""
            ),
        }
        for e in targets
    ]
    await progress("planning", "Planning search queries...")
    plans = await get_query_planner().plan_queries_batch(
        [{"text": claim["text"], "claim_index": 0, "elements": elements}]
    )
    if not plans or not any(p.get("queries") for p in plans):
        raise RuntimeError("No search queries could be generated")
    merged = {
        "queries": [],
        "query_element_ids": [],
        "query_freshness": [],
        "claim_index": 0,
        "freshness": plans[0].get("freshness", "py"),
        "reasoning": plans[0].get("reasoning", ""),
    }
    for plan in plans:
        for query in plan.get("queries", []):
            merged["queries"].append(query)
            merged["query_element_ids"].append(
                plan.get("element_id", elements[0]["element_id"])
            )
            merged["query_freshness"].append(plan.get("freshness", "py"))
    await progress("retrieving", "Searching for new evidence...")
    result = await EvidenceRetriever().retrieve_evidence_for_claims(
        [
            {
                "text": claim["text"],
                "position": 0,
                "elements": elements,
                "query_plan": merged,
            }
        ]
    )
    candidates = prepare_new_evidence(
        result.get("evidence_by_claim", {}).get("0", []),
        {e["url"] for e in claim["evidence"]},
    )
    if not candidates:
        return cm, []
    # Retriever-local IDs can repeat an original run's IDs. Resolve collisions
    # before mapping, without changing any existing references.
    used_ids = {e.get("evidence_id") or e["id"] for e in claim["evidence"]}
    for candidate in candidates:
        if candidate["evidence_id"] in used_ids:
            candidate["evidence_id"] = "ev-research-" + uuid.uuid4().hex
        used_ids.add(candidate["evidence_id"])
    await progress("classifying", "Classifying new evidence...")
    candidates = await EvidenceClassifier().classify_batch(candidates)
    for ev in candidates:
        ev["receipt_status"] = "classified"
    if settings.ENABLE_EVIDENCE_DISTILLATION:
        await progress("distilling", "Reading the new evidence...")
        candidates = await EvidenceDistiller().distil_evidence_for_claim(
            claim["text"], candidates
        )
        # Mapper reads snippet first: do not bypass distilled facts with a stale
        # search snippet or persist that snippet under a 'distilled' receipt.
        for ev in candidates:
            if ev.get("_distilled"):
                ev["snippet"] = ev["text"]
    existing = [
        {**e, "evidence_id": e.get("evidence_id") or e["id"], "text": e["snippet"]}
        for e in claim["evidence"]
        if e.get("receipt_status") != "excluded"
    ]
    await progress("mapping", "Mapping the combined evidence...")
    updated = await ClaimMapAnalyzer().map_evidence_to_elements(
        cm, existing + candidates
    )
    if {e["element_id"] for e in updated["elements"]} != {
        e["element_id"] for e in claim["claimMap"]["elements"]
    }:
        raise RuntimeError("Research changed the claim's element identities")
    briefs = {
        e["element_id"]: e.get("bounty_text") for e in claim["claimMap"]["elements"]
    }
    for element in updated["elements"]:
        if briefs.get(element["element_id"]):
            element["bounty_text"] = briefs[element["element_id"]]
    return updated, candidates
