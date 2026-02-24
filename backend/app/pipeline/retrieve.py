import copy
import hashlib
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone
import os
from app.services.search import SearchService, SearchResult
from app.services.evidence import EvidenceExtractor, EvidenceSnippet
from app.services.embeddings import get_embedding_service
from app.services.vector_store import get_vector_store
from app.utils.url_utils import extract_domain
from app.services.government_api_client import get_api_registry
from app.core.config import settings

logger = logging.getLogger(__name__)

SATIRE_DOMAINS = {
    "theonion.com",
    "babylonbee.com",
    "clickhole.com",
    "thebeaverton.com",
    "waterfordwhispersnews.com",
    "thedailymash.co.uk",
    "newsthump.com",
    "borowitz-report.newyorker.com",
    "reductress.com",
    "hard-drive.net",
}


class EvidenceRetriever:
    """Retrieve and rank evidence for claims using search, embeddings, and vector storage"""

    # Minimum evidence per claim - triggers recovery search if below this threshold
    MIN_EVIDENCE_PER_CLAIM = 2

    # Authoritative sources by domain for targeted recovery searches
    AUTHORITATIVE_SOURCES_BY_DOMAIN = {
        "health": [
            "who.int",
            "cdc.gov",
            "nih.gov",
            "nhs.uk",
            "pubmed.ncbi.nlm.nih.gov",
        ],
        "science": ["nature.com", "science.org", "ncbi.nlm.nih.gov", "arxiv.org"],
        "government": ["gov.uk", "usa.gov", "congress.gov", "govinfo.gov"],
        "finance": ["sec.gov", "federalreserve.gov", "imf.org", "worldbank.org"],
        "sports": ["transfermarkt.com", "espn.com", "bbc.com/sport"],
        "general": ["reuters.com", "apnews.com", "bbc.com"],
    }

    # Mapping from temporal_window (from claim extraction) to Brave freshness parameter
    # temporal_window values: current_day, current_week, current_month, current_year, any, historical
    # Brave freshness values: pd (past day), pw (past week), pm (past month), py (past year), 2y (2 years)
    TEMPORAL_TO_FRESHNESS = {
        "current_day": "pd",  # Past day - breaking news, live events
        "current_week": "pw",  # Past week - recent developments
        "current_month": "pm",  # Past month - recent news
        "current_year": "py",  # Past year - annual events, seasons
        "any": "2y",  # Default 2 years
        "historical": "2y",  # Historical claims - use 2 years
    }

    def __init__(self):
        self.search_service = SearchService()
        self.evidence_extractor = EvidenceExtractor()
        self.max_sources_per_claim = 20
        self.max_concurrent_claims = 3

        # Phase 5: Government API Integration
        self.api_registry = get_api_registry()
        self.enable_api_retrieval = True  # Feature flag (set via settings)

    async def retrieve_evidence_for_claims(
        self,
        claims: List[Dict[str, Any]],
        exclude_source_url: Optional[str] = None,
        progressive_results: Optional[Dict] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve evidence for multiple claims concurrently.

        Args:
            progressive_results: Optional shared dict. If provided, results are
                written progressively as each claim completes so the caller can
                read partial results on timeout.
        """
        import time as _time

        _func_start = _time.time()
        logger.info(
            f"[RETRIEVER DEBUG] retrieve_evidence_for_claims called with {len(claims)} claims"
        )
        try:
            # Extract excluded domain if provided
            excluded_domain = None
            if exclude_source_url:
                excluded_domain = extract_domain(exclude_source_url)
                logger.debug(f"Excluding source domain: {excluded_domain}")

            # Query Planning Agent: Generate targeted queries for all claims (single LLM call)
            query_plans = None
            logger.info(
                f"[RETRIEVE] QUERY_PLANNING_ENABLED: {settings.ENABLE_QUERY_PLANNING}"
            )
            if settings.ENABLE_QUERY_PLANNING:
                try:
                    from app.utils.query_planner import get_query_planner

                    planner = get_query_planner()

                    # Phase 4: Pass article context to query planner for dynamic freshness decisions
                    article_context = None
                    if claims and claims[0].get("article_classification"):
                        article_context = claims[0]["article_classification"]
                        logger.info(
                            f"[RETRIEVE] Passing article context to query planner: domain={article_context.get('primary_domain')}"
                        )

                    # Build claims_with_elements for element-level query planning
                    claims_with_elements = []
                    for i, claim in enumerate(claims):
                        elements = claim.get("elements", [])
                        if elements:
                            elem_list = [
                                {
                                    "element_id": el.get("element_id", f"e{j+1}"),
                                    "description": el.get("description", ""),
                                }
                                for j, el in enumerate(elements)
                            ]
                        else:
                            # Pre-decomposition: synthetic single element from claim text
                            elem_list = [
                                {
                                    "element_id": "e1",
                                    "description": claim.get("text", ""),
                                }
                            ]
                        claims_with_elements.append(
                            {
                                "text": claim.get("text", ""),
                                "claim_index": i,
                                "elements": elem_list,
                            }
                        )

                    _qp_start = _time.time()
                    query_plans = await planner.plan_queries_batch(
                        claims_with_elements, article_context=article_context
                    )
                    _qp_elapsed = _time.time() - _qp_start
                    if query_plans:
                        logger.info(
                            f"Query planning complete: {len(query_plans)} element plans "
                            f"for {len(claims)} claims"
                        )
                        # Group plans by claim_index and build merged query plans
                        plans_by_claim = {}
                        for plan in query_plans:
                            idx = plan.get("claim_index", 0)
                            if idx not in plans_by_claim:
                                plans_by_claim[idx] = []
                            plans_by_claim[idx].append(plan)

                        for claim_idx, plans in plans_by_claim.items():
                            if claim_idx < len(claims):
                                # Merge element plans into one query_plan with element tracking
                                merged_queries = []
                                query_element_ids = []
                                query_freshness = []
                                for p in plans:
                                    element_id = p.get("element_id", "e1")
                                    element_freshness = p.get("freshness", "py")
                                    for q in p.get("queries", []):
                                        merged_queries.append(q)
                                        query_element_ids.append(element_id)
                                        query_freshness.append(element_freshness)
                                claims[claim_idx]["query_plan"] = {
                                    "queries": merged_queries,
                                    "query_element_ids": query_element_ids,
                                    "query_freshness": query_freshness,
                                    "claim_index": claim_idx,
                                    "freshness": plans[0].get("freshness", "py"),
                                    "reasoning": plans[0].get("reasoning", ""),
                                }
                    else:
                        logger.warning(
                            "Query planning returned no plans, using fallback"
                        )
                except Exception as e:
                    logger.warning(f"Query planning failed: {e}, using fallback")

            # Process claims with concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrent_claims)

            # Shared accumulators — written progressively as each claim completes
            evidence_by_claim = {}
            all_raw_evidence = []
            pre_weighting_by_claim = {}

            # Expose accumulators to caller for partial recovery on timeout
            if progressive_results is not None:
                progressive_results["evidence_by_claim"] = evidence_by_claim
                progressive_results["raw_evidence"] = all_raw_evidence
                progressive_results["pre_weighting_evidence"] = pre_weighting_by_claim

            async def _retrieve_and_store(claim_index: int, claim: Dict):
                """Retrieve evidence for one claim and store immediately."""
                try:
                    result = await self._retrieve_evidence_for_single_claim(
                        claim, semaphore, excluded_domain
                    )
                except Exception as exc:
                    logger.error(
                        f"[RETRIEVER DEBUG] Result {claim_index}: EXCEPTION {type(exc).__name__}: {exc}"
                    )
                    evidence_by_claim[str(claim_index)] = []
                    return

                if isinstance(result, dict):
                    evidence_by_claim[str(claim_index)] = result.get(
                        "filtered_evidence", []
                    )
                    pre_weighting_by_claim[str(claim_index)] = result.get(
                        "pre_weighting_evidence", []
                    )
                    raw_evidence = result.get("raw_evidence", [])
                    claim_position = result.get("claim_position", claim_index)
                    claim_text = result.get("claim_text", "")
                    for raw_item in raw_evidence:
                        raw_item["claim_position"] = claim_position
                        raw_item["claim_text"] = claim_text
                    all_raw_evidence.extend(raw_evidence)
                    logger.info(
                        f"[RETRIEVER DEBUG] Result {claim_index}: dict with "
                        f"{len(result.get('filtered_evidence', []))} filtered, "
                        f"{len(result.get('raw_evidence', []))} raw"
                    )
                else:
                    # Legacy list format (backward compatibility)
                    evidence_by_claim[str(claim_index)] = (
                        result if isinstance(result, list) else []
                    )

            _gather_start = _time.time()
            logger.info(f"[RETRIEVER DEBUG] Gathering results for {len(claims)} tasks")
            await asyncio.gather(
                *[_retrieve_and_store(i, claim) for i, claim in enumerate(claims)],
                return_exceptions=True,
            )
            _gather_elapsed = _time.time() - _gather_start
            logger.info(
                f"[RETRIEVER DEBUG] Gather complete in {_gather_elapsed:.2f}s. "
                f"Claims completed: {len(evidence_by_claim)}"
            )

            # RECOVERY: Ensure minimum evidence per claim
            # This catches claims that ended up with insufficient evidence after initial retrieval
            _recovery_start = _time.time()
            evidence_by_claim, recovery_raw = await self._ensure_minimum_evidence(
                evidence_by_claim=evidence_by_claim,
                claims=claims,
                excluded_domain=excluded_domain,
            )
            _recovery_elapsed = _time.time() - _recovery_start
            all_raw_evidence.extend(recovery_raw)

            # Return both filtered evidence and raw evidence
            _func_elapsed = _time.time() - _func_start
            total_evidence = sum(len(ev) for ev in evidence_by_claim.values())
            return {
                "evidence_by_claim": evidence_by_claim,
                "raw_evidence": all_raw_evidence,
                "raw_sources_count": len(all_raw_evidence),
                "pre_weighting_evidence": pre_weighting_by_claim,
            }

        except Exception as e:
            import traceback

            logger.error(
                f"[RETRIEVER DEBUG] Evidence retrieval EXCEPTION: {type(e).__name__}: {e}"
            )
            logger.error(f"[RETRIEVER DEBUG] Full traceback:\n{traceback.format_exc()}")
            return {"evidence_by_claim": {}, "raw_evidence": [], "raw_sources_count": 0}

    async def _ensure_minimum_evidence(
        self,
        evidence_by_claim: Dict[str, List[Dict[str, Any]]],
        claims: List[Dict[str, Any]],
        excluded_domain: Optional[str] = None,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """
        Ensure each claim has minimum evidence, triggering recovery search if needed.

        This runs AFTER initial retrieval to catch claims that ended up with
        insufficient evidence. Recovery uses targeted authoritative-source queries.

        Args:
            evidence_by_claim: Current evidence dict (claim_position -> evidence list)
            claims: List of claim dicts with text and metadata
            excluded_domain: Domain to exclude from search

        Returns:
            Tuple of (updated evidence_by_claim, raw_evidence from recovery)
        """
        # Identify claims needing recovery
        claims_needing_recovery = []
        for claim in claims:
            claim_pos = str(claim.get("position", 0))
            current_evidence = evidence_by_claim.get(claim_pos, [])

            if len(current_evidence) < self.MIN_EVIDENCE_PER_CLAIM:
                claims_needing_recovery.append(
                    {
                        "claim": claim,
                        "position": claim_pos,
                        "current_count": len(current_evidence),
                    }
                )

        if not claims_needing_recovery:
            return evidence_by_claim, []

        logger.warning(
            f"[RECOVERY] {len(claims_needing_recovery)} claims below minimum evidence "
            f"(min={self.MIN_EVIDENCE_PER_CLAIM}): positions {[c['position'] for c in claims_needing_recovery]}"
        )

        # Collect existing URLs to avoid duplicates
        existing_urls = set()
        for ev_list in evidence_by_claim.values():
            for ev in ev_list:
                if ev.get("url"):
                    existing_urls.add(ev.get("url"))

        # Run recovery for all claims in parallel (with rate limiting via semaphore)
        all_recovery_raw = []
        semaphore = asyncio.Semaphore(2)  # Limit concurrent recovery searches

        async def recover_single_claim(claim_info):
            async with semaphore:
                return await self._recover_evidence_for_claim(
                    claim=claim_info["claim"],
                    claim_position=claim_info["position"],
                    existing_urls=existing_urls,
                    excluded_domain=excluded_domain,
                )

        recovery_tasks = [recover_single_claim(c) for c in claims_needing_recovery]
        recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)

        # Process recovery results
        for claim_info, result in zip(claims_needing_recovery, recovery_results):
            claim_pos = claim_info["position"]

            if isinstance(result, Exception):
                logger.error(f"[RECOVERY] Failed for claim {claim_pos}: {result}")
                continue

            recovered_evidence, raw_evidence = result

            if recovered_evidence:
                # Add recovered evidence to the claim
                if claim_pos not in evidence_by_claim:
                    evidence_by_claim[claim_pos] = []
                evidence_by_claim[claim_pos].extend(recovered_evidence)

                # Add URLs to existing set to prevent duplicates in subsequent claims
                for ev in recovered_evidence:
                    if ev.get("url"):
                        existing_urls.add(ev.get("url"))

                logger.info(
                    f"[RECOVERY] Claim {claim_pos}: recovered {len(recovered_evidence)} items "
                    f"(now has {len(evidence_by_claim[claim_pos])} total)"
                )
            else:
                logger.warning(f"[RECOVERY] Claim {claim_pos}: no evidence recovered")

            all_recovery_raw.extend(raw_evidence)

        return evidence_by_claim, all_recovery_raw

    async def _recover_evidence_for_claim(
        self,
        claim: Dict[str, Any],
        claim_position: str,
        existing_urls: set,
        excluded_domain: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Run targeted recovery search for a single claim with insufficient evidence.

        Uses authoritative-source-focused queries based on claim domain.

        Args:
            claim: Claim dict with text and metadata
            claim_position: Position string for logging
            existing_urls: URLs already in evidence pool (for deduplication)
            excluded_domain: Domain to exclude

        Returns:
            Tuple of (filtered_evidence, raw_evidence_metadata)
        """
        claim_text = claim.get("text", "")
        if not claim_text:
            return [], []

        try:
            # Determine domain for authoritative source selection
            article_classification = claim.get("article_classification", {})
            primary_domain = article_classification.get(
                "primary_domain", "general"
            ).lower()

            # Map to our domain categories
            domain_key = "general"
            if any(
                d in primary_domain for d in ["health", "medical", "disease", "virus"]
            ):
                domain_key = "health"
            elif any(d in primary_domain for d in ["science", "research", "study"]):
                domain_key = "science"
            elif any(d in primary_domain for d in ["government", "politics", "law"]):
                domain_key = "government"
            elif any(d in primary_domain for d in ["finance", "economic", "market"]):
                domain_key = "finance"
            elif any(d in primary_domain for d in ["sport"]):
                domain_key = "sports"

            authoritative_sources = self.AUTHORITATIVE_SOURCES_BY_DOMAIN.get(
                domain_key, []
            )

            logger.info(
                f"[RECOVERY] Claim {claim_position}: domain={domain_key}, "
                f"authoritative sources={authoritative_sources[:3]}"
            )

            # Generate targeted queries
            # Query 1: Direct claim text with site filter for authoritative sources
            # Query 2: Simplified key phrase extraction
            queries = self._generate_recovery_queries(claim_text, authoritative_sources)

            if not queries:
                logger.warning(
                    f"[RECOVERY] No queries generated for claim {claim_position}"
                )
                return [], []

            # Execute searches
            all_snippets = []
            for query in queries[:2]:  # Limit to 2 queries to control latency
                try:
                    results = await self.search_service.search_for_evidence(
                        query, max_results=5, freshness="py"  # Past year - stable facts
                    )
                    if results:
                        # Convert SearchResult to EvidenceSnippet format
                        for r in results:
                            # Skip if URL already exists
                            url = (
                                getattr(r, "url", "")
                                if hasattr(r, "url")
                                else r.get("url", "")
                            )
                            if url in existing_urls:
                                continue

                            snippet = EvidenceSnippet(
                                text=(
                                    getattr(r, "snippet", "")
                                    if hasattr(r, "snippet")
                                    else r.get("snippet", "")
                                ),
                                source=(
                                    getattr(r, "source", "")
                                    if hasattr(r, "source")
                                    else r.get("source", "")
                                ),
                                url=url,
                                title=(
                                    getattr(r, "title", "")
                                    if hasattr(r, "title")
                                    else r.get("title", "")
                                ),
                                published_date=(
                                    getattr(r, "published_date", None)
                                    if hasattr(r, "published_date")
                                    else r.get("published_date")
                                ),
                                relevance_score=0.0,  # No hardcoded score, LLM scorer decides
                                # word_count is calculated automatically in EvidenceSnippet.__init__
                                metadata={
                                    "recovery_search": True,
                                    "domain_key": domain_key,
                                },
                            )
                            all_snippets.append(snippet)

                except Exception as e:
                    logger.warning(
                        f"[RECOVERY] Search failed for query '{query[:50]}...': {e}"
                    )
                    continue

            if not all_snippets:
                return [], []

            # Apply same evidence filtering as main retrieval
            # This ensures satire exclusion, dedup, etc. are applied
            ranked_evidence = []
            for idx, snippet in enumerate(
                all_snippets[:10]
            ):  # Cap at 10 for processing
                ev_hash = hashlib.sha256((snippet.url or "").encode()).hexdigest()[:8]
                ranked_evidence.append(
                    {
                        "id": f"recovery_{claim_position}_{idx}",
                        "evidence_id": f"ev-rec-{claim_position}_{idx}_{ev_hash}",
                        "element_ids": [],
                        "text": snippet.text,
                        "source": snippet.source,
                        "url": snippet.url,
                        "title": snippet.title,
                        "published_date": snippet.published_date,
                        "relevance_score": float(snippet.relevance_score),
                        "semantic_similarity": 0.0,
                        "combined_score": 0.0,
                        "word_count": snippet.word_count,
                        "receipt_status": "extracted",
                        "metadata": snippet.metadata,
                        "is_recovery": True,
                    }
                )

            # Apply evidence filters (satire exclusion + dedup)
            result = self._apply_evidence_filters(
                ranked_evidence, claim, track_raw_evidence=True
            )
            final_evidence, raw_evidence = (
                result if isinstance(result, tuple) else (result, [])
            )

            # Mark raw evidence as from recovery
            for raw_item in raw_evidence:
                raw_item["is_recovery"] = True
                raw_item["claim_position"] = claim_position

            return final_evidence, raw_evidence

        except Exception as e:
            logger.error(
                f"[RECOVERY] Error recovering evidence for claim {claim_position}: {e}"
            )
            return [], []

    def _generate_recovery_queries(
        self, claim_text: str, authoritative_sources: List[str]
    ) -> List[str]:
        """
        Generate targeted queries for recovery search.

        Focuses on authoritative sources and simplified query formulation.

        Args:
            claim_text: Original claim text
            authoritative_sources: List of authoritative domains for this claim type

        Returns:
            List of search queries
        """
        import re

        queries = []

        # Extract key phrases (nouns, numbers, proper nouns)
        # Simple extraction: words > 3 chars, exclude common words
        stop_words = {
            "the",
            "and",
            "for",
            "are",
            "was",
            "were",
            "been",
            "have",
            "has",
            "had",
            "will",
            "would",
            "could",
            "should",
            "this",
            "that",
            "with",
            "from",
            "they",
            "their",
            "there",
            "what",
            "when",
            "where",
            "which",
            "about",
            "into",
            "than",
            "then",
            "can",
            "may",
            "also",
            "some",
            "only",
            "more",
            "most",
            "other",
        }

        words = re.findall(r"\b[a-zA-Z]{4,}\b", claim_text)
        key_words = [w for w in words if w.lower() not in stop_words][:6]

        # Also extract numbers (important for factual claims)
        numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", claim_text)

        # Query 1: Key words + numbers (general search)
        base_query = " ".join(key_words[:4])
        if numbers:
            base_query += " " + " ".join(numbers[:2])
        queries.append(base_query)

        # Query 2: With site filter for top authoritative source
        if authoritative_sources:
            site_query = f"{base_query} site:{authoritative_sources[0]}"
            queries.append(site_query)

        # Query 3: Alternative formulation with "official" or "fact sheet"
        if key_words:
            alt_query = f"{key_words[0]} official information"
            queries.append(alt_query)

        return queries

    async def _retrieve_evidence_for_single_claim(
        self,
        claim: Dict[str, Any],
        semaphore: asyncio.Semaphore,
        excluded_domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve evidence for a single claim.

        Returns:
            Dict with keys: filtered_evidence, raw_evidence, claim_position, claim_text
        """
        async with semaphore:
            try:
                claim_text = claim.get("text", "")
                claim_position = claim.get("position", 0)

                if not claim_text:
                    return []

                logger.debug(f"Processing claim {claim_position}")

                # FROZEN EVIDENCE REPLAY: Skip ALL network, construct evidence directly
                frozen_evidence_items = claim.get("frozen_evidence")
                if frozen_evidence_items is not None:
                    logger.info(
                        f"[FROZEN EVIDENCE REPLAY] Claim {claim_position}: "
                        f"replaying {len(frozen_evidence_items)} frozen evidence items (zero network)"
                    )

                    if not frozen_evidence_items:
                        return {
                            "filtered_evidence": [],
                            "raw_evidence": [],
                            "pre_weighting_evidence": [],
                            "claim_position": claim_position,
                            "claim_text": claim_text[:500] if claim_text else "",
                            "search_mode": "frozen_evidence_replay",
                        }

                    # Reconstruct ranked_evidence from frozen data (same shape as lines 763-777)
                    ranked_evidence = []
                    for idx, item in enumerate(frozen_evidence_items):
                        text = item.get("text", "")
                        ranked_evidence.append(
                            {
                                "id": f"evidence_{idx}",
                                "evidence_id": item.get(
                                    "evidence_id",
                                    f"ev-{hashlib.sha256((item.get('url', '') + item.get('text', '')).encode()).hexdigest()[:12]}",
                                ),
                                "element_ids": item.get("element_ids", []),
                                "text": text,
                                "source": item.get("source", ""),
                                "url": item.get("url", ""),
                                "title": item.get("title", ""),
                                "published_date": item.get("published_date"),
                                "relevance_score": float(
                                    item.get("relevance_score", 0.0)
                                ),
                                "semantic_similarity": 0.0,
                                "combined_score": 0.0,
                                "word_count": len(text.split()) if text else 0,
                                "external_source_provider": item.get(
                                    "external_source_provider"
                                ),
                                "is_factcheck": item.get("is_factcheck", False),
                                "source_type": item.get("source_type"),
                                "receipt_status": "shown",
                                "metadata": item.get("metadata", {}),
                            }
                        )

                    # Run through evidence filters — SAME path as normal pipeline
                    result = self._apply_evidence_filters(
                        ranked_evidence, claim, track_raw_evidence=True
                    )
                    final_evidence, raw_evidence = (
                        result if isinstance(result, tuple) else (result, [])
                    )

                    return {
                        "filtered_evidence": final_evidence[
                            : self.max_sources_per_claim
                        ],
                        "raw_evidence": raw_evidence,
                        "pre_weighting_evidence": ranked_evidence,
                        "claim_position": claim_position,
                        "claim_text": claim_text[:500] if claim_text else "",
                        "search_mode": "frozen_evidence_replay",
                    }

                # Step 1: Parallel retrieval from web search AND government APIs
                subject_context = claim.get("subject_context")
                key_entities = claim.get("key_entities", [])
                temporal_analysis = claim.get(
                    "temporal_analysis"
                )  # TIER 1: For query refinement

                # Article context grounding (Phase 4)
                article_title = claim.get("source_title")
                article_date = claim.get("source_date")

                # Context logging moved to DEBUG to reduce noise
                if subject_context:
                    logger.debug(
                        f"Using context: '{subject_context}' with entities: {key_entities[:3]}"
                    )

                # Check for query plan (from Query Planning Agent)
                query_plan = claim.get("query_plan")

                # DEPRECATED: Extract freshness from temporal_analysis (now disabled, Query Planner provides freshness)
                freshness = None
                if temporal_analysis:
                    temporal_window = temporal_analysis.get("temporal_window", "any")
                    freshness = self.TEMPORAL_TO_FRESHNESS.get(temporal_window, "2y")
                    if freshness != "2y":
                        logger.info(
                            f"[RETRIEVE] FRESHNESS | Claim {claim_position} | temporal_window={temporal_window} -> freshness={freshness}"
                        )

                # Run web search and API retrieval in parallel
                if query_plan and query_plan.get("queries"):
                    # Use Query Planning Agent's targeted queries
                    web_search_task = self._execute_planned_queries(
                        claim_text,
                        query_plan,
                        excluded_domain=excluded_domain,
                        max_sources=self.max_sources_per_claim * 2,
                        freshness=freshness,
                    )
                    queries_preview = query_plan["queries"][:2]  # Show first 2 queries
                    logger.info(
                        f"[RETRIEVE] QUERY PLAN | Claim {claim_position} | Type: {query_plan.get('claim_type')} | Queries: {queries_preview}"
                    )
                else:
                    # Fallback: Standard query formulation
                    web_search_task = self.evidence_extractor.extract_evidence_for_claim(
                        claim_text,
                        max_sources=self.max_sources_per_claim
                        * 2,  # Get extra for filtering
                        subject_context=subject_context,
                        key_entities=key_entities,
                        excluded_domain=excluded_domain,
                        temporal_analysis=temporal_analysis,  # TIER 1: Pass to query formulation
                        article_title=article_title,  # Article context grounding
                        article_date=article_date,  # Article context grounding
                    )

                # Phase 5: Government API retrieval (parallel with web search)
                api_results_task = self._retrieve_from_government_apis(
                    claim_text, claim
                )

                # Await both tasks concurrently with per-claim timeout
                # IMPORTANT: Use asyncio.wait instead of wait_for+gather to preserve partial results
                # If one task completes but the other times out, we keep the completed results
                CLAIM_TIMEOUT = 45  # seconds per claim
                logger.info(
                    f"[SINGLE CLAIM DEBUG] Awaiting web search + API tasks for claim {claim_position} (timeout={CLAIM_TIMEOUT}s)"
                )

                # Wrap coroutines in named tasks so we can identify them after wait()
                web_task = asyncio.create_task(web_search_task, name="web_search")
                api_task = asyncio.create_task(api_results_task, name="api_retrieval")

                # Wait for tasks with timeout - returns (done, pending) sets
                done, pending = await asyncio.wait(
                    {web_task, api_task},
                    timeout=CLAIM_TIMEOUT,
                    return_when=asyncio.ALL_COMPLETED,
                )

                # Extract results from completed tasks, use defaults for timed-out ones
                web_evidence_snippets = []
                api_evidence = {"evidence": [], "api_stats": {}}
                timed_out_tasks = []

                for task in done:
                    try:
                        result = task.result()
                        if task.get_name() == "web_search":
                            web_evidence_snippets = (
                                result if not isinstance(result, Exception) else []
                            )
                            if isinstance(result, Exception):
                                logger.error(
                                    f"[CLAIM {claim_position}] Web search exception: {result}"
                                )
                        elif task.get_name() == "api_retrieval":
                            api_evidence = (
                                result
                                if not isinstance(result, Exception)
                                else {"evidence": [], "api_stats": {}}
                            )
                            if isinstance(result, Exception):
                                logger.error(
                                    f"[CLAIM {claim_position}] API retrieval exception: {result}"
                                )
                    except Exception as e:
                        logger.error(
                            f"[CLAIM {claim_position}] Error extracting task result: {e}"
                        )

                # Cancel any still-pending tasks and log what timed out
                for task in pending:
                    task.cancel()
                    timed_out_tasks.append(task.get_name())

                if timed_out_tasks:
                    logger.warning(
                        f"[CLAIM {claim_position}] Tasks timed out after {CLAIM_TIMEOUT}s: {timed_out_tasks}"
                    )
                    api_evidence["api_stats"]["timeout"] = True
                else:
                    logger.info(
                        f"[SINGLE CLAIM DEBUG] All tasks complete for claim {claim_position}"
                    )

                # Merge web search and API results
                evidence_snippets = web_evidence_snippets

                # Mine Wikipedia references for authority sources
                from app.pipeline.wikipedia_miner import mine_wikipedia_references

                wiki_ref_snippets = await mine_wikipedia_references(
                    evidence_snippets,
                    claim_text,
                    self.evidence_extractor,
                    semaphore,
                )
                if wiki_ref_snippets:
                    logger.info(
                        f"[WIKI MINING] Found {len(wiki_ref_snippets)} authority references from Wikipedia"
                    )
                    evidence_snippets = evidence_snippets + wiki_ref_snippets
                api_evidence_items = api_evidence.get("evidence", [])

                # Store API stats in claim for later tracking
                claim["api_stats"] = api_evidence.get("api_stats", {})

                # Log evidence counts (single consolidated log)
                web_count = (
                    len(web_evidence_snippets)
                    if isinstance(web_evidence_snippets, list)
                    else 0
                )
                api_count = len(api_evidence_items)
                logger.info(
                    f"[RETRIEVE] Claim {claim_position}: {web_count} web + {api_count} API sources"
                )

                if not evidence_snippets and not api_evidence_items:
                    logger.warning(f"[RETRIEVE] NO EVIDENCE for claim {claim_position}")
                    return {
                        "filtered_evidence": [],
                        "raw_evidence": [],
                        "claim_position": claim_position,
                        "claim_text": claim_text[:500] if claim_text else "",
                    }

                # Step 2: Merge and rank ALL evidence (web + API) using embeddings (bi-encoder)
                api_snippets = self._convert_api_evidence_to_snippets(
                    api_evidence_items
                )
                logger.critical(
                    f"[EVIDENCE TRACE] Claim {claim_position}: {len(evidence_snippets)} web snippets + {len(api_snippets)} API snippets (from {len(api_evidence_items)} API items)"
                )
                all_evidence_snippets = evidence_snippets + api_snippets

                # Fix 0c: Cap combined evidence before expensive ranking
                # Reduced from 50 to 30: focus on quality, not quantity
                MAX_EVIDENCE_FOR_RANKING = 30
                if len(all_evidence_snippets) > MAX_EVIDENCE_FOR_RANKING:
                    logger.info(
                        f"[EVIDENCE CAP] Reducing {len(all_evidence_snippets)} items to {MAX_EVIDENCE_FOR_RANKING} before ranking"
                    )
                    # Round-robin: alternate web and API to ensure source diversity
                    web = evidence_snippets
                    api = api_snippets
                    interleaved = []
                    wi, ai = 0, 0
                    while len(interleaved) < MAX_EVIDENCE_FOR_RANKING and (
                        wi < len(web) or ai < len(api)
                    ):
                        if wi < len(web):
                            interleaved.append(web[wi])
                            wi += 1
                        if (
                            ai < len(api)
                            and len(interleaved) < MAX_EVIDENCE_FOR_RANKING
                        ):
                            interleaved.append(api[ai])
                            ai += 1
                    all_evidence_snippets = interleaved

                # Build evidence dicts (LLM scorer handles relevance downstream in Stage 3.7)
                ranked_evidence = []
                for idx, snippet in enumerate(all_evidence_snippets):
                    external_source = (
                        snippet.metadata.get("external_source_provider")
                        if snippet.metadata
                        else None
                    )
                    ev_hash = hashlib.sha256(
                        (snippet.url + snippet.text).encode()
                    ).hexdigest()[:12]
                    ranked_evidence.append(
                        {
                            "id": f"evidence_{idx}",
                            "evidence_id": f"ev-{ev_hash}",
                            "element_ids": (
                                snippet.metadata.get("element_ids", [])
                                if snippet.metadata
                                else []
                            ),
                            "text": snippet.text,
                            "source": snippet.source,
                            "url": snippet.url,
                            "title": snippet.title,
                            "published_date": snippet.published_date,
                            "relevance_score": float(snippet.relevance_score),
                            "semantic_similarity": 0.0,
                            "combined_score": 0.0,
                            "word_count": snippet.word_count,
                            "external_source_provider": external_source,
                            "receipt_status": "extracted",
                            "metadata": snippet.metadata,
                        }
                    )

                # Step 3: Apply credibility and recency weighting (with raw evidence tracking)
                logger.critical(
                    f"[EVIDENCE TRACE] Claim {claim_position}: {len(ranked_evidence)} items BEFORE evidence filtering"
                )
                pre_weighting_snapshot = copy.deepcopy(ranked_evidence)
                result = self._apply_evidence_filters(
                    ranked_evidence, claim, track_raw_evidence=True
                )
                final_evidence, raw_evidence = (
                    result if isinstance(result, tuple) else (result, [])
                )
                logger.critical(
                    f"[EVIDENCE TRACE] Claim {claim_position}: {len(final_evidence)} items AFTER evidence filtering"
                )

                # Step 4: Store in vector database for future retrieval
                await self._store_evidence_embeddings(claim, final_evidence)

                # Return top evidence along with raw evidence metadata
                return {
                    "filtered_evidence": final_evidence[: self.max_sources_per_claim],
                    "raw_evidence": raw_evidence,
                    "pre_weighting_evidence": pre_weighting_snapshot,
                    "claim_position": claim_position,
                    "claim_text": claim_text[:500] if claim_text else "",
                }

            except Exception as e:
                logger.error(f"Single claim evidence retrieval error: {e}")
                return {
                    "filtered_evidence": [],
                    "raw_evidence": [],
                    "claim_position": claim.get("position", 0),
                    "claim_text": (
                        claim.get("text", "")[:500] if claim.get("text") else ""
                    ),
                }

    async def _execute_planned_queries(
        self,
        claim_text: str,
        query_plan: Dict[str, Any],
        excluded_domain: Optional[str] = None,
        max_sources: int = 20,
        freshness: Optional[str] = None,
    ) -> List[EvidenceSnippet]:
        """
        Execute multiple targeted queries from Query Planning Agent.

        Args:
            claim_text: Original claim text
            query_plan: Query plan with targeted queries and source priorities
            excluded_domain: Domain to exclude from results
            max_sources: Maximum total sources to return
            freshness: Brave freshness filter (pd/pw/pm/py/2y) from temporal_analysis

        Returns:
            List of deduplicated EvidenceSnippet from all queries
        """
        try:
            queries = query_plan.get("queries", [])
            claim_type = query_plan.get("claim_type", "general")

            # ============================================================
            # DYNAMIC FRESHNESS: Per-query freshness from query plan
            # ============================================================
            # Each query carries its own freshness from the element it targets.
            # The plan-level freshness is a fallback for backward compatibility.
            query_freshness_list = query_plan.get("query_freshness", [])
            default_freshness = query_plan.get("freshness", "py")
            plan_reasoning = query_plan.get("reasoning", "default")

            logger.info(
                f"[FRESHNESS] Per-query freshness: {query_freshness_list[:4]}... (default: {default_freshness}, reasoning: {plan_reasoning[:50]})"
            )

            if not queries:
                logger.warning(f"No queries in plan for claim: {claim_text[:50]}...")
                return []

            logger.debug(f"Executing {len(queries)} planned queries")

            # Execute all queries concurrently
            query_tasks = []
            sources_per_query = max(
                3, max_sources // len(queries)
            )  # Distribute sources across queries

            for i, query in enumerate(queries):
                # Per-query freshness: use the freshness for this specific query's element
                this_freshness = (
                    query_freshness_list[i]
                    if i < len(query_freshness_list)
                    else default_freshness
                )
                task = self.evidence_extractor.search_service.search_for_evidence(
                    query,
                    max_results=sources_per_query,
                    freshness=this_freshness,
                )
                query_tasks.append(task)

            # Gather all search results
            all_results = await asyncio.gather(*query_tasks, return_exceptions=True)

            # Merge and deduplicate search results by URL
            # Track element associations so cross-element URL dedup preserves all element_ids
            query_element_ids = query_plan.get("query_element_ids", [])
            seen_urls = {}  # URL -> search result reference
            unique_search_results = []

            for i, results in enumerate(all_results):
                if isinstance(results, Exception):
                    logger.warning(f"Query {i+1} failed: {results}")
                    continue

                element_id = (
                    query_element_ids[i] if i < len(query_element_ids) else None
                )

                for result in results:
                    # Skip excluded domain
                    if (
                        excluded_domain
                        and extract_domain(result.url) == excluded_domain
                    ):
                        continue

                    # Deduplicate by URL, but accumulate element associations
                    if result.url in seen_urls:
                        if element_id:
                            seen_urls[result.url]._element_ids.add(element_id)
                        continue

                    # Attach query metadata to result for later preservation
                    result._query_index = i
                    result._query_used = queries[i]
                    result._claim_type = claim_type
                    result._freshness = default_freshness  # For staleness check
                    result._element_ids = {element_id} if element_id else set()
                    seen_urls[result.url] = result
                    unique_search_results.append(result)

            # BALANCED FRESHNESS FALLBACK when 0 results
            if not unique_search_results:
                fallback_progression = ["pw", "pm", "py"]
                current_idx = (
                    fallback_progression.index(default_freshness)
                    if default_freshness in fallback_progression
                    else -1
                )

                # FALLBACK: Progressively relax freshness (pw->pm->py, never 2y)
                if (
                    not unique_search_results
                    and current_idx >= 0
                    and current_idx < len(fallback_progression) - 1
                ):
                    for fallback_freshness in fallback_progression[current_idx + 1 :]:
                        logger.info(
                            f"[FRESHNESS FALLBACK] Relaxing: {default_freshness} -> {fallback_freshness}"
                        )
                        for query in queries:
                            try:
                                results = await self.evidence_extractor.search_service.search_for_evidence(
                                    query,
                                    max_results=sources_per_query,
                                    freshness=fallback_freshness,
                                )
                                for result in results:
                                    if (
                                        excluded_domain
                                        and extract_domain(result.url)
                                        == excluded_domain
                                    ):
                                        continue
                                    if result.url not in seen_urls:
                                        seen_urls.add(result.url)
                                        result._query_index = queries.index(query)
                                        result._query_used = query
                                        result._claim_type = claim_type
                                        result._freshness = (
                                            fallback_freshness  # Use fallback freshness
                                        )
                                        result._freshness_fallback = fallback_freshness
                                        unique_search_results.append(result)
                            except Exception as e:
                                logger.warning(f"Fallback query failed: {e}")
                        if unique_search_results:
                            logger.info(
                                f"[FRESHNESS FALLBACK] Found {len(unique_search_results)} with {fallback_freshness}"
                            )
                            break

                if not unique_search_results:
                    logger.warning(
                        f"[FRESHNESS FALLBACK] No results after all attempts"
                    )
                    return []

            # ============================================================
            # CRITICAL FIX: Extract actual page content (like standard path)
            # ============================================================
            semaphore = asyncio.Semaphore(self.evidence_extractor.max_concurrent)
            extraction_tasks = [
                self._extract_with_fallback(result, claim_text, semaphore)
                for result in unique_search_results[:max_sources]
            ]

            extracted_results = await asyncio.gather(
                *extraction_tasks, return_exceptions=True
            )

            # Filter successful extractions and track fallback stats
            evidence_snippets = []
            fallback_count = 0
            dropped_count = 0

            for result in extracted_results:
                if isinstance(result, Exception):
                    logger.warning(f"Content extraction exception: {result}")
                    dropped_count += 1
                    continue
                if result is None:
                    dropped_count += 1
                    continue
                if result.metadata and result.metadata.get("is_snippet_fallback"):
                    fallback_count += 1
                evidence_snippets.append(result)

            # Log extraction stats
            total = len(unique_search_results[:max_sources])
            success_count = len(evidence_snippets) - fallback_count
            logger.info(
                f"[RETRIEVE] Query Planning extraction: "
                f"{success_count}/{total} content, {fallback_count} fallback, {dropped_count} dropped | "
                f"claim_type={claim_type}"
            )

            return evidence_snippets

        except Exception as e:
            logger.error(f"Planned query execution failed: {e}")
            # Fallback to standard search with claim text
            return await self.evidence_extractor.extract_evidence_for_claim(
                claim_text, max_sources=max_sources
            )

    async def _extract_with_fallback(
        self, search_result, claim_text: str, semaphore: asyncio.Semaphore
    ) -> Optional[EvidenceSnippet]:
        """
        Extract content from a search result with nuanced fallback policy.

        Fallback Policy:
        - 403/429 blocked: Keep snippet if ALLOW_SNIPPET_FALLBACK=True, mark as fallback
        - Timeout: Keep snippet if ALLOW_SNIPPET_FALLBACK=True, mark as fallback
        - Empty/JS-only: Drop entirely (return None)
        - Success: Return extracted content

        Args:
            search_result: SearchResult with attached query metadata
            claim_text: Claim text for relevance matching
            semaphore: Concurrency limiter

        Returns:
            EvidenceSnippet with extracted content, or None if dropped
        """
        # Preserve query planning metadata
        query_index = getattr(search_result, "_query_index", None)
        query_used = getattr(search_result, "_query_used", None)
        claim_type = getattr(search_result, "_claim_type", "general")
        freshness = getattr(search_result, "_freshness", "py")  # For staleness check
        element_ids = list(getattr(search_result, "_element_ids", set()))

        try:
            # Attempt full content extraction
            snippet = await self.evidence_extractor._extract_from_page(
                search_result, claim_text, semaphore
            )

            if snippet is not None:
                # Success: Enrich with query planning metadata
                snippet.metadata = snippet.metadata or {}
                snippet.metadata["query_index"] = query_index
                snippet.metadata["query_used"] = query_used
                snippet.metadata["claim_type"] = claim_type
                snippet.metadata["source_path"] = "query_planning"
                snippet.metadata["extraction_status"] = "success"
                snippet.metadata["is_snippet_fallback"] = False
                snippet.metadata["element_ids"] = element_ids

                # Add staleness check for time-sensitive claims (using dynamic freshness)
                from app.utils.query_planner import check_evidence_staleness

                staleness = check_evidence_staleness(
                    evidence_date=snippet.published_date,
                    freshness=freshness,  # Use LLM-decided freshness from query plan
                )
                snippet.metadata["staleness_check"] = staleness
                if staleness["is_stale"]:
                    logger.warning(
                        f"[STALE EVIDENCE] {staleness['message']} - URL: {snippet.url}"
                    )

                return snippet

            # Content extraction returned None
            # This means HTML was fetched but yielded no substantive content (JS-only/empty)
            # Policy: Drop entirely - don't pollute with low-signal meta descriptions
            logger.debug(f"Dropping empty extraction for {search_result.url}")
            return None

        except Exception as e:
            # Extraction failed - check if we should use snippet fallback
            error_str = str(e).lower()
            is_blocked = (
                "403" in error_str or "429" in error_str or "forbidden" in error_str
            )
            is_timeout = "timeout" in error_str

            if (is_blocked or is_timeout) and settings.ALLOW_SNIPPET_FALLBACK:
                # Transient failure: Use snippet as fallback with lower score
                extraction_status = (
                    "fallback_blocked" if is_blocked else "fallback_timeout"
                )
                logger.debug(
                    f"Using snippet fallback ({extraction_status}) for {search_result.url}"
                )

                return EvidenceSnippet(
                    text=search_result.snippet or "",
                    source=extract_domain(search_result.url),
                    url=search_result.url,
                    title=search_result.title or "",
                    published_date=search_result.published_date,
                    relevance_score=0.0,  # No hardcoded score, status tracked via metadata
                    metadata={
                        "query_index": query_index,
                        "query_used": query_used,
                        "claim_type": claim_type,
                        "source_path": "query_planning",
                        "extraction_status": extraction_status,
                        "is_snippet_fallback": True,
                        "fallback_reason": str(e)[:100],
                        "element_ids": element_ids,
                    },
                )
            else:
                # Other failure or fallback disabled: Drop
                logger.debug(f"Dropping failed extraction for {search_result.url}: {e}")
                return None

    def _apply_evidence_filters(
        self,
        evidence_list: List[Dict[str, Any]],
        claim: Dict[str, Any] = None,
        track_raw_evidence: bool = False,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]] | List[Dict[str, Any]]:
        """Apply minimal filtering to evidence.

        Two stages:
        1. Satire exclusion — remove known satire domains
        2. Content dedup — remove identical/syndicated content
        Plus corroboration boost (annotation, not a filter).

        Args:
            evidence_list: List of evidence items
            claim: Claim dict for context-aware filtering
            track_raw_evidence: If True, returns tuple (filtered, raw_evidence_metadata)

        Returns:
            If track_raw_evidence=False: List of filtered evidence
            If track_raw_evidence=True: Tuple of (filtered_evidence, raw_evidence_metadata)
        """
        try:
            original_evidence_count = len(evidence_list)

            # --- RAW EVIDENCE TRACKING: snapshot before any filtering ---
            raw_evidence_tracking = []
            if track_raw_evidence:
                for ev in evidence_list:
                    raw_evidence_tracking.append(
                        {
                            "source": ev.get("source", ""),
                            "url": ev.get("url", ""),
                            "title": ev.get("title", ""),
                            "snippet": ev.get("snippet", ""),
                            "published_date": ev.get("published_date"),
                            "is_included": True,
                            "filter_stage": None,
                            "filter_reason": None,
                            "tier": ev.get("tier"),
                            "is_factcheck": ev.get("is_factcheck", False),
                            "external_source_provider": ev.get(
                                "external_source_provider"
                            ),
                            "relevance_score": ev.get("combined_score", 0.0),
                        }
                    )
            url_to_raw = (
                {item["url"]: item for item in raw_evidence_tracking}
                if track_raw_evidence
                else {}
            )

            # --- STAGE 1: Satire exclusion ---
            before_satire = len(evidence_list)
            satire_excluded = []
            kept = []
            for ev in evidence_list:
                domain = extract_domain(ev.get("url", ""), fallback="")
                if domain in SATIRE_DOMAINS:
                    satire_excluded.append(ev)
                else:
                    kept.append(ev)
            evidence_list = kept
            if track_raw_evidence:
                for e in satire_excluded:
                    url = e.get("url", "")
                    if url in url_to_raw:
                        url_to_raw[url]["is_included"] = False
                        url_to_raw[url]["filter_stage"] = "satire"
                        url_to_raw[url]["filter_reason"] = "Excluded: satire source"
            logger.info(
                f"[FILTER] Satire exclusion: {before_satire} -> {len(evidence_list)}"
            )

            # --- STAGE 2: Content dedup ---
            before_dedup = len(evidence_list)
            from app.utils.deduplication import EvidenceDeduplicator

            deduplicator = EvidenceDeduplicator()
            before_dedup_list = list(evidence_list) if track_raw_evidence else []
            evidence_list, dedup_stats = deduplicator.deduplicate(evidence_list)
            if track_raw_evidence:
                after_urls = {e.get("url") for e in evidence_list}
                for e in before_dedup_list:
                    url = e.get("url", "")
                    if url not in after_urls and url in url_to_raw:
                        url_to_raw[url]["is_included"] = False
                        url_to_raw[url]["filter_stage"] = "dedup"
                        url_to_raw[url]["filter_reason"] = "Duplicate content"
            logger.info(f"[FILTER] Dedup: {before_dedup} -> {len(evidence_list)}")

            # --- Corroboration boost (annotation only) ---
            if len(evidence_list) >= 2:
                from app.utils.corroboration import apply_corroboration_boost

                evidence_list, corroboration_stats = apply_corroboration_boost(
                    evidence_list
                )
                if corroboration_stats.get("items_annotated", 0) > 0:
                    logger.info(
                        f"[FILTER] Corroboration: {corroboration_stats['items_annotated']} items annotated "
                        f"({corroboration_stats['corroboration_pairs']} pairs, "
                        f"{corroboration_stats.get('groups', 0)} groups)"
                    )

            # Sort by combined_score
            evidence_list.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

            # Safety check
            if len(evidence_list) == 0 and original_evidence_count > 0:
                logger.warning(
                    f"All {original_evidence_count} evidence items eliminated by filters"
                )

            if track_raw_evidence:
                return evidence_list, raw_evidence_tracking
            return evidence_list

        except Exception as e:
            logger.error(f"Evidence filtering error: {e}")
            if track_raw_evidence:
                return evidence_list, []
            return evidence_list

    def _label_entities_for_api(self, key_entities: List[str]) -> List[Dict[str, str]]:
        """
        Convert string entities to labeled format for API adapters.

        Uses heuristics to classify entities as PERSON, ORG, or ENTITY.
        This enables API adapters (e.g., TransfermarktAdapter) to properly
        query for players, clubs, etc.

        Args:
            key_entities: List of entity strings from claim extraction

        Returns:
            List of labeled entities: [{"text": "...", "label": "PERSON|ORG|ENTITY"}]
        """
        # Common sports organization suffixes
        org_suffixes = (
            "FC",
            "United",
            "City",
            "Rovers",
            "Wanderers",
            "Athletic",
            "Dortmund",
            "Arsenal",
            "Chelsea",
            "Munich",
            "Madrid",
            "Barcelona",
            "Milan",
            "Inter",
            "Juventus",
            "PSG",
            "Bayern",
            "Liverpool",
            "Tottenham",
            "Spurs",
            "Hotspur",
            "Rangers",
            "Celtic",
            "Club",
            "Association",
            "Federation",
            "League",
            "UEFA",
            "FIFA",
            "Inc",
            "Ltd",
            "Corp",
            "Company",
            "Organization",
            "Government",
        )

        # Common title prefixes that indicate PERSON
        person_prefixes = (
            "Mr",
            "Mrs",
            "Ms",
            "Dr",
            "Prof",
            "Sir",
            "Lord",
            "Lady",
            "President",
            "Prime Minister",
            "Minister",
            "Senator",
            "Governor",
        )

        labeled = []
        for entity in key_entities:
            if not entity or not isinstance(entity, str):
                continue

            entity_stripped = entity.strip()
            words = entity_stripped.split()

            # Check for organization indicators
            if any(entity_stripped.endswith(suffix) for suffix in org_suffixes):
                labeled.append({"text": entity_stripped, "label": "ORG"})
            # Check for person name patterns (2+ capitalized words, not org)
            elif (
                len(words) >= 2
                and all(w[0].isupper() for w in words if w)
                and not any(suffix in entity_stripped for suffix in org_suffixes)
            ):
                labeled.append({"text": entity_stripped, "label": "PERSON"})
            # Check for title prefix
            elif any(entity_stripped.startswith(prefix) for prefix in person_prefixes):
                labeled.append({"text": entity_stripped, "label": "PERSON"})
            # Default to ENTITY (adapters can still try to use these)
            else:
                labeled.append({"text": entity_stripped, "label": "ENTITY"})

        logger.debug(f"[API ROUTING] Labeled entities: {labeled}")
        return labeled

    async def _retrieve_from_government_apis(
        self, claim_text: str, claim: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve evidence from government APIs based on claim domain/jurisdiction.

        Phase 5: Government API Integration

        Args:
            claim_text: The claim text to search for
            claim: Full claim dictionary (may include domain info)

        Returns:
            Dictionary with:
                - evidence: List of evidence items
                - api_stats: API usage statistics
        """
        from app.core.config import settings

        # Check feature flag
        api_flag = getattr(settings, "ENABLE_API_RETRIEVAL", False)
        logger.info(
            f"[API DEBUG] ENABLE_API_RETRIEVAL={api_flag}, self.enable_api_retrieval={self.enable_api_retrieval}"
        )
        logger.info(
            f"[API DEBUG] Registry adapter count: {len(self.api_registry.adapters)}"
        )

        if not api_flag or not self.enable_api_retrieval:
            logger.warning("[API DEBUG] API retrieval DISABLED by feature flag")
            return {"evidence": [], "api_stats": {}}

        # Safety check: if registry is empty, adapters weren't initialized
        if len(self.api_registry.adapters) == 0:
            logger.error(
                "[API DEBUG] CRITICAL: Registry has 0 adapters! Initializing now..."
            )
            from app.services.api_adapters import initialize_adapters

            initialize_adapters()
            logger.info(
                f"[API DEBUG] After emergency init: {len(self.api_registry.adapters)} adapters"
            )

        try:
            # PRIORITY 1: Check if claim was classified as legal during extraction
            # If legal, use legal_metadata for targeted routing to statute APIs
            claim_type = claim.get("claim_type")
            legal_metadata = claim.get("legal_metadata", {})

            # Extract entities from key_entities field (set during extraction)
            # Convert to labeled entity format for API adapters (PERSON, ORG, etc.)
            key_entities = claim.get("key_entities", [])
            entities = self._label_entities_for_api(key_entities)

            if claim_type == "legal" and legal_metadata:
                # Use legal classification for routing (override domain/jurisdiction)
                domain = "Law"
                jurisdiction = legal_metadata.get("jurisdiction", "US")
                confidence = claim.get("classification", {}).get("confidence", 0.9)

            else:
                # PRIORITY 2: Use article-level classification (once per check, not per claim)
                # This is set during extraction and attached to all claims
                article_classification = claim.get("article_classification", {})

                if article_classification:
                    # Use article-level classification
                    domain = article_classification.get("primary_domain", "General")
                    jurisdiction = article_classification.get("jurisdiction", "Global")
                    confidence = article_classification.get("confidence", 0.0)
                    secondary_domains = article_classification.get(
                        "secondary_domains", []
                    )

                    # Warn if classification failed (using fallback "General")
                    if article_classification.get("classification_failed"):
                        logger.warning(
                            f"[API ROUTING] Classification failed - using General domain, "
                            f"API evidence may be less targeted"
                        )

                    logger.debug(
                        f"[API ROUTING] Using article classification: "
                        f"domain={domain}, jurisdiction={jurisdiction}, "
                        f"confidence={confidence:.2f}, source={article_classification.get('source', 'unknown')}"
                    )
                else:
                    # Fallback: No article classification available
                    # This happens when ENABLE_ARTICLE_CLASSIFICATION is disabled
                    # or classification failed during extraction
                    domain = "General"
                    jurisdiction = "Global"
                    confidence = 0.0
                    secondary_domains = []
                    logger.warning(
                        "[API ROUTING] No article classification, defaulting to General"
                    )

            # Get relevant API adapters for primary domain
            relevant_adapters = self.api_registry.get_adapters_for_domain(
                domain, jurisdiction
            )

            # Also query secondary domain adapters (for cross-domain articles)
            if "secondary_domains" in dir() and secondary_domains:
                for sec_domain in secondary_domains:
                    sec_adapters = self.api_registry.get_adapters_for_domain(
                        sec_domain, jurisdiction
                    )
                    # Add unique adapters (avoid duplicates)
                    for adapter in sec_adapters:
                        if adapter not in relevant_adapters:
                            relevant_adapters.append(adapter)
                            logger.debug(
                                f"[API ROUTING] Added secondary domain adapter: {adapter.api_name} ({sec_domain})"
                            )

            # Claim-level keyword routing: add adapters based on claim text keywords
            # This catches cross-domain claims (e.g., oil prices in Politics articles)
            from app.utils.claim_keyword_router import get_keyword_router

            keyword_router = get_keyword_router()
            keyword_adapters = keyword_router.get_additional_adapters(
                claim_text, relevant_adapters, self.api_registry
            )
            for adapter in keyword_adapters:
                relevant_adapters.append(adapter)
                logger.info(
                    f"[KEYWORD ROUTING] Added {adapter.api_name} for claim: {claim_text[:50]}..."
                )

            # Fix 0a: Limit adapters per claim - most claims don't need 5+ API sources
            # Reduced from 5 to 3: fewer irrelevant keyword matches, faster processing
            MAX_ADAPTERS_PER_CLAIM = 3
            if len(relevant_adapters) > MAX_ADAPTERS_PER_CLAIM:
                logger.info(
                    f"[API LIMIT] Reducing {len(relevant_adapters)} adapters to {MAX_ADAPTERS_PER_CLAIM}"
                )
                relevant_adapters = relevant_adapters[:MAX_ADAPTERS_PER_CLAIM]

            # Log final adapter list
            adapter_names = [a.api_name for a in relevant_adapters]
            logger.info(f"[API DEBUG] Final adapters to query: {adapter_names}")

            if not relevant_adapters:
                logger.warning(
                    f"[API] No adapters found for domain={domain}, jurisdiction={jurisdiction}"
                )
                return {"evidence": [], "api_stats": {}}

            # Query all relevant APIs concurrently
            api_tasks = []
            for adapter in relevant_adapters:
                # Use asyncio.to_thread to run sync API calls in executor
                # Pass entities for dynamic entity extraction (no hardcoded lists!)
                task = asyncio.to_thread(
                    adapter.search_with_cache,
                    claim_text,
                    domain,
                    jurisdiction,
                    entities,
                )
                api_tasks.append((adapter.api_name, task))

            # Gather all API results
            api_results = await asyncio.gather(
                *[task for _, task in api_tasks], return_exceptions=True
            )

            # Collect evidence and statistics
            all_api_evidence = []
            api_stats = {
                "apis_queried": [],
                "total_api_calls": 0,
                "total_api_results": 0,
            }

            for i, (api_name, _) in enumerate(api_tasks):
                result = api_results[i]

                if isinstance(result, Exception):
                    logger.error(f"{api_name} API call failed: {result}")
                    api_stats["apis_queried"].append(
                        {"name": api_name, "results": 0, "error": str(result)}
                    )
                    continue

                if result:
                    all_api_evidence.extend(result)
                    api_stats["apis_queried"].append(
                        {"name": api_name, "results": len(result)}
                    )
                    api_stats["total_api_results"] += len(result)
                else:
                    api_stats["apis_queried"].append({"name": api_name, "results": 0})

            api_stats["total_api_calls"] = len(api_tasks)

            # Log API results summary
            logger.info(
                f"[API DEBUG] Results: {api_stats['total_api_calls']} APIs queried, {api_stats['total_api_results']} total results"
            )
            for api_stat in api_stats["apis_queried"]:
                logger.info(
                    f"[API DEBUG]   - {api_stat['name']}: {api_stat.get('results', 0)} results"
                    + (
                        f" (ERROR: {api_stat.get('error', '')})"
                        if api_stat.get("error")
                        else ""
                    )
                )

            # Fix 0b: Cap total API evidence per claim
            # Reduced from 30 to 10: analyzer has limited context, quality over quantity
            MAX_API_EVIDENCE_PER_CLAIM = (
                5  # Reduced: API evidence supplements web search
            )
            if len(all_api_evidence) > MAX_API_EVIDENCE_PER_CLAIM:
                logger.info(
                    f"[API CAP] Reducing {len(all_api_evidence)} API items to {MAX_API_EVIDENCE_PER_CLAIM}"
                )
                # Round-robin across API providers for source diversity
                from collections import defaultdict

                by_provider = defaultdict(list)
                for item in all_api_evidence:
                    by_provider[item.get("external_source_provider", "unknown")].append(
                        item
                    )
                providers = list(by_provider.values())
                interleaved = []
                idx = 0
                while len(interleaved) < MAX_API_EVIDENCE_PER_CLAIM:
                    added = False
                    for group in providers:
                        if (
                            idx < len(group)
                            and len(interleaved) < MAX_API_EVIDENCE_PER_CLAIM
                        ):
                            interleaved.append(group[idx])
                            added = True
                    if not added:
                        break
                    idx += 1
                all_api_evidence = interleaved

            # CRITICAL DIAGNOSTIC: Log final API evidence count
            logger.critical(
                f"[API RETRIEVAL] Returning {len(all_api_evidence)} evidence items from {api_stats['total_api_calls']} API calls"
            )
            if all_api_evidence:
                logger.info(
                    f"[API RETRIEVAL] First item: {all_api_evidence[0].get('source', 'N/A')} - {all_api_evidence[0].get('title', 'N/A')[:50]}"
                )

            return {"evidence": all_api_evidence, "api_stats": api_stats}

        except Exception as e:
            logger.error(f"Government API retrieval error: {e}", exc_info=True)
            return {"evidence": [], "api_stats": {}}

    def _convert_api_evidence_to_snippets(
        self, api_evidence: List[Dict[str, Any]]
    ) -> List[EvidenceSnippet]:
        """
        Convert API evidence dictionaries to EvidenceSnippet objects.

        Args:
            api_evidence: List of evidence dictionaries from APIs

        Returns:
            List of EvidenceSnippet objects
        """
        snippets = []
        conversion_failures = 0

        for i, evidence in enumerate(api_evidence):
            try:
                text = evidence.get("snippet", "")
                if not text:
                    logger.warning(
                        f"[API CONVERT] Item {i}: Empty snippet, source={evidence.get('source', 'N/A')}"
                    )
                    conversion_failures += 1
                    continue

                snippet = EvidenceSnippet(
                    text=text,
                    source=evidence.get("source", "Unknown API"),
                    url=evidence.get("url", ""),
                    title=evidence.get("title", ""),
                    published_date=evidence.get("source_date"),
                    relevance_score=0.0,  # No hardcoded score, LLM scorer decides
                    # word_count is calculated automatically in EvidenceSnippet.__init__
                    metadata={
                        **evidence.get("metadata", {}),
                        "external_source_provider": evidence.get(
                            "external_source_provider"
                        ),
                    },
                )
                snippets.append(snippet)
            except Exception as e:
                logger.warning(f"[API CONVERT] Item {i}: Failed to convert - {e}")
                conversion_failures += 1
                continue

        if conversion_failures > 0:
            logger.warning(
                f"[API CONVERT] {conversion_failures}/{len(api_evidence)} items failed conversion"
            )

        return snippets

    async def _store_evidence_embeddings(
        self, claim: Dict[str, Any], evidence_list: List[Dict[str, Any]]
    ):
        """Store evidence embeddings in vector database for future use"""
        try:
            if not evidence_list:
                return

            embedding_service = await get_embedding_service()
            vector_store = await get_vector_store()

            # Generate embeddings for evidence texts
            evidence_texts = [evidence["text"] for evidence in evidence_list]
            embeddings = await embedding_service.embed_batch(evidence_texts)

            # Prepare data for vector storage
            evidence_data = []
            for evidence, embedding in zip(evidence_list, embeddings):
                evidence_item = {
                    **evidence,
                    "embedding": embedding,
                    "claim_text": claim.get("text"),
                    "claim_position": claim.get("position"),
                    "created_at": datetime.utcnow().isoformat(),
                }
                evidence_data.append(evidence_item)

            # Store embeddings
            stored_ids = await vector_store.store_evidence_embeddings(evidence_data)
            logger.debug(f"Stored {len(stored_ids)} embeddings")

        except Exception as e:
            logger.warning(f"Evidence storage error: {e}")
            # Don't fail the pipeline if storage fails

    async def retrieve_from_vector_store(
        self, claim: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve similar evidence from vector store"""
        try:
            embedding_service = await get_embedding_service()
            vector_store = await get_vector_store()

            # Generate claim embedding
            claim_embedding = await embedding_service.embed_text(claim)

            # Search for similar evidence
            similar_evidence = await vector_store.search_similar_evidence(
                query_embedding=claim_embedding, limit=limit, score_threshold=0.7
            )

            logger.debug(f"Vector store: {len(similar_evidence)} items")
            return similar_evidence

        except Exception as e:
            logger.error(f"Vector store retrieval error: {e}")
            return []
