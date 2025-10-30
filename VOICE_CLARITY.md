# 🎯 VOICE INPUT & SEARCH CLARITY - IMPLEMENTATION PLAN

## Overview

Adding two major features to Tru8 MVP:

1. **Voice Input** - 3rd input type (alongside URL and Text) using OpenAI Whisper API
2. **Search Clarity** - Optional user query with confidence-based response and related claims fallback

**Target Timeline:** 4 weeks
**Cost Impact:** $0.023-0.025 per check (from current $0.02)
**Dependencies:** OpenAI Whisper API (already using OpenAI SDK)

---

## 📊 PHASE 1: DATABASE SCHEMA CHANGES

### Migration File: `backend/alembic/versions/2025_10_30_add_voice_and_clarity_fields.py`

```python
"""add_voice_and_clarity_fields

Adds support for:
- Voice input type
- User query (Search Clarity feature)
- Query response and confidence

Revision ID: [generated]
Revises: 954dd02c2ec1
Create Date: 2025-10-30 [timestamp]
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '[auto-generated]'
down_revision: Union[str, None] = '954dd02c2ec1'  # Latest migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add Search Clarity fields to Check table
    op.add_column('check', sa.Column('user_query', sa.String(200), nullable=True))
    op.add_column('check', sa.Column('query_response', sa.Text(), nullable=True))
    op.add_column('check', sa.Column('query_confidence', sa.Float(), nullable=True))
    op.add_column('check', sa.Column('query_sources', sa.Text(), nullable=True))  # JSON array of evidence IDs

def downgrade() -> None:
    op.drop_column('check', 'query_sources')
    op.drop_column('check', 'query_confidence')
    op.drop_column('check', 'query_response')
    op.drop_column('check', 'user_query')
```

### Model Updates: `backend/app/models/check.py`

**ADD to Check class (after line 31):**

```python
# Search Clarity fields (MVP Feature)
user_query: Optional[str] = Field(default=None, max_length=200, description="User's specific question about the content")
query_response: Optional[str] = Field(default=None, description="Answer to user's query based on evidence")
query_confidence: Optional[float] = Field(default=None, ge=0, le=100, description="Confidence in query answer 0-100")
query_sources: Optional[str] = Field(default=None, sa_column=Column(JSON), description="Evidence IDs used for query response")
```

**Note:** `input_type` field (line 12) already supports string values, so 'voice' will work without modification.

---

## 📦 PHASE 2: BACKEND API CHANGES

### 2.1 Update API Request Schema: `backend/app/api/v1/checks.py`

**MODIFY CreateCheckRequest (lines 40-44):**

```python
class CreateCheckRequest(BaseModel):
    input_type: str  # 'url', 'text', 'image', 'video', 'voice' (NEW)
    content: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None  # For uploaded files (images, audio)
    user_query: Optional[str] = Field(None, max_length=200)  # NEW: Search Clarity
```

### 2.2 Update Validation Logic: `backend/app/api/v1/checks.py`

**MODIFY create_check function (after line 128):**

```python
# Validate input (update existing validation)
if request.input_type not in ["url", "text", "image", "video", "voice"]:  # ADD 'voice'
    raise HTTPException(status_code=400, detail="Invalid input type")

# ... existing validations ...

# NEW: Validate voice input
if request.input_type == "voice" and not request.file_path:
    raise HTTPException(status_code=400, detail="File path is required for voice input type")

# NEW: Validate user_query if provided
if request.user_query and len(request.user_query) > 200:
    raise HTTPException(status_code=400, detail="Query must be 200 characters or less")
```

### 2.3 Update Check Creation: `backend/app/api/v1/checks.py`

**MODIFY check creation (line 150):**

```python
check = Check(
    id=str(uuid.uuid4()),
    user_id=user.id,
    input_type=request.input_type,
    input_content=json.dumps({
        "content": request.content,
        "url": request.url,
        "file_path": request.file_path
    }),
    input_url=request.url,
    status="pending",
    credits_used=1,
    user_query=request.user_query  # NEW
)
```

### 2.4 New Endpoint: Audio Upload: `backend/app/api/v1/checks.py`

**ADD after upload endpoint (after line 102):**

```python
@router.post("/upload-audio")
async def upload_audio(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload an audio file for voice fact-checking"""

    # Validate file type
    allowed_types = ['audio/webm', 'audio/wav', 'audio/m4a', 'audio/mpeg', 'audio/mp3']
    if not file.content_type or file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: webm, wav, m4a, mp3"
        )

    # Check file size (25MB limit for Whisper API)
    max_size = 25 * 1024 * 1024  # 25MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail="Audio file too large. Maximum size is 25MB."
        )

    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ['.webm', '.wav', '.m4a', '.mp3', '.mpeg']:
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio file extension"
        )

    filename = f"{file_id}{file_extension}"

    # Store locally (TODO: implement S3 storage post-MVP)
    upload_dir = Path("uploads/audio")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    try:
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        return {
            "success": True,
            "filePath": str(file_path),
            "filename": file.filename,
            "contentType": file.content_type,
            "size": len(content),
            "duration": None  # Could add ffprobe for duration if needed
        }

    except Exception as e:
        logger.error(f"Audio upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save audio file"
        )
```

### 2.5 Update GET Response: `backend/app/api/v1/checks.py`

**MODIFY get_check function return (after line 371):**

```python
return {
    # ... existing fields ...
    "userQuery": check.user_query,  # NEW
    "queryResponse": check.query_response,  # NEW
    "queryConfidence": check.query_confidence,  # NEW
    "querySources": json.loads(check.query_sources) if check.query_sources else None,  # NEW
}
```

---

## 🔧 PHASE 3: PIPELINE IMPLEMENTATION

### 3.1 New Ingester: `backend/app/pipeline/ingest.py`

**ADD new class (after VideoIngester, line 312):**

```python
class VoiceIngester(BaseIngester):
    """Extract text from audio using Whisper API"""

    async def process(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file to text"""
        try:
            import aiofiles
            from openai import AsyncOpenAI

            # Initialize OpenAI client
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            # Read audio file
            async with aiofiles.open(audio_path, 'rb') as audio_file:
                audio_data = await audio_file.read()

            # Create temporary file-like object for OpenAI API
            from io import BytesIO
            audio_buffer = BytesIO(audio_data)
            audio_buffer.name = audio_path  # Whisper needs a filename

            # Transcribe with Whisper
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_buffer,
                response_format="verbose_json"  # Includes language, duration, confidence
            )

            # Extract text
            content = await self.sanitize_content(transcript.text)

            # Quality check
            if len(content.strip()) < 10:
                return {
                    "success": False,
                    "error": "Insufficient text extracted from audio",
                    "content": content
                }

            return {
                "success": True,
                "content": content,
                "metadata": {
                    "extraction_method": "whisper_api",
                    "language": transcript.language,
                    "duration": transcript.duration,
                    "word_count": len(content.split()),
                    "audio_path": audio_path
                }
            }

        except Exception as e:
            logger.error(f"Error processing audio {audio_path}: {e}")
            return {"success": False, "error": str(e), "content": ""}
```

### 3.2 Update Ingest Routing: `backend/app/workers/pipeline.py`

**MODIFY ingest_content_async (line 618):**

```python
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
        elif input_type == "voice":  # NEW
            from app.pipeline.ingest import VoiceIngester
            voice_ingester = VoiceIngester()
            return await voice_ingester.process(input_data.get("file_path", ""))
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
```

### 3.3 New Query Answering Stage: `backend/app/pipeline/query_answer.py` (NEW FILE)

**Create complete file:**

```python
"""
Query Answering Pipeline Stage
Answers user's specific question using retrieved evidence
"""
import logging
import httpx
from typing import Dict, List, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class QueryAnswerer:
    """Answer user queries based on evidence"""

    async def answer_query(
        self,
        user_query: str,
        claims: List[Dict[str, Any]],
        evidence_by_claim: Dict[str, List[Dict[str, Any]]],
        original_text: str
    ) -> Dict[str, Any]:
        """
        Answer user query using evidence pool.
        Returns:
            {
                "answer": str,
                "confidence": float (0-100),
                "source_ids": List[str],
                "related_claims": List[int] (claim positions if confidence < 40)
            }
        """
        try:
            # Build evidence context
            all_evidence = []
            for position, evidence_list in evidence_by_claim.items():
                all_evidence.extend(evidence_list)

            # Check relevance of existing evidence to query
            relevance_score = await self._check_query_relevance(user_query, all_evidence)
            logger.info(f"Query relevance score: {relevance_score}")

            # If relevance low, do targeted retrieval
            if relevance_score < 0.7:
                targeted_evidence = await self._retrieve_targeted_evidence(user_query, original_text)
                all_evidence.extend(targeted_evidence)

            # Build context for LLM
            evidence_context = self._build_evidence_context(all_evidence[:10])  # Top 10 sources

            # LLM prompt for answering
            prompt = f"""You are a fact-checking assistant answering a specific user question.

ORIGINAL CONTENT PREVIEW: {original_text[:500]}

USER QUESTION: {user_query}

AVAILABLE EVIDENCE:
{evidence_context}

Answer the user's specific question using ONLY the evidence above.
Be direct and concise (2-3 sentences maximum).
If the evidence doesn't contain a clear answer, say so.
Cite which sources you used by number (e.g., "According to sources 1 and 3...").

Format your response as:
ANSWER: [your answer]
CONFIDENCE: [0-100 number only]
SOURCES: [comma-separated source numbers used]
"""

            # Call OpenAI
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini-2024-07-18",
                        "messages": [
                            {"role": "system", "content": "You are a precise fact-checking assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 300,
                        "temperature": 0.2
                    }
                )

                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.status_code}")
                    return self._create_fallback_response(user_query, claims)

                result = response.json()
                raw_answer = result["choices"][0]["message"]["content"].strip()

                # Parse response
                parsed = self._parse_llm_response(raw_answer)

                # Map source numbers to evidence IDs
                source_ids = []
                for idx in parsed["source_indices"]:
                    if 0 <= idx < len(all_evidence):
                        source_ids.append(all_evidence[idx].get("id", f"evidence_{idx}"))

                # If confidence < 40%, find related claims
                related_claims = []
                if parsed["confidence"] < 40:
                    related_claims = await self._find_related_claims(user_query, claims)

                return {
                    "answer": parsed["answer"],
                    "confidence": parsed["confidence"],
                    "source_ids": source_ids,
                    "related_claims": related_claims,
                    "found_answer": parsed["confidence"] >= 40
                }

        except Exception as e:
            logger.error(f"Query answering error: {e}")
            return self._create_fallback_response(user_query, claims)

    def _build_evidence_context(self, evidence_list: List[Dict[str, Any]]) -> str:
        """Build numbered evidence context for LLM"""
        context_lines = []
        for i, ev in enumerate(evidence_list, 1):
            source = ev.get("source", "Unknown")
            snippet = ev.get("snippet", ev.get("text", ""))[:200]
            date = ev.get("published_date", "")
            context_lines.append(f"[{i}] {source} ({date}): {snippet}")
        return "\n".join(context_lines)

    async def _check_query_relevance(self, query: str, evidence: List[Dict[str, Any]]) -> float:
        """Quick semantic check if evidence might answer query"""
        # Simple keyword overlap for MVP (could use embeddings post-MVP)
        query_words = set(query.lower().split())

        relevant_count = 0
        for ev in evidence[:5]:  # Check top 5
            ev_text = ev.get("snippet", ev.get("text", "")).lower()
            overlap = len(query_words.intersection(set(ev_text.split())))
            if overlap >= 2:  # At least 2 keyword matches
                relevant_count += 1

        return relevant_count / min(len(evidence), 5) if evidence else 0.0

    async def _retrieve_targeted_evidence(self, query: str, context: str) -> List[Dict[str, Any]]:
        """Retrieve evidence specifically for the query"""
        from app.services.search import SearchService

        try:
            search_service = SearchService()
            # Search with query + context snippet
            search_query = f"{query} {context[:100]}"
            results = await search_service.search(search_query, max_results=3)

            return [
                {
                    "id": f"query_evidence_{i}",
                    "source": r.get("source", "Web"),
                    "snippet": r.get("snippet", ""),
                    "url": r.get("url", ""),
                    "published_date": r.get("date", ""),
                    "credibility_score": 0.7,
                    "relevance_score": 0.85
                }
                for i, r in enumerate(results)
            ]
        except Exception as e:
            logger.error(f"Targeted evidence retrieval failed: {e}")
            return []

    def _parse_llm_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse structured LLM response"""
        import re

        answer = ""
        confidence = 0.0
        source_indices = []

        # Extract ANSWER
        answer_match = re.search(r'ANSWER:\s*(.+?)(?=\nCONFIDENCE:|\nSOURCES:|\Z)', raw_response, re.DOTALL)
        if answer_match:
            answer = answer_match.group(1).strip()

        # Extract CONFIDENCE
        conf_match = re.search(r'CONFIDENCE:\s*(\d+)', raw_response)
        if conf_match:
            confidence = float(conf_match.group(1))

        # Extract SOURCES
        sources_match = re.search(r'SOURCES:\s*(.+)', raw_response)
        if sources_match:
            sources_str = sources_match.group(1)
            # Parse "1, 3, 5" or "1 and 3"
            numbers = re.findall(r'\d+', sources_str)
            source_indices = [int(n) - 1 for n in numbers]  # Convert to 0-indexed

        return {
            "answer": answer if answer else raw_response[:300],
            "confidence": confidence,
            "source_indices": source_indices
        }

    async def _find_related_claims(self, query: str, claims: List[Dict[str, Any]]) -> List[int]:
        """Find claims semantically related to query"""
        # Simple keyword matching for MVP
        query_words = set(query.lower().split())

        related = []
        for claim in claims:
            claim_text = claim.get("text", "").lower()
            claim_words = set(claim_text.split())
            overlap = len(query_words.intersection(claim_words))

            if overlap >= 2:  # At least 2 keyword matches
                related.append(claim.get("position", 0))

        return related[:3]  # Top 3 related claims

    def _create_fallback_response(self, query: str, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback response when query answering fails"""
        related_claims = []
        # Simple fallback: find any claim with keyword match
        query_words = set(query.lower().split())
        for claim in claims:
            claim_text = claim.get("text", "").lower()
            if any(word in claim_text for word in query_words if len(word) > 3):
                related_claims.append(claim.get("position", 0))

        return {
            "answer": "",
            "confidence": 0,
            "source_ids": [],
            "related_claims": related_claims[:3],
            "found_answer": False
        }

# Singleton instance
_query_answerer = None

async def get_query_answerer() -> QueryAnswerer:
    """Get or create QueryAnswerer instance"""
    global _query_answerer
    if _query_answerer is None:
        _query_answerer = QueryAnswerer()
    return _query_answerer
```

### 3.4 Integrate Query Stage: `backend/app/workers/pipeline.py`

**ADD after Stage 5 (Judge), before Stage 6 (Summary) - around line 371:**

```python
# Stage 5.5: Query Answering (if user_query exists)
query_response_data = None
if input_data.get("user_query"):  # Check if user provided a query
    self.update_state(state="PROGRESS", meta={"stage": "query", "progress": 85})
    stage_start = datetime.utcnow()

    try:
        from app.pipeline.query_answer import get_query_answerer
        query_answerer = await get_query_answerer()

        user_query = input_data.get("user_query")
        logger.info(f"Answering user query: {user_query}")

        query_result = await query_answerer.answer_query(
            user_query=user_query,
            claims=claims,
            evidence_by_claim=evidence,
            original_text=content.get("content", "")
        )

        # Store query response
        query_response_data = {
            "answer": query_result["answer"],
            "confidence": query_result["confidence"],
            "source_ids": query_result["source_ids"],
            "related_claims": query_result["related_claims"],
            "found_answer": query_result["found_answer"]
        }

        logger.info(f"Query answered with confidence: {query_result['confidence']}")
    except Exception as e:
        logger.error(f"Query answering failed (non-critical): {e}")
        query_response_data = None

    stage_timings["query"] = (datetime.utcnow() - stage_start).total_seconds()
```

**UPDATE final_result (around line 461):**

```python
final_result = {
    "check_id": check_id,
    "status": "completed",
    "claims": results,
    "overall_summary": assessment["summary"],
    "credibility_score": assessment["credibility_score"],
    "claims_supported": assessment["claims_supported"],
    "claims_contradicted": assessment["claims_contradicted"],
    "claims_uncertain": assessment["claims_uncertain"],
    "processing_time_ms": processing_time_ms,
    "ingest_metadata": content.get("metadata", {}),
    # NEW: Query response
    "query_response": query_response_data,
    "pipeline_stats": {
        # ... existing stats ...
    }
}
```

**UPDATE save_check_results_sync (around line 105):**

```python
def save_check_results_sync(check_id: str, results: Dict[str, Any]):
    """Save pipeline results to database (synchronous for Celery)"""
    try:
        from app.core.database import sync_session
        from app.models import Check, Claim, Evidence
        from sqlalchemy import select

        with sync_session() as session:
            # Update check
            stmt = select(Check).where(Check.id == check_id)
            result = session.execute(stmt)
            check = result.scalar_one_or_none()

            if not check:
                logger.error(f"Check {check_id} not found in database")
                return

            check.status = "completed"
            check.completed_at = datetime.utcnow()
            check.processing_time_ms = results.get("processing_time_ms", 0)

            # Save overall summary fields
            check.overall_summary = results.get("overall_summary")
            check.credibility_score = results.get("credibility_score")
            check.claims_supported = results.get("claims_supported", 0)
            check.claims_contradicted = results.get("claims_contradicted", 0)
            check.claims_uncertain = results.get("claims_uncertain", 0)

            # NEW: Save query response fields
            query_data = results.get("query_response")
            if query_data:
                check.query_response = query_data.get("answer")
                check.query_confidence = query_data.get("confidence")
                check.query_sources = json.dumps(query_data.get("source_ids", []))

            # ... rest of function unchanged ...
```

---

## 🎨 PHASE 4: FRONTEND IMPLEMENTATION

### 4.1 Update New Check Page: `web/app/dashboard/new-check/page.tsx`

**UPDATE TabType (line 11):**

```typescript
type TabType = 'url' | 'text' | 'voice';
```

**ADD state variables (after line 22):**

```typescript
const [audioFile, setAudioFile] = useState<File | null>(null);
const [audioPath, setAudioPath] = useState<string>('');
const [queryInput, setQueryInput] = useState('');  // NEW: Search Clarity
```

**ADD Voice tab button (after TEXT button, around line 145):**

```typescript
<button
  type="button"
  onClick={() => setActiveTab('voice')}
  className={`pb-2 font-bold uppercase text-sm transition-colors ${
    activeTab === 'voice'
      ? 'text-[#f57a07] border-b-2 border-[#f57a07]'
      : 'text-slate-400 hover:text-slate-300'
  }`}
>
  VOICE
</button>
```

**ADD Voice tab content (after TEXT content, around line 194):**

```typescript
{/* VOICE Tab Content */}
{activeTab === 'voice' && (
  <div>
    <label htmlFor="voice-input" className="block text-sm font-semibold text-white mb-2">
      Voice Recording
    </label>

    {!audioFile ? (
      <div className="border-2 border-dashed border-slate-700 rounded-lg p-8 text-center">
        <p className="text-slate-400 mb-4">
          Record your voice or upload an audio file
        </p>

        {/* File Upload */}
        <input
          id="voice-input"
          type="file"
          accept="audio/webm,audio/wav,audio/m4a,audio/mp3,audio/mpeg"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (file) {
              setAudioFile(file);
              // Upload immediately
              try {
                const formData = new FormData();
                formData.append('file', file);
                const token = await getToken();
                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/checks/upload-audio`, {
                  method: 'POST',
                  headers: { Authorization: `Bearer ${token}` },
                  body: formData
                });
                const data = await response.json();
                setAudioPath(data.filePath);
              } catch (err) {
                setError('Failed to upload audio file');
                setAudioFile(null);
              }
            }
          }}
          className="hidden"
        />
        <label
          htmlFor="voice-input"
          className="inline-block bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold py-2 px-6 rounded-lg cursor-pointer transition-colors"
        >
          Choose Audio File
        </label>

        <p className="text-sm text-slate-500 mt-4">
          Supported: WAV, MP3, M4A, WebM (max 25MB, 2 minutes)
        </p>
      </div>
    ) : (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-white font-semibold">{audioFile.name}</p>
            <p className="text-sm text-slate-400">{(audioFile.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
          <button
            type="button"
            onClick={() => {
              setAudioFile(null);
              setAudioPath('');
            }}
            className="text-red-400 hover:text-red-300 font-semibold"
          >
            Remove
          </button>
        </div>
      </div>
    )}
  </div>
)}
```

**ADD Search Clarity field (after all tabs, before error message - around line 195):**

```typescript
{/* Search Clarity Field - Always visible after input */}
<div className="border-t border-slate-700 pt-6 mt-2">
  <label htmlFor="query-input" className="block text-sm font-semibold text-white mb-2">
    🔍 Search Clarity
  </label>
  <textarea
    id="query-input"
    value={queryInput}
    onChange={(e) => setQueryInput(e.target.value)}
    placeholder="Looking for something specific? Ask a focused question and we'll search our evidence sources for the answer.

Leave blank for standard fact-check."
    maxLength={200}
    rows={3}
    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder:text-slate-500 focus:border-[#f57a07] focus:outline-none transition-colors resize-vertical"
    disabled={isSubmitting}
  />
  <div className="flex justify-between items-center mt-2">
    <p className="text-sm text-slate-400">
      Optional: Ask what you want to know
    </p>
    <p className="text-sm text-slate-400">
      {queryInput.length} / 200 characters
    </p>
  </div>
</div>
```

**UPDATE handleSubmit function (around line 34):**

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setError(null);

  // Validate based on active tab
  if (activeTab === 'url') {
    if (!urlInput.trim()) {
      setError('Please enter a URL');
      return;
    }
    if (!isValidUrl(urlInput)) {
      setError('Please enter a valid URL (e.g., https://example.com)');
      return;
    }
  }

  if (activeTab === 'text') {
    if (!textInput.trim()) {
      setError('Please enter some text');
      return;
    }
    if (textInput.length < 10) {
      setError('Text must be at least 10 characters');
      return;
    }
    if (textInput.length > 5000) {
      setError('Text must be less than 5000 characters');
      return;
    }
  }

  // NEW: Voice validation
  if (activeTab === 'voice') {
    if (!audioPath) {
      setError('Please upload an audio file');
      return;
    }
  }

  setIsSubmitting(true);

  try {
    const token = await getToken();

    const result = await apiClient.createCheck({
      input_type: activeTab,
      url: activeTab === 'url' ? urlInput : undefined,
      content: activeTab === 'text' ? textInput : undefined,
      file_path: activeTab === 'voice' ? audioPath : undefined,  // NEW
      user_query: queryInput.trim() || undefined,  // NEW: Search Clarity
    }, token) as any;

    // Redirect to check detail page
    router.push(`/dashboard/check/${result.check.id}`);
  } catch (err: any) {
    setError(err.message || 'Failed to create check. Please try again.');
    setIsSubmitting(false);
  }
};
```

### 4.2 New Component: Clarity Response Card

**CREATE: `web/app/dashboard/check/[id]/components/clarity-response-card.tsx`**

```typescript
'use client';

interface ClarityResponseProps {
  userQuery: string;
  queryResponse: string;
  queryConfidence: number;
  querySources: Array<{
    id: string;
    source: string;
    url: string;
    credibilityScore: number;
  }>;
  relatedClaims?: number[];
  claims?: any[];
}

export function ClarityResponseCard({
  userQuery,
  queryResponse,
  queryConfidence,
  querySources,
  relatedClaims,
  claims
}: ClarityResponseProps) {
  const hasDirectAnswer = queryConfidence >= 40;

  return (
    <div className="bg-gradient-to-r from-[#1E40AF05] to-[#7C3AED05] border-l-4 border-[#1E40AF] rounded-xl p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-2xl">💡</span>
        <h3 className="text-xl font-bold text-white">CLARITY RESPONSE</h3>
      </div>

      {/* User's Question */}
      <div>
        <p className="text-sm text-slate-400 italic mb-1">Your question:</p>
        <p className="text-lg text-slate-200">"{userQuery}"</p>
      </div>

      <hr className="border-slate-700" />

      {/* Direct Answer (if confidence >= 40%) */}
      {hasDirectAnswer && queryResponse && (
        <>
          <div>
            <p className="text-base text-white leading-relaxed">
              {queryResponse}
            </p>
          </div>

          {/* Confidence Bar */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-semibold text-slate-300">Confidence</span>
              <span className="text-sm font-bold text-white">{Math.round(queryConfidence)}%</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-3">
              <div
                className="bg-gradient-to-r from-[#1E40AF] to-[#7C3AED] h-3 rounded-full transition-all"
                style={{ width: `${queryConfidence}%` }}
              />
            </div>
            {queryConfidence < 70 && (
              <p className="text-xs text-slate-400 mt-1">
                ℹ️ Moderate confidence - limited sources available
              </p>
            )}
          </div>

          {/* Sources */}
          {querySources && querySources.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-slate-300 mb-2">📚 Sources:</p>
              <div className="space-y-2">
                {querySources.map((source, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-800/50 rounded-lg p-3 border border-slate-700"
                  >
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#f57a07] hover:text-[#e06a00] font-semibold transition-colors"
                    >
                      {source.source}
                    </a>
                    <span className="text-slate-500 mx-2">·</span>
                    <span className="text-sm text-slate-400">
                      Credibility: {Math.round(source.credibilityScore * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* No Direct Answer - Show Related Claims (if confidence < 40%) */}
      {!hasDirectAnswer && relatedClaims && relatedClaims.length > 0 && (
        <>
          <div className="bg-amber-900/20 border border-amber-600/30 rounded-lg p-4">
            <p className="text-amber-200 text-sm">
              ⚠️ We couldn't find a direct answer to your question in the available sources.
            </p>
          </div>

          <div>
            <p className="text-sm font-semibold text-slate-300 mb-3">
              However, these related claims may help:
            </p>
            <div className="space-y-3">
              {relatedClaims.map((position) => {
                const claim = claims?.find(c => c.position === position);
                if (!claim) return null;

                return (
                  <div
                    key={position}
                    className="bg-slate-800/50 rounded-lg p-4 border border-slate-700 cursor-pointer hover:border-slate-600 transition-colors"
                    onClick={() => {
                      // Scroll to claim
                      const element = document.getElementById(`claim-${position}`);
                      element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }}
                  >
                    <div className="flex items-start justify-between">
                      <p className="text-white flex-1">
                        → Claim {position + 1}: {claim.text}
                      </p>
                      <span className="ml-4 text-xs font-semibold text-slate-400">
                        {claim.verdict.toUpperCase()} ({claim.confidence}%)
                      </span>
                    </div>
                    <p className="text-sm text-[#f57a07] mt-2 hover:underline">
                      Jump to details ↓
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* No Related Claims Either */}
      {!hasDirectAnswer && (!relatedClaims || relatedClaims.length === 0) && (
        <div className="bg-red-900/20 border border-red-600/30 rounded-lg p-4">
          <p className="text-red-200 text-sm">
            We couldn't find information addressing your question in the analyzed content or evidence sources.
            The standard fact-check below may still contain relevant information.
          </p>
        </div>
      )}
    </div>
  );
}
```

### 4.3 Update Check Detail Client: `web/app/dashboard/check/[id]/check-detail-client.tsx`

**ADD import (line 11):**

```typescript
import { ClarityResponseCard } from './components/clarity-response-card';
```

**ADD Clarity Response rendering (after line 71, before ClaimsSection):**

```typescript
{checkData.status === 'completed' && checkData.userQuery && checkData.queryResponse !== undefined && (
  <ClarityResponseCard
    userQuery={checkData.userQuery}
    queryResponse={checkData.queryResponse}
    queryConfidence={checkData.queryConfidence || 0}
    querySources={checkData.querySources || []}
    relatedClaims={checkData.queryRelatedClaims}
    claims={checkData.claims}
  />
)}
```

---

## 🧪 PHASE 5: TESTING

### Backend Unit Tests

**CREATE: `backend/tests/unit/test_voice_ingester.py`**

```python
import pytest
from app.pipeline.ingest import VoiceIngester

@pytest.mark.asyncio
async def test_voice_ingester_success():
    """Test successful voice transcription"""
    ingester = VoiceIngester()
    # Mock audio file path
    result = await ingester.process("tests/fixtures/sample_audio.wav")
    assert result["success"] == True
    assert len(result["content"]) > 0
    assert "whisper_api" in result["metadata"]["extraction_method"]

@pytest.mark.asyncio
async def test_voice_ingester_invalid_file():
    """Test error handling for invalid audio file"""
    ingester = VoiceIngester()
    result = await ingester.process("nonexistent.wav")
    assert result["success"] == False
    assert "error" in result
```

**CREATE: `backend/tests/unit/test_query_answerer.py`**

```python
import pytest
from app.pipeline.query_answer import QueryAnswerer

@pytest.mark.asyncio
async def test_query_answerer_high_confidence():
    """Test query answering with high confidence"""
    answerer = QueryAnswerer()

    claims = [{"text": "Event happens in 2025", "position": 0}]
    evidence = {"0": [{"snippet": "The event is scheduled for Q2 2025", "source": "BBC"}]}

    result = await answerer.answer_query(
        user_query="When will the event happen?",
        claims=claims,
        evidence_by_claim=evidence,
        original_text="Event announcement for 2025"
    )

    assert result["confidence"] >= 40
    assert len(result["answer"]) > 0
    assert result["found_answer"] == True

@pytest.mark.asyncio
async def test_query_answerer_low_confidence():
    """Test query answering with insufficient evidence"""
    answerer = QueryAnswerer()

    claims = [{"text": "Unrelated claim", "position": 0}]
    evidence = {"0": [{"snippet": "Different topic", "source": "Source"}]}

    result = await answerer.answer_query(
        user_query="What is the environmental impact?",
        claims=claims,
        evidence_by_claim=evidence,
        original_text="Article about economics"
    )

    assert result["confidence"] < 40
    assert result["found_answer"] == False
    assert len(result["related_claims"]) >= 0
```

### Integration Tests

1. **Voice End-to-End:**
   - Upload audio file → `/api/checks/upload-audio`
   - Create check with `input_type='voice'` and `file_path`
   - Verify VoiceIngester called
   - Verify transcription occurs
   - Verify claims extracted from transcribed text

2. **Query End-to-End:**
   - Create check with `user_query`
   - Verify query answering stage runs
   - Verify response saved to database
   - Verify frontend displays ClarityResponseCard correctly

---

## 📋 PHASE 6: DEPLOYMENT

### 6.1 Environment Variables

**ADD to `backend/app/core/config.py`:**

```python
# Voice/Clarity Features
ENABLE_VOICE_INPUT: bool = Field(default=True, description="Enable voice input feature")
WHISPER_MODEL: str = Field(default="whisper-1", description="Whisper model for transcription")
MAX_AUDIO_DURATION_SECONDS: int = Field(default=120, description="Max audio duration (2 minutes)")
MAX_AUDIO_SIZE_MB: int = Field(default=25, description="Max audio file size")
ENABLE_QUERY_FEATURE: bool = Field(default=True, description="Enable Search Clarity feature")
```

### 6.2 Database Migration

```bash
cd backend
alembic revision --autogenerate -m "add_voice_and_clarity_fields"
alembic upgrade head
```

### 6.3 Deployment Steps

**Backend:**

```bash
# Install dependencies (already have openai>=1.0.0)
pip install -r requirements.txt

# Run migration
alembic upgrade head

# Restart services
systemctl restart tru8-api
systemctl restart tru8-worker
```

**Frontend:**

```bash
# Build
npm run build

# Deploy
vercel --prod
```

**Verification:**

- Test voice upload endpoint
- Test voice check creation
- Test query with high confidence
- Test query with low confidence
- Test UI rendering on desktop & mobile

---

## 📊 MONITORING & METRICS

### Key Metrics to Track:

**Voice Feature:**
- Voice input usage rate (% of total checks)
- Whisper API success rate
- Average transcription time
- Average audio duration
- Cost per voice check

**Clarity Feature:**
- Query feature usage rate (% of checks with query)
- Average query confidence
- Direct answer rate (confidence >= 40%)
- Related claims fallback rate (confidence < 40%)
- Average query answering time
- Targeted retrieval trigger rate

### Cost Analysis:

```python
# Pipeline metrics
"costs": {
    "whisper_transcription": 0.006 * (duration_minutes),  # $0.006/min
    "query_targeted_search": 0.0006 if targeted_retrieval else 0,
    "query_llm_answer": 0.002,
    "total_query_cost": sum_above
}
```

**Expected Costs:**
- Standard check: $0.020
- Voice check (2min audio): $0.032
- Check with query (no targeted search): $0.022
- Check with query (with targeted search): $0.025

---

## 🎯 ROLLOUT TIMELINE

### Week 1: Backend Foundation (Days 1-7)
- ✅ Create and run database migration
- ✅ Implement VoiceIngester class
- ✅ Implement QueryAnswerer class
- ✅ Integrate voice ingester into pipeline routing
- ✅ Add query stage to pipeline
- ✅ Write unit tests
- ✅ Test locally with sample audio files

### Week 2: API & Frontend (Days 8-14)
- ✅ Add `/upload-audio` endpoint
- ✅ Update API validation and responses
- ✅ Add voice tab to new-check page
- ✅ Add Search Clarity input field
- ✅ Create ClarityResponseCard component
- ✅ Update check detail client
- ✅ Test frontend flows locally

### Week 3: Testing & Polish (Days 15-21)
- ✅ Write integration tests
- ✅ UI/UX refinements based on testing
- ✅ Error handling improvements
- ✅ Performance optimization
- ✅ Mobile responsive testing
- ✅ Documentation updates

### Week 4: Deploy & Monitor (Days 22-28)
- ✅ Deploy to staging environment
- ✅ QA testing on staging
- ✅ Production deployment
- ✅ Monitor metrics and costs
- ✅ Collect user feedback
- ✅ Bug fixes and adjustments

---

## ✅ COMPLETION CRITERIA

### Feature Functionality
- [ ] User can upload audio files (WAV, MP3, M4A, WebM)
- [ ] Audio files transcribe correctly via Whisper API
- [ ] Voice checks extract claims from transcription
- [ ] User can add optional 200-char query to any check type
- [ ] Queries with confidence >= 40% show direct answers with sources
- [ ] Queries with confidence < 40% show related claims with jump links
- [ ] Related claims scroll smoothly when clicked

### Technical Requirements
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] No performance degradation in standard checks
- [ ] Pipeline latency stays under 15 seconds for voice+query
- [ ] Cost per check stays under $0.03 average
- [ ] Database migration successful on staging and production

### UI/UX Requirements
- [ ] Voice tab matches existing URL/TEXT design
- [ ] Audio file upload is intuitive
- [ ] Clarity input field clearly labeled and positioned
- [ ] ClarityResponseCard visually distinct from claims
- [ ] Confidence bars render correctly
- [ ] Related claims are clickable and functional
- [ ] Mobile responsive on all screen sizes
- [ ] Follows design system (4pt grid, colors, typography)

### Documentation & Monitoring
- [ ] API documentation updated
- [ ] README updated with new features
- [ ] Monitoring dashboards include voice/query metrics
- [ ] Cost tracking includes Whisper API calls
- [ ] Error logging captures voice/query failures

---

## 🔍 KNOWN LIMITATIONS & FUTURE ENHANCEMENTS

### Current MVP Limitations:
1. **Voice Input:**
   - Max 2 minutes audio duration
   - English language only (Whisper supports 90+ but not implemented)
   - No real-time recording UI (file upload only)
   - No speaker diarization

2. **Search Clarity:**
   - Simple keyword matching for relevance (not semantic embeddings)
   - Single query per check (no follow-up questions)
   - No conversation history
   - Basic fallback to related claims

### Post-MVP Enhancements:
1. **Voice Input:**
   - Add in-browser audio recorder with waveform visualization
   - Support multi-language transcription
   - Add speaker diarization for multi-speaker audio
   - Extend duration limit for premium tier

2. **Search Clarity:**
   - Upgrade to semantic similarity using embeddings
   - Add multi-turn conversation support
   - Add query refinement suggestions
   - Add "Ask another question" button on results page
   - Show query-to-claim relevance scores

3. **General:**
   - A/B test different confidence thresholds
   - Add user feedback mechanism ("Was this answer helpful?")
   - Track query patterns to improve retrieval
   - Add query autocomplete based on common questions

---

## 📞 SUPPORT & TROUBLESHOOTING

### Common Issues:

**Voice transcription fails:**
- Check Whisper API key is valid
- Verify audio file format is supported
- Check audio file isn't corrupted
- Ensure file size under 25MB

**Query returns no answer:**
- Check if evidence was retrieved for claims
- Verify OpenAI API key is valid
- Check query isn't too vague or unrelated
- Review targeted retrieval trigger logic

**Audio upload fails:**
- Check file extension is allowed
- Verify file size under 25MB limit
- Check uploads/audio directory exists and is writable
- Review nginx/server upload size limits

**Frontend issues:**
- Clear browser cache
- Check API_URL environment variable
- Verify Clerk auth token is valid
- Review browser console for errors

---

**END OF IMPLEMENTATION PLAN**

*Document Version: 1.0*
*Last Updated: 2025-10-30*
*Author: Claude (Tru8 Technical Architect)*
