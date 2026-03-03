"""Extract mapping audit cases from the database.

Queries completed checks, builds frozen case files with stratified sampling
for human review of mapping quality failure modes.

Usage:
    # Stratified sample: prioritise disputed/unresolved, 3+ elements, 6+ evidence
    python scripts/audit_extract.py --sample 20

    # Extract specific check
    python scripts/audit_extract.py --check-id UUID

    # Filters
    python scripts/audit_extract.py --sample 20 --min-elements 3 --min-evidence 6

    # Dry-run with synthetic data (no DB required)
    python scripts/audit_extract.py --synthetic --sample 3

Output:
    audit/track-n/audit/cases/case-{NNN}.json     — frozen case files
    audit/track-n/audit/judgments/case-{NNN}.json  — pre-populated review templates
"""

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from scripts.eval_mapping_model import (
    SYNTHETIC_CLAIMS,
    build_mapping_prompt,
)

logger = logging.getLogger(__name__)

AUDIT_DIR = backend_dir / "audit" / "track-n" / "audit"
CASES_DIR = AUDIT_DIR / "cases"
JUDGMENTS_DIR = AUDIT_DIR / "judgments"

# Failure mode codes
VALID_FAILURE_MODES = {"A", "B", "C", "D"}

# Snippet length matching production (claim_map_analyzer.py)
DEFAULT_SNIPPET_LENGTH = 400


# ---------------------------------------------------------------------------
# Stratified sampling
# ---------------------------------------------------------------------------


def score_claim_for_audit(claim: Dict[str, Any]) -> int:
    """Score a claim for audit priority via stratified sampling.

    Higher score = more interesting for failure mode discovery.
    +2 if has disputed/unresolved element
    +1 if 3+ elements
    +1 if 6+ evidence items
    """
    score = 0
    elements = claim.get("elements", [])
    evidence = claim.get("evidence", [])

    # Check for disputed/unresolved elements in the original claim_map
    original_cm = claim.get("original_claim_map", {})
    if original_cm:
        for elem in original_cm.get("elements", []):
            state = elem.get("state", "")
            if isinstance(state, str) and state in ("disputed", "unresolved"):
                score += 2
                break

    # Complexity signals
    if len(elements) >= 3:
        score += 1
    if len(evidence) >= 6:
        score += 1

    return score


def stratified_sample(
    claims: List[Dict[str, Any]],
    n: int,
    min_elements: int = 0,
    min_evidence: int = 0,
) -> List[Dict[str, Any]]:
    """Select top-N claims by audit priority score, with optional filters."""
    filtered = claims
    if min_elements > 0:
        filtered = [c for c in filtered if len(c.get("elements", [])) >= min_elements]
    if min_evidence > 0:
        filtered = [c for c in filtered if len(c.get("evidence", [])) >= min_evidence]

    scored = [(score_claim_for_audit(c), c) for c in filtered]
    scored.sort(key=lambda x: x[0], reverse=True)

    selected = [c for _, c in scored[:n]]

    # Log stratification breakdown
    score_counts = {}
    for s, _ in scored[:n]:
        score_counts[s] = score_counts.get(s, 0) + 1
    logger.info(f"Stratification: {len(filtered)} eligible, selected {len(selected)}")
    for s in sorted(score_counts.keys(), reverse=True):
        logger.info(f"  score={s}: {score_counts[s]} claims")

    return selected


# ---------------------------------------------------------------------------
# Case file construction
# ---------------------------------------------------------------------------


def build_case_file(
    claim: Dict[str, Any],
    case_number: int,
    snippet_length: int = DEFAULT_SNIPPET_LENGTH,
) -> Dict[str, Any]:
    """Build a frozen case file from a claim dict."""
    original_cm = claim.get("original_claim_map", {})
    elements = claim.get("elements", [])
    evidence = claim.get("evidence", [])

    # Compute prompt hash for reproducibility
    prompt = build_mapping_prompt(
        normalised_claim=claim.get("normalised_claim", ""),
        elements=elements,
        evidence_list=evidence,
        snippet_length=snippet_length,
    )
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:12]

    # Determine model from metadata
    metadata = original_cm.get("metadata", {})
    model = metadata.get("mapping_model", "unknown")

    # Build evidence list with full_text + mapper_window
    evidence_items = []
    for ev in evidence:
        full_text = ev.get("snippet") or ev.get("text") or ""
        mapper_window = full_text[:snippet_length]
        evidence_items.append(
            {
                "evidence_id": ev.get("evidence_id", "unknown"),
                "title": ev.get("title", ""),
                "full_text": full_text,
                "mapper_window": mapper_window,
                "tier": ev.get("tier"),
                "evidence_type": ev.get("evidence_type"),
                "llm_relevance_score": ev.get("llm_relevance_score"),
                "classification_method": ev.get("classification_method"),
                "source": ev.get("source", ""),
                "url": ev.get("url", ""),
            }
        )

    # Build mapper_output from the original claim_map
    mapper_elements = []
    for elem in original_cm.get("elements", []):
        refs = []
        for ref in elem.get("evidence_refs", []):
            ref_entry = {
                "evidence_id": ref.get("evidence_id", ""),
                "relationship": ref.get("relationship", ""),
            }
            # Handle EvidenceRelationship enum
            rel = ref_entry["relationship"]
            if hasattr(rel, "value"):
                ref_entry["relationship"] = rel.value
            reasoning = ref.get("reasoning")
            ref_entry["reasoning"] = reasoning
            refs.append(ref_entry)

        state = elem.get("state", "unresolved")
        if hasattr(state, "value"):
            state = state.value

        mapper_elements.append(
            {
                "element_id": elem.get("element_id", ""),
                "evidence_refs": refs,
                "state": state,
                "uncertainty": elem.get("uncertainty"),
            }
        )

    case_id = f"case-{case_number:03d}"
    return {
        "case_id": case_id,
        "source": {
            "check_id": claim.get("check_id"),
            "claim_id": claim.get("claim_id"),
            "claim_position": claim.get("position", 0),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        },
        "claim": {
            "normalised_claim": claim.get("normalised_claim", ""),
            "claim_type": _extract_claim_type(original_cm),
            "elements": [
                {"element_id": e["element_id"], "description": e["description"]}
                for e in elements
            ],
        },
        "evidence": evidence_items,
        "mapper_output": {
            "model": model,
            "prompt_hash": prompt_hash,
            "elements": mapper_elements,
        },
    }


def _extract_claim_type(claim_map: Dict[str, Any]) -> str:
    """Extract claim_type as a string from a claim_map."""
    ct = claim_map.get("claim_type", "empirical")
    if hasattr(ct, "value"):
        return ct.value
    return str(ct) if ct else "empirical"


# ---------------------------------------------------------------------------
# Judgment template construction
# ---------------------------------------------------------------------------


def build_judgment_template(case: Dict[str, Any]) -> Dict[str, Any]:
    """Build a pre-populated judgment template from a case file."""
    case_id = case["case_id"]

    ref_judgments = []
    state_judgments = []

    for elem in case["mapper_output"]["elements"]:
        eid = elem["element_id"]

        # Pre-populate ref_judgments from mapper's evidence_refs
        for ref in elem.get("evidence_refs", []):
            ref_judgments.append(
                {
                    "element_id": eid,
                    "evidence_id": ref.get("evidence_id", ""),
                    "mapper_relationship": ref.get("relationship", ""),
                    "mapper_reasoning": ref.get("reasoning", ""),
                    "correct": None,
                    "expected_relationship": None,
                    "failure_mode": None,
                    "window_sufficient": None,
                    "notes": "",
                }
            )

        # Pre-populate state_judgments
        state_judgments.append(
            {
                "element_id": eid,
                "mapper_state": elem.get("state", "unresolved"),
                "correct": None,
                "expected_state": None,
                "failure_mode": None,
                "notes": "",
            }
        )

    return {
        "case_id": case_id,
        "reviewed_at": None,
        "ref_judgments": ref_judgments,
        "missing_refs": [],
        "state_judgments": state_judgments,
    }


# ---------------------------------------------------------------------------
# DB loading (async, reuses pattern from eval_mapping_model.py)
# ---------------------------------------------------------------------------


async def load_claims_for_audit(
    limit: int = 50,
    check_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load claims with evidence from the database for audit extraction."""
    from app.core.config import settings
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    db_url = getattr(settings, "DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL not configured")

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)

    # Base query for claims with claim_maps
    if check_id:
        query = text(
            """
            SELECT
                c.id AS claim_id,
                c.check_id,
                c.text AS claim_text,
                c.claim_map,
                c.position
            FROM claim c
            JOIN "check" ch ON c.check_id = ch.id
            WHERE ch.id = :check_id
              AND c.claim_map IS NOT NULL
              AND json_array_length(c.claim_map->'elements') > 0
            ORDER BY c.position
        """
        )
        params = {"check_id": check_id}
    else:
        query = text(
            """
            SELECT
                c.id AS claim_id,
                c.check_id,
                c.text AS claim_text,
                c.claim_map,
                c.position
            FROM claim c
            JOIN "check" ch ON c.check_id = ch.id
            WHERE ch.status = 'completed'
              AND c.claim_map IS NOT NULL
              AND json_array_length(c.claim_map->'elements') > 0
            ORDER BY ch.completed_at DESC
            LIMIT :limit
        """
        )
        params = {"limit": limit}

    claims = []
    async with engine.connect() as conn:
        # Check which provenance columns exist (M-01 may not be migrated yet)
        col_check = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'evidence' "
                "AND column_name IN ('llm_relevance_score', 'classification_method')"
            )
        )
        has_provenance = len(col_check.fetchall()) > 0

        if has_provenance:
            evidence_query = text(
                "SELECT e.evidence_id, e.source, e.url, e.title, e.snippet, "
                "e.relevance_score, e.tier, e.evidence_type, "
                "e.llm_relevance_score, e.classification_method "
                "FROM evidence e WHERE e.claim_id = :claim_id "
                "AND e.receipt_status = 'shown' ORDER BY e.relevance_score DESC"
            )
        else:
            evidence_query = text(
                "SELECT e.evidence_id, e.source, e.url, e.title, e.snippet, "
                "e.relevance_score, e.tier, e.evidence_type "
                "FROM evidence e WHERE e.claim_id = :claim_id "
                "AND e.receipt_status = 'shown' ORDER BY e.relevance_score DESC"
            )
        result = await conn.execute(query, params)
        rows = result.fetchall()

        for row in rows:
            claim_map = row.claim_map
            if not claim_map or not claim_map.get("elements"):
                continue

            ev_result = await conn.execute(evidence_query, {"claim_id": row.claim_id})
            ev_rows = ev_result.fetchall()

            evidence_list = []
            for ev in ev_rows:
                ev_dict = {
                    "evidence_id": ev.evidence_id,
                    "title": ev.title or "",
                    "text": ev.snippet or "",
                    "snippet": ev.snippet or "",
                    "source": ev.source or "",
                    "url": ev.url or "",
                    "tier": ev.tier,
                    "evidence_type": ev.evidence_type,
                    "relevance_score": float(ev.relevance_score or 0),
                    "llm_relevance_score": (
                        ev.llm_relevance_score if has_provenance else None
                    ),
                    "classification_method": (
                        ev.classification_method if has_provenance else None
                    ),
                }
                evidence_list.append(ev_dict)

            claims.append(
                {
                    "claim_id": row.claim_id,
                    "check_id": row.check_id,
                    "position": row.position,
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


def load_synthetic_claims() -> List[Dict[str, Any]]:
    """Build audit-compatible claims from synthetic fixture data."""
    claims = []
    for sc in SYNTHETIC_CLAIMS:
        # Build a fake original_claim_map with elements having states
        elements = []
        for i, elem in enumerate(sc["elements"], start=1):
            elements.append(
                {
                    "element_id": f"e{i}",
                    "description": elem["description"],
                    "evidence_refs": [
                        {
                            "evidence_id": ev["evidence_id"],
                            "relationship": "supports",
                            "reasoning": f"Synthetic ref for {elem['element_id']}",
                        }
                        for ev in sc["evidence"][:2]
                    ],
                    "state": "supported" if i == 1 else "disputed",
                    "uncertainty": None,
                }
            )

        claims.append(
            {
                "claim_id": sc["claim_id"],
                "check_id": f"check-{sc['claim_id']}",
                "position": 0,
                "normalised_claim": sc["normalised_claim"],
                "elements": [
                    {"element_id": e["element_id"], "description": e["description"]}
                    for e in elements
                ],
                "evidence": sc["evidence"],
                "original_claim_map": {
                    "claim_id": sc["claim_id"],
                    "normalised_claim": sc["normalised_claim"],
                    "claim_type": "empirical",
                    "elements": elements,
                    "orientation": None,
                    "metadata": {
                        "decomposition_model": "synthetic",
                        "mapping_model": "synthetic",
                        "element_count": len(elements),
                        "completed_at": None,
                    },
                },
            }
        )
    return claims


# ---------------------------------------------------------------------------
# Main extraction pipeline
# ---------------------------------------------------------------------------


def extract_cases(
    claims: List[Dict[str, Any]],
    start_number: int = 1,
    snippet_length: int = DEFAULT_SNIPPET_LENGTH,
) -> List[Dict[str, Any]]:
    """Build case files and judgment templates from claims.

    Returns list of (case, judgment) pairs.
    """
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    JUDGMENTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for i, claim in enumerate(claims):
        case_num = start_number + i
        case = build_case_file(claim, case_num, snippet_length=snippet_length)
        judgment = build_judgment_template(case)

        # Write case file
        case_path = CASES_DIR / f"{case['case_id']}.json"
        with open(case_path, "w", encoding="utf-8") as f:
            json.dump(case, f, indent=2, default=str)

        # Write judgment template
        judgment_path = JUDGMENTS_DIR / f"{case['case_id']}.json"
        with open(judgment_path, "w", encoding="utf-8") as f:
            json.dump(judgment, f, indent=2, default=str)

        results.append({"case": case, "judgment": judgment})
        logger.info(
            f"  {case['case_id']}: "
            f"{len(case['evidence'])} evidence, "
            f"{len(case['mapper_output']['elements'])} elements"
        )

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Extract mapping audit cases from the database"
    )
    parser.add_argument("--sample", type=int, help="Stratified sample of N claims")
    parser.add_argument(
        "--check-id", type=str, help="Extract all claims from a specific check"
    )
    parser.add_argument(
        "--synthetic", action="store_true", help="Use synthetic fixture data"
    )

    parser.add_argument(
        "--min-elements", type=int, default=0, help="Minimum elements per claim"
    )
    parser.add_argument(
        "--min-evidence", type=int, default=0, help="Minimum evidence items per claim"
    )
    parser.add_argument(
        "--start-number", type=int, default=1, help="Starting case number (default: 1)"
    )
    parser.add_argument(
        "--snippet-length",
        type=int,
        default=DEFAULT_SNIPPET_LENGTH,
        help="Snippet truncation length",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.synthetic and not args.check_id and not args.sample:
        parser.error("One of --synthetic, --check-id, or --sample is required")

    # Load claims
    if args.synthetic:
        claims = load_synthetic_claims()
        print(f"Loaded {len(claims)} synthetic claims")
    elif args.check_id:
        claims = asyncio.run(load_claims_for_audit(check_id=args.check_id))
        print(f"Loaded {len(claims)} claims from check {args.check_id}")
    else:
        # Load more than needed for stratified sampling
        claims = asyncio.run(load_claims_for_audit(limit=args.sample * 3))
        print(f"Loaded {len(claims)} claims from database")
        claims = stratified_sample(
            claims,
            n=args.sample,
            min_elements=args.min_elements,
            min_evidence=args.min_evidence,
        )
        print(f"Selected {len(claims)} claims after stratified sampling")

    if not claims:
        print("No claims to extract. Exiting.")
        return

    # If synthetic, still respect --sample
    if args.synthetic and args.sample:
        claims = claims[: args.sample]

    # Determine start number from existing cases
    start = args.start_number
    existing = list(CASES_DIR.glob("case-*.json"))
    if existing:
        max_existing = max(int(p.stem.split("-")[1]) for p in existing)
        start = max(start, max_existing + 1)
        print(f"Found {len(existing)} existing cases, starting at case-{start:03d}")

    # Extract
    results = extract_cases(
        claims,
        start_number=start,
        snippet_length=args.snippet_length,
    )

    print(f"\nExtracted {len(results)} cases to {CASES_DIR}")
    print(f"Judgment templates written to {JUDGMENTS_DIR}")


if __name__ == "__main__":
    main()
