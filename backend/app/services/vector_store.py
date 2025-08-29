import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import uuid
import numpy as np
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, CreateCollection, PointStruct, 
    Filter, FieldCondition, Match, UpdateResult, ScoredPoint
)
from qdrant_client.http import models as rest
from app.core.config import settings

logger = logging.getLogger(__name__)

class VectorStore:
    """Qdrant vector database service for fact-checking"""
    
    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None
        self.collection_name = "tru8_evidence"
        self.embedding_dimension = 384  # MiniLM-L6-v2 dimension
        self.batch_size = 100
        self._initialized = False
    
    async def initialize(self):
        """Initialize Qdrant client and collections"""
        if self._initialized:
            return
            
        try:
            # Initialize async client
            if settings.QDRANT_URL.startswith('http'):
                self.client = AsyncQdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                    timeout=30
                )
            else:
                # Local instance
                self.client = AsyncQdrantClient(host="localhost", port=6333)
            
            # Test connection
            collections = await self.client.get_collections()
            logger.info(f"Connected to Qdrant. Collections: {len(collections.collections)}")
            
            # Create collection if it doesn't exist
            await self._ensure_collection_exists()
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise
    
    async def _ensure_collection_exists(self):
        """Create the evidence collection if it doesn't exist"""
        try:
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    ),
                    optimizers_config=rest.OptimizersConfigDiff(
                        default_segment_number=2,
                        max_segment_size=None,
                        memmap_threshold=None,
                    ),
                    hnsw_config=rest.HnswConfigDiff(
                        m=16,
                        ef_construct=200,
                        full_scan_threshold=10000,
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    async def store_evidence_embeddings(self, evidence_data: List[Dict[str, Any]]) -> List[str]:
        """Store evidence snippets with their embeddings"""
        await self.initialize()
        
        points = []
        point_ids = []
        
        for evidence in evidence_data:
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            # Prepare metadata
            payload = {
                "text": evidence.get("text", ""),
                "source": evidence.get("source", ""),
                "url": evidence.get("url", ""),
                "title": evidence.get("title", ""),
                "published_date": evidence.get("published_date"),
                "relevance_score": evidence.get("relevance_score", 0.0),
                "claim_id": evidence.get("claim_id"),
                "check_id": evidence.get("check_id"),
                "created_at": evidence.get("created_at"),
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            point = PointStruct(
                id=point_id,
                vector=evidence["embedding"].tolist() if isinstance(evidence["embedding"], np.ndarray) 
                       else evidence["embedding"],
                payload=payload
            )
            points.append(point)
        
        try:
            # Store in batches
            for i in range(0, len(points), self.batch_size):
                batch = points[i:i + self.batch_size]
                result = await self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                logger.debug(f"Stored batch {i//self.batch_size + 1}: {result}")
            
            logger.info(f"Stored {len(points)} evidence embeddings")
            return point_ids
            
        except Exception as e:
            logger.error(f"Error storing evidence embeddings: {e}")
            return []
    
    async def search_similar_evidence(self, 
                                    query_embedding: np.ndarray,
                                    limit: int = 10,
                                    score_threshold: float = 0.7,
                                    filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar evidence using vector similarity"""
        await self.initialize()
        
        try:
            # Prepare query vector
            query_vector = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding
            
            # Prepare filters
            qdrant_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if value is not None:
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=Match(value=value)
                            )
                        )
                if conditions:
                    qdrant_filter = Filter(must=conditions)
            
            # Perform search
            search_result = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False
            )
            
            # Convert results
            results = []
            for scored_point in search_result:
                result = {
                    "id": scored_point.id,
                    "score": scored_point.score,
                    **scored_point.payload
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} similar evidence items")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar evidence: {e}")
            return []
    
    async def search_evidence_for_claim(self, 
                                      claim_embedding: np.ndarray,
                                      claim_id: Optional[str] = None,
                                      check_id: Optional[str] = None,
                                      limit: int = 5) -> List[Dict[str, Any]]:
        """Search for evidence related to a specific claim"""
        filters = {}
        if claim_id:
            filters["claim_id"] = claim_id
        if check_id:
            filters["check_id"] = check_id
        
        return await self.search_similar_evidence(
            query_embedding=claim_embedding,
            limit=limit,
            score_threshold=0.6,  # Lower threshold for claim-evidence matching
            filters=filters
        )
    
    async def get_evidence_by_ids(self, evidence_ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve evidence by IDs"""
        await self.initialize()
        
        try:
            points = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=evidence_ids,
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for point in points:
                result = {
                    "id": point.id,
                    **point.payload
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving evidence by IDs: {e}")
            return []
    
    async def delete_evidence_for_check(self, check_id: str) -> bool:
        """Delete all evidence for a specific check"""
        await self.initialize()
        
        try:
            result = await self.client.delete(
                collection_name=self.collection_name,
                points_selector=rest.FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="check_id",
                                match=Match(value=check_id)
                            )
                        ]
                    )
                )
            )
            
            logger.info(f"Deleted evidence for check {check_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting evidence for check {check_id}: {e}")
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the evidence collection"""
        await self.initialize()
        
        try:
            info = await self.client.get_collection(self.collection_name)
            return {
                "name": info.config.collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            await self.initialize()
            collections = await self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.close()

# Helper functions for the fact-checking pipeline

async def store_check_evidence(check_id: str, claims_evidence: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Store evidence for all claims in a check"""
    vector_store = await get_vector_store()
    
    stored_ids = {}
    
    for claim_data in claims_evidence:
        claim_id = claim_data.get("claim_id")
        evidence_list = claim_data.get("evidence", [])
        
        # Prepare evidence data for storage
        evidence_data = []
        for evidence in evidence_list:
            evidence_item = {
                **evidence,
                "claim_id": claim_id,
                "check_id": check_id,
                "created_at": evidence.get("created_at"),
            }
            evidence_data.append(evidence_item)
        
        if evidence_data:
            ids = await vector_store.store_evidence_embeddings(evidence_data)
            stored_ids[claim_id] = ids
    
    return stored_ids

async def retrieve_claim_evidence(claim_embedding: np.ndarray, 
                                claim_id: Optional[str] = None,
                                limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve evidence for a claim using vector similarity"""
    vector_store = await get_vector_store()
    
    return await vector_store.search_evidence_for_claim(
        claim_embedding=claim_embedding,
        claim_id=claim_id,
        limit=limit
    )

# Global vector store instance
_vector_store = None

async def get_vector_store() -> VectorStore:
    """Get singleton vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        await _vector_store.initialize()
    return _vector_store