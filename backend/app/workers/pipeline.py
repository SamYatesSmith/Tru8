"""
Pipeline helper functions for inline SSE execution.

This module contains the core pipeline stage functions used by both
the inline runner (app/pipeline/runner.py) and other components.
Celery has been removed - all processing happens inline with SSE streaming.
"""

from typing import Dict, List, Any, Optional
import asyncio
import logging
from datetime import datetime
from app.pipeline.ingest import UrlIngester, ImageIngester, VideoIngester
from app.pipeline.extract import ClaimExtractor
from app.pipeline.retrieve import EvidenceRetriever
from app.services.cache import get_cache_service
from app.core.config import settings

logger = logging.getLogger(__name__)


async def ingest_content_async(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Real ingest implementation using pipeline classes"""
    input_type = input_data.get("input_type")

    try:
        if input_type == "text":
            return {
                "success": True,
                "content": input_data.get("content", ""),
                "metadata": {
                    "input_type": "text",
                    "word_count": len(input_data.get("content", "").split()),
                },
            }
        elif input_type == "url":
            url_ingester = UrlIngester()
            return await url_ingester.process(input_data.get("url", ""))
        elif input_type == "image":
            image_ingester = ImageIngester()
            return await image_ingester.process(input_data.get("file_path", ""))
        elif input_type == "video":
            video_ingester = VideoIngester()
            return await video_ingester.process(input_data.get("url", ""))
        else:
            return {
                "success": False,
                "error": f"Unsupported input type: {input_type}",
                "content": "",
            }
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        return {"success": False, "error": str(e), "content": ""}


async def extract_claims_with_cache(
    content: str, metadata: Dict[str, Any], cache_service
) -> List[Dict[str, Any]]:
    """Extract claims using LLM with caching"""
    try:
        # Try cache first using content hash and model name
        model_name = "gpt-4o-mini"  # Default extraction model

        # Check cache if available
        if cache_service:
            cached_claims = await cache_service.get_cached_claim_extraction(
                content, model_name
            )
            if cached_claims:
                logger.info("Using cached claim extraction")
                # BUGFIX: Add current metadata to cached claims (may be missing from old cache)
                for claim in cached_claims:
                    claim["source_title"] = metadata.get("title") if metadata else None
                    claim["source_url"] = metadata.get("url") if metadata else None
                    claim["source_date"] = metadata.get("date") if metadata else None
                logger.info(f"Added metadata to {len(cached_claims)} cached claims")
                return cached_claims

        # Extract claims with real LLM
        extractor = ClaimExtractor()
        extraction_result = await extractor.extract_claims(content, metadata)

        if extraction_result.get("success"):
            claims = extraction_result.get("claims", [])
            # Cache the result if cache is available
            if cache_service:
                await cache_service.cache_claim_extraction(content, model_name, claims)
            return claims
        else:
            logger.warning(f"LLM extraction failed: {extraction_result.get('error')}")
            # Fallback to simple extraction
            fallback_claims = extract_claims_fallback(content)
            return fallback_claims

    except Exception as e:
        logger.error(f"Claims extraction error: {e}")
        return extract_claims_fallback(content)


async def search_factchecks_for_claims(
    claims: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Search for existing fact-checks for claims"""
    from app.services.factcheck_api import FactCheckAPI

    factcheck_api = FactCheckAPI()
    factcheck_evidence = {}
    seen_urls = set()  # Cross-claim URL dedup

    for claim in claims:
        claim_text = claim.get("text", "")
        position = str(claim.get("position", 0))

        # Search for fact-checks
        fact_checks = await factcheck_api.search_fact_checks(claim_text)

        if fact_checks:
            # Convert to evidence format with text extraction + cross-claim URL dedup
            evidence_items = []
            for fc in fact_checks:
                url = fc.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                extracted_text = await factcheck_api._extract_factcheck_text(url)
                ev = factcheck_api.convert_to_evidence(
                    fc, claim_text, extracted_text=extracted_text
                )
                evidence_items.append(ev)

            factcheck_evidence[position] = evidence_items
            logger.info(
                f"Found {len(evidence_items)} fact-checks for claim position {position}"
            )

    return factcheck_evidence


async def retrieve_evidence_with_cache(
    claims: List[Dict[str, Any]],
    cache_service,
    factcheck_evidence: Dict = None,
    source_url: Optional[str] = None,
    progressive_results: Optional[Dict] = None,
    max_queries_per_element: Optional[int] = None,
    enable_api_adapters: Optional[bool] = None,
    max_sources_per_claim: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrieve evidence using real search and embeddings with caching.

    Returns:
        Dict with keys:
        - evidence_by_claim: Dict[str, List[Dict]] - Filtered evidence by claim position
        - raw_evidence: List[Dict] - All sources reviewed with filtering metadata
        - raw_sources_count: int - Total count of raw sources
    """
    import time as _time

    _wrapper_start = _time.time()
    if factcheck_evidence is None:
        factcheck_evidence = {}

    try:
        logger.info(
            f"[EVIDENCE DEBUG] Starting retrieve_evidence_with_cache for {len(claims)} claims"
        )
        retriever = EvidenceRetriever()
        # Apply config overrides from PipelineConfig (L-04)
        if max_sources_per_claim is not None:
            retriever.max_sources_per_claim = max_sources_per_claim
        if enable_api_adapters is not None:
            retriever.enable_api_retrieval = enable_api_adapters
        if max_queries_per_element is not None:
            retriever.max_queries_per_element = max_queries_per_element
        logger.info(
            f"[EVIDENCE DEBUG] EvidenceRetriever created, search_service providers: {[p.__class__.__name__ for p in retriever.search_service.providers]}"
        )

        # Check if we have cached evidence for each claim
        cached_evidence = {}
        uncached_claims = []

        _cache_start = _time.time()
        for claim in claims:
            claim_text = claim.get("text", "")
            position = str(claim.get("position", 0))
            # Check cache if available
            if cache_service:
                cached_result = await cache_service.get_cached_evidence_extraction(
                    claim_text
                )
                if cached_result:
                    cached_evidence[position] = cached_result
                    logger.info(
                        f"[CACHE HIT] Claim {position}: retrieved {len(cached_result)} cached evidence items"
                    )
                    continue
            # If no cache or no cached result, add to uncached list
            uncached_claims.append(claim)

        _cache_elapsed = _time.time() - _cache_start
        logger.info(
            f"[EVIDENCE DEBUG] Cache check: {len(cached_evidence)} cached, {len(uncached_claims)} uncached"
        )

        # Retrieve evidence for uncached claims
        all_raw_evidence = []
        pre_weighting_by_claim = {}
        if uncached_claims:
            logger.info(
                f"[EVIDENCE DEBUG] Retrieving evidence for {len(uncached_claims)} uncached claims"
            )
            _retrieve_start = _time.time()
            retrieval_result = await retriever.retrieve_evidence_for_claims(
                uncached_claims,
                exclude_source_url=source_url,
                progressive_results=progressive_results,
            )
            _retrieve_elapsed = _time.time() - _retrieve_start
            logger.info(
                f"[EVIDENCE DEBUG] retrieve_evidence_for_claims returned type: {type(retrieval_result)}"
            )

            # Extract evidence and raw evidence from new structure
            if (
                isinstance(retrieval_result, dict)
                and "evidence_by_claim" in retrieval_result
            ):
                new_evidence = retrieval_result["evidence_by_claim"]
                all_raw_evidence = retrieval_result.get("raw_evidence", [])
                pre_weighting_by_claim = retrieval_result.get(
                    "pre_weighting_evidence", {}
                )

                # A8b: diagnostic instrumentation — was logger.critical, but
                # this is a normal stage-completion summary, not an error.
                # Demoted to INFO so Sentry no longer flags routine pipeline
                # runs as critical events.
                total_ev = sum(len(ev) for ev in new_evidence.values())
                logger.info(
                    f"[EVIDENCE CRITICAL] Retrieved {total_ev} total evidence items for {len(new_evidence)} claims"
                )
                for pos, ev_list in new_evidence.items():
                    logger.info(
                        f"[EVIDENCE DEBUG] Claim {pos}: {len(ev_list)} evidence items"
                    )
                    if ev_list:
                        logger.info(
                            f"[EVIDENCE DEBUG] First item: source={ev_list[0].get('source', 'N/A')}, url={ev_list[0].get('url', 'N/A')[:60]}"
                        )
            else:
                # Backward compatibility: old format returned Dict[str, List]
                new_evidence = (
                    retrieval_result if isinstance(retrieval_result, dict) else {}
                )
                all_raw_evidence = []

            # Quality-gated caching: only cache evidence that meets minimum count
            # This prevents poor results (from rate limiting, timeouts, etc.) from being cached
            if cache_service:
                for claim in uncached_claims:
                    claim_text = claim.get("text", "")
                    position = str(claim.get("position", 0))
                    evidence_list = new_evidence.get(position, [])

                    # Quality gate: Minimum evidence count
                    if len(evidence_list) < settings.MIN_SOURCES_FOR_CACHE:
                        logger.info(
                            f"[CACHE SKIP] Claim {position}: insufficient evidence ({len(evidence_list)} < {settings.MIN_SOURCES_FOR_CACHE})"
                        )
                        continue

                    # Quality gate passed - cache this evidence
                    await cache_service.cache_evidence_extraction(
                        claim_text, evidence_list
                    )
                    logger.info(
                        f"[CACHE OK] Claim {position}: cached {len(evidence_list)} evidence items"
                    )

            # Merge cached and new evidence
            cached_evidence.update(new_evidence)

        # Merge fact-check evidence (prepend to give it priority)
        for position, fc_evidence in factcheck_evidence.items():
            if position in cached_evidence:
                cached_evidence[position] = fc_evidence + cached_evidence[position]
            else:
                cached_evidence[position] = fc_evidence

        return {
            "evidence_by_claim": cached_evidence,
            "raw_evidence": all_raw_evidence,
            "raw_sources_count": len(all_raw_evidence),
            "pre_weighting_evidence": pre_weighting_by_claim,
        }

    except Exception as e:
        logger.error(f"Evidence retrieval error: {e}")
        logger.critical(
            f"Evidence retrieval failed in {settings.ENVIRONMENT} environment: {e}"
        )
        return {"evidence_by_claim": {}, "raw_evidence": [], "raw_sources_count": 0}


def extract_claims_fallback(content: str) -> List[Dict[str, Any]]:
    """Mock claim extraction - Week 3 will implement real LLM"""
    if not content.strip():
        return [{"text": "No claims found in empty content", "position": 0}]

    # Simple sentence splitting as mock
    sentences = [s.strip() for s in content.split(".") if s.strip()]
    claims = []

    for i, sentence in enumerate(sentences[:6]):  # Max 6 claims for demo
        if len(sentence) > 20:  # Only substantial sentences
            claims.append({"text": sentence + ".", "position": i})

    if not claims:
        claims = [{"text": content[:200] + "...", "position": 0}]

    return claims
