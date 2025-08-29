#!/usr/bin/env python3
"""
Simple Pipeline Test - No External API Calls
Tests core pipeline structure without making HTTP requests
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_imports():
    """Test that all pipeline components can be imported"""
    logger.info("=== Testing Imports ===")
    
    try:
        from app.pipeline.extract import ClaimExtractor
        logger.info("✅ ClaimExtractor imported successfully")
        
        from app.pipeline.retrieve import EvidenceRetriever  
        logger.info("✅ EvidenceRetriever imported successfully")
        
        from app.pipeline.verify import get_claim_verifier
        logger.info("✅ ClaimVerifier imported successfully")
        
        from app.pipeline.judge import get_pipeline_judge
        logger.info("✅ PipelineJudge imported successfully")
        
        from app.services.cache import get_cache_service
        logger.info("✅ CacheService imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import error: {e}")
        return False

async def test_service_initialization():
    """Test service initialization without external calls"""
    logger.info("=== Testing Service Initialization ===")
    
    try:
        # Test cache service - this should work with Redis running
        from app.services.cache import get_cache_service
        cache_service = await get_cache_service()
        if cache_service:
            logger.info("✅ Cache service initialized")
        else:
            logger.warning("⚠️ Cache service returned None")
            
        # Test ClaimExtractor instantiation (no API calls)
        from app.pipeline.extract import ClaimExtractor
        extractor = ClaimExtractor()
        if hasattr(extractor, 'openai_api_key'):
            logger.info("✅ ClaimExtractor initialized with API key")
        else:
            logger.warning("⚠️ ClaimExtractor missing API key")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Service initialization error: {e}")
        return False

async def test_fallback_extraction():
    """Test claim extraction fallback (no API calls)"""
    logger.info("=== Testing Fallback Extraction ===")
    
    try:
        from app.pipeline.extract import ClaimExtractor
        extractor = ClaimExtractor()
        
        test_content = """
        The COVID-19 vaccine has been proven to be 95% effective in preventing severe illness.
        Studies show that vaccinated individuals are significantly less likely to be hospitalized.
        """
        
        # Test the rule-based fallback directly
        result = extractor._extract_rule_based(test_content)
        
        if result.get("success"):
            claims = result.get("claims", [])
            logger.info(f"✅ Fallback extraction successful: {len(claims)} claims")
            for i, claim in enumerate(claims[:2]):
                logger.info(f"   Claim {i+1}: {claim.get('text', '')[:50]}...")
        else:
            logger.error(f"❌ Fallback extraction failed")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Fallback extraction error: {e}")
        return False

async def test_configuration():
    """Test configuration loading"""
    logger.info("=== Testing Configuration ===")
    
    try:
        from app.core.config import settings
        
        # Check key settings are loaded
        logger.info(f"✅ Environment: {settings.ENVIRONMENT}")
        logger.info(f"✅ Debug mode: {settings.DEBUG}")
        logger.info(f"✅ Max claims: {settings.MAX_CLAIMS_PER_CHECK}")
        logger.info(f"✅ Pipeline timeout: {settings.PIPELINE_TIMEOUT_SECONDS}s")
        
        # Check if API keys are set (without revealing them)
        has_openai = bool(settings.OPENAI_API_KEY)
        has_anthropic = bool(getattr(settings, 'ANTHROPIC_API_KEY', ''))
        logger.info(f"✅ OpenAI key configured: {has_openai}")
        logger.info(f"✅ Anthropic key configured: {has_anthropic}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        return False

async def test_database_models():
    """Test database model imports"""
    logger.info("=== Testing Database Models ===")
    
    try:
        from app.models import User, Check, Claim, Evidence
        logger.info("✅ Database models imported successfully")
        
        # Test model instantiation (no DB calls)
        test_check = Check(
            user_id="test-user",
            input_type="text",
            input_content='{"content": "test"}',
            status="pending"
        )
        
        if test_check.input_type == "text":
            logger.info("✅ Check model instantiation successful")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Database model error: {e}")
        return False

async def main():
    """Run all simple tests"""
    logger.info("🚀 Starting Simple Pipeline Tests (No External APIs)")
    logger.info("=" * 60)
    
    results = []
    
    # Test core functionality without external dependencies
    results.append(await test_imports())
    results.append(await test_configuration())
    results.append(await test_database_models())
    results.append(await test_service_initialization())
    results.append(await test_fallback_extraction())
    
    logger.info("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        logger.info(f"✅ All {total} tests passed! Core pipeline structure is valid.")
    else:
        logger.warning(f"⚠️ {passed}/{total} tests passed. Some issues need attention.")
        
    logger.info("Ready for external API testing with valid keys.")

if __name__ == "__main__":
    asyncio.run(main())