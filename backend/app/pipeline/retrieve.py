import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from app.services.search import SearchService
from app.services.evidence import EvidenceExtractor, EvidenceSnippet
from app.services.embeddings import get_embedding_service, rank_evidence_by_similarity
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

class EvidenceRetriever:
    """Retrieve and rank evidence for claims using search, embeddings, and vector storage"""
    
    def __init__(self):
        self.search_service = SearchService()
        self.evidence_extractor = EvidenceExtractor()
        self.max_sources_per_claim = 5
        self.max_concurrent_claims = 3
        
        # Credibility weights for different source types
        self.credibility_weights = {
            'academic': 1.0,      # .edu, .org, peer-reviewed
            'news_tier1': 0.9,    # BBC, Reuters, AP
            'news_tier2': 0.8,    # Guardian, Telegraph, Independent
            'government': 0.85,   # .gov domains
            'scientific': 0.95,   # Nature, Science journals
            'general': 0.6        # Other sources
        }
    
    async def retrieve_evidence_for_claims(self, claims: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve evidence for multiple claims concurrently"""
        try:
            # Process claims with concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrent_claims)
            tasks = [
                self._retrieve_evidence_for_single_claim(claim, semaphore)
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
    
    async def _retrieve_evidence_for_single_claim(self, claim: Dict[str, Any], 
                                                 semaphore: asyncio.Semaphore) -> List[Dict[str, Any]]:
        """Retrieve evidence for a single claim"""
        async with semaphore:
            try:
                claim_text = claim.get("text", "")
                claim_position = claim.get("position", 0)
                
                if not claim_text:
                    return []
                
                logger.info(f"Retrieving evidence for claim {claim_position}: {claim_text[:50]}...")
                
                # Step 1: Search and extract evidence snippets
                evidence_snippets = await self.evidence_extractor.extract_evidence_for_claim(
                    claim_text, 
                    max_sources=self.max_sources_per_claim * 2  # Get extra for filtering
                )
                
                if not evidence_snippets:
                    logger.warning(f"No evidence found for claim {claim_position}")
                    return []
                
                # Step 2: Rank evidence using embeddings
                ranked_evidence = await self._rank_evidence_with_embeddings(
                    claim_text, 
                    evidence_snippets
                )
                
                # Step 3: Apply credibility and recency weighting
                final_evidence = self._apply_credibility_weighting(ranked_evidence)
                
                # Step 4: Store in vector database for future retrieval
                await self._store_evidence_embeddings(claim, final_evidence)
                
                # Return top evidence
                return final_evidence[:self.max_sources_per_claim]
                
            except Exception as e:
                logger.error(f"Single claim evidence retrieval error: {e}")
                return []
    
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
                        "word_count": snippet.word_count
                    }
                    ranked_evidence.append(evidence_item)
            
            # Sort by combined score
            ranked_evidence.sort(key=lambda x: x["combined_score"], reverse=True)
            
            logger.info(f"Ranked {len(ranked_evidence)} evidence items by similarity")
            return ranked_evidence
            
        except Exception as e:
            logger.error(f"Evidence ranking error: {e}")
            # Fallback: return evidence without embedding ranking
            return [
                {
                    "id": f"evidence_{i}",
                    "text": snippet.text,
                    "source": snippet.source,
                    "url": snippet.url,
                    "title": snippet.title,
                    "published_date": snippet.published_date,
                    "relevance_score": float(snippet.relevance_score),
                    "semantic_similarity": 0.5,
                    "combined_score": float(snippet.relevance_score),
                    "word_count": snippet.word_count
                }
                for i, snippet in enumerate(evidence_snippets)
            ]
    
    def _apply_credibility_weighting(self, evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply credibility and recency weighting to evidence"""
        try:
            for evidence in evidence_list:
                source = evidence.get("source", "").lower()
                
                # Determine credibility tier
                credibility_score = self._get_credibility_score(source)
                
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
            
            # Sort by final weighted score
            evidence_list.sort(key=lambda x: x["final_score"], reverse=True)

            # NEW: Apply deduplication if enabled
            from app.core.config import settings
            if settings.ENABLE_DEDUPLICATION:
                from app.utils.deduplication import EvidenceDeduplicator
                deduplicator = EvidenceDeduplicator()
                evidence_list, dedup_stats = deduplicator.deduplicate(evidence_list)
                logger.info(f"Deduplication: {dedup_stats.get('duplicates_removed', 0)} duplicates removed")

            # Apply source independence checking if enabled
            if settings.ENABLE_SOURCE_DIVERSITY:
                from app.utils.source_independence import SourceIndependenceChecker
                independence_checker = SourceIndependenceChecker()
                evidence_list = independence_checker.enrich_evidence(evidence_list)
                diversity_score, passes = independence_checker.check_diversity(evidence_list)
                logger.info(f"Source diversity: {diversity_score} (passes: {passes})")

            # Apply domain capping if enabled
            if settings.ENABLE_DOMAIN_CAPPING:
                from app.utils.domain_capping import DomainCapper
                capper = DomainCapper(
                    max_per_domain=settings.MAX_EVIDENCE_PER_DOMAIN,
                    max_domain_ratio=settings.DOMAIN_DIVERSITY_THRESHOLD
                )
                evidence_list = capper.apply_caps(evidence_list, target_count=self.max_sources_per_claim)

            logger.info("Applied credibility and recency weighting")
            return evidence_list
            
        except Exception as e:
            logger.error(f"Credibility weighting error: {e}")
            return evidence_list
    
    def _get_credibility_score(self, source: str) -> float:
        """Determine credibility score for a source"""
        # Academic/research institutions
        if any(domain in source for domain in ['.edu', '.ac.uk', 'university', 'research']):
            return self.credibility_weights['academic']
        
        # Scientific journals
        if any(journal in source for journal in ['nature', 'science', 'cell', 'lancet', 'nejm']):
            return self.credibility_weights['scientific']
        
        # Government sources
        if any(domain in source for domain in ['.gov', 'nhs.uk', 'who.int']):
            return self.credibility_weights['government']
        
        # Tier 1 news
        if any(outlet in source for outlet in ['bbc', 'reuters', 'ap.org', 'apnews']):
            return self.credibility_weights['news_tier1']
        
        # Tier 2 news
        if any(outlet in source for outlet in [
            'guardian', 'telegraph', 'independent', 'economist', 'ft.com'
        ]):
            return self.credibility_weights['news_tier2']
        
        # Default
        return self.credibility_weights['general']
    
    def _get_recency_score(self, published_date: Optional[str]) -> float:
        """Calculate recency score (more recent = higher score)"""
        if not published_date:
            return 0.8  # Default for unknown dates
        
        try:
            # Parse date (handle different formats)
            if '2024' in published_date:
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
            logger.info(f"Stored {len(stored_ids)} evidence embeddings")
            
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
            
            logger.info(f"Retrieved {len(similar_evidence)} items from vector store")
            return similar_evidence
            
        except Exception as e:
            logger.error(f"Vector store retrieval error: {e}")
            return []