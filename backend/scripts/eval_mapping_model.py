"""Mapping model evaluation harness — Option A gating question.

Runs the same mapping prompt through two models (Gemini Flash-Lite and GPT-4o)
on identical inputs and records structured results for human scoring.

Usage:
    # With real DB data (requires DATABASE_URL):
    python scripts/eval_mapping_model.py --from-db --limit 25

    # With pre-captured claims JSON:
    python scripts/eval_mapping_model.py --from-file audit/track-n/evaluation/claims.json

    # With synthetic fixture data (for testing the harness itself):
    python scripts/eval_mapping_model.py --synthetic

    # Dry-run (build prompts only, no LLM calls):
    python scripts/eval_mapping_model.py --synthetic --dry-run

Output:
    audit/track-n/evaluation/
        claims.json               # Input claims + evidence (frozen for reproducibility)
        results_flash_lite.json   # Per-claim raw + parsed mapper output
        results_gpt4o.json        # Per-claim raw + parsed mapper output
        scoring_sheet.json        # Template for human scoring (pre-filled with stubs)
        prompts/                  # One .txt per claim (the exact prompt sent)
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.pipeline.claim_map_analyzer import (
    MAPPING_PROMPT,
    ClaimMapAnalyzer,
    _VALID_RELATIONSHIPS,
    _VALID_STATES,
)
from app.models.claim_map import (
    ElementState,
    EvidenceRef,
    EvidenceRelationship,
)

logger = logging.getLogger(__name__)

EVAL_DIR = backend_dir / "audit" / "track-n" / "evaluation"
PROMPTS_DIR = EVAL_DIR / "prompts"


# ---------------------------------------------------------------------------
# Synthetic fixture data (for testing the harness without DB or live LLMs)
# ---------------------------------------------------------------------------

SYNTHETIC_CLAIMS = [
    {
        "claim_id": "eval-001",
        "normalised_claim": "UK GDP grew by 0.5% in Q3 2025",
        "elements": [
            {"element_id": "e1", "description": "UK GDP grew in Q3 2025"},
            {"element_id": "e2", "description": "The growth rate was 0.5%"},
        ],
        "evidence": [
            {
                "evidence_id": "ev-001",
                "title": "ONS GDP Estimate - Q3 2025",
                "text": "The Office for National Statistics estimates that UK gross domestic product grew by 0.1% in Quarter 3 2025, following growth of 0.5% in Quarter 2. The services sector was the main contributor to growth.",
                "snippet": "The Office for National Statistics estimates that UK gross domestic product grew by 0.1% in Quarter 3 2025, following growth of 0.5% in Quarter 2.",
                "source": "ons.gov.uk",
                "url": "https://ons.gov.uk/gdp/q3-2025",
                "tier": "primary",
                "evidence_type": "data",
                "relevance_score": 0.95,
            },
            {
                "evidence_id": "ev-002",
                "title": "UK economy shows resilience despite headwinds",
                "text": "Britain's economy continued to expand in the third quarter according to preliminary data, though at a slower pace than previously. Analysts had expected growth of around 0.3 per cent.",
                "snippet": "Britain's economy continued to expand in the third quarter according to preliminary data, though at a slower pace than previously.",
                "source": "ft.com",
                "url": "https://ft.com/content/uk-economy-q3",
                "tier": "reporting",
                "evidence_type": "news_reporting",
                "relevance_score": 0.80,
            },
            {
                "evidence_id": "ev-003",
                "title": "Why the UK economy is still underperforming",
                "text": "Commentators have noted that while GDP is growing, the pace remains below trend. Some attribute this to persistent supply-side constraints and weak business investment.",
                "snippet": "Commentators have noted that while GDP is growing, the pace remains below trend.",
                "source": "economist.com",
                "url": "https://economist.com/uk-underperformance",
                "tier": "commentary",
                "evidence_type": "analysis",
                "relevance_score": 0.55,
            },
        ],
    },
    {
        "claim_id": "eval-002",
        "normalised_claim": "The Amazon rainforest lost 10,000 square kilometres of tree cover in 2024",
        "elements": [
            {
                "element_id": "e1",
                "description": "The Amazon rainforest experienced tree cover loss in 2024",
            },
            {
                "element_id": "e2",
                "description": "The amount of tree cover lost was 10,000 square kilometres",
            },
        ],
        "evidence": [
            {
                "evidence_id": "ev-010",
                "title": "INPE Deforestation Alert Data 2024",
                "text": "Brazil's National Institute for Space Research (INPE) recorded 8,453 square kilometres of deforestation alerts in the Legal Amazon region during 2024, a 22% reduction from the previous year's 10,834 sq km.",
                "snippet": "Brazil's National Institute for Space Research (INPE) recorded 8,453 square kilometres of deforestation alerts in the Legal Amazon during 2024.",
                "source": "inpe.br",
                "url": "https://terrabrasilis.dpi.inpe.br/deforestation-2024",
                "tier": "primary",
                "evidence_type": "data",
                "relevance_score": 0.92,
            },
            {
                "evidence_id": "ev-011",
                "title": "Amazon deforestation falls to lowest level in six years",
                "text": "Deforestation in the Brazilian Amazon dropped significantly in 2024, with satellite data showing the lowest annual rate since 2018. Environmental groups cautiously welcomed the decline.",
                "snippet": "Deforestation in the Brazilian Amazon dropped significantly in 2024, with satellite data showing the lowest annual rate since 2018.",
                "source": "reuters.com",
                "url": "https://reuters.com/amazon-deforestation-2024",
                "tier": "reporting",
                "evidence_type": "news_reporting",
                "relevance_score": 0.78,
            },
        ],
    },
    {
        "claim_id": "eval-003",
        "normalised_claim": "Tesla delivered over 2 million vehicles globally in 2024",
        "elements": [
            {
                "element_id": "e1",
                "description": "Tesla made vehicle deliveries globally in 2024",
            },
            {
                "element_id": "e2",
                "description": "The number of deliveries exceeded 2 million",
            },
        ],
        "evidence": [
            {
                "evidence_id": "ev-020",
                "title": "Tesla Q4 and Full Year 2024 Delivery Report",
                "text": "Tesla reported total deliveries of 1,789,226 vehicles for full year 2024, down from 1,808,581 in 2023. This marked the company's first annual delivery decline.",
                "snippet": "Tesla reported total deliveries of 1,789,226 vehicles for full year 2024, down from 1,808,581 in 2023.",
                "source": "ir.tesla.com",
                "url": "https://ir.tesla.com/press-release/q4-2024-deliveries",
                "tier": "primary",
                "evidence_type": "data",
                "relevance_score": 0.98,
            },
            {
                "evidence_id": "ev-021",
                "title": "Electric vehicle market trends 2024",
                "text": "Global EV sales reached new records in 2024, driven by Chinese manufacturers. Tesla remained the single largest EV brand but faced growing competition.",
                "snippet": "Global EV sales reached new records in 2024. Tesla remained the single largest EV brand but faced growing competition.",
                "source": "iea.org",
                "url": "https://iea.org/reports/ev-trends-2024",
                "tier": "reporting",
                "evidence_type": "analysis",
                "relevance_score": 0.45,
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Prompt construction (mirrors claim_map_analyzer.py exactly)
# ---------------------------------------------------------------------------


def build_mapping_prompt(
    normalised_claim: str,
    elements: List[Dict[str, str]],
    evidence_list: List[Dict[str, Any]],
    snippet_length: int = 400,
    include_metadata: bool = False,
) -> str:
    """Build the exact prompt that map_evidence_to_elements() sends to the LLM."""
    elements_desc = "\n".join(
        f"- {e['element_id']}: {e['description']}" for e in elements
    )
    if include_metadata:
        evidence_desc = "\n".join(
            f"- {ev.get('evidence_id', 'unknown')}: "
            f"[{ev.get('title', 'Untitled')}] "
            f"[Tier: {ev.get('tier') or 'unclassified'}] "
            f"[Type: {ev.get('evidence_type') or 'unclassified'}] "
            f"{(ev.get('snippet') or ev.get('text') or '')[:snippet_length]}"
            for ev in evidence_list
        )
    else:
        evidence_desc = "\n".join(
            f"- {ev.get('evidence_id', 'unknown')}: "
            f"[{ev.get('title', 'Untitled')}] "
            f"{(ev.get('snippet') or ev.get('text') or '')[:snippet_length]}"
            for ev in evidence_list
        )
    return (
        f"{MAPPING_PROMPT}\n\n"
        f"Claim: {normalised_claim}\n\n"
        f"Elements:\n{elements_desc}\n\n"
        f"Evidence:\n{evidence_desc}"
    )


# ---------------------------------------------------------------------------
# Model callers (isolated — bypass ClaimMapAnalyzer fallback chain)
# ---------------------------------------------------------------------------


async def call_google_model(
    prompt: str,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    timeout: float = 120,
) -> Dict[str, Any]:
    """Call Google Gemini directly and return raw + parsed response."""
    import httpx

    api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
    if not api_key:
        return {
            "error": "GOOGLE_AI_API_KEY not configured",
            "raw": None,
            "parsed": None,
        }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        },
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            headers={"Content-Type": "application/json"},
            json=body,
        )

    if response.status_code != 200:
        return {
            "error": f"HTTP {response.status_code}",
            "raw": response.text[:500],
            "parsed": None,
        }

    result = response.json()
    usage_meta = result.get("usageMetadata", {})
    usage = {
        "input_tokens": usage_meta.get("promptTokenCount", 0),
        "output_tokens": usage_meta.get("candidatesTokenCount", 0),
    }

    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return {
            "error": f"Parse error: {e}",
            "raw": result,
            "parsed": None,
            "usage": usage,
        }

    return {"error": None, "raw": result, "parsed": parsed, "usage": usage}


async def call_openai_model(
    prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.2,
    max_tokens: int = 4000,
    timeout: float = 30,
) -> Dict[str, Any]:
    """Call OpenAI directly and return raw + parsed response."""
    import httpx

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return {"error": "OPENAI_API_KEY not configured", "raw": None, "parsed": None}

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "system", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
            },
        )

    if response.status_code != 200:
        return {
            "error": f"HTTP {response.status_code}",
            "raw": response.text[:500],
            "parsed": None,
        }

    result = response.json()
    usage_raw = result.get("usage", {})
    usage = {
        "input_tokens": usage_raw.get("prompt_tokens", 0),
        "output_tokens": usage_raw.get("completion_tokens", 0),
    }

    try:
        content = result["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return {
            "error": f"Parse error: {e}",
            "raw": result,
            "parsed": None,
            "usage": usage,
        }

    return {"error": None, "raw": result, "parsed": parsed, "usage": usage}


# ---------------------------------------------------------------------------
# Validation (mirrors _validate_evidence_refs + _parse_mapping_response)
# ---------------------------------------------------------------------------


def validate_mapping_output(
    parsed: Optional[Dict[str, Any]],
    elements: List[Dict[str, str]],
    evidence_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Apply the same validation as ClaimMapAnalyzer._parse_mapping_response().

    Returns a validated result dict with the same shape as a parsed claim_map.
    """
    if parsed is None:
        return {
            "elements": [
                {
                    "element_id": e["element_id"],
                    "evidence_refs": [],
                    "state": "unresolved",
                    "uncertainty": "LLM call failed",
                }
                for e in elements
            ],
            "validation_errors": ["parsed is None"],
        }

    valid_evidence_ids = {
        ev.get("evidence_id") for ev in evidence_list if ev.get("evidence_id")
    }
    raw_elements = parsed.get("elements", [])
    raw_by_id = {e.get("element_id"): e for e in raw_elements}

    validated_elements = []
    validation_errors = []

    for elem in elements:
        eid = elem["element_id"]
        mapped = raw_by_id.get(eid)

        if not mapped:
            validated_elements.append(
                {
                    "element_id": eid,
                    "evidence_refs": [],
                    "state": "unresolved",
                    "uncertainty": None,
                }
            )
            validation_errors.append(f"Element {eid} missing from LLM output")
            continue

        # Validate evidence_refs
        raw_refs = mapped.get("evidence_refs", [])
        valid_refs = []
        for ref in raw_refs:
            ref_eid = ref.get("evidence_id", "")
            rel = ref.get("relationship", "")
            if ref_eid not in valid_evidence_ids:
                validation_errors.append(
                    f"Hallucinated evidence_id: {ref_eid} on element {eid}"
                )
                continue
            if rel not in _VALID_RELATIONSHIPS:
                validation_errors.append(
                    f"Invalid relationship: {rel} on element {eid}"
                )
                continue
            valid_refs.append(
                {
                    "evidence_id": ref_eid,
                    "relationship": rel,
                    "reasoning": ref.get("reasoning") or None,
                }
            )

        # Validate state
        raw_state = mapped.get("state", "unresolved")
        if raw_state not in _VALID_STATES:
            validation_errors.append(
                f"Invalid state '{raw_state}' on element {eid}, defaulting to unresolved"
            )
            raw_state = "unresolved"

        validated_elements.append(
            {
                "element_id": eid,
                "evidence_refs": valid_refs,
                "state": raw_state,
                "uncertainty": mapped.get("uncertainty") or None,
            }
        )

    return {
        "elements": validated_elements,
        "validation_errors": validation_errors,
    }


# ---------------------------------------------------------------------------
# Claim loading
# ---------------------------------------------------------------------------


async def load_claims_from_db(limit: int = 25) -> List[Dict[str, Any]]:
    """Load real claims with evidence from the database."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    db_url = getattr(settings, "DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL not configured")

    # Convert sync URL to async if needed
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)

    query = text(
        """
        SELECT
            c.id AS claim_id,
            c.claim_text,
            c.claim_map,
            c.position,
            ch.status AS check_status
        FROM claim c
        JOIN "check" ch ON c.check_id = ch.id
        WHERE ch.status = 'completed'
          AND c.claim_map IS NOT NULL
          AND jsonb_array_length(c.claim_map->'elements') > 0
        ORDER BY ch.completed_at DESC
        LIMIT :limit
    """
    )

    evidence_query = text(
        """
        SELECT
            e.evidence_id,
            e.source,
            e.url,
            e.title,
            e.snippet,
            e.relevance_score,
            e.tier,
            e.evidence_type
        FROM evidence e
        WHERE e.claim_id = :claim_id
          AND e.receipt_status = 'shown'
        ORDER BY e.relevance_score DESC
    """
    )

    claims = []
    async with engine.connect() as conn:
        result = await conn.execute(query, {"limit": limit})
        rows = result.fetchall()

        for row in rows:
            claim_map = row.claim_map
            if not claim_map or not claim_map.get("elements"):
                continue

            # Load evidence for this claim
            ev_result = await conn.execute(evidence_query, {"claim_id": row.claim_id})
            ev_rows = ev_result.fetchall()

            evidence_list = []
            for ev in ev_rows:
                evidence_list.append(
                    {
                        "evidence_id": ev.evidence_id,
                        "title": ev.title or "",
                        "text": ev.snippet or "",
                        "snippet": ev.snippet or "",
                        "source": ev.source or "",
                        "url": ev.url or "",
                        "tier": ev.tier,
                        "evidence_type": ev.evidence_type,
                        "relevance_score": float(ev.relevance_score or 0),
                    }
                )

            claims.append(
                {
                    "claim_id": row.claim_id,
                    "normalised_claim": claim_map.get(
                        "normalised_claim", row.claim_text or ""
                    ),
                    "elements": [
                        {
                            "element_id": e["element_id"],
                            "description": e.get("description", ""),
                        }
                        for e in claim_map["elements"]
                    ],
                    "evidence": evidence_list,
                    "original_claim_map": claim_map,
                }
            )

    await engine.dispose()
    return claims


def load_claims_from_file(path: str) -> List[Dict[str, Any]]:
    """Load pre-captured claims from a JSON file."""
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Main evaluation runner
# ---------------------------------------------------------------------------


async def run_evaluation(
    claims: List[Dict[str, Any]],
    dry_run: bool = False,
    snippet_length: int = 400,
    include_metadata: bool = False,
) -> None:
    """Run the mapping model evaluation."""

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save frozen claims input
    claims_path = EVAL_DIR / "claims.json"
    with open(claims_path, "w") as f:
        json.dump(claims, f, indent=2, default=str)
    print(f"Saved {len(claims)} claims to {claims_path}")

    results_flash_lite = []
    results_gpt4o = []

    for i, claim in enumerate(claims):
        claim_id = claim["claim_id"]
        print(f"\n[{i+1}/{len(claims)}] Processing claim: {claim_id}")
        print(f"  Claim: {claim['normalised_claim'][:80]}...")
        print(
            f"  Elements: {len(claim['elements'])}, Evidence: {len(claim['evidence'])}"
        )

        # Build the prompt (identical for both models)
        prompt = build_mapping_prompt(
            normalised_claim=claim["normalised_claim"],
            elements=claim["elements"],
            evidence_list=claim["evidence"],
            snippet_length=snippet_length,
            include_metadata=include_metadata,
        )

        # Save prompt for reproducibility
        prompt_path = PROMPTS_DIR / f"{claim_id}.txt"
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)

        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:12]

        if dry_run:
            print(f"  [DRY RUN] Prompt saved ({len(prompt)} chars, hash={prompt_hash})")
            results_flash_lite.append(
                {
                    "claim_id": claim_id,
                    "prompt_hash": prompt_hash,
                    "prompt_length_chars": len(prompt),
                    "dry_run": True,
                }
            )
            results_gpt4o.append(
                {
                    "claim_id": claim_id,
                    "prompt_hash": prompt_hash,
                    "prompt_length_chars": len(prompt),
                    "dry_run": True,
                }
            )
            continue

        # --- Run Flash-Lite ---
        print("  Running gemini-2.5-flash-lite...")
        flash_result = await call_google_model(
            prompt=prompt,
            model="gemini-2.5-flash-lite",
            temperature=0.2,
            max_tokens=4000,
        )

        flash_validated = validate_mapping_output(
            flash_result.get("parsed"),
            claim["elements"],
            claim["evidence"],
        )

        results_flash_lite.append(
            {
                "claim_id": claim_id,
                "normalised_claim": claim["normalised_claim"],
                "elements": claim["elements"],
                "evidence_summary": [
                    {"evidence_id": e["evidence_id"], "title": e.get("title", "")}
                    for e in claim["evidence"]
                ],
                "prompt_hash": prompt_hash,
                "model": "gemini-2.5-flash-lite",
                "error": flash_result.get("error"),
                "usage": flash_result.get("usage"),
                "raw_response": flash_result.get("parsed"),
                "validated": flash_validated,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        if flash_result.get("error"):
            print(f"  Flash-lite error: {flash_result['error']}")
        else:
            states = [e["state"] for e in flash_validated["elements"]]
            ref_counts = [len(e["evidence_refs"]) for e in flash_validated["elements"]]
            print(f"  Flash-lite: states={states}, refs={ref_counts}")
            if flash_validated["validation_errors"]:
                print(
                    f"  Flash-lite validation: {len(flash_validated['validation_errors'])} issues"
                )

        # --- Run GPT-4o ---
        print("  Running gpt-4o...")
        gpt4o_result = await call_openai_model(
            prompt=prompt,
            model="gpt-4o",
            temperature=0.2,
            max_tokens=4000,
        )

        gpt4o_validated = validate_mapping_output(
            gpt4o_result.get("parsed"),
            claim["elements"],
            claim["evidence"],
        )

        results_gpt4o.append(
            {
                "claim_id": claim_id,
                "normalised_claim": claim["normalised_claim"],
                "elements": claim["elements"],
                "evidence_summary": [
                    {"evidence_id": e["evidence_id"], "title": e.get("title", "")}
                    for e in claim["evidence"]
                ],
                "prompt_hash": prompt_hash,
                "model": "gpt-4o",
                "error": gpt4o_result.get("error"),
                "usage": gpt4o_result.get("usage"),
                "raw_response": gpt4o_result.get("parsed"),
                "validated": gpt4o_validated,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        if gpt4o_result.get("error"):
            print(f"  GPT-4o error: {gpt4o_result['error']}")
        else:
            states = [e["state"] for e in gpt4o_validated["elements"]]
            ref_counts = [len(e["evidence_refs"]) for e in gpt4o_validated["elements"]]
            print(f"  GPT-4o:     states={states}, refs={ref_counts}")
            if gpt4o_validated["validation_errors"]:
                print(
                    f"  GPT-4o validation: {len(gpt4o_validated['validation_errors'])} issues"
                )

    # Save results
    flash_path = EVAL_DIR / "results_flash_lite.json"
    with open(flash_path, "w") as f:
        json.dump(results_flash_lite, f, indent=2, default=str)
    print(f"\nSaved flash-lite results to {flash_path}")

    gpt4o_path = EVAL_DIR / "results_gpt4o.json"
    with open(gpt4o_path, "w") as f:
        json.dump(results_gpt4o, f, indent=2, default=str)
    print(f"Saved gpt-4o results to {gpt4o_path}")

    # Generate scoring sheet template
    if not dry_run:
        scoring_sheet = _build_scoring_sheet(results_flash_lite, results_gpt4o)
        scoring_path = EVAL_DIR / "scoring_sheet.json"
        with open(scoring_path, "w") as f:
            json.dump(scoring_sheet, f, indent=2)
        print(f"Saved scoring template to {scoring_path}")

    print(f"\nEvaluation complete. {len(claims)} claims processed.")


def _build_scoring_sheet(
    flash_results: List[Dict], gpt4o_results: List[Dict]
) -> List[Dict]:
    """Build a human scoring template from both result sets."""
    sheet = []

    for flash, gpt4o in zip(flash_results, gpt4o_results):
        if flash.get("dry_run"):
            continue

        claim_id = flash["claim_id"]

        for model_label, result in [
            ("flash_lite", flash),
            ("gpt4o", gpt4o),
        ]:
            validated = result.get("validated", {})
            elements = validated.get("elements", [])

            element_scores = []
            ref_scores = []

            for elem in elements:
                # Per-element state scoring stub
                element_scores.append(
                    {
                        "element_id": elem["element_id"],
                        "assigned_state": elem["state"],
                        "state_score": None,  # correct / overconfident / underconfident / wrong
                        "notes": "",
                    }
                )

                # Per-ref relationship + reasoning scoring stubs
                for ref in elem.get("evidence_refs", []):
                    ref_scores.append(
                        {
                            "element_id": elem["element_id"],
                            "evidence_id": ref["evidence_id"],
                            "assigned_relationship": ref["relationship"],
                            "reasoning_text": ref.get("reasoning", ""),
                            "relationship_score": None,  # correct / defensible / wrong
                            "reasoning_score": None,  # grounded / vague / fabricated
                            "notes": "",
                        }
                    )

            sheet.append(
                {
                    "claim_id": claim_id,
                    "model": model_label,
                    "normalised_claim": result.get("normalised_claim", ""),
                    "element_scores": element_scores,
                    "ref_scores": ref_scores,
                    "coverage_score": None,  # complete / partial / sparse
                    "overall_notes": "",
                }
            )

    return sheet


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Mapping model evaluation harness (Option A)"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from-db",
        action="store_true",
        help="Load claims from the database",
    )
    source.add_argument(
        "--from-file",
        type=str,
        help="Load claims from a JSON file",
    )
    source.add_argument(
        "--synthetic",
        action="store_true",
        help="Use built-in synthetic fixture data",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Number of claims to evaluate (default: 25)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompts only, no LLM calls",
    )
    parser.add_argument(
        "--snippet-length",
        type=int,
        default=400,
        help="Evidence snippet truncation length (default: 400, matching production)",
    )
    parser.add_argument(
        "--include-metadata",
        action="store_true",
        help="Include tier/type metadata in evidence formatting (matches pipeline)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Load claims
    if args.synthetic:
        claims = SYNTHETIC_CLAIMS
        print(f"Using {len(claims)} synthetic claims")
    elif args.from_file:
        claims = load_claims_from_file(args.from_file)
        print(f"Loaded {len(claims)} claims from {args.from_file}")
    elif args.from_db:
        claims = asyncio.run(load_claims_from_db(limit=args.limit))
        print(f"Loaded {len(claims)} claims from database")

    if not claims:
        print("No claims to evaluate. Exiting.")
        return

    # Run evaluation
    asyncio.run(
        run_evaluation(
            claims=claims,
            dry_run=args.dry_run,
            snippet_length=args.snippet_length,
            include_metadata=args.include_metadata,
        )
    )


if __name__ == "__main__":
    main()
