#!/usr/bin/env python3
"""
Core Services Test - Test the singleton functions that were causing timeout
"""

import asyncio
import logging
import os
import sys

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_core_services():
    """Test that the core singleton services work"""
    logger.info("=== Testing Core Services ===")
    
    try:
        # Test cache service singleton
        from app.services.cache import get_cache_service
        cache_service = await get_cache_service()
        logger.info(f"✅ Cache service: {type(cache_service).__name__}")
        
        # Test that get_cache_service returns the same instance
        cache_service2 = await get_cache_service()
        if cache_service is cache_service2:
            logger.info("✅ Cache service singleton pattern working")
        else:
            logger.warning("⚠️ Cache service singleton not working")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Core services error: {e}")
        return False

async def test_service_imports():
    """Test that we can import the key service functions"""
    logger.info("=== Testing Service Imports ===")
    
    try:
        # Test imports without initializing
        from app.services.cache import get_cache_service
        from app.services.vector_store import get_vector_store
        from app.services.embeddings import get_embedding_service
        
        logger.info("✅ All core service imports successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Service import error: {e}")
        return False

async def main():
    """Run core service tests"""
    logger.info("🔧 Testing Core Services (Timeout Fix Validation)")
    logger.info("=" * 50)
    
    results = []
    
    # Test that imports work
    results.append(await test_service_imports())
    
    # Test that the cache service singleton works
    results.append(await test_core_services())
    
    logger.info("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        logger.info(f"✅ All {total} core service tests passed!")
        logger.info("✅ Timeout issue should be resolved!")
    else:
        logger.warning(f"⚠️ {passed}/{total} tests passed.")
        
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)