import copy
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone
import numpy as np
import os
from app.services.search import SearchService, SearchResult
from app.services.evidence import EvidenceExtractor, EvidenceSnippet
from app.services.embeddings import get_embedding_service, rank_evidence_by_similarity
from app.services.vector_store import get_vector_store
from app.utils.url_utils import extract_domain
from app.services.government_api_client import get_api_registry
from app.core.config import settings

logger = logging.getLogger(__name__)

# Module load timestamp for debugging stale worker issues
import time as _time
_MODULE_LOAD_TIME = _time.strftime("%Y-%m-%d %H:%M:%S")
_MODULE_VERSION = "v3-per-claim-timeout"  # Added 45s per-claim timeout to prevent hangs
print(f"[RETRIEVE MODULE LOADED] {_MODULE_LOAD_TIME} - Version: {_MODULE_VERSION} - Query Planning: {settings.ENABLE_QUERY_PLANNING}", flush=True)

class EvidenceRetriever:
    """Retrieve and rank evidence for claims using search, embeddings, and vector storage"""

    # Minimum evidence per claim - triggers recovery search if below this threshold
    MIN_EVIDENCE_PER_CLAIM = 2

    # Authoritative sources by domain for targeted recovery searches
    AUTHORITATIVE_SOURCES_BY_DOMAIN = {
        "health": ["who.int", "cdc.gov", "nih.gov", "nhs.uk", "pubmed.ncbi.nlm.nih.gov"],
        "science": ["nature.com", "science.org", "ncbi.nlm.nih.gov", "arxiv.org"],
        "government": ["gov.uk", "usa.gov", "congress.gov", "govinfo.gov"],
        "finance": ["sec.gov", "federalreserve.gov", "imf.org", "worldbank.org"],
        "sports": ["transfermarkt.com", "espn.com", "bbc.com/sport"],
        "general": ["reuters.com", "apnews.com", "bbc.com"]
    }

    # Mapping from temporal_window (from claim extraction) to Brave freshness parameter
    # temporal_window values: current_day, current_week, current_month, current_year, any, historical
    # Brave freshness values: pd (past day), pw (past week), pm (past month), py (past year), 2y (2 years)
    TEMPORAL_TO_FRESHNESS = {
        "current_day": "pd",      # Past day - breaking news, live events
        "current_week": "pw",     # Past week - recent developments
        "current_month": "pm",    # Past month - recent news
        "current_year": "py",     # Past year - annual events, seasons
        "any": "2y",              # Default 2 years
        "historical": "2y",       # Historical claims - use 2 years
    }

    def __init__(self):
        self.search_service = SearchService()
        self.evidence_extractor = EvidenceExtractor()
        self.max_sources_per_claim = 10
        self.max_concurrent_claims = 3

        # Phase 5: Government API Integration
        self.api_registry = get_api_registry()
        self.enable_api_retrieval = True  # Feature flag (set via settings)

        # Credibility weights for different source types
        self.credibility_weights = {
            'academic': 1.0,      # .edu, .org, peer-reviewed
            'news_tier1': 0.9,    # BBC, Reuters, AP
            'news_tier2': 0.8,    # Guardian, Telegraph, Independent
            'government': 0.85,   # .gov domains
            'scientific': 0.95,   # Nature, Science journals
            'general': 0.6        # Other sources
        }
    
    async def retrieve_evidence_for_claims(
        self,
        claims: List[Dict[str, Any]],
        exclude_source_url: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve evidence for multiple claims concurrently"""
        import time as _time
        _func_start = _time.time()
        print(f"\n[RETRIEVER ENTRY] retrieve_evidence_for_claims called with {len(claims)} claims at {_func_start:.2f}", flush=True)
        logger.info(f"[RETRIEVER DEBUG] retrieve_evidence_for_claims called with {len(claims)} claims")
        try:
            # Extract excluded domain if provided
            excluded_domain = None
            if exclude_source_url:
                excluded_domain = extract_domain(exclude_source_url)
                logger.debug(f"Excluding source domain: {excluded_domain}")

            # Query Planning Agent: Generate targeted queries for all claims (single LLM call)
            query_plans = None
            print(f"[RETRIEVER] QUERY_PLANNING_ENABLED: {settings.ENABLE_QUERY_PLANNING}", flush=True)
            logger.info(f"[RETRIEVE] QUERY_PLANNING_ENABLED: {settings.ENABLE_QUERY_PLANNING}")
            if settings.ENABLE_QUERY_PLANNING:
                try:
                    print(f"[RETRIEVER] Importing query_planner...", flush=True)
                    from app.utils.query_planner import get_query_planner
                    print(f"[RETRIEVER] Getting query planner instance...", flush=True)
                    planner = get_query_planner()
                    print(f"[RETRIEVER] Query planner ready, preparing article context...", flush=True)

                    # Phase 4: Pass article context to query planner for dynamic freshness decisions
                    article_context = None
                    if claims and claims[0].get("article_classification"):
                        article_context = claims[0]["article_classification"]
                        logger.info(f"[RETRIEVE] Passing article context to query planner: domain={article_context.get('primary_domain')}")

                    print(f"[RETRIEVER] Calling plan_queries_batch for {len(claims)} claims... (this is an LLM call)", flush=True)
                    _qp_start = _time.time()
                    query_plans = await planner.plan_queries_batch(claims, article_context=article_context)
                    _qp_elapsed = _time.time() - _qp_start
                    print(f"[RETRIEVER] Query planning returned in {_qp_elapsed:.2f}s", flush=True)
                    if query_plans:
                        logger.info(f"Query planning complete: {len(query_plans)} plans for {len(claims)} claims")
                        # Attach query plans to claims
                        for i, plan in enumerate(query_plans):
                            claim_idx = plan.get("claim_index", i)
                            if claim_idx < len(claims):
                                claims[claim_idx]["query_plan"] = plan
                    else:
                        logger.warning("Query planning returned no plans, using fallback")
                except Exception as e:
                    print(f"[RETRIEVER] Query planning FAILED: {type(e).__name__}: {e}", flush=True)
                    logger.warning(f"Query planning failed: {e}, using fallback")
            else:
                print(f"[RETRIEVER] Query planning disabled, skipping...", flush=True)

            # Process claims with concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrent_claims)
            tasks = [
                self._retrieve_evidence_for_single_claim(claim, semaphore, excluded_domain)
                for claim in claims
            ]
            
            import time as _time
            _gather_start = _time.time()
            print(f"\n[RETRIEVER] Starting gather for {len(tasks)} tasks at {_gather_start:.2f}", flush=True)
            logger.info(f"[RETRIEVER DEBUG] Gathering results for {len(tasks)} tasks")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            _gather_elapsed = _time.time() - _gather_start
            print(f"[RETRIEVER] Gather complete in {_gather_elapsed:.2f}s - {len(results)} results", flush=True)
            logger.info(f"[RETRIEVER DEBUG] Gather complete in {_gather_elapsed:.2f}s. Results count: {len(results)}")

            # Log each result type
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.error(f"[RETRIEVER DEBUG] Result {i}: EXCEPTION {type(r).__name__}: {r}")
                elif isinstance(r, dict):
                    logger.info(f"[RETRIEVER DEBUG] Result {i}: dict with {len(r.get('filtered_evidence', []))} filtered, {len(r.get('raw_evidence', []))} raw")
                else:
                    logger.info(f"[RETRIEVER DEBUG] Result {i}: type={type(r)}, len={len(r) if hasattr(r, '__len__') else 'N/A'}")

            # Organize results by claim position
            evidence_by_claim = {}
            all_raw_evidence = []
            pre_weighting_by_claim = {}

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Evidence retrieval failed for claim {i}: {result}")
                    evidence_by_claim[str(i)] = []
                elif isinstance(result, dict):
                    # New structure with raw evidence
                    evidence_by_claim[str(i)] = result.get("filtered_evidence", [])
                    pre_weighting_by_claim[str(i)] = result.get("pre_weighting_evidence", [])
                    raw_evidence = result.get("raw_evidence", [])
                    claim_position = result.get("claim_position", i)
                    claim_text = result.get("claim_text", "")
                    # Add claim context to each raw evidence item
                    for raw_item in raw_evidence:
                        raw_item["claim_position"] = claim_position
                        raw_item["claim_text"] = claim_text
                    all_raw_evidence.extend(raw_evidence)
                else:
                    # Legacy list format (backward compatibility)
                    evidence_by_claim[str(i)] = result if isinstance(result, list) else []

            # RECOVERY: Ensure minimum evidence per claim
            # This catches claims that ended up with insufficient evidence after initial retrieval
            _recovery_start = _time.time()
            print(f"[RETRIEVER] Starting recovery search for claims with <{self.MIN_EVIDENCE_PER_CLAIM} evidence...", flush=True)
            evidence_by_claim, recovery_raw = await self._ensure_minimum_evidence(
                evidence_by_claim=evidence_by_claim,
                claims=claims,
                excluded_domain=excluded_domain
            )
            _recovery_elapsed = _time.time() - _recovery_start
            print(f"[RETRIEVER] Recovery complete in {_recovery_elapsed:.2f}s - added {len(recovery_raw)} raw items", flush=True)
            all_raw_evidence.extend(recovery_raw)

            # Return both filtered evidence and raw evidence
            _func_elapsed = _time.time() - _func_start
            total_evidence = sum(len(ev) for ev in evidence_by_claim.values())
            print(f"[RETRIEVER EXIT] Returning {total_evidence} total evidence items for {len(evidence_by_claim)} claims in {_func_elapsed:.2f}s", flush=True)
            return {
                "evidence_by_claim": evidence_by_claim,
                "raw_evidence": all_raw_evidence,
                "raw_sources_count": len(all_raw_evidence),
                "pre_weighting_evidence": pre_weighting_by_claim,
            }

        except Exception as e:
            import traceback
            logger.error(f"[RETRIEVER DEBUG] Evidence retrieval EXCEPTION: {type(e).__name__}: {e}")
            logger.error(f"[RETRIEVER DEBUG] Full traceback:\n{traceback.format_exc()}")
            return {
                "evidence_by_claim": {},
                "raw_evidence": [],
                "raw_sources_count": 0
            }
    
    async def _ensure_minimum_evidence(
        self,
        evidence_by_claim: Dict[str, List[Dict[str, Any]]],
        claims: List[Dict[str, Any]],
        excluded_domain: Optional[str] = None
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
                claims_needing_recovery.append({
                    "claim": claim,
                    "position": claim_pos,
                    "current_count": len(current_evidence)
                })

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
                    excluded_domain=excluded_domain
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
        excluded_domain: Optional[str] = None
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
            primary_domain = article_classification.get("primary_domain", "general").lower()

            # Map to our domain categories
            domain_key = "general"
            if any(d in primary_domain for d in ["health", "medical", "disease", "virus"]):
                domain_key = "health"
            elif any(d in primary_domain for d in ["science", "research", "study"]):
                domain_key = "science"
            elif any(d in primary_domain for d in ["government", "politics", "law"]):
                domain_key = "government"
            elif any(d in primary_domain for d in ["finance", "economic", "market"]):
                domain_key = "finance"
            elif any(d in primary_domain for d in ["sport"]):
                domain_key = "sports"

            authoritative_sources = self.AUTHORITATIVE_SOURCES_BY_DOMAIN.get(domain_key, [])

            logger.info(
                f"[RECOVERY] Claim {claim_position}: domain={domain_key}, "
                f"authoritative sources={authoritative_sources[:3]}"
            )

            # Generate targeted queries
            # Query 1: Direct claim text with site filter for authoritative sources
            # Query 2: Simplified key phrase extraction
            queries = self._generate_recovery_queries(claim_text, authoritative_sources)

            if not queries:
                logger.warning(f"[RECOVERY] No queries generated for claim {claim_position}")
                return [], []

            # Execute searches
            all_snippets = []
            for query in queries[:2]:  # Limit to 2 queries to control latency
                try:
                    results = await self.search_service.search_for_evidence(
                        query,
                        max_results=5,
                        freshness="py"  # Past year - stable facts
                    )
                    if results:
                        # Convert SearchResult to EvidenceSnippet format
                        for r in results:
                            # Skip if URL already exists
                            url = getattr(r, 'url', '') if hasattr(r, 'url') else r.get('url', '')
                            if url in existing_urls:
                                continue

                            snippet = EvidenceSnippet(
                                text=getattr(r, 'snippet', '') if hasattr(r, 'snippet') else r.get('snippet', ''),
                                source=getattr(r, 'source', '') if hasattr(r, 'source') else r.get('source', ''),
                                url=url,
                                title=getattr(r, 'title', '') if hasattr(r, 'title') else r.get('title', ''),
                                published_date=getattr(r, 'published_date', None) if hasattr(r, 'published_date') else r.get('published_date'),
                                relevance_score=0.5,  # Neutral score, let LLM scorer decide
                                # word_count is calculated automatically in EvidenceSnippet.__init__
                                metadata={"recovery_search": True, "domain_key": domain_key}
                            )
                            all_snippets.append(snippet)

                except Exception as e:
                    logger.warning(f"[RECOVERY] Search failed for query '{query[:50]}...': {e}")
                    continue

            if not all_snippets:
                return [], []

            # Apply same credibility weighting/filtering as main retrieval
            # This ensures domain capping, credibility scoring, etc. are applied
            ranked_evidence = []
            for idx, snippet in enumerate(all_snippets[:10]):  # Cap at 10 for processing
                credibility = snippet.metadata.get("credibility_score", 0.6) if snippet.metadata else 0.6
                ranked_evidence.append({
                    "id": f"recovery_{claim_position}_{idx}",
                    "text": snippet.text,
                    "source": snippet.source,
                    "url": snippet.url,
                    "title": snippet.title,
                    "published_date": snippet.published_date,
                    "relevance_score": float(snippet.relevance_score),
                    "semantic_similarity": 0.0,
                    "combined_score": 0.0,
                    "word_count": snippet.word_count,
                    "credibility_score": credibility,
                    "metadata": snippet.metadata,
                    "is_recovery": True
                })

            # Apply credibility weighting (includes domain capping)
            result = self._apply_credibility_weighting(
                ranked_evidence,
                claim,
                track_raw_evidence=True
            )
            final_evidence, raw_evidence = result if isinstance(result, tuple) else (result, [])

            # Mark raw evidence as from recovery
            for raw_item in raw_evidence:
                raw_item["is_recovery"] = True
                raw_item["claim_position"] = claim_position

            return final_evidence, raw_evidence

        except Exception as e:
            logger.error(f"[RECOVERY] Error recovering evidence for claim {claim_position}: {e}")
            return [], []

    def _generate_recovery_queries(
        self,
        claim_text: str,
        authoritative_sources: List[str]
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
            'the', 'and', 'for', 'are', 'was', 'were', 'been', 'have', 'has', 'had',
            'will', 'would', 'could', 'should', 'this', 'that', 'with', 'from', 'they',
            'their', 'there', 'what', 'when', 'where', 'which', 'about', 'into', 'than',
            'then', 'can', 'may', 'also', 'some', 'only', 'more', 'most', 'other'
        }

        words = re.findall(r'\b[a-zA-Z]{4,}\b', claim_text)
        key_words = [w for w in words if w.lower() not in stop_words][:6]

        # Also extract numbers (important for factual claims)
        numbers = re.findall(r'\b\d+(?:\.\d+)?%?\b', claim_text)

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
        excluded_domain: Optional[str] = None
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
                    logger.info(f"[FROZEN EVIDENCE REPLAY] Claim {claim_position}: "
                                f"replaying {len(frozen_evidence_items)} frozen evidence items (zero network)")

                    if not frozen_evidence_items:
                        return {
                            "filtered_evidence": [],
                            "raw_evidence": [],
                            "pre_weighting_evidence": [],
                            "claim_position": claim_position,
                            "claim_text": claim_text[:500] if claim_text else "",
                            "search_mode": "frozen_evidence_replay"
                        }

                    # Reconstruct ranked_evidence from frozen data (same shape as lines 763-777)
                    ranked_evidence = []
                    for idx, item in enumerate(frozen_evidence_items):
                        text = item.get("text", "")
                        ranked_evidence.append({
                            "id": f"evidence_{idx}",
                            "text": text,
                            "source": item.get("source", ""),
                            "url": item.get("url", ""),
                            "title": item.get("title", ""),
                            "published_date": item.get("published_date"),
                            "relevance_score": float(item.get("relevance_score", 0.0)),
                            "semantic_similarity": 0.0,
                            "combined_score": 0.0,
                            "word_count": len(text.split()) if text else 0,
                            "external_source_provider": item.get("external_source_provider"),
                            "is_factcheck": item.get("is_factcheck", False),
                            "source_type": item.get("source_type"),
                            "metadata": item.get("metadata", {}),
                        })

                    # Run through credibility weighting — SAME path as normal pipeline
                    result = self._apply_credibility_weighting(ranked_evidence, claim, track_raw_evidence=True)
                    final_evidence, raw_evidence = result if isinstance(result, tuple) else (result, [])

                    return {
                        "filtered_evidence": final_evidence[:self.max_sources_per_claim],
                        "raw_evidence": raw_evidence,
                        "pre_weighting_evidence": ranked_evidence,
                        "claim_position": claim_position,
                        "claim_text": claim_text[:500] if claim_text else "",
                        "search_mode": "frozen_evidence_replay"
                    }

                # FROZEN REPLAY: Skip web search, use pre-set URLs
                frozen_url_data = claim.get("frozen_urls")  # List[Dict] with url/title/snippet
                if frozen_url_data is not None:
                    logger.info(f"[FROZEN REPLAY] Claim {claim_position}: replaying {len(frozen_url_data)} frozen URLs")

                    # Create SearchResult objects with stored metadata
                    synthetic_results = []
                    for item in frozen_url_data:
                        url = item.get("url", "") if isinstance(item, dict) else str(item)
                        if not url or not url.startswith("http"):
                            continue
                        title = item.get("title", "") if isinstance(item, dict) else ""
                        snippet = item.get("snippet", "") if isinstance(item, dict) else ""
                        synthetic_results.append(SearchResult(title=title, url=url, snippet=snippet))

                    # Extract content from frozen URLs (same path as normal pipeline)
                    frozen_semaphore = asyncio.Semaphore(3)
                    extraction_tasks = [
                        self.evidence_extractor._extract_from_page(sr, claim_text, frozen_semaphore)
                        for sr in synthetic_results
                    ]
                    extracted = await asyncio.gather(*extraction_tasks, return_exceptions=True)
                    web_evidence_snippets = [r for r in extracted if isinstance(r, EvidenceSnippet)]

                    # Government APIs: run by default (matches normal pipeline behavior)
                    api_evidence = {"evidence": [], "api_stats": {}}
                    skip_gov_apis = os.environ.get("FROZEN_REPLAY_SKIP_GOV_APIS", "0") == "1"
                    if not skip_gov_apis:
                        try:
                            api_evidence = await asyncio.wait_for(
                                self._retrieve_from_government_apis(claim_text, claim),
                                timeout=15
                            )
                        except (asyncio.TimeoutError, Exception) as e:
                            logger.warning(f"[FROZEN REPLAY] Gov API failed for claim {claim_position}: {e}")

                    logger.info(f"[FROZEN REPLAY] Claim {claim_position}: {len(web_evidence_snippets)} extracted + {len(api_evidence.get('evidence', []))} API")

                    # Merge web + API evidence through the same ranking/credibility path
                    api_snippets = self._convert_api_evidence_to_snippets(api_evidence.get("evidence", []))
                    all_evidence_snippets = list(web_evidence_snippets) + api_snippets
                    claim["api_stats"] = api_evidence.get("api_stats", {})

                    if not all_evidence_snippets:
                        return {
                            "filtered_evidence": [],
                            "raw_evidence": [],
                            "claim_position": claim_position,
                            "claim_text": claim_text[:500] if claim_text else "",
                            "search_mode": "frozen_replay"
                        }

                    # Apply same ranking/credibility path as normal pipeline
                    MAX_EVIDENCE_FOR_RANKING = 30
                    if len(all_evidence_snippets) > MAX_EVIDENCE_FOR_RANKING:
                        all_evidence_snippets.sort(key=lambda x: x.relevance_score if hasattr(x, 'relevance_score') else 0.5, reverse=True)
                        all_evidence_snippets = all_evidence_snippets[:MAX_EVIDENCE_FOR_RANKING]

                    if getattr(settings, 'ENABLE_LLM_RELEVANCE_SCORER', True):
                        ranked_evidence = []
                        for idx, snippet_item in enumerate(all_evidence_snippets):
                            external_source = snippet_item.metadata.get("external_source_provider") if snippet_item.metadata else None
                            credibility = snippet_item.metadata.get("credibility_score", 0.6) if snippet_item.metadata else 0.6
                            ranked_evidence.append({
                                "id": f"evidence_{idx}",
                                "text": snippet_item.text,
                                "source": snippet_item.source,
                                "url": snippet_item.url,
                                "title": snippet_item.title,
                                "published_date": snippet_item.published_date,
                                "relevance_score": float(snippet_item.relevance_score),
                                "semantic_similarity": 0.0,
                                "combined_score": 0.0,
                                "word_count": snippet_item.word_count,
                                "credibility_score": credibility,
                                "external_source_provider": external_source,
                                "metadata": snippet_item.metadata
                            })
                    else:
                        ranked_evidence = await self._rank_evidence_with_embeddings(claim_text, all_evidence_snippets)
                        ranked_evidence = await self._rerank_with_cross_encoder(claim_text, ranked_evidence)

                    pre_weighting_snapshot = copy.deepcopy(ranked_evidence)

                    result = self._apply_credibility_weighting(ranked_evidence, claim, track_raw_evidence=True)
                    final_evidence, raw_evidence = result if isinstance(result, tuple) else (result, [])

                    await self._store_evidence_embeddings(claim, final_evidence)

                    return {
                        "filtered_evidence": final_evidence[:self.max_sources_per_claim],
                        "raw_evidence": raw_evidence,
                        "pre_weighting_evidence": pre_weighting_snapshot,
                        "claim_position": claim_position,
                        "claim_text": claim_text[:500] if claim_text else "",
                        "search_mode": "frozen_replay"
                    }

                # Step 1: Parallel retrieval from web search AND government APIs
                subject_context = claim.get("subject_context")
                key_entities = claim.get("key_entities", [])
                temporal_analysis = claim.get("temporal_analysis")  # TIER 1: For query refinement

                # Article context grounding (Phase 4)
                article_title = claim.get("source_title")
                article_date = claim.get("source_date")

                # Context logging moved to DEBUG to reduce noise
                if subject_context:
                    logger.debug(f"Using context: '{subject_context}' with entities: {key_entities[:3]}")

                # Check for query plan (from Query Planning Agent)
                query_plan = claim.get("query_plan")

                # DEPRECATED: Extract freshness from temporal_analysis (now disabled, Query Planner provides freshness)
                freshness = None
                if temporal_analysis:
                    temporal_window = temporal_analysis.get("temporal_window", "any")
                    freshness = self.TEMPORAL_TO_FRESHNESS.get(temporal_window, "2y")
                    if freshness != "2y":
                        logger.info(f"[RETRIEVE] FRESHNESS | Claim {claim_position} | temporal_window={temporal_window} -> freshness={freshness}")

                # Run web search and API retrieval in parallel
                if query_plan and query_plan.get("queries"):
                    # Use Query Planning Agent's targeted queries
                    web_search_task = self._execute_planned_queries(
                        claim_text,
                        query_plan,
                        excluded_domain=excluded_domain,
                        max_sources=self.max_sources_per_claim * 2,
                        freshness=freshness
                    )
                    queries_preview = query_plan['queries'][:2]  # Show first 2 queries
                    logger.info(f"[RETRIEVE] QUERY PLAN | Claim {claim_position} | Type: {query_plan.get('claim_type')} | Queries: {queries_preview}")
                else:
                    # Fallback: Standard query formulation
                    web_search_task = self.evidence_extractor.extract_evidence_for_claim(
                        claim_text,
                        max_sources=self.max_sources_per_claim * 2,  # Get extra for filtering
                        subject_context=subject_context,
                        key_entities=key_entities,
                        excluded_domain=excluded_domain,
                        temporal_analysis=temporal_analysis,  # TIER 1: Pass to query formulation
                        article_title=article_title,  # Article context grounding
                        article_date=article_date  # Article context grounding
                    )

                # Phase 5: Government API retrieval (parallel with web search)
                api_results_task = self._retrieve_from_government_apis(claim_text, claim)

                # Await both tasks concurrently with per-claim timeout
                # IMPORTANT: Use asyncio.wait instead of wait_for+gather to preserve partial results
                # If one task completes but the other times out, we keep the completed results
                CLAIM_TIMEOUT = 45  # seconds per claim
                logger.info(f"[SINGLE CLAIM DEBUG] Awaiting web search + API tasks for claim {claim_position} (timeout={CLAIM_TIMEOUT}s)")

                # Wrap coroutines in named tasks so we can identify them after wait()
                web_task = asyncio.create_task(web_search_task, name="web_search")
                api_task = asyncio.create_task(api_results_task, name="api_retrieval")

                # Wait for tasks with timeout - returns (done, pending) sets
                done, pending = await asyncio.wait(
                    {web_task, api_task},
                    timeout=CLAIM_TIMEOUT,
                    return_when=asyncio.ALL_COMPLETED
                )

                # Extract results from completed tasks, use defaults for timed-out ones
                web_evidence_snippets = []
                api_evidence = {"evidence": [], "api_stats": {}}
                timed_out_tasks = []

                for task in done:
                    try:
                        result = task.result()
                        if task.get_name() == "web_search":
                            web_evidence_snippets = result if not isinstance(result, Exception) else []
                            if isinstance(result, Exception):
                                logger.error(f"[CLAIM {claim_position}] Web search exception: {result}")
                        elif task.get_name() == "api_retrieval":
                            api_evidence = result if not isinstance(result, Exception) else {"evidence": [], "api_stats": {}}
                            if isinstance(result, Exception):
                                logger.error(f"[CLAIM {claim_position}] API retrieval exception: {result}")
                    except Exception as e:
                        logger.error(f"[CLAIM {claim_position}] Error extracting task result: {e}")

                # Cancel any still-pending tasks and log what timed out
                for task in pending:
                    task.cancel()
                    timed_out_tasks.append(task.get_name())

                if timed_out_tasks:
                    logger.warning(f"[CLAIM {claim_position}] Tasks timed out after {CLAIM_TIMEOUT}s: {timed_out_tasks}")
                    print(f"[CLAIM {claim_position}] Partial timeout - {timed_out_tasks} timed out, keeping completed results", flush=True)
                    api_evidence["api_stats"]["timeout"] = True
                else:
                    logger.info(f"[SINGLE CLAIM DEBUG] All tasks complete for claim {claim_position}")

                # Merge web search and API results
                evidence_snippets = web_evidence_snippets
                api_evidence_items = api_evidence.get("evidence", [])

                # Store API stats in claim for later tracking
                claim["api_stats"] = api_evidence.get("api_stats", {})

                # CRITICAL STDOUT DIAGNOSTIC: Ensure visibility even if logging fails
                print(f"\n{'='*60}", flush=True)
                print(f"[CLAIM {claim_position}] WEB SEARCH: {len(evidence_snippets) if isinstance(evidence_snippets, list) else 'ERROR'} snippets", flush=True)
                print(f"[CLAIM {claim_position}] API EVIDENCE: {len(api_evidence_items)} items", flush=True)
                print(f"[CLAIM {claim_position}] API STATS: {api_evidence.get('api_stats', {})}", flush=True)
                if api_evidence_items:
                    print(f"[CLAIM {claim_position}] First API item: {api_evidence_items[0].get('title', 'N/A')[:50]}", flush=True)
                print(f"{'='*60}\n", flush=True)

                # Log evidence counts (single consolidated log)
                web_count = len(web_evidence_snippets) if isinstance(web_evidence_snippets, list) else 0
                api_count = len(api_evidence_items)
                logger.info(f"[RETRIEVE] Claim {claim_position}: {web_count} web + {api_count} API sources")

                if not evidence_snippets and not api_evidence_items:
                    logger.warning(f"[RETRIEVE] NO EVIDENCE for claim {claim_position}")
                    return {
                        "filtered_evidence": [],
                        "raw_evidence": [],
                        "claim_position": claim_position,
                        "claim_text": claim_text[:500] if claim_text else ""
                    }

                # Step 2: Merge and rank ALL evidence (web + API) using embeddings (bi-encoder)
                api_snippets = self._convert_api_evidence_to_snippets(api_evidence_items)
                logger.critical(f"[EVIDENCE TRACE] Claim {claim_position}: {len(evidence_snippets)} web snippets + {len(api_snippets)} API snippets (from {len(api_evidence_items)} API items)")
                all_evidence_snippets = evidence_snippets + api_snippets

                # Fix 0c: Cap combined evidence before expensive ranking
                # Reduced from 50 to 30: focus on quality, not quantity
                MAX_EVIDENCE_FOR_RANKING = 30
                if len(all_evidence_snippets) > MAX_EVIDENCE_FOR_RANKING:
                    logger.info(f"[EVIDENCE CAP] Reducing {len(all_evidence_snippets)} items to {MAX_EVIDENCE_FOR_RANKING} before ranking")
                    # Sort by relevance_score and keep best
                    all_evidence_snippets.sort(key=lambda x: x.relevance_score if hasattr(x, 'relevance_score') else 0.5, reverse=True)
                    all_evidence_snippets = all_evidence_snippets[:MAX_EVIDENCE_FOR_RANKING]

                # If LLM scorer is enabled, skip embedding ranking (it's done later in pipeline)
                # This saves ~1-2s of compute per claim and avoids redundant topical scoring
                if getattr(settings, 'ENABLE_LLM_RELEVANCE_SCORER', True):
                    # Pass evidence through without embedding ranking
                    # LLM scorer will handle relevance scoring later
                    logger.debug(f"[RETRIEVE] Skipping embedding ranking - LLM scorer enabled")
                    ranked_evidence = []
                    for idx, snippet in enumerate(all_evidence_snippets):
                        external_source = snippet.metadata.get("external_source_provider") if snippet.metadata else None
                        credibility = snippet.metadata.get("credibility_score", 0.6) if snippet.metadata else 0.6
                        ranked_evidence.append({
                            "id": f"evidence_{idx}",
                            "text": snippet.text,
                            "source": snippet.source,
                            "url": snippet.url,
                            "title": snippet.title,
                            "published_date": snippet.published_date,
                            "relevance_score": float(snippet.relevance_score),
                            "semantic_similarity": 0.0,  # Not computed - LLM scorer will score relevance
                            "combined_score": 0.0,  # Not computed - LLM scorer will score relevance
                            "word_count": snippet.word_count,
                            "credibility_score": credibility,
                            "external_source_provider": external_source,
                            "metadata": snippet.metadata
                        })
                else:
                    # Legacy path: Use embedding-based ranking
                    ranked_evidence = await self._rank_evidence_with_embeddings(
                        claim_text,
                        all_evidence_snippets
                    )

                    # Step 2.5: Cross-encoder reranking for precision (Phase 1.3)
                    ranked_evidence = await self._rerank_with_cross_encoder(
                        claim_text,
                        ranked_evidence
                    )

                # Step 3: Apply credibility and recency weighting (with raw evidence tracking)
                logger.critical(f"[EVIDENCE TRACE] Claim {claim_position}: {len(ranked_evidence)} items BEFORE credibility weighting")
                pre_weighting_snapshot = copy.deepcopy(ranked_evidence)
                result = self._apply_credibility_weighting(ranked_evidence, claim, track_raw_evidence=True)
                final_evidence, raw_evidence = result if isinstance(result, tuple) else (result, [])
                logger.critical(f"[EVIDENCE TRACE] Claim {claim_position}: {len(final_evidence)} items AFTER credibility weighting")

                # Step 4: Store in vector database for future retrieval
                await self._store_evidence_embeddings(claim, final_evidence)

                # Return top evidence along with raw evidence metadata
                return {
                    "filtered_evidence": final_evidence[:self.max_sources_per_claim],
                    "raw_evidence": raw_evidence,
                    "pre_weighting_evidence": pre_weighting_snapshot,
                    "claim_position": claim_position,
                    "claim_text": claim_text[:500] if claim_text else ""
                }
                
            except Exception as e:
                logger.error(f"Single claim evidence retrieval error: {e}")
                return {
                    "filtered_evidence": [],
                    "raw_evidence": [],
                    "claim_position": claim.get("position", 0),
                    "claim_text": claim.get("text", "")[:500] if claim.get("text") else ""
                }

    async def _execute_planned_queries(
        self,
        claim_text: str,
        query_plan: Dict[str, Any],
        excluded_domain: Optional[str] = None,
        max_sources: int = 20,
        freshness: Optional[str] = None
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
            priority_sources = query_plan.get("priority_sources", [])
            claim_type = query_plan.get("claim_type", "general")  # Keep for metadata/backward compat

            # ============================================================
            # DYNAMIC FRESHNESS: Use LLM-decided freshness from query plan
            # ============================================================
            # The query planner receives full article context and decides
            # freshness per claim based on domain, temporal context, and
            # evidence guidance. No more hardcoded claim_type lookups.
            effective_freshness = query_plan.get("freshness", "py")
            plan_reasoning = query_plan.get("reasoning", "default")

            # NOTE: TemporalAnalyzer reconciliation removed - Query Planner is single source of truth

            logger.info(
                f"[FRESHNESS] Using plan freshness: {effective_freshness} (reasoning: {plan_reasoning[:50]})"
            )

            if not queries:
                logger.warning(f"No queries in plan for claim: {claim_text[:50]}...")
                return []

            # Get site filter from query planner
            from app.utils.query_planner import get_query_planner
            planner = get_query_planner()
            site_filter = planner.get_site_filter(priority_sources, claim_type)

            logger.debug(f"Executing {len(queries)} planned queries")

            # Execute all queries concurrently
            query_tasks = []
            sources_per_query = max(3, max_sources // len(queries))  # Distribute sources across queries

            for query in queries:
                # Only append site filter if query doesn't already have one (LLM may include it)
                if site_filter and "site:" not in query.lower():
                    full_query = f"{query} {site_filter}"
                else:
                    full_query = query
                task = self.evidence_extractor.search_service.search_for_evidence(
                    full_query,
                    max_results=sources_per_query,
                    freshness=effective_freshness  # Use domain-aware freshness
                )
                query_tasks.append(task)

            # Gather all search results
            all_results = await asyncio.gather(*query_tasks, return_exceptions=True)

            # Merge and deduplicate search results by URL
            seen_urls = set()
            unique_search_results = []

            for i, results in enumerate(all_results):
                if isinstance(results, Exception):
                    logger.warning(f"Query {i+1} failed: {results}")
                    continue

                for result in results:
                    # Skip excluded domain
                    if excluded_domain and extract_domain(result.url) == excluded_domain:
                        continue

                    # Deduplicate by URL
                    if result.url in seen_urls:
                        continue
                    seen_urls.add(result.url)

                    # Attach query metadata to result for later preservation
                    result._query_index = i
                    result._query_used = queries[i]
                    result._claim_type = claim_type
                    result._freshness = effective_freshness  # For staleness check
                    unique_search_results.append(result)

            # BALANCED FRESHNESS FALLBACK when 0 results
            if not unique_search_results:
                fallback_progression = ["pw", "pm", "py"]
                current_idx = fallback_progression.index(effective_freshness) if effective_freshness in fallback_progression else -1

                # FALLBACK 1: Try WITHOUT site filter (same freshness)
                if site_filter:
                    logger.info(f"[FRESHNESS FALLBACK] 0 results. Trying without site filter (freshness={effective_freshness})")
                    for query in queries:
                        try:
                            results = await self.evidence_extractor.search_service.search_for_evidence(
                                query, max_results=sources_per_query, freshness=effective_freshness)
                            for result in results:
                                if excluded_domain and extract_domain(result.url) == excluded_domain:
                                    continue
                                if result.url not in seen_urls:
                                    seen_urls.add(result.url)
                                    result._query_index = queries.index(query)
                                    result._query_used = query
                                    result._claim_type = claim_type
                                    result._freshness = effective_freshness
                                    unique_search_results.append(result)
                        except Exception as e:
                            logger.warning(f"Fallback query failed: {e}")
                    if unique_search_results:
                        logger.info(f"[FRESHNESS FALLBACK] Found {len(unique_search_results)} without site filter")

                # FALLBACK 2: Progressively relax freshness (pw->pm->py, never 2y)
                if not unique_search_results and current_idx >= 0 and current_idx < len(fallback_progression) - 1:
                    for fallback_freshness in fallback_progression[current_idx + 1:]:
                        logger.info(f"[FRESHNESS FALLBACK] Relaxing: {effective_freshness} -> {fallback_freshness}")
                        for query in queries:
                            try:
                                results = await self.evidence_extractor.search_service.search_for_evidence(
                                    query, max_results=sources_per_query, freshness=fallback_freshness)
                                for result in results:
                                    if excluded_domain and extract_domain(result.url) == excluded_domain:
                                        continue
                                    if result.url not in seen_urls:
                                        seen_urls.add(result.url)
                                        result._query_index = queries.index(query)
                                        result._query_used = query
                                        result._claim_type = claim_type
                                        result._freshness = fallback_freshness  # Use fallback freshness
                                        result._freshness_fallback = fallback_freshness
                                        unique_search_results.append(result)
                            except Exception as e:
                                logger.warning(f"Fallback query failed: {e}")
                        if unique_search_results:
                            logger.info(f"[FRESHNESS FALLBACK] Found {len(unique_search_results)} with {fallback_freshness}")
                            break

                if not unique_search_results:
                    logger.warning(f"[FRESHNESS FALLBACK] No results after all attempts")
                    return []

            # ============================================================
            # CRITICAL FIX: Extract actual page content (like standard path)
            # ============================================================
            semaphore = asyncio.Semaphore(self.evidence_extractor.max_concurrent)
            extraction_tasks = [
                self._extract_with_fallback(result, claim_text, semaphore)
                for result in unique_search_results[:max_sources]
            ]

            extracted_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

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
                claim_text,
                max_sources=max_sources
            )

    async def _extract_with_fallback(
        self,
        search_result,
        claim_text: str,
        semaphore: asyncio.Semaphore
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
        query_index = getattr(search_result, '_query_index', None)
        query_used = getattr(search_result, '_query_used', None)
        claim_type = getattr(search_result, '_claim_type', 'general')
        freshness = getattr(search_result, '_freshness', 'py')  # For staleness check

        try:
            # Attempt full content extraction
            snippet = await self.evidence_extractor._extract_from_page(
                search_result,
                claim_text,
                semaphore
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

                # Add staleness check for time-sensitive claims (using dynamic freshness)
                from app.utils.query_planner import check_evidence_staleness
                staleness = check_evidence_staleness(
                    evidence_date=snippet.published_date,
                    freshness=freshness  # Use LLM-decided freshness from query plan
                )
                snippet.metadata["staleness_check"] = staleness
                if staleness["is_stale"]:
                    logger.warning(f"[STALE EVIDENCE] {staleness['message']} - URL: {snippet.url}")

                return snippet

            # Content extraction returned None
            # This means HTML was fetched but yielded no substantive content (JS-only/empty)
            # Policy: Drop entirely - don't pollute with low-signal meta descriptions
            logger.debug(f"Dropping empty extraction for {search_result.url}")
            return None

        except Exception as e:
            # Extraction failed - check if we should use snippet fallback
            error_str = str(e).lower()
            is_blocked = "403" in error_str or "429" in error_str or "forbidden" in error_str
            is_timeout = "timeout" in error_str

            if (is_blocked or is_timeout) and settings.ALLOW_SNIPPET_FALLBACK:
                # Transient failure: Use snippet as fallback with lower score
                extraction_status = "fallback_blocked" if is_blocked else "fallback_timeout"
                logger.debug(f"Using snippet fallback ({extraction_status}) for {search_result.url}")

                return EvidenceSnippet(
                    text=search_result.snippet or "",
                    source=extract_domain(search_result.url),
                    url=search_result.url,
                    title=search_result.title or "",
                    published_date=search_result.published_date,
                    relevance_score=0.4,  # Lower score for fallback snippets
                    metadata={
                        "query_index": query_index,
                        "query_used": query_used,
                        "claim_type": claim_type,
                        "source_path": "query_planning",
                        "extraction_status": extraction_status,
                        "is_snippet_fallback": True,
                        "fallback_reason": str(e)[:100]
                    }
                )
            else:
                # Other failure or fallback disabled: Drop
                logger.debug(f"Dropping failed extraction for {search_result.url}: {e}")
                return None

    async def _rank_evidence_with_embeddings(self, claim: str,
                                           evidence_snippets: List[EvidenceSnippet]) -> List[Dict[str, Any]]:
        """Rank evidence using semantic similarity"""
        try:
            if not evidence_snippets:
                return []
            
            # Prepare evidence texts for embedding
            evidence_texts = [snippet.text for snippet in evidence_snippets]
            
            # Get similarity rankings
            ranked_results = await rank_evidence_by_similarity(
                claim, 
                evidence_texts, 
                top_k=len(evidence_texts)
            )
            
            # Convert to evidence format with similarity scores
            ranked_evidence = []
            filtered_count = 0

            for idx, similarity, text in ranked_results:
                if idx < len(evidence_snippets):
                    snippet = evidence_snippets[idx]

                    # SEMANTIC RELEVANCE FILTER: Skip evidence below similarity threshold
                    # This prevents generic landing pages (e.g., "how to fact check" guides)
                    # from being used as evidence when they have no relevance to the claim
                    if settings.ENABLE_SEMANTIC_RELEVANCE_FILTER:
                        if similarity < settings.SEMANTIC_SIMILARITY_THRESHOLD:
                            filtered_count += 1
                            logger.info(
                                f"[RETRIEVE] FILTERED (low relevance): {snippet.source} "
                                f"(similarity={similarity:.3f} < {settings.SEMANTIC_SIMILARITY_THRESHOLD}) "
                                f"- {snippet.title[:60]}..."
                            )
                            continue

                    # Extract API-specific fields from metadata (if present)
                    # Issue #6 Fix: Preserve external_source_provider at top level
                    external_source = snippet.metadata.get("external_source_provider") if snippet.metadata else None
                    credibility = snippet.metadata.get("credibility_score", 0.6) if snippet.metadata else 0.6

                    evidence_item = {
                        "id": f"evidence_{idx}",
                        "text": snippet.text,
                        "source": snippet.source,
                        "url": snippet.url,
                        "title": snippet.title,
                        "published_date": snippet.published_date,
                        "relevance_score": float(snippet.relevance_score),
                        "semantic_similarity": float(similarity),
                        "combined_score": float((snippet.relevance_score + similarity) / 2),
                        "word_count": snippet.word_count,
                        "credibility_score": credibility,  # Add at top level
                        "external_source_provider": external_source,  # Add at top level for Issue #6 fix
                        "metadata": snippet.metadata  # Phase 2: Include PDF metadata (page_number, context)
                    }
                    ranked_evidence.append(evidence_item)

            if filtered_count > 0:
                logger.info(f"[RETRIEVE] Semantic filter: {filtered_count} low-relevance evidence items removed")

            # ALIGNED FALLBACK: Keep top 3 when all filtered (same pattern as credibility fallback)
            if len(ranked_evidence) == 0 and len(ranked_results) > 0:
                logger.warning(
                    f"[RETRIEVE] SEMANTIC FALLBACK: All {len(ranked_results)} items below "
                    f"TIER1 threshold ({settings.SEMANTIC_SIMILARITY_THRESHOLD}), keeping top 3"
                )
                sorted_results = sorted(ranked_results, key=lambda x: x[1], reverse=True)
                for idx, similarity, text in sorted_results[:3]:
                    if idx < len(evidence_snippets):
                        snippet = evidence_snippets[idx]
                        external_source = snippet.metadata.get("external_source_provider") if snippet.metadata else None
                        credibility = snippet.metadata.get("credibility_score", settings.UNKNOWN_SOURCE_CREDIBILITY) if snippet.metadata else settings.UNKNOWN_SOURCE_CREDIBILITY
                        ranked_evidence.append({
                            "id": f"evidence_{idx}",
                            "text": snippet.text,
                            "source": snippet.source,
                            "url": snippet.url,
                            "title": snippet.title,
                            "published_date": snippet.published_date,
                            "relevance_score": float(snippet.relevance_score),
                            "semantic_similarity": float(similarity),
                            "combined_score": float((snippet.relevance_score + similarity) / 2),
                            "word_count": snippet.word_count,
                            "credibility_score": credibility,
                            "external_source_provider": external_source,
                            "metadata": snippet.metadata,
                            "is_semantic_fallback": True
                        })
                        logger.info(f"[RETRIEVE] FALLBACK: {snippet.source} (sim={similarity:.3f})")

            # Sort by combined score
            ranked_evidence.sort(key=lambda x: x["combined_score"], reverse=True)
            
            logger.debug(f"Ranked {len(ranked_evidence)} evidence items by similarity")
            return ranked_evidence
            
        except Exception as e:
            logger.error(f"Evidence ranking error: {e}")
            # Fallback: return evidence without embedding ranking
            fallback_evidence = []
            for i, snippet in enumerate(evidence_snippets):
                # Extract API fields (same pattern as main code)
                external_source = snippet.metadata.get("external_source_provider") if snippet.metadata else None
                credibility = snippet.metadata.get("credibility_score", 0.6) if snippet.metadata else 0.6

                fallback_evidence.append({
                    "id": f"evidence_{i}",
                    "text": snippet.text,
                    "source": snippet.source,
                    "url": snippet.url,
                    "title": snippet.title,
                    "published_date": snippet.published_date,
                    "relevance_score": float(snippet.relevance_score),
                    "semantic_similarity": 0.5,
                    "combined_score": float(snippet.relevance_score),
                    "word_count": snippet.word_count,
                    "credibility_score": credibility,  # Add at top level
                    "external_source_provider": external_source,  # Add at top level for Issue #6 fix
                    "metadata": snippet.metadata  # Phase 2: Include PDF metadata (page_number, context)
                })

            return fallback_evidence

    async def _rerank_with_cross_encoder(self, claim_text: str,
                                        evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank evidence using cross-encoder for precision (Phase 1.3).

        Cross-encoders process claim+evidence together with full attention,
        providing more accurate relevance scores than bi-encoders.

        Args:
            claim_text: The claim text
            evidence_list: Evidence items ranked by bi-encoder

        Returns:
            Evidence items reranked by cross-encoder scores
        """
        from app.core.config import settings
        import time

        if not settings.ENABLE_CROSS_ENCODER_RERANK:
            return evidence_list

        if not evidence_list:
            return []

        start_time = time.time()

        try:
            # Lazy load cross-encoder (only when actually used)
            if not hasattr(self, '_cross_encoder'):
                from sentence_transformers import CrossEncoder
                self._cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                logger.debug("Cross-encoder loaded")

            # Prepare claim-evidence pairs
            pairs = [(claim_text, ev.get('text', '')) for ev in evidence_list]

            # Score all pairs (synchronous but fast ~50ms for 10 pairs)
            scores = self._cross_encoder.predict(pairs)

            # Attach scores and preserve bi-encoder scores for comparison
            for i, ev in enumerate(evidence_list):
                ev['cross_encoder_score'] = float(scores[i])
                ev['bi_encoder_score'] = ev.get('combined_score', 0.0)

            # Sort by cross-encoder score
            reranked = sorted(evidence_list, key=lambda x: x['cross_encoder_score'], reverse=True)

            # Log latency and ranking changes
            latency_ms = (time.time() - start_time) * 1000
            ranking_changes = sum(1 for i, ev in enumerate(reranked) if evidence_list.index(ev) != i)

            logger.debug(f"Cross-encoder: {len(pairs)} pairs in {latency_ms:.1f}ms")

            return reranked

        except ImportError as e:
            logger.warning(f"Cross-encoder not available (sentence-transformers.CrossEncoder): {e}")
            logger.warning("Falling back to bi-encoder ranking. Install sentence-transformers>=2.3.0 to enable cross-encoder.")
            return evidence_list
        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}, falling back to bi-encoder ranking")
            return evidence_list

    def _apply_credibility_weighting(
        self,
        evidence_list: List[Dict[str, Any]],
        claim: Dict[str, Any] = None,
        track_raw_evidence: bool = False
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]] | List[Dict[str, Any]]:
        """Apply credibility and recency weighting to evidence.

        Args:
            evidence_list: List of evidence items to filter
            claim: Claim dict for context-aware filtering
            track_raw_evidence: If True, returns tuple (filtered, raw_evidence_metadata)

        Returns:
            If track_raw_evidence=False: List of filtered evidence (backward compatible)
            If track_raw_evidence=True: Tuple of (filtered_evidence, raw_evidence_metadata)
        """
        try:
            from app.core.config import settings
            import copy

            # Store original count for safety check
            original_evidence_count = len(evidence_list)

            # RAW EVIDENCE TRACKING: Create deep copy of all evidence before filtering
            raw_evidence_tracking = []
            if track_raw_evidence:
                for ev in evidence_list:
                    raw_item = {
                        "source": ev.get("source", ""),
                        "url": ev.get("url", ""),
                        "title": ev.get("title", ""),
                        "snippet": ev.get("snippet", ""),
                        "published_date": ev.get("published_date"),
                        "is_included": True,  # Starts as included, may be filtered
                        "filter_stage": None,
                        "filter_reason": None,
                        "tier": None,
                        "is_factcheck": ev.get("is_factcheck", False),
                        "external_source_provider": ev.get("external_source_provider"),
                        "relevance_score": ev.get("combined_score", 0.0),
                        "credibility_score": 0.6,  # Will be updated
                    }
                    raw_evidence_tracking.append(raw_item)

            # Create URL -> raw_item lookup for efficient updates
            url_to_raw = {item["url"]: item for item in raw_evidence_tracking} if track_raw_evidence else {}

            # Phase 6: Extract story jurisdiction for geographic boosting
            story_jurisdiction = None
            if claim:
                article_classification = claim.get("article_classification", {})
                if article_classification:
                    story_jurisdiction = article_classification.get("jurisdiction")
                    if story_jurisdiction and story_jurisdiction != "Global":
                        logger.debug(f"[JURISDICTION] Using story jurisdiction: {story_jurisdiction}")

            for evidence in evidence_list:
                source = evidence.get("source", "").lower()
                url = evidence.get("url", "")

                # Determine credibility tier (Phase 3: pass url and evidence for enrichment)
                # Phase 6: Include story jurisdiction for geographic boosting
                credibility_score = self._get_credibility_score(source, url, evidence, story_jurisdiction)

                # Apply recency weighting (favor recent content)
                recency_score = self._get_recency_score(evidence.get("published_date"))

                # Calculate final weighted score
                base_score = evidence.get("combined_score", 0.5)
                weighted_score = base_score * credibility_score * recency_score

                evidence.update({
                    "credibility_score": credibility_score,
                    "recency_score": recency_score,
                    "final_score": weighted_score
                })

                # RAW EVIDENCE TRACKING: Update credibility and tier info
                if track_raw_evidence and url in url_to_raw:
                    url_to_raw[url]["credibility_score"] = credibility_score
                    url_to_raw[url]["tier"] = evidence.get("tier")
                    url_to_raw[url]["relevance_score"] = base_score

            # Filter by credibility threshold + auto_exclude flag
            # Aligned with CREDIBILITY_MINIMUM (unified threshold)
            MIN_CREDIBILITY = getattr(settings, 'SOURCE_CREDIBILITY_THRESHOLD', 0.55)

            # First, remove auto-excluded sources (social media, satire, etc.)
            before_auto_exclude = len(evidence_list)
            auto_excluded = [e for e in evidence_list if e.get("auto_exclude", False)]
            evidence_list = [e for e in evidence_list if not e.get("auto_exclude", False)]
            auto_excluded_count = before_auto_exclude - len(evidence_list)

            # RAW EVIDENCE TRACKING: Mark auto-excluded sources
            if track_raw_evidence:
                for e in auto_excluded:
                    url = e.get("url", "")
                    if url in url_to_raw:
                        url_to_raw[url]["is_included"] = False
                        url_to_raw[url]["filter_stage"] = "credibility"
                        url_to_raw[url]["filter_reason"] = f"Auto-excluded: {e.get('tier', 'blacklist')} source"

            # Then, filter by minimum credibility
            before_credibility = len(evidence_list)
            # Log sources being filtered for debugging
            low_cred_sources = [e for e in evidence_list if e.get("credibility_score", 0.6) < MIN_CREDIBILITY]
            for e in low_cred_sources[:3]:  # Show first 3 filtered
                logger.info(f"[FILTER] LOW-CRED: {e.get('source')} (cred={e.get('credibility_score', 0.6):.2f} < {MIN_CREDIBILITY}) - {e.get('url', '')[:60]}")

            passing_cred = [e for e in evidence_list if e.get("credibility_score", 0.6) >= MIN_CREDIBILITY]
            failing_cred = [e for e in evidence_list if e.get("credibility_score", 0.6) < MIN_CREDIBILITY]

            # RAW EVIDENCE TRACKING: Mark credibility-filtered sources
            if track_raw_evidence:
                for e in failing_cred:
                    url = e.get("url", "")
                    if url in url_to_raw:
                        url_to_raw[url]["is_included"] = False
                        url_to_raw[url]["filter_stage"] = "credibility"
                        url_to_raw[url]["filter_reason"] = f"Below credibility threshold ({e.get('credibility_score', 0.6):.2f} < {MIN_CREDIBILITY})"

            # ADAPTIVE FALLBACK: If ALL evidence would be filtered, keep top 3 by credibility score
            # This prevents returning 0 evidence when all sources are unknown (0.60 default)
            if len(passing_cred) == 0 and len(evidence_list) > 0:
                # Sort by credibility and take top 3
                evidence_list.sort(key=lambda x: x.get("credibility_score", 0.6), reverse=True)
                fallback_count = min(3, len(evidence_list))
                fallback_kept = evidence_list[:fallback_count]
                fallback_excluded = evidence_list[fallback_count:]
                evidence_list = fallback_kept
                logger.warning(
                    f"[FILTER] ADAPTIVE FALLBACK: All {before_credibility} sources below threshold "
                    f"({MIN_CREDIBILITY}), keeping top {fallback_count} by credibility"
                )
                for e in evidence_list:
                    logger.info(f"[FILTER] FALLBACK KEPT: {e.get('source')} (cred={e.get('credibility_score', 0.6):.2f})")

                # RAW EVIDENCE TRACKING: Mark fallback-excluded sources (adaptive fallback didn't keep them)
                if track_raw_evidence:
                    for e in fallback_excluded:
                        url = e.get("url", "")
                        if url in url_to_raw:
                            url_to_raw[url]["is_included"] = False
                            url_to_raw[url]["filter_stage"] = "credibility"
                            url_to_raw[url]["filter_reason"] = f"Adaptive fallback: only top {fallback_count} kept by credibility"
                    # Also re-mark the ones we're keeping as included
                    for e in fallback_kept:
                        url = e.get("url", "")
                        if url in url_to_raw:
                            url_to_raw[url]["is_included"] = True
                            url_to_raw[url]["filter_stage"] = None
                            url_to_raw[url]["filter_reason"] = None
            else:
                evidence_list = passing_cred
                credibility_filtered_count = before_credibility - len(evidence_list)

            logger.info(f"[FILTER] Stage 1: {original_evidence_count} raw -> {before_auto_exclude - auto_excluded_count} after auto-exclude -> {len(evidence_list)} after cred filter (threshold={MIN_CREDIBILITY})")

            # Stage 1.5: Corroboration boost - boost credibility for evidence corroborated by independent sources
            if settings.ENABLE_CORROBORATION_BOOST and len(evidence_list) >= 2:
                from app.utils.corroboration import apply_corroboration_boost
                evidence_list, corroboration_stats = apply_corroboration_boost(evidence_list)
                if corroboration_stats.get("items_boosted", 0) > 0:
                    logger.info(
                        f"[FILTER] Stage 1.5 (corroboration): {corroboration_stats['items_boosted']} items boosted "
                        f"({corroboration_stats['corroboration_pairs']} corroborating pairs)"
                    )

            # Sort by final weighted score
            evidence_list.sort(key=lambda x: x["final_score"], reverse=True)

            # Helper to track excluded evidence
            def mark_excluded(before_list, after_list, stage, reason_fn):
                """Mark sources that were filtered out."""
                if not track_raw_evidence:
                    return
                after_urls = {e.get("url") for e in after_list}
                for e in before_list:
                    url = e.get("url", "")
                    if url not in after_urls and url in url_to_raw:
                        url_to_raw[url]["is_included"] = False
                        url_to_raw[url]["filter_stage"] = stage
                        url_to_raw[url]["filter_reason"] = reason_fn(e)

            # DEPRECATED: Temporal filtering via TemporalAnalyzer (now disabled, Query Planner handles freshness)
            # This happens BEFORE deduplication to filter out old evidence first
            before_temporal = len(evidence_list)
            before_temporal_list = list(evidence_list) if track_raw_evidence else []
            if claim and settings.ENABLE_TEMPORAL_CONTEXT and claim.get("temporal_analysis"):
                from app.utils.temporal import TemporalAnalyzer
                temporal_analyzer = TemporalAnalyzer()
                evidence_list = temporal_analyzer.filter_evidence_by_time(
                    evidence_list,
                    claim["temporal_analysis"]
                )
            mark_excluded(before_temporal_list, evidence_list, "temporal",
                          lambda e: f"Outdated for time-sensitive claim (date: {e.get('published_date', 'unknown')})")
            logger.info(f"[FILTER] Stage 2 (temporal): {before_temporal} -> {len(evidence_list)}")

            # NEW: Apply deduplication if enabled
            before_dedup = len(evidence_list)
            before_dedup_list = list(evidence_list) if track_raw_evidence else []
            if settings.ENABLE_DEDUPLICATION:
                from app.utils.deduplication import EvidenceDeduplicator
                deduplicator = EvidenceDeduplicator()
                evidence_list, dedup_stats = deduplicator.deduplicate(evidence_list)
            mark_excluded(before_dedup_list, evidence_list, "dedup",
                          lambda e: f"Duplicate content (syndicated from {e.get('original_source_url', 'other source')[:50]})" if e.get('is_syndicated') else "Duplicate content")
            logger.info(f"[FILTER] Stage 3 (dedup): {before_dedup} -> {len(evidence_list)}")

            # Apply source independence checking if enabled
            before_diversity = len(evidence_list)
            before_diversity_list = list(evidence_list) if track_raw_evidence else []
            if settings.ENABLE_SOURCE_DIVERSITY:
                from app.utils.source_independence import SourceIndependenceChecker
                independence_checker = SourceIndependenceChecker()
                evidence_list = independence_checker.enrich_evidence(evidence_list)
                diversity_score, passes = independence_checker.check_diversity(evidence_list)
            mark_excluded(before_diversity_list, evidence_list, "diversity",
                          lambda e: f"Same ownership group as other sources ({e.get('parent_company', 'unknown')})")
            logger.info(f"[FILTER] Stage 4 (diversity): {before_diversity} -> {len(evidence_list)}")

            # Apply domain capping if enabled
            before_domain_cap = len(evidence_list)
            before_domain_cap_list = list(evidence_list) if track_raw_evidence else []
            if settings.ENABLE_DOMAIN_CAPPING:
                from app.utils.domain_capping import DomainCapper
                capper = DomainCapper(
                    max_per_domain=settings.MAX_EVIDENCE_PER_DOMAIN,
                    max_domain_ratio=settings.DOMAIN_DIVERSITY_THRESHOLD
                )
                evidence_list = capper.apply_caps(
                    evidence_list,
                    target_count=self.max_sources_per_claim,
                    outstanding_threshold=getattr(settings, 'OUTSTANDING_SOURCE_THRESHOLD', 0.95)
                )
            mark_excluded(before_domain_cap_list, evidence_list, "domain_cap",
                          lambda e: f"Domain cap reached for {e.get('source', 'this domain')} (max {settings.MAX_EVIDENCE_PER_DOMAIN} per domain)")
            logger.info(f"[FILTER] Stage 5 (domain cap, max={settings.MAX_EVIDENCE_PER_DOMAIN}): {before_domain_cap} -> {len(evidence_list)}")

            # Apply source validation if enabled (Phase 1)
            before_validation = len(evidence_list)
            before_validation_list = list(evidence_list) if track_raw_evidence else []
            if settings.ENABLE_SOURCE_VALIDATION:
                from app.utils.source_validator import get_source_validator
                validator = get_source_validator()
                evidence_list, validation_stats = validator.validate_sources(evidence_list)
            mark_excluded(before_validation_list, evidence_list, "validation",
                          lambda e: "Failed source validation (URL unreachable or content mismatch)")
            logger.info(f"[FILTER] Stage 6 (validation): {before_validation} -> {len(evidence_list)} FINAL")

            # Safety check: Warn if all evidence eliminated
            if len(evidence_list) == 0 and original_evidence_count > 0:
                logger.warning(
                    f"All evidence eliminated by filters for claim. "
                    f"This suggests filters are too aggressive. "
                    f"Original count: {original_evidence_count}"
                )

            # Return with or without raw evidence tracking
            if track_raw_evidence:
                return evidence_list, raw_evidence_tracking
            return evidence_list
            
        except Exception as e:
            logger.error(f"Credibility weighting error: {e}")
            if track_raw_evidence:
                return evidence_list, []
            return evidence_list

    def _get_credibility_score(
        self,
        source: str,
        url: str = None,
        evidence_item: Dict[str, Any] = None,
        story_jurisdiction: Optional[str] = None
    ) -> float:
        """
        Determine credibility score for a source.

        Phase 3 Enhancement: Uses Domain Credibility Framework if enabled,
        otherwise falls back to legacy hardcoded weights.

        TIER 1 IMPROVEMENT: Enhanced with primary source detection.

        Phase 6: Geographic boosting - local sources get credibility boost
        when covering stories in their region.

        Args:
            source: Source name
            url: Source URL (required for Phase 3)
            evidence_item: Evidence dict to enrich with metadata (optional)
            story_jurisdiction: Jurisdiction of the story (e.g., "DK", "UK", "US")
                               for geographic boosting

        Returns:
            Credibility score 0.0-1.0 (with jurisdiction boost if applicable)
        """
        from app.core.config import settings

        # API SOURCE PRIORITY: If evidence comes from a registered API adapter,
        # use its embedded credibility score (0.95) without domain framework lookup.
        # API sources (NOAA, OpenAlex, PubMed, etc.) are authoritative by design.
        if evidence_item and evidence_item.get("external_source_provider"):
            api_provider = evidence_item.get("external_source_provider")
            api_credibility = evidence_item.get("credibility_score", 0.95)

            # Enrich evidence with API-specific metadata
            evidence_item['tier'] = 'authoritative_api'
            evidence_item['risk_flags'] = []
            evidence_item['credibility_reasoning'] = f"Authoritative API source: {api_provider}"
            evidence_item['auto_exclude'] = False
            evidence_item['risk_level'] = 'none'
            evidence_item['risk_warning'] = None

            logger.debug(f"[CREDIBILITY] API source '{api_provider}' using embedded credibility: {api_credibility}")
            return api_credibility

        # Phase 3: Use Domain Credibility Framework if enabled
        # Phase 6: With jurisdiction boosting for local sources
        if settings.ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK and url:
            try:
                from app.services.source_credibility import get_credibility_service

                credibility_service = get_credibility_service()

                # Use jurisdiction-aware method if story jurisdiction is known
                if story_jurisdiction:
                    cred_info = credibility_service.get_credibility_with_jurisdiction(
                        source, url, story_jurisdiction
                    )
                else:
                    cred_info = credibility_service.get_credibility(source, url)

                # Enrich evidence item with credibility metadata if provided
                if evidence_item is not None:
                    evidence_item['tier'] = cred_info.get('tier')
                    evidence_item['risk_flags'] = cred_info.get('risk_flags', [])
                    evidence_item['credibility_reasoning'] = cred_info.get('reasoning')
                    evidence_item['auto_exclude'] = cred_info.get('auto_exclude', False)

                    # Phase 6: Track jurisdiction boost if applied
                    if cred_info.get('jurisdiction_boost', 0) > 0:
                        evidence_item['jurisdiction_boost'] = cred_info.get('jurisdiction_boost')
                        evidence_item['source_jurisdiction'] = cred_info.get('source_jurisdiction')
                        evidence_item['jurisdiction_reasoning'] = cred_info.get('jurisdiction_reasoning')

                    # Get risk assessment
                    risk_info = credibility_service.get_risk_assessment(url)
                    evidence_item['risk_level'] = risk_info.get('risk_level')
                    evidence_item['risk_warning'] = risk_info.get('warning_message')

                # Log unknown sources for progressive curation (Phase 1)
                if cred_info.get('tier') == 'general' and evidence_item is not None:
                    try:
                        from app.services.source_monitor import get_source_monitor
                        from app.core.database import sync_session

                        with sync_session() as db:
                            monitor = get_source_monitor(db)
                            monitor.log_unknown_source(
                                url=url,
                                claim_topic=evidence_item.get('claim_text', '')[:200] if 'claim_text' in evidence_item else None,
                                evidence_title=evidence_item.get('title'),
                                evidence_snippet=evidence_item.get('snippet'),
                                has_https=url.startswith('https://'),
                                has_author_byline=None,  # Could be enriched later
                                has_primary_sources=None  # Could be enriched later
                            )
                    except Exception as e:
                        logger.warning(f"Failed to log unknown source {url}: {e}")

                # Use boosted_credibility if jurisdiction boost was applied, otherwise base credibility
                base_credibility = cred_info.get('boosted_credibility', cred_info.get('credibility', 0.6))

            except Exception as e:
                logger.warning(f"Credibility framework error for {url}: {e}, falling back to legacy")
                base_credibility = None  # Fall through to legacy logic

        else:
            base_credibility = None  # Use legacy logic

        # Legacy fallback: Hardcoded pattern matching
        if base_credibility is None:
            # Academic/research institutions
            if any(domain in source for domain in ['.edu', '.ac.uk', 'university', 'research']):
                base_credibility = self.credibility_weights['academic']

            # Scientific journals
            elif any(journal in source for journal in ['nature', 'science', 'cell', 'lancet', 'nejm']):
                base_credibility = self.credibility_weights['scientific']

            # Government sources
            elif any(domain in source for domain in ['.gov', 'nhs.uk', 'who.int']):
                base_credibility = self.credibility_weights['government']

            # Tier 1 news
            elif any(outlet in source for outlet in ['bbc', 'reuters', 'ap.org', 'apnews']):
                base_credibility = self.credibility_weights['news_tier1']

            # Tier 2 news
            elif any(outlet in source for outlet in [
                'guardian', 'telegraph', 'independent', 'economist', 'ft.com'
            ]):
                base_credibility = self.credibility_weights['news_tier2']

            # Default
            else:
                base_credibility = self.credibility_weights['general']

        # TIER 1 IMPROVEMENT: Apply primary source boost/penalty
        if settings.ENABLE_PRIMARY_SOURCE_DETECTION and evidence_item and url:
            from app.utils.source_type_classifier import get_source_type_classifier
            classifier = get_source_type_classifier()

            source_info = classifier.classify_source(
                url,
                evidence_item.get('title', ''),
                evidence_item.get('snippet', '')
            )

            # Enrich evidence metadata
            evidence_item['source_type'] = source_info['source_type']
            evidence_item['is_primary_source'] = source_info['is_original_research']
            evidence_item['primary_indicators'] = source_info['primary_indicators']

            # Apply boost/penalty (capped at 1.0)
            boost = source_info['credibility_boost']
            final_credibility = min(1.0, base_credibility + boost)

            if boost != 0:
                logger.debug(f"Primary source boost: {source_info['source_type']}")

            return final_credibility

        return base_credibility
    
    def _get_recency_score(self, published_date: Optional[str]) -> float:
        """Calculate recency score (more recent = higher score)"""
        if not published_date:
            return 0.8  # Default for unknown dates

        try:
            source_year = None

            # Pass 1: ISO-like prefix (YYYY-MM-DD or YYYY/MM/DD)
            iso_match = re.match(r'^(\d{4})[-/]', published_date)
            if iso_match:
                source_year = int(iso_match.group(1))

            # Pass 2: fallback regex scan for 4-digit year (19xx/20xx)
            if source_year is None:
                year_match = re.search(r'(?:19|20)\d{2}', published_date)
                if not year_match:
                    return 0.8
                source_year = int(year_match.group(0))

            current_year = datetime.now(timezone.utc).year
            age_years = max(0, current_year - source_year)  # Future dates → 0

            if age_years <= 1:
                return 1.0
            elif age_years == 2:
                return 0.95
            elif age_years == 3:
                return 0.90
            elif age_years == 4:
                return 0.85
            else:
                return 0.80
        except Exception:
            return 0.8

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
            "FC", "United", "City", "Rovers", "Wanderers", "Athletic",
            "Dortmund", "Arsenal", "Chelsea", "Munich", "Madrid", "Barcelona",
            "Milan", "Inter", "Juventus", "PSG", "Bayern", "Liverpool",
            "Tottenham", "Spurs", "Hotspur", "Rangers", "Celtic",
            "Club", "Association", "Federation", "League", "UEFA", "FIFA",
            "Inc", "Ltd", "Corp", "Company", "Organization", "Government"
        )

        # Common title prefixes that indicate PERSON
        person_prefixes = (
            "Mr", "Mrs", "Ms", "Dr", "Prof", "Sir", "Lord", "Lady",
            "President", "Prime Minister", "Minister", "Senator", "Governor"
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
            elif (len(words) >= 2 and
                  all(w[0].isupper() for w in words if w) and
                  not any(suffix in entity_stripped for suffix in org_suffixes)):
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
        self,
        claim_text: str,
        claim: Dict[str, Any]
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
        api_flag = getattr(settings, 'ENABLE_API_RETRIEVAL', False)
        logger.info(f"[API DEBUG] ENABLE_API_RETRIEVAL={api_flag}, self.enable_api_retrieval={self.enable_api_retrieval}")
        logger.info(f"[API DEBUG] Registry adapter count: {len(self.api_registry.adapters)}")

        if not api_flag or not self.enable_api_retrieval:
            logger.warning("[API DEBUG] API retrieval DISABLED by feature flag")
            return {"evidence": [], "api_stats": {}}

        # Safety check: if registry is empty, adapters weren't initialized
        if len(self.api_registry.adapters) == 0:
            logger.error("[API DEBUG] CRITICAL: Registry has 0 adapters! Initializing now...")
            from app.services.api_adapters import initialize_adapters
            initialize_adapters()
            logger.info(f"[API DEBUG] After emergency init: {len(self.api_registry.adapters)} adapters")

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
                    secondary_domains = article_classification.get("secondary_domains", [])

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
                    logger.warning("[API ROUTING] No article classification, defaulting to General")


            # Get relevant API adapters for primary domain
            relevant_adapters = self.api_registry.get_adapters_for_domain(domain, jurisdiction)

            # Also query secondary domain adapters (for cross-domain articles)
            if 'secondary_domains' in dir() and secondary_domains:
                for sec_domain in secondary_domains:
                    sec_adapters = self.api_registry.get_adapters_for_domain(sec_domain, jurisdiction)
                    # Add unique adapters (avoid duplicates)
                    for adapter in sec_adapters:
                        if adapter not in relevant_adapters:
                            relevant_adapters.append(adapter)
                            logger.debug(f"[API ROUTING] Added secondary domain adapter: {adapter.api_name} ({sec_domain})")

            # Claim-level keyword routing: add adapters based on claim text keywords
            # This catches cross-domain claims (e.g., oil prices in Politics articles)
            from app.utils.claim_keyword_router import get_keyword_router
            keyword_router = get_keyword_router()
            keyword_adapters = keyword_router.get_additional_adapters(
                claim_text,
                relevant_adapters,
                self.api_registry
            )
            for adapter in keyword_adapters:
                relevant_adapters.append(adapter)
                logger.info(f"[KEYWORD ROUTING] Added {adapter.api_name} for claim: {claim_text[:50]}...")

            # Fix 0a: Limit adapters per claim - most claims don't need 5+ API sources
            # Reduced from 5 to 3: fewer irrelevant keyword matches, faster processing
            MAX_ADAPTERS_PER_CLAIM = 3
            if len(relevant_adapters) > MAX_ADAPTERS_PER_CLAIM:
                logger.info(f"[API LIMIT] Reducing {len(relevant_adapters)} adapters to {MAX_ADAPTERS_PER_CLAIM}")
                relevant_adapters = relevant_adapters[:MAX_ADAPTERS_PER_CLAIM]

            # Log final adapter list
            adapter_names = [a.api_name for a in relevant_adapters]
            logger.info(f"[API DEBUG] Final adapters to query: {adapter_names}")

            if not relevant_adapters:
                logger.warning(f"[API] No adapters found for domain={domain}, jurisdiction={jurisdiction}")
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
                    entities
                )
                api_tasks.append((adapter.api_name, task))

            # Gather all API results
            api_results = await asyncio.gather(
                *[task for _, task in api_tasks],
                return_exceptions=True
            )

            # Collect evidence and statistics
            all_api_evidence = []
            api_stats = {
                "apis_queried": [],
                "total_api_calls": 0,
                "total_api_results": 0
            }

            for i, (api_name, _) in enumerate(api_tasks):
                result = api_results[i]

                if isinstance(result, Exception):
                    logger.error(f"{api_name} API call failed: {result}")
                    api_stats["apis_queried"].append({"name": api_name, "results": 0, "error": str(result)})
                    continue

                if result:
                    all_api_evidence.extend(result)
                    api_stats["apis_queried"].append({"name": api_name, "results": len(result)})
                    api_stats["total_api_results"] += len(result)
                else:
                    api_stats["apis_queried"].append({"name": api_name, "results": 0})

            api_stats["total_api_calls"] = len(api_tasks)

            # Log API results summary
            logger.info(f"[API DEBUG] Results: {api_stats['total_api_calls']} APIs queried, {api_stats['total_api_results']} total results")
            for api_stat in api_stats["apis_queried"]:
                logger.info(f"[API DEBUG]   - {api_stat['name']}: {api_stat.get('results', 0)} results" +
                           (f" (ERROR: {api_stat.get('error', '')})" if api_stat.get('error') else ""))

            # Fix 0b: Cap total API evidence per claim
            # Reduced from 30 to 10: LLM judge has limited context, quality over quantity
            MAX_API_EVIDENCE_PER_CLAIM = 10
            if len(all_api_evidence) > MAX_API_EVIDENCE_PER_CLAIM:
                logger.info(f"[API CAP] Reducing {len(all_api_evidence)} API items to {MAX_API_EVIDENCE_PER_CLAIM}")
                # Sort by credibility/score and keep best
                all_api_evidence.sort(key=lambda x: x.get('credibility_score', 0.5), reverse=True)
                all_api_evidence = all_api_evidence[:MAX_API_EVIDENCE_PER_CLAIM]

            # CRITICAL DIAGNOSTIC: Log final API evidence count
            logger.critical(f"[API RETRIEVAL] Returning {len(all_api_evidence)} evidence items from {api_stats['total_api_calls']} API calls")
            if all_api_evidence:
                logger.info(f"[API RETRIEVAL] First item: {all_api_evidence[0].get('source', 'N/A')} - {all_api_evidence[0].get('title', 'N/A')[:50]}")

            return {
                "evidence": all_api_evidence,
                "api_stats": api_stats
            }

        except Exception as e:
            logger.error(f"Government API retrieval error: {e}", exc_info=True)
            return {"evidence": [], "api_stats": {}}

    def _convert_api_evidence_to_snippets(
        self,
        api_evidence: List[Dict[str, Any]]
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
                    logger.warning(f"[API CONVERT] Item {i}: Empty snippet, source={evidence.get('source', 'N/A')}")
                    conversion_failures += 1
                    continue

                snippet = EvidenceSnippet(
                    text=text,
                    source=evidence.get("source", "Unknown API"),
                    url=evidence.get("url", ""),
                    title=evidence.get("title", ""),
                    published_date=evidence.get("source_date"),
                    relevance_score=0.8,  # Default relevance for API sources
                    # word_count is calculated automatically in EvidenceSnippet.__init__
                    metadata={
                        **evidence.get("metadata", {}),
                        "external_source_provider": evidence.get("external_source_provider"),
                        "credibility_score": evidence.get("credibility_score", 0.95)
                    }
                )
                snippets.append(snippet)
            except Exception as e:
                logger.warning(f"[API CONVERT] Item {i}: Failed to convert - {e}")
                conversion_failures += 1
                continue

        if conversion_failures > 0:
            logger.warning(f"[API CONVERT] {conversion_failures}/{len(api_evidence)} items failed conversion")

        return snippets
    
    async def _store_evidence_embeddings(self, claim: Dict[str, Any], 
                                       evidence_list: List[Dict[str, Any]]):
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
                    "created_at": datetime.utcnow().isoformat()
                }
                evidence_data.append(evidence_item)
            
            # Store embeddings
            stored_ids = await vector_store.store_evidence_embeddings(evidence_data)
            logger.debug(f"Stored {len(stored_ids)} embeddings")
            
        except Exception as e:
            logger.warning(f"Evidence storage error: {e}")
            # Don't fail the pipeline if storage fails
    
    async def retrieve_from_vector_store(self, claim: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve similar evidence from vector store"""
        try:
            embedding_service = await get_embedding_service()
            vector_store = await get_vector_store()
            
            # Generate claim embedding
            claim_embedding = await embedding_service.embed_text(claim)
            
            # Search for similar evidence
            similar_evidence = await vector_store.search_similar_evidence(
                query_embedding=claim_embedding,
                limit=limit,
                score_threshold=0.7
            )
            
            logger.debug(f"Vector store: {len(similar_evidence)} items")
            return similar_evidence
            
        except Exception as e:
            logger.error(f"Vector store retrieval error: {e}")
            return []