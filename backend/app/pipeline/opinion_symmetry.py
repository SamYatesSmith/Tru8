"""Opinion grounds stage — Phase 1b (decoupling plan §20, minimal scope).

Given a claim the extraction stage hinted ``normative`` (a retained
main-predicate opinion, 1a), this rebuilds its elements into a set of NEUTRAL
empirical grounds — the measurable sub-questions a neutral analyst would
research to inform (never settle) the judgement. The stage never adds, drops,
or rebalances elements by direction: balance lives in RETRIEVAL and honest
mechanical MAPPING (D1 Option A), never in forced route symmetry (§19/§20 —
false balance is forbidden equally with sycophancy).

History: the direction-forcing rebalancing apparatus that briefly lived here
(option C — union guard, rebalance loop, ``_claim_dominated`` gate) was removed
in slice 1 of the §20 rework after it was live-eval-caught manufacturing false
balance (transcript ``scripts/.opinion_symmetry_eval.json``, the regression
witness). Its one-directional balance gate scored a counter-dominated set
"balanced" — do not reintroduce a balance gate here unless it fails two-sided.

Guarantees (mechanical, over LLM signals that are fail-safe-preserved):
  * on-subject — every final element is about the claim's named subject
    (fail-safe: an unreadable assessment preserves, never condemns);
  * structural coverage — no on-subject element the baseline decomposition
    kept is silently dropped;
  * never empty given a non-empty baseline or decompose (degenerate all-empty
    input leaves the claim_map untouched, disclosed); breadth floor 3 is a
    DISCLOSURE target, not a fill mandate — a thinner set
    converges-or-discloses via ``metadata.grounds``, it never fails a check;
  * total stage failure returns the baseline GENUINELY untouched (elements not
    rebuilt — scope_flags etc. preserved), disclosed via ``metadata.grounds``.

Empirical claims never reach this module. Flag-gated upstream by
``ENABLE_OPINION_REFRAME`` (called only for ``type_hint == "normative"``
claims when the flag is on).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_ELEMENTS = 5
BREADTH_FLOOR = 3

# ── Prompts (slice 2 reshapes these to open questions; slice 1 = removal only,
#    so the direction-forcing instructions are gone and nothing replaces them) ──

NORMATIVE_DECOMPOSE_PROMPT = """\
You are decomposing an EVALUATIVE claim into empirical sub-assertions a NEUTRAL
analyst would test to inform (never settle) the judgement.

Output 3-5 TESTABLE ASSERTIONS about the claim's NAMED SUBJECT:
- Each assertion must be a single declarative, checkable sentence — NOT an open
  question, NOT "the impact of X". State something evidence could confirm or
  contradict.
- Every assertion must be specifically about the claim's named subject, never
  its general topic area.
- NEVER restate the value judgement itself as an assertion (e.g. for "X is a
  disaster", "X is a disaster" or "X has bad outcomes" are FORBIDDEN — decompose
  into the specific measurable grounds instead).

Respond with JSON only:
{"elements": [{"description": "<testable assertion>"}, ...]}
"""

ON_SUBJECT_PROMPT = """\
You are auditing a research design. You are given an evaluative claim and a
numbered list of empirical items chosen to investigate it.

For EACH item, say whether it is specifically about the claim's NAMED subject
(the particular entity, policy, event, or situation the claim names) — true —
or whether it addresses the general topic area without being about that
subject — false. A comparison of the named subject to precedents / base rates
IS on-subject.

Respond with JSON only, in the SAME ORDER as the input:
{"assessments": [{"on_subject": true|false}, ...]}
The array length MUST equal the number of items given.
"""

COVERAGE_PROMPT = """\
You are checking coverage of a research design. You are given the FINAL set of
items, and a numbered list of CANDIDATE items.

For EACH candidate, say whether its substance is already covered by at least one
final item — i.e. investigating the final set would necessarily answer the
candidate's underlying question, even if worded differently.

Respond with JSON only, in the SAME ORDER as the candidates:
{"covered": [true|false, ...]}
The array length MUST equal the number of candidates given.
"""


# ── LLM helpers (fail-safe: preserve, never condemn) ─────────────────────────


def _descs(parsed: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(parsed, dict):
        return []
    out = []
    for e in parsed.get("elements") or []:
        d = e.get("description") if isinstance(e, dict) else str(e)
        if d and isinstance(d, str):
            out.append(d.strip())
    return out


async def _decompose(analyzer, claim: str) -> List[str]:
    parsed = await analyzer._call_llm(
        prompt=f"{NORMATIVE_DECOMPOSE_PROMPT}\n\nClaim: {claim}",
        temperature=analyzer.decomposition_temperature,
        max_tokens=2000,
        label="decomposition",
    )
    return _descs(parsed)[:MAX_ELEMENTS]


async def _on_subject(analyzer, claim: str, elements: List[str]) -> List[bool]:
    """On-subject flag per element. FAIL-SAFE: on any malformation, preserve
    every element — never condemn to drop."""
    if not elements:
        return []
    numbered = "\n".join(f"{i + 1}. {e}" for i, e in enumerate(elements))
    parsed = await analyzer._call_llm(
        prompt=f"{ON_SUBJECT_PROMPT}\n\nClaim: {claim}\n\nItems:\n{numbered}",
        temperature=0.0,
        max_tokens=800,
        label="decomposition",
    )
    rows = (parsed or {}).get("assessments") if isinstance(parsed, dict) else None
    if not isinstance(rows, list) or len(rows) != len(elements):
        return [True] * len(elements)
    return [
        bool(r.get("on_subject", True)) if isinstance(r, dict) else True for r in rows
    ]


async def _coverage(
    analyzer, claim: str, final: List[str], candidates: List[str]
) -> List[bool]:
    """Which candidates are covered by the final set? Malformation → all
    uncovered (safe: uncovered means ADD; a genuine gap surfaces, not hides)."""
    if not candidates:
        return []
    fin = "\n".join(f"- {e}" for e in final) or "(none)"
    cand = "\n".join(f"{i + 1}. {e}" for i, e in enumerate(candidates))
    parsed = await analyzer._call_llm(
        prompt=f"{COVERAGE_PROMPT}\n\nClaim: {claim}\n\nFinal set:\n{fin}\n\nCandidates:\n{cand}",
        temperature=0.0,
        max_tokens=400,
        label="decomposition",
    )
    cov = (parsed or {}).get("covered") if isinstance(parsed, dict) else None
    if not isinstance(cov, list) or len(cov) != len(candidates):
        return [False] * len(candidates)
    return [bool(c) for c in cov]


# ── The stage ────────────────────────────────────────────────────────────────


async def apply_grounds_stage(
    analyzer,
    claim_text: str,
    baseline_claim_map: Dict[str, Any],
) -> Dict[str, Any]:
    """Rebuild a normative claim_map's elements into neutral empirical grounds.

    Mutates and returns ``baseline_claim_map``. The baseline elements (already
    decomposed by the shipped stage — free) are the structural-coverage
    reference. On any total failure the baseline is returned untouched with a
    disclosed ``metadata.grounds`` — a live check can NEVER fail here.
    """
    baseline_elems = [
        e.get("description", "")
        for e in (baseline_claim_map.get("elements") or [])
        if e.get("description")
    ]

    try:
        candidate = await _decompose(analyzer, claim_text)
        if not candidate:
            candidate = baseline_elems[:MAX_ELEMENTS]

        cand_subj = await _on_subject(analyzer, claim_text, candidate)
        kept: List[str] = [e for e, s in zip(candidate, cand_subj) if s]

        # Structural coverage: baseline on-subject elements not already covered
        # are added back (catches a silently dropped structural element).
        base_subj = await _on_subject(analyzer, claim_text, baseline_elems)
        structural = [e for e, s in zip(baseline_elems, base_subj) if s]
        pre_cov = await _coverage(analyzer, claim_text, kept, structural)
        for e, covered in zip(structural, pre_cov):
            if not covered and len(kept) < MAX_ELEMENTS and e not in kept:
                kept.append(e)

        final = kept[:MAX_ELEMENTS]

        if not final:  # never empty (given a non-empty baseline or candidate)
            final = baseline_elems[:MAX_ELEMENTS] or candidate[:MAX_ELEMENTS]

        converged = len(final) >= min(BREADTH_FLOOR, MAX_ELEMENTS)

    except Exception as e:  # never fail a live check — baseline GENUINELY untouched
        logger.warning(
            f"[OPINION GROUNDS] stage failed, keeping baseline untouched: {e}"
        )
        baseline_claim_map.setdefault("metadata", {})["grounds"] = {
            "applied": False,
            "converged": False,
            "element_count": len(baseline_claim_map.get("elements") or []),
        }
        return baseline_claim_map

    if not final:
        # Degenerate input (empty baseline AND empty decompose — unreachable via
        # the ClaimMap contract's 1-5 elements, guarded anyway): leave untouched.
        baseline_claim_map.setdefault("metadata", {})["grounds"] = {
            "applied": False,
            "converged": False,
            "element_count": 0,
        }
        return baseline_claim_map

    _write_elements(baseline_claim_map, final)
    baseline_claim_map.setdefault("metadata", {})["grounds"] = {
        "applied": True,
        "converged": bool(converged),
        "element_count": len(final),
    }
    return baseline_claim_map


def _write_elements(claim_map: Dict[str, Any], descriptions: List[str]) -> None:
    """Replace claim_map elements with the grounds set. Evidence_refs/state stay
    empty for the mapper to fill."""
    elements = []
    for i, desc in enumerate(descriptions):
        elements.append(
            {
                "element_id": f"e{i + 1}",
                "description": desc,
                "evidence_refs": [],
                "state": None,
                "uncertainty": None,
            }
        )
    claim_map["elements"] = elements
    claim_map.setdefault("metadata", {})["element_count"] = len(elements)
