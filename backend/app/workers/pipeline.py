from celery import Task
from typing import Dict, List, Any
import asyncio
import logging
from datetime import datetime
from app.workers import celery_app
from app.pipeline.ingest import UrlIngester, ImageIngester, VideoIngester

logger = logging.getLogger(__name__)

class PipelineTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")
        # TODO: Update check status to 'failed' in database
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} completed successfully")

@celery_app.task(base=PipelineTask, bind=True)
def process_check(self, check_id: str, user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main pipeline task that processes a fact-check request.
    Now using real ingest pipeline!
    """
    start_time = datetime.utcnow()
    
    try:
        # Update progress: Starting
        self.update_state(state="PROGRESS", meta={"stage": "ingest", "progress": 10})
        
        # Stage 1: Ingest (REAL IMPLEMENTATION)
        content = asyncio.run(ingest_content_async(input_data))
        if not content.get("success"):
            raise Exception(f"Ingest failed: {content.get('error', 'Unknown error')}")
            
        self.update_state(state="PROGRESS", meta={"stage": "extract", "progress": 25})
        
        # Stage 2: Extract claims (still mock for now)
        claims = extract_claims(content.get("content", ""))
        self.update_state(state="PROGRESS", meta={"stage": "retrieve", "progress": 40})
        
        # Stage 3: Retrieve evidence (mock)
        evidence = retrieve_evidence(claims)
        self.update_state(state="PROGRESS", meta={"stage": "verify", "progress": 60})
        
        # Stage 4: Verify with NLI (mock)
        verifications = verify_claims(claims, evidence)
        self.update_state(state="PROGRESS", meta={"stage": "judge", "progress": 80})
        
        # Stage 5: Judge and finalize (mock)
        results = judge_claims(claims, verifications, evidence)
        
        # Calculate processing time
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return {
            "check_id": check_id,
            "status": "completed",
            "claims": results,
            "processing_time_ms": processing_time_ms,
            "ingest_metadata": content.get("metadata", {}),
        }
        
    except Exception as e:
        logger.error(f"Pipeline failed for check {check_id}: {e}")
        raise

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
                    "word_count": len(input_data.get("content", "").split())
                }
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
                "content": ""
            }
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        return {
            "success": False,
            "error": str(e),
            "content": ""
        }

def extract_claims(content: str) -> List[Dict[str, Any]]:
    """Mock claim extraction - Week 3 will implement real LLM"""
    if not content.strip():
        return [{"text": "No claims found in empty content", "position": 0}]
    
    # Simple sentence splitting as mock
    sentences = [s.strip() for s in content.split('.') if s.strip()]
    claims = []
    
    for i, sentence in enumerate(sentences[:6]):  # Max 6 claims for demo
        if len(sentence) > 20:  # Only substantial sentences
            claims.append({
                "text": sentence + ".",
                "position": i
            })
    
    if not claims:
        claims = [{"text": content[:200] + "...", "position": 0}]
    
    return claims

def retrieve_evidence(claims: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Mock evidence retrieval - Week 3 implementation"""
    evidence = {}
    
    for i, claim in enumerate(claims):
        # Generate realistic mock evidence
        sources = [
            ("BBC", "2024-01-15", "https://bbc.com/example"),
            ("Reuters", "2024-01-10", "https://reuters.com/example"),
            ("Scientific American", "2023-12-20", "https://sciam.com/example"),
        ]
        
        evidence[str(i)] = []
        for source, date, url in sources:
            evidence[str(i)].append({
                "source": source,
                "url": url,
                "title": f"Article about: {claim['text'][:50]}...",
                "snippet": f"Supporting evidence for the claim about {claim['text'][:30]}...",
                "published_date": date,
                "relevance_score": 0.85 + (i * 0.05),  # Vary scores
            })
    
    return evidence

def verify_claims(claims: List[Dict[str, Any]], evidence: Dict) -> List[Dict[str, Any]]:
    """Mock NLI verification - Week 3 implementation"""
    verdicts = ["supported", "contradicted", "uncertain"]
    verifications = []
    
    for i, claim in enumerate(claims):
        # Mock realistic confidence based on content
        confidence = 85.0 + (i * 3.0) % 30  # Vary confidence
        verdict = verdicts[i % len(verdicts)]
        
        verifications.append({
            "verdict": verdict,
            "confidence": confidence
        })
    
    return verifications

def judge_claims(claims: List[Dict[str, Any]], verifications: List[Dict], 
                evidence: Dict) -> List[Dict[str, Any]]:
    """Mock judge stage - Week 4 implementation"""
    rationales = {
        "supported": "This claim is well-supported by multiple reliable sources with consistent reporting.",
        "contradicted": "Evidence from credible sources contradicts this claim with factual information.",
        "uncertain": "Available evidence is mixed or insufficient to make a definitive determination.",
    }
    
    results = []
    for i, claim in enumerate(claims):
        verdict = verifications[i]["verdict"]
        confidence = verifications[i]["confidence"]
        
        results.append({
            "text": claim["text"],
            "verdict": verdict,
            "confidence": confidence,
            "rationale": rationales.get(verdict, "Assessment based on available evidence."),
            "evidence": evidence.get(str(i), [])[:3],  # Top 3 sources
            "position": claim["position"],
        })
    
    return results