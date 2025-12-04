"""
Query Answering Pipeline Stage
Answers user's specific question using retrieved evidence
"""
import logging
import httpx
import json
from typing import Dict, List, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class QueryAnswerer:
    """Answer user queries based on evidence pool"""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.timeout = 30
        self.model = "gpt-4o-mini-2024-07-18"  # MUST match Judge stage
        self.max_tokens = 300
        self.temperature = 0.2
        self.confidence_threshold = settings.QUERY_CONFIDENCE_THRESHOLD  # Below this = show related claims

        self.system_prompt = """You are a Tru8 fact-checking specialist specializing in answering user questions with evidence.

TASK: Answer the user's question using ONLY the provided evidence sources.
Be direct and concise (2-3 sentences maximum).
Cite which sources you used by number.

HANDLING UNCERTAINTY:
If the evidence doesn't contain a clear answer:
- Set confidence below 40
- Say "Based on the available evidence, I cannot determine..."
- In your answer, explain what information would be needed

EXAMPLES:

Example 1 - High Confidence Answer:
Question: "How many goals did the player score?"
Evidence: [0] Transfermarkt shows 15 goals this season
Answer: {"answer": "According to Transfermarkt [0], the player has scored 15 goals this season.", "confidence": 90, "sources_used": [0]}

Example 2 - Low Confidence Answer:
Question: "What was the exact budget?"
Evidence: [0] Article mentions "significant funding" but no specific amount
Answer: {"answer": "Based on the available evidence, I cannot determine the exact budget. The sources mention 'significant funding' but don't provide specific figures.", "confidence": 25, "sources_used": [0]}

RESPONSE FORMAT: JSON only
{
  "answer": "Your concise answer here",
  "confidence": 85,
  "sources_used": [0, 2, 4]
}

confidence: Integer 0-100 (how confident you are in the answer based on evidence quality)
  - 90-100: Direct, clear answer from multiple credible sources
  - 75-89: Good answer, minor gaps in evidence
  - 50-74: Partial answer, some uncertainty
  - Below 50: Cannot answer confidently
sources_used: List of source indices (0-indexed) that support your answer
"""

    async def answer_query(
        self,
        user_query: str,
        claims: List[Dict[str, Any]],
        evidence_by_claim: Dict[str, List[Dict[str, Any]]],
        original_text: str
    ) -> Dict[str, Any]:
        """
        Answer user query using evidence pool.

        Args:
            user_query: User's question
            claims: List of extracted claims
            evidence_by_claim: Dict mapping claim positions to evidence lists
            original_text: Original content being fact-checked

        Returns:
            {
                "answer": str,
                "confidence": float (0-100),
                "source_ids": List[str],  # Evidence UUIDs
                "related_claims": List[int],  # Claim positions (if confidence < 40)
                "found_answer": bool
            }
        """
        try:
            # Build evidence pool (all evidence from all claims)
            all_evidence = []
            for position, evidence_list in evidence_by_claim.items():
                all_evidence.extend(evidence_list)

            # If no evidence, return early
            if not all_evidence:
                logger.warning("No evidence available for query answering")
                return self._create_fallback_response(user_query, claims)

            # Build context for LLM
            evidence_context = self._build_evidence_context(all_evidence[:10])  # Top 10

            # Build prompt
            prompt = f"""ORIGINAL CONTENT PREVIEW:
{original_text[:500]}

USER QUESTION: {user_query}

AVAILABLE EVIDENCE SOURCES:
{evidence_context}

Answer the user's question using ONLY the evidence above.
Be direct and concise. Cite source numbers used."""

            # Call OpenAI
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "response_format": {"type": "json_object"}
                    }
                )

                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.status_code}")
                    return self._create_fallback_response(user_query, claims)

                result = response.json()
                raw_answer = result["choices"][0]["message"]["content"].strip()

                # Parse JSON response
                try:
                    parsed = json.loads(raw_answer)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse LLM response: {raw_answer}")
                    return self._create_fallback_response(user_query, claims)

                answer = parsed.get("answer", "")
                confidence = float(parsed.get("confidence", 0))
                source_indices = parsed.get("sources_used", [])

                # Map source indices to evidence IDs
                source_objects = []
                for idx in source_indices:
                    if 0 <= idx < len(all_evidence):
                        ev = all_evidence[idx]
                        source_objects.append({
                            "id": ev.get("id", f"evidence_{idx}"),
                            "source": ev.get("source", "Unknown"),
                            "url": ev.get("url", ""),
                            "title": ev.get("title", ""),
                            "snippet": ev.get("snippet", "")[:settings.EVIDENCE_SNIPPET_LENGTH],
                            "publishedDate": ev.get("published_date"),
                            "credibilityScore": ev.get("credibility_score", 0.7)
                        })

                # If confidence < threshold, find related claims
                related_claims = []
                if confidence < self.confidence_threshold:
                    related_claims = await self._find_related_claims(user_query, claims)

                logger.info(f"Query answered: confidence={confidence}%, sources={len(source_objects)}")

                return {
                    "answer": answer,
                    "confidence": confidence,
                    "source_ids": source_objects,  # Full objects, not just IDs
                    "related_claims": related_claims,
                    "found_answer": confidence >= self.confidence_threshold
                }

        except Exception as e:
            logger.error(f"Query answering error: {e}", exc_info=True)
            return self._create_fallback_response(user_query, claims)

    def _build_evidence_context(self, evidence_list: List[Dict[str, Any]]) -> str:
        """Build numbered evidence context for LLM"""
        context_lines = []
        for i, ev in enumerate(evidence_list):
            source = ev.get("source", "Unknown")
            snippet = ev.get("snippet", ev.get("text", ""))[:settings.EVIDENCE_SNIPPET_LENGTH]
            date = ev.get("published_date", "")
            credibility = ev.get("credibility_score", 0.7)

            context_lines.append(
                f"[{i}] {source} ({date}) - Credibility: {credibility:.0%}\n"
                f"    {snippet}..."
            )

        return "\n\n".join(context_lines)

    async def _find_related_claims(self, query: str, claims: List[Dict[str, Any]]) -> List[int]:
        """
        Find claims semantically related to query using keyword matching.
        Returns list of claim positions (0-indexed).
        """
        query_words = set(query.lower().split())

        related = []
        for claim in claims:
            claim_text = claim.get("text", "").lower()
            claim_words = set(claim_text.split())

            # Calculate keyword overlap
            overlap = len(query_words.intersection(claim_words))

            # Require at least 2 keyword matches
            if overlap >= 2:
                related.append(claim.get("position", 0))

        # Return top 3 related claims
        return related[:3]

    def _create_fallback_response(self, query: str, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback response when query answering fails"""
        # Try to find any claims with keyword matches
        query_words = set(query.lower().split())
        related_claims = []

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
