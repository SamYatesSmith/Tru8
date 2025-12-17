"""
Rhetorical Context Analyzer

Detects when evidence sources describe rhetorical intent (sarcasm, mockery, satire)
rather than trying to detect sarcasm directly in claims.

This approach is more reliable because:
1. News sources explicitly label tone ("Trump mocked", "sarcastically posted")
2. Fact-checkers like Snopes investigate satirical intent
3. We trust professional journalists' characterization of tone

Example: Trump's "very sad" post about Rob Reiner
- Literal: He wrote "very sad"
- Sources say: "mocked", "satirical", "Trump Derangement Syndrome joke"
- This analyzer detects the source descriptions, not the sarcasm itself
"""

import re
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class RhetoricalContextAnalyzer:
    """
    Detect rhetorical context by analyzing how SOURCES describe tone/intent.

    More reliable than direct sarcasm detection because we trust journalists'
    characterization of rhetorical devices.
    """

    def __init__(self):
        # Markers that sources use to describe rhetorical intent
        # These appear in evidence snippets, not the original claim
        self.rhetorical_markers = {
            "sarcasm": [
                r"\bsarcastic(?:ally)?\b",
                r"\bsarcasm\b",
                r"\bironic(?:ally)?\b",
                r"\birony\b",
                r"\btongue[- ]in[- ]cheek\b",
            ],
            "mockery": [
                r"\bmock(?:ed|ing|s)?\b",
                r"\bridicul(?:ed|ing|es)?\b",
                r"\btaunt(?:ed|ing|s)?\b",
                r"\bderid(?:ed|ing|es)?\b",
                r"\bbelittl(?:ed|ing|es)?\b",
                r"\bsnark(?:y|ily)?\b",
            ],
            "satire": [
                r"\bsatir(?:e|ical|ically)\b",
                r"\bparody\b",
                r"\bparodi(?:ed|es|ying)\b",
                r"\blampooning?\b",
            ],
            "joking": [
                r"\bjok(?:e|ed|ing|ingly)\b",
                r"\bin jest\b",
                r"\bnot serious(?:ly)?\b",
                r"\bfacetious(?:ly)?\b",
            ],
            "inflammatory": [
                r"\binflammatory\b",
                r"\bprovocative\b",
                r"\bincendiary\b",
                r"\boutrageous(?:ly)?\b",
            ],
            "hyperbole": [
                r"\bhyperbol(?:e|ic|ically)\b",
                r"\bexaggerat(?:ed|ing|ion)\b",
                r"\boverstated?\b",
            ],
        }

        # Markers indicating literal vs intended meaning conflict
        self.intent_conflict_markers = [
            r"\bwhile (saying|writing|posting|claiming)\b.*\b(actually|really|in fact)\b",
            r"\bdespite (saying|writing|calling)\b",
            r"\b(appeared|seemed) to\b.*\bbut\b",
            r"\bliterally said\b.*\b(meant|implied|suggested)\b",
            r"\bwords (were|said)\b.*\b(tone|intent|meaning)\b",
        ]

        # Phrases indicating sources are questioning sincerity
        self.sincerity_question_markers = [
            r"\bwhether.*(serious|sincere|genuine)\b",
            r"\b(questioned|doubted|disputed).*(sincerity|intent)\b",
            r"\b(unclear|uncertain) (if|whether).*meant\b",
            r"\bsome (interpreted|saw|viewed).*as\b",
        ]

    def analyze_evidence_for_rhetorical_context(
        self,
        evidence_list: List[Dict[str, Any]],
        claim_text: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze evidence snippets for rhetorical context markers.

        Returns analysis of whether sources describe the claim/statement
        as having rhetorical intent (sarcasm, mockery, etc.)
        """
        all_markers_found = []
        sources_describing_rhetoric = []
        intent_conflicts_found = []
        sincerity_questions_found = []

        for evidence in evidence_list:
            snippet = evidence.get("snippet", "") or evidence.get("content", "")
            title = evidence.get("title", "")
            source = evidence.get("source", evidence.get("publisher", "Unknown"))

            combined_text = f"{title} {snippet}".lower()

            # Check for rhetorical markers
            evidence_markers = self._find_markers(combined_text, self.rhetorical_markers)
            if evidence_markers:
                all_markers_found.extend(evidence_markers)
                sources_describing_rhetoric.append({
                    "source": source,
                    "title": title[:100],
                    "markers_found": evidence_markers,
                    "url": evidence.get("url", "")
                })

            # Check for intent conflict markers
            for pattern in self.intent_conflict_markers:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    intent_conflicts_found.append({
                        "source": source,
                        "pattern": pattern,
                        "snippet_excerpt": snippet[:200] if snippet else ""
                    })

            # Check for sincerity questioning
            for pattern in self.sincerity_question_markers:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    sincerity_questions_found.append({
                        "source": source,
                        "pattern": pattern
                    })

        # Determine overall rhetorical context
        has_rhetorical_context = bool(all_markers_found) or bool(intent_conflicts_found)

        # Calculate confidence based on number and diversity of sources
        unique_sources = len(set(s["source"] for s in sources_describing_rhetoric))
        marker_types = len(set(all_markers_found))

        confidence = 0.0
        if unique_sources >= 3:
            confidence = 0.9
        elif unique_sources >= 2:
            confidence = 0.75
        elif unique_sources >= 1:
            confidence = 0.6

        # Boost confidence if multiple marker types found
        if marker_types >= 2:
            confidence = min(1.0, confidence + 0.1)

        # Determine primary rhetorical style
        primary_style = self._determine_primary_style(all_markers_found)

        return {
            "has_rhetorical_context": has_rhetorical_context,
            "confidence": confidence,
            "primary_style": primary_style,
            "markers_found": list(set(all_markers_found)),
            "sources_describing_rhetoric": sources_describing_rhetoric,
            "intent_conflicts_detected": len(intent_conflicts_found) > 0,
            "sincerity_questioned": len(sincerity_questions_found) > 0,
            "unique_sources_flagging": unique_sources,
            "explanation": self._generate_explanation(
                has_rhetorical_context,
                primary_style,
                unique_sources,
                all_markers_found,
                intent_conflicts_found,
                sincerity_questions_found
            )
        }

    def _find_markers(
        self,
        text: str,
        marker_dict: Dict[str, List[str]]
    ) -> List[str]:
        """Find all rhetorical markers in text"""
        found = []
        for marker_type, patterns in marker_dict.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    found.append(marker_type)
                    break  # One match per type is enough
        return found

    def _determine_primary_style(self, markers: List[str]) -> Optional[str]:
        """Determine the primary rhetorical style from markers"""
        if not markers:
            return None

        # Count occurrences
        from collections import Counter
        counts = Counter(markers)

        # Return most common, with preference order for ties
        preference_order = ["sarcasm", "mockery", "satire", "joking", "inflammatory", "hyperbole"]
        max_count = max(counts.values()) if counts else 0

        for style in preference_order:
            if counts.get(style, 0) == max_count and max_count > 0:
                return style

        return counts.most_common(1)[0][0] if counts else None

    def _generate_explanation(
        self,
        has_context: bool,
        primary_style: Optional[str],
        source_count: int,
        markers: List[str],
        intent_conflicts: List[Dict],
        sincerity_questions: List[Dict]
    ) -> str:
        """Generate human-readable explanation of rhetorical context"""
        if not has_context:
            return "No rhetorical context detected in evidence sources."

        parts = []

        if primary_style:
            style_descriptions = {
                "sarcasm": "sarcastic or ironic",
                "mockery": "mocking or ridiculing",
                "satire": "satirical",
                "joking": "made in jest or not serious",
                "inflammatory": "inflammatory or provocative",
                "hyperbole": "hyperbolic or exaggerated"
            }
            style_desc = style_descriptions.get(primary_style, primary_style)
            parts.append(f"{source_count} source(s) describe this statement as {style_desc}")

        if intent_conflicts:
            parts.append("Sources indicate a conflict between literal words and intended meaning")

        if sincerity_questions:
            parts.append("Sources question whether the statement was sincere")

        return ". ".join(parts) + "." if parts else "Rhetorical context detected."

    def get_judge_guidance(self, analysis: Dict[str, Any]) -> str:
        """
        Generate guidance for the judge based on rhetorical analysis.

        This helps the LLM judge understand why evidence might conflict
        and how to handle literal-vs-intent discrepancies.
        """
        if not analysis.get("has_rhetorical_context"):
            return ""

        guidance_parts = []

        primary_style = analysis.get("primary_style")
        if primary_style:
            guidance_parts.append(
                f"RHETORICAL CONTEXT WARNING: {analysis['unique_sources_flagging']} evidence source(s) "
                f"characterize this statement as {primary_style}."
            )

        if analysis.get("intent_conflicts_detected"):
            guidance_parts.append(
                "Evidence suggests a discrepancy between the LITERAL words used and the "
                "INTENDED meaning. When judging, consider that the speaker may have meant "
                "the opposite of what was literally said."
            )

        if analysis.get("sincerity_questioned"):
            guidance_parts.append(
                "Sources question whether this statement was made sincerely. "
                "Consider this when evaluating claims about what was 'said' vs what was 'meant'."
            )

        # Add specific guidance based on style
        style_guidance = {
            "sarcasm": (
                "For sarcastic statements, verify the LITERAL words were said (likely true), "
                "but note that the intended meaning may be the opposite. The verdict should "
                "acknowledge this context."
            ),
            "mockery": (
                "This appears to be mockery. The literal claim about what was said may be true, "
                "but characterizing it as sincere would be misleading."
            ),
            "satire": (
                "This may be satirical content. Claims about what was 'said' are technically true, "
                "but the speaker may not have meant it literally."
            ),
            "joking": (
                "Sources indicate this was said in jest. Claims about exact words may be supported, "
                "but claims about sincerity or belief should be approached carefully."
            ),
        }

        if primary_style in style_guidance:
            guidance_parts.append(style_guidance[primary_style])

        return "\n\n".join(guidance_parts)


# Convenience function for pipeline integration
def analyze_rhetorical_context(
    evidence_list: List[Dict[str, Any]],
    claim_text: str = ""
) -> Dict[str, Any]:
    """
    Convenience function to analyze evidence for rhetorical context.

    Usage in pipeline:
        from app.utils.rhetorical_analyzer import analyze_rhetorical_context
        rhetorical_analysis = analyze_rhetorical_context(evidence, claim["text"])
    """
    analyzer = RhetoricalContextAnalyzer()
    return analyzer.analyze_evidence_for_rhetorical_context(evidence_list, claim_text)
