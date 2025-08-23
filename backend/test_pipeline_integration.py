#!/usr/bin/env python3
"""
Pipeline Integration Test
Tests the full pipeline with real LLM, search, embeddings, and caching
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.pipeline.extract import ClaimExtractor
from app.pipeline.retrieve import EvidenceRetriever
from app.services.cache import get_cache_service
from app.services.search import SearchService
from app.services.embeddings import get_embedding_service
from app.services.vector_store import get_vector_store

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_claim_extraction():
    """Test LLM claim extraction"""
    logger.info("=== Testing Claim Extraction ===")
    
    test_content = """
    The COVID-19 vaccine has been proven to be 95% effective in preventing severe illness.
    Studies show that vaccinated individuals are significantly less likely to be hospitalized.
    The vaccine was developed in record time, taking less than 12 months from start to finish.
    Side effects are minimal and typically resolve within 24-48 hours.
    """
    
    try:
        extractor = ClaimExtractor()
        result = await extractor.extract_claims(test_content)
        
        if result.get("success"):
            claims = result.get("claims", [])
            logger.info(f"✅ Extracted {len(claims)} claims successfully")
            for i, claim in enumerate(claims[:3]):  # Show first 3
                logger.info(f"   Claim {i+1}: {claim.get('text', '')[:60]}...")
        else:
            logger.error(f"❌ Claim extraction failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"❌ Claim extraction error: {e}")

async def test_search_integration():
    """Test search service integration"""
    logger.info("=== Testing Search Integration ===")
    
    try:
        search_service = SearchService()
        results = await search_service.search_for_evidence(
            "COVID-19 vaccine effectiveness", 
            max_results=5
        )
        
        logger.info(f"✅ Found {len(results)} search results")
        for i, result in enumerate(results[:2]):  # Show first 2
            logger.info(f"   Result {i+1}: {result.title[:50]}... from {result.source}")
            
    except Exception as e:
        logger.error(f"❌ Search integration error: {e}")

async def test_embeddings_service():
    """Test embeddings service"""
    logger.info("=== Testing Embeddings Service ===")
    
    try:
        embedding_service = await get_embedding_service()
        
        test_texts = [
            "COVID-19 vaccine effectiveness",
            "Vaccine prevents severe illness",
            "Side effects are minimal"
        ]
        
        embeddings = await embedding_service.embed_batch(test_texts)
        logger.info(f"✅ Generated {len(embeddings)} embeddings")
        logger.info(f"   Embedding dimension: {len(embeddings[0])}")
        
        # Test similarity
        similarity = await embedding_service.compute_similarity(embeddings[0], embeddings[1])
        logger.info(f"   Similarity between text 1 and 2: {similarity:.3f}")
        
    except Exception as e:
        logger.error(f"❌ Embeddings service error: {e}")

async def test_vector_store():
    """Test vector store operations"""
    logger.info("=== Testing Vector Store ===")
    
    try:
        vector_store = await get_vector_store()
        
        # Test health check
        is_healthy = await vector_store.health_check()
        if is_healthy:
            logger.info("✅ Vector store is healthy")
            
            # Get collection info
            info = await vector_store.get_collection_info()
            logger.info(f"   Collection: {info.get('name', 'unknown')}")
            logger.info(f"   Points: {info.get('points_count', 0)}")
        else:
            logger.warning("⚠️  Vector store health check failed")
            
    except Exception as e:
        logger.error(f"❌ Vector store error: {e}")

async def test_caching_service():
    """Test caching service"""
    logger.info("=== Testing Cache Service ===")
    
    try:
        cache_service = await get_cache_service()
        
        # Test basic caching
        test_key = "test_integration"
        test_data = {"message": "Integration test", "timestamp": datetime.utcnow().isoformat()}
        
        # Set cache
        set_result = await cache_service.set("integration_test", test_key, test_data)
        if set_result:
            logger.info("✅ Cache set successful")
            
            # Get from cache
            cached_data = await cache_service.get("integration_test", test_key)
            if cached_data:
                logger.info("✅ Cache retrieval successful")
                logger.info(f"   Cached data: {cached_data.get('message')}")
            else:
                logger.error("❌ Cache retrieval failed")
        else:
            logger.error("❌ Cache set failed")
            
        # Get cache stats
        stats = await cache_service.get_cache_stats()
        if stats:
            logger.info(f"   Cache memory used: {stats.get('memory_used', 'unknown')}")
            logger.info(f"   Total keys: {stats.get('total_keys', 0)}")
            
    except Exception as e:
        logger.error(f"❌ Cache service error: {e}")

async def test_evidence_retrieval():
    """Test full evidence retrieval pipeline"""
    logger.info("=== Testing Evidence Retrieval ===")
    
    try:
        test_claims = [
            {"text": "COVID-19 vaccines are 95% effective", "position": 0},
            {"text": "Vaccinated people have lower hospitalization rates", "position": 1}
        ]
        
        retriever = EvidenceRetriever()
        evidence = await retriever.retrieve_evidence_for_claims(test_claims)
        
        logger.info(f"✅ Evidence retrieval completed")
        logger.info(f"   Retrieved evidence for {len(evidence)} claims")
        
        for claim_pos, evidence_list in evidence.items():
            logger.info(f"   Claim {claim_pos}: {len(evidence_list)} evidence items")
            if evidence_list:
                top_evidence = evidence_list[0]
                logger.info(f"     Top evidence: {top_evidence.get('title', 'No title')[:50]}...")
                logger.info(f"     Score: {top_evidence.get('final_score', 'N/A')}")
                
    except Exception as e:
        logger.error(f"❌ Evidence retrieval error: {e}")

async def main():
    """Run all integration tests"""
    logger.info("🚀 Starting Pipeline Integration Tests")
    logger.info("=" * 60)
    
    # Test individual components
    await test_claim_extraction()
    await test_search_integration()
    await test_embeddings_service()
    await test_vector_store()
    await test_caching_service()
    await test_evidence_retrieval()
    
    logger.info("=" * 60)
    logger.info("✅ Pipeline Integration Tests Complete!")
    logger.info("Ready for NLI Verification & Judge Implementation")

if __name__ == "__main__":
    asyncio.run(main())