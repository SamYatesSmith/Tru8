import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import numpy as np
from app.services.search import SearchService
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
print(f"[RETRIEVE MODULE LOADED] {_MODULE_LOAD_TIME} - Query Planning: {settings.ENABLE_QUERY_PLANNING}", flush=True)

class EvidenceRetriever:
    """Retrieve and rank evidence for claims using search, embeddings, and vector storage"""

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
        try:
            # Extract excluded domain if provided
            excluded_domain = None
            if exclude_source_url:
                excluded_domain = extract_domain(exclude_source_url)
                logger.debug(f"Excluding source domain: {excluded_domain}")

            # Query Planning Agent: Generate targeted queries for all claims (single LLM call)
            query_plans = None
            logger.info(f"[RETRIEVE] QUERY_PLANNING_ENABLED: {settings.ENABLE_QUERY_PLANNING}")
            if settings.ENABLE_QUERY_PLANNING:
                try:
                    from app.utils.query_planner import get_query_planner
                    planner = get_query_planner()
                    query_plans = await planner.plan_queries_batch(claims)
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
                    logger.warning(f"Query planning failed: {e}, using fallback")

            # Process claims with concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrent_claims)
            tasks = [
                self._retrieve_evidence_for_single_claim(claim, semaphore, excluded_domain)
                for claim in claims
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Organize results by claim position
            evidence_by_claim = {}
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Evidence retrieval failed for claim {i}: {result}")
                    evidence_by_claim[str(i)] = []
                else:
                    evidence_by_claim[str(i)] = result
            
            return evidence_by_claim
            
        except Exception as e:
            logger.error(f"Evidence retrieval error: {e}")
            return {}
    
    async def _retrieve_evidence_for_single_claim(
        self,
        claim: Dict[str, Any],
        semaphore: asyncio.Semaphore,
        excluded_domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve evidence for a single claim"""
        async with semaphore:
            try:
                claim_text = claim.get("text", "")
                claim_position = claim.get("position", 0)

                if not claim_text:
                    return []

                logger.debug(f"Processing claim {claim_position}")

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

                # Extract freshness from temporal_analysis (single source of truth)
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

                # Await both tasks concurrently
                web_evidence_snippets, api_evidence = await asyncio.gather(
                    web_search_task,
                    api_results_task,
                    return_exceptions=True
                )

                # Handle exceptions
                if isinstance(web_evidence_snippets, Exception):
                    logger.error(f"Web search failed: {web_evidence_snippets}")
                    web_evidence_snippets = []
                if isinstance(api_evidence, Exception):
                    logger.error(f"API retrieval failed: {api_evidence}")
                    api_evidence = {"evidence": [], "api_stats": {}}

                # Merge web search and API results
                evidence_snippets = web_evidence_snippets
                api_evidence_items = api_evidence.get("evidence", [])

                # Store API stats in claim for later tracking
                claim["api_stats"] = api_evidence.get("api_stats", {})

                # Log evidence counts (single consolidated log)
                web_count = len(web_evidence_snippets) if isinstance(web_evidence_snippets, list) else 0
                api_count = len(api_evidence_items)
                logger.info(f"[RETRIEVE] Claim {claim_position}: {web_count} web + {api_count} API sources")

                if not evidence_snippets and not api_evidence_items:
                    logger.warning(f"[RETRIEVE] NO EVIDENCE for claim {claim_position}")
                    return []

                # Step 2: Merge and rank ALL evidence (web + API) using embeddings (bi-encoder)
                all_evidence_snippets = evidence_snippets + self._convert_api_evidence_to_snippets(api_evidence_items)

                ranked_evidence = await self._rank_evidence_with_embeddings(
                    claim_text,
                    all_evidence_snippets
                )

                # Step 2.5: Cross-encoder reranking for precision (Phase 1.3)
                ranked_evidence = await self._rerank_with_cross_encoder(
                    claim_text,
                    ranked_evidence
                )

                # Step 3: Apply credibility and recency weighting
                final_evidence = self._apply_credibility_weighting(ranked_evidence, claim)

                # Step 4: Store in vector database for future retrieval
                await self._store_evidence_embeddings(claim, final_evidence)
                
                # Return top evidence
                return final_evidence[:self.max_sources_per_claim]
                
            except Exception as e:
                logger.error(f"Single claim evidence retrieval error: {e}")
                return []

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
            claim_type = query_plan.get("claim_type", "general")

            # ============================================================
            # DOMAIN-AWARE FRESHNESS: Use claim_type to determine freshness
            # ============================================================
            # Claim type is more semantically meaningful than temporal_analysis
            # E.g., "squad_composition" ALWAYS needs fresh evidence (days/weeks)
            # whereas temporal_analysis might default to "any" -> 2y
            from app.utils.query_planner import get_freshness_for_claim_type
            freshness_req = get_freshness_for_claim_type(claim_type)
            claim_type_freshness = freshness_req["brave_freshness"]

            # Use the MORE RESTRICTIVE freshness filter
            # (lower is fresher: pd < pw < pm < py < 2y)
            freshness_order = {"pd": 1, "pw": 2, "pm": 3, "py": 4, "2y": 5}
            if freshness is None:
                effective_freshness = claim_type_freshness
            else:
                # Use whichever is more restrictive (fresher)
                if freshness_order.get(claim_type_freshness, 5) < freshness_order.get(freshness, 5):
                    effective_freshness = claim_type_freshness
                    logger.info(
                        f"[FRESHNESS] Overriding temporal_analysis '{freshness}' with claim_type '{claim_type}' "
                        f"freshness '{claim_type_freshness}' (more restrictive)"
                    )
                else:
                    effective_freshness = freshness

            logger.info(
                f"[FRESHNESS] claim_type={claim_type} -> freshness={effective_freshness} "
                f"(max_age={freshness_req['max_age_days']} days)"
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
                    unique_search_results.append(result)

            if not unique_search_results:
                logger.warning(f"No search results for planned queries")
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

                # Add staleness check for time-sensitive claims
                from app.utils.query_planner import check_evidence_staleness
                staleness = check_evidence_staleness(
                    claim_type,
                    snippet.published_date
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
            for idx, similarity, text in ranked_results:
                if idx < len(evidence_snippets):
                    snippet = evidence_snippets[idx]

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

    def _apply_credibility_weighting(self, evidence_list: List[Dict[str, Any]], claim: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Apply credibility and recency weighting to evidence"""
        try:
            from app.core.config import settings

            # Store original count for safety check
            original_evidence_count = len(evidence_list)

            for evidence in evidence_list:
                source = evidence.get("source", "").lower()
                url = evidence.get("url", "")

                # Determine credibility tier (Phase 3: pass url and evidence for enrichment)
                credibility_score = self._get_credibility_score(source, url, evidence)

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

            # Filter by credibility threshold + auto_exclude flag
            MIN_CREDIBILITY = getattr(settings, 'SOURCE_CREDIBILITY_THRESHOLD', 0.70)

            # First, remove auto-excluded sources (social media, satire, etc.)
            before_auto_exclude = len(evidence_list)
            evidence_list = [e for e in evidence_list if not e.get("auto_exclude", False)]
            auto_excluded_count = before_auto_exclude - len(evidence_list)

            # Then, filter by minimum credibility
            before_credibility = len(evidence_list)
            # Log sources being filtered for debugging
            low_cred_sources = [e for e in evidence_list if e.get("credibility_score", 0.6) < MIN_CREDIBILITY]
            for e in low_cred_sources[:3]:  # Show first 3 filtered
                logger.info(f"[FILTER] LOW-CRED: {e.get('source')} (cred={e.get('credibility_score', 0.6):.2f} < {MIN_CREDIBILITY}) - {e.get('url', '')[:60]}")
            evidence_list = [e for e in evidence_list if e.get("credibility_score", 0.6) >= MIN_CREDIBILITY]
            credibility_filtered_count = before_credibility - len(evidence_list)

            logger.info(f"[FILTER] Stage 1: {original_evidence_count} raw -> {before_auto_exclude - auto_excluded_count} after auto-exclude -> {len(evidence_list)} after cred filter (threshold={MIN_CREDIBILITY})")

            # Sort by final weighted score
            evidence_list.sort(key=lambda x: x["final_score"], reverse=True)

            # Apply temporal filtering if claim is time-sensitive (Phase 1.5, Week 4.5-5.5)
            # This happens BEFORE deduplication to filter out old evidence first
            before_temporal = len(evidence_list)
            if claim and settings.ENABLE_TEMPORAL_CONTEXT and claim.get("temporal_analysis"):
                from app.utils.temporal import TemporalAnalyzer
                temporal_analyzer = TemporalAnalyzer()
                evidence_list = temporal_analyzer.filter_evidence_by_time(
                    evidence_list,
                    claim["temporal_analysis"]
                )
            logger.info(f"[FILTER] Stage 2 (temporal): {before_temporal} -> {len(evidence_list)}")

            # NEW: Apply deduplication if enabled
            before_dedup = len(evidence_list)
            if settings.ENABLE_DEDUPLICATION:
                from app.utils.deduplication import EvidenceDeduplicator
                deduplicator = EvidenceDeduplicator()
                evidence_list, dedup_stats = deduplicator.deduplicate(evidence_list)
            logger.info(f"[FILTER] Stage 3 (dedup): {before_dedup} -> {len(evidence_list)}")

            # Apply source independence checking if enabled
            before_diversity = len(evidence_list)
            if settings.ENABLE_SOURCE_DIVERSITY:
                from app.utils.source_independence import SourceIndependenceChecker
                independence_checker = SourceIndependenceChecker()
                evidence_list = independence_checker.enrich_evidence(evidence_list)
                diversity_score, passes = independence_checker.check_diversity(evidence_list)
            logger.info(f"[FILTER] Stage 4 (diversity): {before_diversity} -> {len(evidence_list)}")

            # Apply domain capping if enabled
            before_domain_cap = len(evidence_list)
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
            logger.info(f"[FILTER] Stage 5 (domain cap, max={settings.MAX_EVIDENCE_PER_DOMAIN}): {before_domain_cap} -> {len(evidence_list)}")

            # Apply source validation if enabled (Phase 1)
            before_validation = len(evidence_list)
            if settings.ENABLE_SOURCE_VALIDATION:
                from app.utils.source_validator import get_source_validator
                validator = get_source_validator()
                evidence_list, validation_stats = validator.validate_sources(evidence_list)
            logger.info(f"[FILTER] Stage 6 (validation): {before_validation} -> {len(evidence_list)} FINAL")

            # Safety check: Warn if all evidence eliminated
            if len(evidence_list) == 0 and original_evidence_count > 0:
                logger.warning(
                    f"All evidence eliminated by filters for claim. "
                    f"This suggests filters are too aggressive. "
                    f"Original count: {original_evidence_count}"
                )

            return evidence_list
            
        except Exception as e:
            logger.error(f"Credibility weighting error: {e}")
            return evidence_list
    
    def _get_credibility_score(self, source: str, url: str = None, evidence_item: Dict[str, Any] = None) -> float:
        """
        Determine credibility score for a source.

        Phase 3 Enhancement: Uses Domain Credibility Framework if enabled,
        otherwise falls back to legacy hardcoded weights.

        TIER 1 IMPROVEMENT: Enhanced with primary source detection.

        Args:
            source: Source name
            url: Source URL (required for Phase 3)
            evidence_item: Evidence dict to enrich with metadata (optional)

        Returns:
            Credibility score 0.0-1.0
        """
        from app.core.config import settings

        # Phase 3: Use Domain Credibility Framework if enabled
        if settings.ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK and url:
            try:
                from app.services.source_credibility import get_credibility_service

                credibility_service = get_credibility_service()
                cred_info = credibility_service.get_credibility(source, url)

                # Enrich evidence item with credibility metadata if provided
                if evidence_item is not None:
                    evidence_item['tier'] = cred_info.get('tier')
                    evidence_item['risk_flags'] = cred_info.get('risk_flags', [])
                    evidence_item['credibility_reasoning'] = cred_info.get('reasoning')
                    evidence_item['auto_exclude'] = cred_info.get('auto_exclude', False)  # NEW: Pass through flag

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

                base_credibility = cred_info.get('credibility', 0.6)

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
            # Parse date (handle different formats)
            if '2024' in published_date or '2025' in published_date:
                return 1.0  # Most recent
            elif '2023' in published_date:
                return 0.95
            elif '2022' in published_date:
                return 0.9
            elif '2021' in published_date:
                return 0.85
            else:
                return 0.8  # Older content

        except Exception:
            return 0.8  # Default for parsing errors

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
        if not getattr(settings, 'ENABLE_API_RETRIEVAL', False) or not self.enable_api_retrieval:
            return {"evidence": [], "api_stats": {}}

        try:
            # PRIORITY 1: Check if claim was classified as legal during extraction
            # If legal, use legal_metadata for targeted routing to statute APIs
            claim_type = claim.get("claim_type")
            legal_metadata = claim.get("legal_metadata", {})

            # Extract entities from key_entities field (set during extraction)
            # Convert to labeled entity format for backward compatibility with API adapters
            key_entities = claim.get("key_entities", [])
            entities = [{"text": entity, "label": "ENTITY"} for entity in key_entities]

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

        for evidence in api_evidence:
            try:
                snippet = EvidenceSnippet(
                    text=evidence.get("snippet", ""),
                    source=evidence.get("source", "Unknown API"),
                    url=evidence.get("url", ""),
                    title=evidence.get("title", ""),
                    published_date=evidence.get("source_date"),
                    relevance_score=0.8,  # Default relevance for API sources
                    word_count=len(evidence.get("snippet", "").split()),
                    metadata={
                        **evidence.get("metadata", {}),
                        "external_source_provider": evidence.get("external_source_provider"),
                        "credibility_score": evidence.get("credibility_score", 0.95)
                    }
                )
                snippets.append(snippet)
            except Exception as e:
                logger.warning(f"Failed to convert API evidence to snippet: {e}")
                continue

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