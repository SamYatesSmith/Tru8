import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
import redis.asyncio as redis
from app.core.config import settings

# Note: sentence_transformers import moved inside functions to prevent
# heavy ML libraries from loading at startup. They will only load when embedding service is actually used.

logger = logging.getLogger(__name__)

# Every model call runs on ONE dedicated thread, with torch capped at a few
# intra-op threads (2026-09-30, audit/2026-09-30_api_crash_brief.md).
# libgomp gives each calling thread its own OpenMP team sized to the visible
# CPUs (48 on Railway, whose quota is 8). ~20 concurrent page encodes from the
# default executor asked for ~940 threads against the container's pids.max of
# 1000; libgomp then failed thread creation and the process segfaulted with no
# shutdown log. One caller thread = one team, and it works across the
# per-pipeline event loops because the executor is module-level.
# Measured at 8 CPUs: 1 worker x 4 threads matches the old throughput.
EMBEDDING_TORCH_THREADS = 4
_ENCODE_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="embed")

class EmbeddingService:
    """Sentence embedding service using Sentence-Transformers"""
    
    def __init__(self):
        self.model = None
        self.model_name = "all-MiniLM-L6-v2"  # Fast, lightweight model for MVP
        # Alternative: "multi-qa-MiniLM-L6-cos-v1" for Q&A tasks
        self.dimension = 384  # Embedding dimension for the model
        self.redis_client = None
        self.cache_ttl = 3600 * 24 * 7  # 1 week cache
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the embedding model and Redis cache"""
        try:
            if self.model is None:
                async with self._lock:
                    if self.model is None:  # Double-check locking
                        logger.info(f"Loading embedding model: {self.model_name}")
                        # Load in thread pool to avoid blocking
                        loop = asyncio.get_event_loop()
                        
                        def load_model():
                            # Import sentence_transformers only when actually needed
                            import torch
                            from sentence_transformers import SentenceTransformer
                            torch.set_num_threads(EMBEDDING_TORCH_THREADS)
                            return SentenceTransformer(self.model_name)
                        
                        self.model = await loop.run_in_executor(_ENCODE_EXECUTOR, load_model)
                        logger.info("Embedding model loaded successfully")
            
            # Initialize Redis for caching
            if self.redis_client is None:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=False  # Keep bytes for numpy arrays
                )
                await self.redis_client.ping()
                logger.info("Embedding cache initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            raise
    
    async def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        await self.initialize()
        
        # Check cache first
        cache_key = self._get_cache_key(text)
        cached_embedding = await self._get_cached_embedding(cache_key)
        
        if cached_embedding is not None:
            return cached_embedding
        
        try:
            # Generate embedding in thread pool
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                _ENCODE_EXECUTOR,
                lambda: self.model.encode(text, normalize_embeddings=True)
            )
            
            # Cache the result
            await self._cache_embedding(cache_key, embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return zero vector as fallback
            return np.zeros(self.dimension)
    
    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts efficiently"""
        await self.initialize()
        
        # Check cache for each text
        embeddings = []
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            cached_embedding = await self._get_cached_embedding(cache_key)
            
            if cached_embedding is not None:
                embeddings.append(cached_embedding)
            else:
                embeddings.append(None)  # Placeholder
                uncached_indices.append(i)
                uncached_texts.append(text)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                loop = asyncio.get_event_loop()
                new_embeddings = await loop.run_in_executor(
                    _ENCODE_EXECUTOR,
                    lambda: self.model.encode(uncached_texts, normalize_embeddings=True)
                )
                
                # Fill in the placeholders and cache results
                for idx, embedding in zip(uncached_indices, new_embeddings):
                    embeddings[idx] = embedding
                    cache_key = self._get_cache_key(texts[idx])
                    await self._cache_embedding(cache_key, embedding)
                    
            except Exception as e:
                logger.error(f"Batch embedding generation failed: {e}")
                # Fill remaining with zero vectors
                for idx in uncached_indices:
                    embeddings[idx] = np.zeros(self.dimension)
        
        return embeddings
    
    async def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        try:
            # Since we normalize embeddings, dot product = cosine similarity
            similarity = float(np.dot(embedding1, embedding2))
            return max(-1.0, min(1.0, similarity))  # Clamp to [-1, 1]
        except Exception as e:
            logger.error(f"Similarity computation failed: {e}")
            return 0.0
    
    async def find_most_similar(self, query_embedding: np.ndarray, 
                               candidate_embeddings: List[np.ndarray],
                               top_k: int = 5) -> List[Tuple[int, float]]:
        """Find the most similar embeddings to a query"""
        try:
            similarities = []
            
            for i, candidate in enumerate(candidate_embeddings):
                similarity = await self.compute_similarity(query_embedding, candidate)
                similarities.append((i, similarity))
            
            # Sort by similarity (descending) and return top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        # Create hash of text and model name for cache key
        content = f"{self.model_name}:{text}"
        return f"embedding:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def _get_cached_embedding(self, cache_key: str) -> Optional[np.ndarray]:
        """Retrieve embedding from cache"""
        try:
            if self.redis_client:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    # Deserialize numpy array
                    embedding_dict = json.loads(cached_data)
                    return np.array(embedding_dict['embedding'])
            return None
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
            return None
    
    async def _cache_embedding(self, cache_key: str, embedding: np.ndarray):
        """Store embedding in cache"""
        try:
            if self.redis_client:
                # Serialize numpy array
                embedding_dict = {
                    'embedding': embedding.tolist(),
                    'dimension': embedding.shape[0]
                }
                await self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(embedding_dict)
                )
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")
    

# Specialized functions for fact-checking pipeline

async def embed_claim_and_evidence(claim: str, evidence_snippets: List[str]) -> Dict[str, Any]:
    """Generate embeddings for a claim and its evidence snippets"""
    service = await get_embedding_service()
    
    try:
        # Embed claim and all evidence snippets in one batch
        all_texts = [claim] + evidence_snippets
        embeddings = await service.embed_batch(all_texts)
        
        claim_embedding = embeddings[0]
        evidence_embeddings = embeddings[1:]
        
        return {
            "claim_embedding": claim_embedding,
            "evidence_embeddings": evidence_embeddings,
            "dimension": service.dimension
        }
        
    except Exception as e:
        logger.error(f"Claim-evidence embedding failed: {e}")
        return {
            "claim_embedding": np.zeros(service.dimension),
            "evidence_embeddings": [np.zeros(service.dimension) for _ in evidence_snippets],
            "dimension": service.dimension
        }


# Global embedding service instance
_embedding_service = None

async def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        await _embedding_service.initialize()
    return _embedding_service