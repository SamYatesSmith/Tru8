from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ExplainabilityEnhancer:
    """Add transparency and detailed explanations to verdicts"""

    def create_decision_trail(self, claim: Dict, evidence: List[Dict],
                             verification_signals: Dict, judgment: Dict) -> Dict[str, Any]:
        """Create detailed decision trail for transparency"""

        trail = {
            "stages": [
                {
                    "stage": "evidence_retrieval",
                    "description": "Searched for evidence using optimized query",
                    "result": f"Found {len(evidence)} sources",
                    "details": {
                        "unique_domains": len(set(ev.get('source', 'unknown') for ev in evidence)),
                        "avg_credibility": round(sum(ev.get('credibility_score', 0.6) for ev in evidence) / max(len(evidence), 1), 2),
                        "temporal_filtered": any(ev.get('is_time_sensitive') for ev in evidence),
                        "factcheck_sources": sum(1 for ev in evidence if ev.get('is_factcheck', False))
                    }
                },
                {
                    "stage": "verification",
                    "description": "Analyzed evidence using NLI model",
                    "result": f"{verification_signals.get('supporting_count', 0)} supporting, "
                             f"{verification_signals.get('contradicting_count', 0)} contradicting",
                    "details": verification_signals
                },
                {
                    "stage": "judgment",
                    "description": "Final verdict determined by LLM judge",
                    "result": f"{judgment.get('verdict', 'unknown')} ({judgment.get('confidence', 0)}% confidence)",
                    "details": {
                        "rationale": judgment.get('rationale', ''),
                        "evidence_used": len(evidence)
                    }
                }
            ],
            "transparency_score": self._calculate_transparency_score(evidence, verification_signals)
        }

        return trail

    def _calculate_transparency_score(self, evidence: List, signals: Dict) -> float:
        """Calculate how transparent/explainable the verdict is"""
        score = 0.5  # Base score

        # More evidence = more transparent
        if len(evidence) >= 3:
            score += 0.2
        elif len(evidence) >= 5:
            score += 0.3

        # High quality evidence = more transparent
        avg_credibility = sum(ev.get('credibility_score', 0.6) for ev in evidence) / max(len(evidence), 1)
        if avg_credibility >= 0.8:
            score += 0.2

        # Clear consensus = more transparent
        supporting = signals.get('supporting_count', 0)
        contradicting = signals.get('contradicting_count', 0)
        total_signals = supporting + contradicting
        if total_signals > 0 and abs(supporting - contradicting) >= 2:
            score += 0.1

        return min(1.0, score)

    def create_uncertainty_explanation(self, verdict: str, signals: Dict, evidence: List) -> str:
        """Explain why verdict is uncertain"""
        if verdict.lower() not in ["uncertain", "unclear", "mixed"]:
            return ""

        total_evidence = len(evidence)

        # Check for insufficient evidence
        if total_evidence < 3:
            return f"Insufficient evidence found (only {total_evidence} source{'s' if total_evidence != 1 else ''}). More research needed."

        # Check for conflicting evidence
        supporting = signals.get('supporting_count', 0)
        contradicting = signals.get('contradicting_count', 0)

        if abs(supporting - contradicting) <= 1:
            return f"Conflicting evidence from equally credible sources ({supporting} supporting vs {contradicting} contradicting)."

        # Check for low quality evidence
        avg_credibility = sum(ev.get('credibility_score', 0.6) for ev in evidence) / max(len(evidence), 1)
        if avg_credibility < 0.5:
            return "Available evidence is low quality or lacks authoritative sources."

        # Check for time-sensitivity issues
        if any(ev.get('is_time_sensitive') for ev in evidence):
            return "Claim is time-sensitive and available evidence may be outdated or incomplete."

        return "Evidence is mixed or insufficient for a definitive determination."

    def create_confidence_breakdown(self, judgment: Dict, evidence: List, signals: Dict) -> Dict[str, Any]:
        """Create detailed breakdown of confidence factors"""
        confidence = judgment.get('confidence', 0)

        breakdown = {
            "overall_confidence": confidence,
            "factors": []
        }

        # Evidence quantity factor
        evidence_count = len(evidence)
        if evidence_count >= 5:
            breakdown["factors"].append({
                "factor": "evidence_quantity",
                "impact": "positive",
                "description": f"Strong evidence base ({evidence_count} sources)",
                "score": 0.2
            })
        elif evidence_count < 3:
            breakdown["factors"].append({
                "factor": "evidence_quantity",
                "impact": "negative",
                "description": f"Limited evidence ({evidence_count} sources)",
                "score": -0.2
            })

        # Evidence quality factor
        avg_credibility = sum(ev.get('credibility_score', 0.6) for ev in evidence) / max(len(evidence), 1)
        if avg_credibility >= 0.8:
            breakdown["factors"].append({
                "factor": "evidence_quality",
                "impact": "positive",
                "description": f"High-quality sources (avg credibility: {avg_credibility:.2f})",
                "score": 0.15
            })

        # Consensus factor
        supporting = signals.get('supporting_count', 0)
        contradicting = signals.get('contradicting_count', 0)
        total_signals = supporting + contradicting

        if total_signals > 0:
            consensus_ratio = max(supporting, contradicting) / total_signals
            if consensus_ratio >= 0.7:
                breakdown["factors"].append({
                    "factor": "evidence_consensus",
                    "impact": "positive",
                    "description": f"Strong consensus ({consensus_ratio:.0%} agreement)",
                    "score": 0.15
                })
            elif consensus_ratio < 0.6:
                breakdown["factors"].append({
                    "factor": "evidence_consensus",
                    "impact": "negative",
                    "description": "Conflicting evidence with no clear consensus",
                    "score": -0.15
                })

        # Fact-check factor
        factcheck_count = sum(1 for ev in evidence if ev.get('is_factcheck', False))
        if factcheck_count > 0:
            breakdown["factors"].append({
                "factor": "fact_check_presence",
                "impact": "positive",
                "description": f"Includes {factcheck_count} professional fact-check{'s' if factcheck_count != 1 else ''}",
                "score": 0.1
            })

        return breakdown

    def get_explainability_summary(self, checks: List[Dict]) -> Dict[str, Any]:
        """Get summary statistics for explainability across checks"""
        if not checks:
            return {
                "total_checks": 0,
                "avg_transparency_score": 0,
                "uncertain_with_explanation": 0
            }

        total = len(checks)
        transparency_scores = [c.get('transparency_score', 0.5) for c in checks]
        uncertain_explained = sum(1 for c in checks
                                 if c.get('verdict') == 'uncertain'
                                 and c.get('uncertainty_explanation'))

        return {
            "total_checks": total,
            "avg_transparency_score": round(sum(transparency_scores) / total, 2),
            "uncertain_with_explanation": uncertain_explained,
            "high_transparency_count": sum(1 for s in transparency_scores if s >= 0.8)
        }
