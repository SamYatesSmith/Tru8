#!/usr/bin/env python3
"""
Pipeline Trace Script for Report Quality Investigation

This script traces a single URL through the verification pipeline,
dumping intermediate artifacts at each stage to diagnose why
irrelevant sources may be appearing as evidence.

Usage:
    python scripts/pipeline_trace.py --url "https://example.com/article"
    python scripts/pipeline_trace.py --url "https://example.com/article" --claim-index 0

Output:
    Creates docs/investigations/traces/{timestamp}/ with:
    - claims.json: Extracted claims with entities
    - queries.json: Generated search queries per claim
    - evidence_raw.json: All retrieved evidence before filtering
    - evidence_ranked.json: Evidence after semantic ranking
    - evidence_filtered.json: Evidence after all filters
    - evidence_displayed.json: Final evidence shown to user
    - verdict.json: Final verdicts and confidence
    - trace_summary.md: Human-readable summary
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings


async def trace_pipeline(url: str, claim_index: Optional[int] = None) -> Dict[str, Any]:
    """
    Trace a URL through the pipeline, capturing artifacts at each stage.
    """
    from app.pipeline.ingest import UrlIngester
    from app.pipeline.extract import ClaimExtractor
    from app.pipeline.retrieve import EvidenceRetriever
    from app.pipeline.judge import ClaimJudge
    from app.utils.article_classifier import classify_article
    from app.utils.query_planner import LLMQueryPlanner

    trace = {
        "url": url,
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "SEMANTIC_SIMILARITY_THRESHOLD": settings.SEMANTIC_SIMILARITY_THRESHOLD,
            "SOURCE_CREDIBILITY_THRESHOLD": settings.SOURCE_CREDIBILITY_THRESHOLD,
            "ENABLE_CROSS_ENCODER_RERANK": settings.ENABLE_CROSS_ENCODER_RERANK,
            "ENABLE_EVIDENCE_RELEVANCE_FILTER": settings.ENABLE_EVIDENCE_RELEVANCE_FILTER,
            "PASS_NLI_VERDICT_TO_JUDGE": settings.PASS_NLI_VERDICT_TO_JUDGE,
        },
        "stages": {}
    }

    print(f"\n{'='*60}")
    print(f"PIPELINE TRACE: {url}")
    print(f"{'='*60}\n")

    # Stage 1: Ingest
    print("[1/7] INGEST - Fetching content...")
    try:
        ingester = UrlIngester()
        ingest_result = await ingester.ingest(url)
        if not ingest_result.get("success"):
            print(f"  ERROR: {ingest_result.get('error')}")
            return trace

        trace["stages"]["ingest"] = {
            "success": True,
            "content_length": len(ingest_result.get("content", "")),
            "title": ingest_result.get("metadata", {}).get("title"),
        }
        content = ingest_result.get("content", "")
        metadata = ingest_result.get("metadata", {})
        print(f"  Content: {len(content)} chars")
        print(f"  Title: {metadata.get('title', 'N/A')[:60]}...")
    except Exception as e:
        print(f"  ERROR: {e}")
        trace["stages"]["ingest"] = {"success": False, "error": str(e)}
        return trace

    # Stage 2: Extract Claims
    print("\n[2/7] EXTRACT - Extracting claims...")
    try:
        extractor = ClaimExtractor()
        extract_result = await extractor.extract_claims(content, metadata)
        claims = extract_result.get("claims", [])

        trace["stages"]["extract"] = {
            "claim_count": len(claims),
            "claims": [
                {
                    "position": c.get("position"),
                    "text": c.get("text"),
                    "confidence": c.get("confidence"),
                    "key_entities": c.get("key_entities", []),
                    "temporal_markers": c.get("temporal_markers", []),
                }
                for c in claims
            ]
        }
        print(f"  Extracted {len(claims)} claims")
        for i, c in enumerate(claims[:3]):
            print(f"  [{i}] {c.get('text', '')[:80]}...")
    except Exception as e:
        print(f"  ERROR: {e}")
        trace["stages"]["extract"] = {"success": False, "error": str(e)}
        return trace

    # Stage 3: Classify Article
    print("\n[3/7] CLASSIFY - Classifying article domain...")
    try:
        classification = await classify_article(
            title=metadata.get("title", ""),
            url=url,
            content=content[:2000]
        )
        trace["stages"]["classify"] = {
            "primary_domain": classification.primary_domain,
            "jurisdiction": classification.jurisdiction,
            "confidence": classification.confidence,
        }
        print(f"  Domain: {classification.primary_domain}")
        print(f"  Jurisdiction: {classification.jurisdiction}")

        # Attach to claims
        for claim in claims:
            claim["article_classification"] = classification.to_dict()
    except Exception as e:
        print(f"  WARNING: Classification failed: {e}")
        trace["stages"]["classify"] = {"success": False, "error": str(e)}

    # If specific claim requested, filter
    if claim_index is not None:
        if claim_index < len(claims):
            claims = [claims[claim_index]]
            print(f"\n  Tracing only claim [{claim_index}]: {claims[0].get('text', '')[:60]}...")
        else:
            print(f"  ERROR: Claim index {claim_index} out of range (0-{len(claims)-1})")
            return trace

    # Stage 4: Query Planning
    print("\n[4/7] PLAN - Generating search queries...")
    try:
        query_planner = LLMQueryPlanner()
        query_plans = await query_planner.plan_queries_batch(claims)

        trace["stages"]["plan"] = {
            "plans": [
                {
                    "claim_index": p.get("claim_index"),
                    "claim_type": p.get("claim_type"),
                    "queries": p.get("queries", []),
                    "freshness": p.get("freshness"),
                    "priority_sources": p.get("priority_sources", []),
                }
                for p in query_plans
            ]
        }
        print(f"  Generated {len(query_plans)} query plans")
        for p in query_plans[:2]:
            print(f"  Claim {p.get('claim_index')}: {p.get('queries', [])}")
    except Exception as e:
        print(f"  WARNING: Query planning failed: {e}")
        trace["stages"]["plan"] = {"success": False, "error": str(e)}
        query_plans = []

    # Stage 5: Retrieve Evidence
    print("\n[5/7] RETRIEVE - Fetching evidence...")
    try:
        retriever = EvidenceRetriever()
        evidence_by_claim = {}
        raw_evidence_by_claim = {}

        for i, claim in enumerate(claims):
            position = str(claim.get("position", i))
            print(f"\n  Claim [{position}]: {claim.get('text', '')[:60]}...")

            # Get raw evidence (before filtering)
            result = await retriever.retrieve_evidence_for_claim(
                claim,
                source_url=url,
                track_raw_evidence=True
            )

            if isinstance(result, dict) and "evidence" in result:
                evidence_by_claim[position] = result["evidence"]
                raw_evidence_by_claim[position] = result.get("raw_evidence", [])
            else:
                evidence_by_claim[position] = result if isinstance(result, list) else []

            ev_count = len(evidence_by_claim.get(position, []))
            raw_count = len(raw_evidence_by_claim.get(position, []))
            print(f"    Retrieved: {raw_count} raw → {ev_count} filtered")

        trace["stages"]["retrieve"] = {
            "evidence_by_claim": {
                pos: [
                    {
                        "source": e.get("source"),
                        "title": e.get("title", "")[:60],
                        "url": e.get("url"),
                        "semantic_similarity": e.get("semantic_similarity"),
                        "credibility_score": e.get("credibility_score"),
                        "final_score": e.get("final_score"),
                        "external_source_provider": e.get("external_source_provider"),
                    }
                    for e in evidence[:10]
                ]
                for pos, evidence in evidence_by_claim.items()
            },
            "raw_evidence_by_claim": {
                pos: [
                    {
                        "source": e.get("source"),
                        "url": e.get("url"),
                        "is_included": e.get("is_included"),
                        "filter_stage": e.get("filter_stage"),
                        "filter_reason": e.get("filter_reason"),
                        "semantic_similarity": e.get("relevance_score"),
                    }
                    for e in raw[:20]
                ]
                for pos, raw in raw_evidence_by_claim.items()
            }
        }
    except Exception as e:
        print(f"  ERROR: Evidence retrieval failed: {e}")
        trace["stages"]["retrieve"] = {"success": False, "error": str(e)}
        return trace

    # Stage 6: Judge (without NLI since it's bypassed)
    print("\n[6/7] JUDGE - Making verdicts...")
    try:
        judge = ClaimJudge()
        await judge.initialize()

        verdicts = []
        for i, claim in enumerate(claims):
            position = str(claim.get("position", i))
            evidence = evidence_by_claim.get(position, [])

            # Empty verification signals (NLI bypassed)
            verification_signals = {
                "overall_verdict": "uncertain",
                "confidence": 0.0,
                "supporting_count": 0,
                "contradicting_count": 0,
                "neutral_count": 0,
                "total_evidence": len(evidence),
            }

            result = await judge.judge_claim(claim, verification_signals, evidence)

            verdict_data = {
                "claim_text": claim.get("text"),
                "verdict": result.verdict,
                "confidence": result.confidence,
                "rationale": result.rationale,
                "evidence_displayed": [
                    {
                        "source": e.get("source"),
                        "title": e.get("title", "")[:60],
                        "semantic_similarity": e.get("semantic_similarity"),
                        "snippet": e.get("snippet", "")[:100],
                    }
                    for e in result.supporting_evidence
                ],
                "evidence_count_available": len(evidence),
                "evidence_count_displayed": len(result.supporting_evidence),
            }
            verdicts.append(verdict_data)

            print(f"\n  Claim [{position}]: {result.verdict} ({result.confidence}%)")
            print(f"    Evidence shown: {len(result.supporting_evidence)}/{len(evidence)}")
            for j, e in enumerate(result.supporting_evidence):
                sim = e.get("semantic_similarity", "N/A")
                print(f"      [{j}] {e.get('source')} (sim={sim})")

        trace["stages"]["judge"] = {"verdicts": verdicts}
    except Exception as e:
        print(f"  ERROR: Judgment failed: {e}")
        trace["stages"]["judge"] = {"success": False, "error": str(e)}

    # Stage 7: Analysis
    print("\n[7/7] ANALYSIS - Identifying issues...")
    issues = []

    for verdict in trace["stages"].get("judge", {}).get("verdicts", []):
        displayed = verdict.get("evidence_displayed", [])
        for ev in displayed:
            sim = ev.get("semantic_similarity")
            if sim is not None and sim < 0.50:
                issues.append({
                    "type": "low_similarity_displayed",
                    "claim": verdict.get("claim_text", "")[:60],
                    "evidence": ev.get("source"),
                    "similarity": sim,
                    "concern": f"Evidence shown with only {sim:.2f} similarity"
                })

    trace["analysis"] = {
        "issues_found": len(issues),
        "issues": issues,
    }

    if issues:
        print(f"\n  Found {len(issues)} potential issues:")
        for issue in issues[:5]:
            print(f"    - {issue['concern']}")
    else:
        print("  No obvious issues detected")

    return trace


def save_trace(trace: Dict[str, Any], output_dir: Optional[str] = None):
    """Save trace artifacts to files."""
    if output_dir is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent.parent / "docs" / "investigations" / "traces" / timestamp

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full trace as JSON
    with open(output_dir / "trace_full.json", "w") as f:
        json.dump(trace, f, indent=2, default=str)

    # Save individual stage files
    for stage_name, stage_data in trace.get("stages", {}).items():
        with open(output_dir / f"{stage_name}.json", "w") as f:
            json.dump(stage_data, f, indent=2, default=str)

    # Create summary markdown
    summary = generate_summary(trace)
    with open(output_dir / "trace_summary.md", "w") as f:
        f.write(summary)

    print(f"\n{'='*60}")
    print(f"Trace saved to: {output_dir}")
    print(f"{'='*60}")


def generate_summary(trace: Dict[str, Any]) -> str:
    """Generate human-readable summary of trace."""
    lines = [
        "# Pipeline Trace Summary",
        "",
        f"**URL:** {trace.get('url')}",
        f"**Timestamp:** {trace.get('timestamp')}",
        "",
        "## Configuration",
        "```",
        json.dumps(trace.get("config", {}), indent=2),
        "```",
        "",
        "## Stages",
        "",
    ]

    stages = trace.get("stages", {})

    # Extract
    if "extract" in stages:
        lines.append("### Extract")
        lines.append(f"- Claims extracted: {stages['extract'].get('claim_count', 0)}")
        for c in stages["extract"].get("claims", [])[:3]:
            lines.append(f"- [{c.get('position')}] {c.get('text', '')[:80]}...")
            if c.get("key_entities"):
                lines.append(f"  - Entities: {', '.join(c.get('key_entities', []))}")
        lines.append("")

    # Classify
    if "classify" in stages:
        lines.append("### Classify")
        lines.append(f"- Domain: {stages['classify'].get('primary_domain')}")
        lines.append(f"- Jurisdiction: {stages['classify'].get('jurisdiction')}")
        lines.append("")

    # Retrieve
    if "retrieve" in stages:
        lines.append("### Retrieve")
        for pos, evidence in stages["retrieve"].get("evidence_by_claim", {}).items():
            lines.append(f"\n**Claim {pos}:**")
            lines.append("| Source | Similarity | Credibility | API |")
            lines.append("|--------|------------|-------------|-----|")
            for e in evidence[:5]:
                sim = e.get("semantic_similarity", "N/A")
                cred = e.get("credibility_score", "N/A")
                api = e.get("external_source_provider", "")
                lines.append(f"| {e.get('source', 'Unknown')[:20]} | {sim} | {cred} | {api} |")
        lines.append("")

    # Judge
    if "judge" in stages:
        lines.append("### Judge")
        for v in stages["judge"].get("verdicts", []):
            lines.append(f"\n**Claim:** {v.get('claim_text', '')[:60]}...")
            lines.append(f"- Verdict: **{v.get('verdict')}** ({v.get('confidence')}%)")
            lines.append(f"- Evidence displayed: {v.get('evidence_count_displayed')}/{v.get('evidence_count_available')}")
            lines.append("\nDisplayed evidence:")
            for e in v.get("evidence_displayed", []):
                sim = e.get("semantic_similarity", "N/A")
                lines.append(f"- {e.get('source')}: similarity={sim}")
        lines.append("")

    # Analysis
    if "analysis" in trace:
        lines.append("## Issues Detected")
        issues = trace["analysis"].get("issues", [])
        if issues:
            for issue in issues:
                lines.append(f"- **{issue.get('type')}**: {issue.get('concern')}")
        else:
            lines.append("No obvious issues detected.")
        lines.append("")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="Trace URL through verification pipeline")
    parser.add_argument("--url", required=True, help="URL to trace")
    parser.add_argument("--claim-index", type=int, help="Trace only this claim index")
    parser.add_argument("--output", help="Output directory (default: auto-generated)")
    args = parser.parse_args()

    trace = await trace_pipeline(args.url, args.claim_index)
    save_trace(trace, args.output)


if __name__ == "__main__":
    asyncio.run(main())
