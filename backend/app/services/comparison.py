"""COMPARE tab orchestration: two sources, one model call, three prose fields.

Design: audit/2026-08-26_compare_tab_design.md. The load-bearing rules:

- WE COMPARE POSITIONS, NOT ARTICLES. Full text goes in; a claim-scoped
  position comes out, scoped by the ELEMENT DESCRIPTIONS — never the claim
  text, which carries valence and induces premise adoption (the PARROT
  failure that keeps mapping on a higher model tier).
- ONE call, three jobs. Three separate calls would leave the comparison
  step seeing only the two summaries; one call holds both originals in
  context while writing all three fields.
- THE MODEL WRITES PROSE, THE CODE COMPUTES STRUCTURE. Collisions are a
  pure function of evidence_refs, computed per request, never stored, and
  never delegated to the model.
- The comparison NEVER adjudicates: no credibility, no winner, no verdict
  on the claim. Attributed voice throughout ("The Reuters piece argues…").
- Budget: 3 per check, +1 per re-search (re_search + top_up kinds, minus
  refunds). Cached re-views and produced-nothing failures never count; a
  comparison produced from STORED text counts (real tokens, real result).
- Nothing here writes to Evidence or claim_map — per-evidence
  content_basis is inside the signed manifest payload, and mutating it
  would break /verify/{id} for the check forever.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Claim, ClaimComparison, Evidence, UsageEvent
from app.models.usage_event import KIND_RE_SEARCH, KIND_REFUND, KIND_TOP_UP
from app.services.article_reader import fetch_article_text
from app.services.google_ai import call_google_ai_with_usage

logger = logging.getLogger(__name__)

BASE_BUDGET = 3

# Word caps enforced by instruction; the schema constrains shape, not length.
SUMMARY_WORD_CAP = 90
DIVERGENCE_WORD_CAP = 120

COMPARISON_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summaryA": {"type": "string"},
        "summaryB": {"type": "string"},
        "divergence": {"type": "string"},
    },
    "required": ["summaryA", "summaryB", "divergence"],
}

# In-process guard against a double-click racing itself. The DB unique
# constraint is the cross-process backstop (IntegrityError → serve the
# winner's row as a cache hit).
_pair_locks: Dict[str, asyncio.Lock] = {}


def sorted_pair(evidence_a: str, evidence_b: str) -> Tuple[str, str]:
    """Canonical (sorted) pair key — A/B and B/A are one comparison."""
    return (
        (evidence_a, evidence_b)
        if evidence_a <= evidence_b
        else (
            evidence_b,
            evidence_a,
        )
    )


# ---------------------------------------------------------------------------
# Collisions — pure function, computed on READ, never persisted.
# ---------------------------------------------------------------------------


def compute_collisions(
    claim_map: Optional[dict], evidence_a: str, evidence_b: str
) -> List[Dict[str, Any]]:
    """Element-by-element relationship of the pair, from the LIVE claim map.

    Returns rows {elementId, a, b, verdict} for every element either source
    addresses; an element neither addresses yields no row.

    Verdicts (a sort key — the UI prints the two relationships themselves):
      'opposed'  — exactly {supports, challenges}: the money row.
      'aligned'  — both sides present and not opposed (identical, or a
                   context/directional mix; the printed relationships carry
                   the nuance, no fifth verdict is introduced).
      'only_a' / 'only_b' — one side is silent on the element.
    """
    if not claim_map:
        return []
    rows: List[Dict[str, Any]] = []
    for element in claim_map.get("elements") or []:
        element_id = element.get("element_id") or element.get("elementId")
        rel_a: Optional[str] = None
        rel_b: Optional[str] = None
        for ref in element.get("evidence_refs") or element.get("evidenceRefs") or []:
            ref_id = ref.get("evidence_id") or ref.get("evidenceId")
            relationship = ref.get("relationship")
            if ref_id == evidence_a:
                rel_a = relationship
            elif ref_id == evidence_b:
                rel_b = relationship
        if rel_a is None and rel_b is None:
            continue
        if rel_a is not None and rel_b is not None:
            if {rel_a, rel_b} == {"supports", "challenges"}:
                verdict = "opposed"
            else:
                verdict = "aligned"
        elif rel_a is not None:
            verdict = "only_a"
        else:
            verdict = "only_b"
        rows.append(
            {"elementId": element_id, "a": rel_a, "b": rel_b, "verdict": verdict}
        )
    # Opposed first — it is the money row.
    order = {"opposed": 0, "aligned": 1, "only_a": 2, "only_b": 3}
    rows.sort(key=lambda r: (order.get(r["verdict"], 9), r["elementId"] or ""))
    return rows


# ---------------------------------------------------------------------------
# Budget — the cache is the counter.
# ---------------------------------------------------------------------------


async def get_comparison_budget(session: AsyncSession, check_id: str) -> Dict[str, int]:
    """limit = 3 + re-searches on this check (re_search + top_up − refunds);
    used = stored comparison rows for the check."""
    re_search_count = (
        await session.execute(
            select(func.count())
            .select_from(UsageEvent)
            .where(
                UsageEvent.check_id == check_id,
                UsageEvent.kind.in_([KIND_RE_SEARCH, KIND_TOP_UP]),
            )
        )
    ).scalar_one()
    refund_count = (
        await session.execute(
            select(func.count())
            .select_from(UsageEvent)
            .where(
                UsageEvent.check_id == check_id,
                UsageEvent.kind == KIND_REFUND,
            )
        )
    ).scalar_one()
    used = (
        await session.execute(
            select(func.count())
            .select_from(ClaimComparison)
            .where(ClaimComparison.check_id == check_id)
        )
    ).scalar_one()
    limit = BASE_BUDGET + max(0, re_search_count - refund_count)
    return {"used": used, "limit": limit}


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def build_comparison_prompt(
    element_descriptions: List[str],
    source_a: Dict[str, str],
    source_b: Dict[str, str],
    text_a: str,
    text_b: str,
    basis_a: str,
    basis_b: str,
) -> str:
    """The single-call prompt. Element descriptions scope it; the claim text
    is DELIBERATELY absent (premise adoption)."""
    questions = "\n".join(f"- {d}" for d in element_descriptions if d)
    basis_note_a = (
        ""
        if basis_a == "full"
        else (
            "\nNOTE: this is a stored extract, not the full article — say so "
            "and summarise only what is present."
        )
    )
    basis_note_b = (
        ""
        if basis_b == "full"
        else (
            "\nNOTE: this is a stored extract, not the full article — say so "
            "and summarise only what is present."
        )
    )
    return f"""You are comparing the POSITIONS two sources take on a set of questions. You organise; you never judge.

THE QUESTIONS UNDER EXAMINATION:
{questions}

SOURCE A — {source_a["domain"]} — "{source_a["title"]}"{basis_note_a}
<article_a>
{text_a}
</article_a>

SOURCE B — {source_b["domain"]} — "{source_b["title"]}"{basis_note_b}
<article_b>
{text_b}
</article_b>

Write three fields, in UK English:

1. "summaryA" (max {SUMMARY_WORD_CAP} words): what Source A asserts ON THE QUESTIONS ABOVE, in its own terms, attributed ("The {source_a["domain"]} piece argues…" — never "studies show…"). Ignore parts of the article that do not bear on the questions.

2. "summaryB" (max {SUMMARY_WORD_CAP} words): the same for Source B.

3. "divergence" (max {DIVERGENCE_WORD_CAP} words): where the two positions differ, where they coincide, and what neither addresses. Name the specific point of disagreement, not merely that they disagree.

HARD RULES:
- Never say which source is more credible, better sourced, more convincing, or correct.
- Never state or imply an answer to any of the questions yourself.
- Attribute every assertion to its source.
- If a source does not address the questions at all, say exactly that.
"""


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


class ComparisonError(Exception):
    """code: budget_exhausted | invalid_pair | fetch_failed | model_failed"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(code)


def _stored_text(evidence: Evidence) -> Optional[str]:
    """The pipeline's stored text for an item — the one fallback path."""
    parts = [
        getattr(evidence, "context_before", None) or "",
        evidence.snippet or "",
        getattr(evidence, "context_after", None) or "",
    ]
    text = " ".join(p for p in parts if p).strip()
    return text if len(text) >= 40 else None


async def run_comparison(
    session: AsyncSession,
    check_id: str,
    claim: Claim,
    evidence_a: Evidence,
    evidence_b: Evidence,
) -> Tuple[ClaimComparison, bool]:
    """Create (or serve cached) comparison. Returns (row, cached).

    Raises ComparisonError. Budget rules: a cached hit never counts; a run
    that produces nothing (no usable text on a side, or model failure) never
    counts — nothing is persisted; a run produced from stored text COUNTS.
    """
    ev_a_id = evidence_a.evidence_id or evidence_a.id
    ev_b_id = evidence_b.evidence_id or evidence_b.id
    pair_a, pair_b = sorted_pair(ev_a_id, ev_b_id)
    # Keep A/B as stored: swap the evidence objects to match the sorted key
    # so summary_a always describes evidence_a_id.
    if pair_a != ev_a_id:
        evidence_a, evidence_b = evidence_b, evidence_a

    lock_key = f"{claim.id}:{pair_a}:{pair_b}"
    lock = _pair_locks.setdefault(lock_key, asyncio.Lock())
    async with lock:
        # Cache first — a re-view is free.
        existing = (
            await session.execute(
                select(ClaimComparison).where(
                    ClaimComparison.claim_id == claim.id,
                    ClaimComparison.evidence_a_id == pair_a,
                    ClaimComparison.evidence_b_id == pair_b,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing, True

        budget = await get_comparison_budget(session, check_id)
        if budget["used"] >= budget["limit"]:
            raise ComparisonError("budget_exhausted")

        # Read both sides whole; fall back to stored text, labelled.
        (text_a, basis_a, words_a), (text_b, basis_b, words_b) = await asyncio.gather(
            fetch_article_text(evidence_a.url),
            fetch_article_text(evidence_b.url),
        )
        if basis_a == "failed":
            text_a = _stored_text(evidence_a)
            basis_a, words_a = "stored", None
        if basis_b == "failed":
            text_b = _stored_text(evidence_b)
            basis_b, words_b = "stored", None
        if not text_a or not text_b:
            # Nothing usable on a side → nothing produced, nothing charged.
            raise ComparisonError(
                "fetch_failed", "no usable text for one or both sources"
            )

        claim_map = _claim_map_dict(claim)
        element_descriptions = [
            e.get("description") or ""
            for e in (claim_map.get("elements") if claim_map else []) or []
        ]

        def _domain(url: str) -> str:
            try:
                from urllib.parse import urlparse

                return urlparse(url).hostname.replace("www.", "")
            except Exception:
                return url or "unknown"

        prompt = build_comparison_prompt(
            element_descriptions,
            {"domain": _domain(evidence_a.url), "title": evidence_a.title or ""},
            {"domain": _domain(evidence_b.url), "title": evidence_b.title or ""},
            text_a,
            text_b,
            basis_a,
            basis_b,
        )

        parsed, usage = await call_google_ai_with_usage(
            prompt,
            temperature=0.1,
            max_tokens=800,
            timeout=60,
            response_schema=COMPARISON_RESPONSE_SCHEMA,
            # 0 → thinkingLevel "minimal" on 3.5-flash-lite (the M1 latency
            # lever). None would mean DYNAMIC thinking: billed thought tokens
            # and added seconds on a user-facing button press.
            thinking_budget=0,
        )
        if not parsed or not all(
            isinstance(parsed.get(k), str) and parsed.get(k, "").strip()
            for k in ("summaryA", "summaryB", "divergence")
        ):
            raise ComparisonError("model_failed")

        from app.core.config import settings

        usage = {
            **(usage or {}),
            "model": getattr(settings, "GOOGLE_LLM_MODEL", ""),
        }

        row = ClaimComparison(
            check_id=check_id,
            claim_id=claim.id,
            evidence_a_id=pair_a,
            evidence_b_id=pair_b,
            summary_a=parsed["summaryA"].strip(),
            summary_b=parsed["summaryB"].strip(),
            divergence=parsed["divergence"].strip(),
            basis_a=basis_a,
            basis_b=basis_b,
            words_a=words_a,
            words_b=words_b,
            usage=usage,
        )
        session.add(row)
        try:
            await session.commit()
        except IntegrityError:
            # Cross-process race: another worker won. Serve theirs.
            await session.rollback()
            winner = (
                await session.execute(
                    select(ClaimComparison).where(
                        ClaimComparison.claim_id == claim.id,
                        ClaimComparison.evidence_a_id == pair_a,
                        ClaimComparison.evidence_b_id == pair_b,
                    )
                )
            ).scalar_one()
            return winner, True
        await session.refresh(row)
        return row, False


def _claim_map_dict(claim: Claim) -> Optional[dict]:
    """Claim.claim_map is JSONB but typed str — normalise to a dict."""
    raw = claim.claim_map
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def serialise_comparison(row: ClaimComparison, claim: Claim) -> Dict[str, Any]:
    """API shape. Collisions computed HERE, from the live map (§7.4)."""
    claim_map = _claim_map_dict(claim)
    return {
        "id": row.id,
        "evidenceA": row.evidence_a_id,
        "evidenceB": row.evidence_b_id,
        "summaryA": row.summary_a,
        "summaryB": row.summary_b,
        "divergence": row.divergence,
        "basisA": row.basis_a,
        "basisB": row.basis_b,
        "wordsA": row.words_a,
        "wordsB": row.words_b,
        "collisions": compute_collisions(
            claim_map, row.evidence_a_id, row.evidence_b_id
        ),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
    }
