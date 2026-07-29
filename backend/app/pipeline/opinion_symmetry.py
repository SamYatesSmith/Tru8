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
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.utils.atomicity import compound_indices, is_compound
from app.utils.scope_sensitivity import apply_scope_flags

logger = logging.getLogger(__name__)

MAX_ELEMENTS = 5
BREADTH_FLOOR = 3

# ── Prompts (§20.6(1): open questions — the discriminating run proved the
#    assertion shape was the §19 toxin; NO direction quotas, NO counter-slot) ──

NORMATIVE_DECOMPOSE_PROMPT = """\
You are decomposing an EVALUATIVE claim into the empirical questions a NEUTRAL
analyst would investigate to inform (never settle) the judgement.

Output 3-5 OPEN QUESTIONS about the claim's NAMED SUBJECT:
- Each question must be OPEN and empirically answerable — it must NOT presuppose
  its own answer, and must NOT assert anything. Ask what the evidence shows;
  never state what it shows. A well-chosen question is one the evidence could
  answer either way.
- Every question must be specifically about the claim's named subject, never
  its general topic area, and must bear directly on the judgement being made —
  not on some other actor or dispute.
- NEVER ask whether the value judgement itself is true (e.g. for "X is a
  disaster", "Is X a disaster?" is FORBIDDEN — ask about the specific
  measurable grounds instead: stated targets, measured outcomes, documented
  problems, comparative context, applicable formal proceedings or definitions).
- Each question must ask EXACTLY ONE thing. Never join two questions with
  "and"/"or" ("What were the targets, and were they met?" is TWO questions).
  Where a question has two parts, ask only the part that bears most directly
  on the judgement — usually the outcome, not the setup.

Respond with JSON only:
{"elements": [{"description": "<open question>"}, ...]}
"""

# Phase 3a (2026-07-29): the prompt rule above is the first line of defence,
# never the guarantee (NF-11 — prompt-only fixes fail). Compounds are detected
# MECHANICALLY (app/utils/atomicity.py) and rewritten by this one repair call.
#
# REWRITE, never split: splitting takes 4 elements to 7, blows MAX_ELEMENTS,
# and — because the trailing conjunct is usually the directional,
# judgement-bearing half — any cap rule would drop precisely the half worth
# keeping. It would also inflate the retrieval budget (element lanes are ≤2
# queries each; 5 elements is exactly the 13-query design) and touch the
# LOCKED 1-5 element contract. 1→1 keeps all of that identical.
COMPOUND_REPAIR_PROMPT = """\
You are repairing research questions that accidentally ask TWO things at once.

Each numbered item below asks more than one question. Rewrite EACH as a SINGLE
open question that asks exactly one thing.

- Keep the part that bears most directly on the judgement being investigated —
  usually the outcome or comparison, not the setup ("What were the targets,
  and were they met?" becomes "To what extent were the targets met?").
- The rewrite must stand alone: resolve any "this"/"these"/"it" back to the
  thing it refers to, so the question is intelligible with no other context.
- Keep it OPEN and empirically answerable. It must NOT presuppose its answer,
  must NOT assert anything, and must NOT ask whether the value judgement
  itself is true.
- Stay on the claim's named subject. Do not broaden to the general topic.

Respond with JSON only, in the SAME ORDER as the input:
{"repaired": ["<single question>", ...]}
The array length MUST equal the number of items given.
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


# ── Mechanical value-predicate lock (§20.6(2) — deterministic, no LLM) ───────

# "evidence"/"indicate" are the _as_question wrap boilerplate — stopped so the
# wrap phrasing can never launder a bare judgement past the lock (slice-2
# verify NIT-3: "What does the evidence indicate about whether X is a
# disaster?" must still count as a restatement).
_STOPWORDS = frozenset(
    """a an the is are was were be been being of in on at to for with by from
    as that this these those it its and or not no does do did has have had
    will would can could should may might what which who whom whose when
    where why how if whether there about into over under than then so such
    any all some more most evidence indicate""".split()
)


def _strip_possessive(word: str) -> str:
    # Suffix strip, NOT rstrip("'s") — rstrip strips a character SET, which
    # would mangle words ending in s ("mess" → "me").
    if word.endswith("'s"):
        return word[:-2]
    return word.rstrip("'")


def _content_words(text: str) -> frozenset:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return frozenset(_strip_possessive(w) for w in words) - _STOPWORDS


def _as_question(text: str) -> str:
    """Mechanical question-wrap for a declarative structural re-add (baseline
    elements are assertion-shaped — today's decompose). Deterministic, no LLM;
    neutral by construction ("what does the evidence indicate" invites either
    answer). Question-shaped text passes through untouched."""
    stripped = text.rstrip().rstrip(".")
    if stripped.endswith("?"):
        return stripped
    body = stripped[0].lower() + stripped[1:] if stripped else stripped
    return f"What does the evidence indicate about whether {body}?"


def _is_restatement(claim_text: str, element_text: str) -> bool:
    """True when the element merely re-asks/restates the value judgement:
    it contains every content word of the claim while adding fewer than two
    of its own. The legal-label exemption (D2) is emergent — a real route
    ("status of ICJ proceedings on genocide") adds content words and passes;
    the bare judgement ("Is the situation in Gaza a genocide?") does not."""
    claim_words = _content_words(claim_text)
    if not claim_words:
        return False
    element_words = _content_words(element_text)
    return claim_words <= element_words and len(element_words - claim_words) < 2


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


async def _repair_compounds(
    analyzer, claim: str, elements: List[str]
) -> tuple[List[str], int, int]:
    """Rewrite two-in-one questions as single questions.

    Returns ``(elements, detected, repaired)``. FAIL-SAFE throughout: any
    malformation, any exception, any rewrite that is STILL compound → that
    element keeps its ORIGINAL text. Repair can improve an element or leave it
    alone; it can never make one worse.
    """
    idx = compound_indices(elements)
    if not idx:
        return elements, 0, 0

    numbered = "\n".join(f"{n + 1}. {elements[i]}" for n, i in enumerate(idx))
    try:
        parsed = await analyzer._call_llm(
            prompt=f"{COMPOUND_REPAIR_PROMPT}\n\nClaim: {claim}\n\nItems:\n{numbered}",
            temperature=0.0,
            max_tokens=800,
            label="decomposition",
        )
    except Exception as e:
        logger.warning(f"[ATOMICITY] repair call failed, keeping originals: {e}")
        return elements, len(idx), 0

    rows = (parsed or {}).get("repaired") if isinstance(parsed, dict) else None
    if not isinstance(rows, list) or len(rows) != len(idx):
        logger.warning(
            f"[ATOMICITY] repair malformed (want {len(idx)}, got "
            f"{len(rows) if isinstance(rows, list) else 'n/a'}), keeping originals"
        )
        return elements, len(idx), 0

    out = list(elements)
    repaired = 0
    for n, i in enumerate(idx):
        candidate = rows[n]
        if not isinstance(candidate, str):
            continue
        candidate = candidate.strip()
        # Accept ONLY if the rewrite actually achieved atomicity. A still-
        # compound rewrite is no better than the original and has lost the
        # original's wording, so it is discarded rather than kept.
        if not candidate or is_compound(candidate):
            continue
        logger.info(f"[ATOMICITY] repaired: {elements[i][:70]} -> {candidate[:70]}")
        out[i] = candidate
        repaired += 1

    return out, len(idx), repaired


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

        # Phase 3a: repair two-in-one questions BEFORE the value-predicate
        # lock. Ordering is load-bearing — a rewrite can collapse into the
        # judgement itself ("To what extent was HS2 a waste of money?"), and
        # _is_restatement must see the FINAL text. Repairing after the lock
        # would open a laundering route through the exact door slice 2 shut.
        # Flag off, or nothing compound → no call, candidate untouched.
        compound_detected = compound_repaired = 0
        if settings.ENABLE_ELEMENT_ATOMICITY:
            candidate, compound_detected, compound_repaired = await _repair_compounds(
                analyzer, claim_text, candidate
            )

        cand_subj = await _on_subject(analyzer, claim_text, candidate)
        kept: List[str] = []
        for e, s in zip(candidate, cand_subj):
            if not s:
                continue
            if _is_restatement(claim_text, e):
                logger.info(
                    f"[OPINION GROUNDS] value-predicate lock dropped restatement: {e[:80]}"
                )
                continue
            kept.append(e)

        # Structural coverage: baseline on-subject elements not already covered
        # are added back (catches a silently dropped structural element).
        base_subj = await _on_subject(analyzer, claim_text, baseline_elems)
        structural = [
            e
            for e, s in zip(baseline_elems, base_subj)
            # The lock guards this door too: the baseline decompose can carry
            # the value predicate as an element (P3, check 4E16197E) — it must
            # not re-enter via structural coverage.
            if s and not _is_restatement(claim_text, e)
        ]
        pre_cov = await _coverage(analyzer, claim_text, kept, structural)
        for e, covered in zip(structural, pre_cov):
            # Dedup on BOTH the raw and wrapped forms (verify NIT-1: when the
            # candidate fell back to baseline, the raw string is already in
            # kept and wrapping it would smuggle in a duplicate element).
            if not covered and len(kept) < MAX_ELEMENTS and e not in kept:
                wrapped = _as_question(e)
                if wrapped not in kept:
                    kept.append(wrapped)

        final = kept[:MAX_ELEMENTS]

        lock_collapsed = False
        if not final:  # never empty (given a non-empty baseline or candidate)
            # The lock/filters emptied the set — restore the baseline but
            # DISCLOSE the collapse (verify NIT-2): downstream must be able to
            # tell these are the unrebuilt baseline elements.
            final = baseline_elems[:MAX_ELEMENTS] or candidate[:MAX_ELEMENTS]
            lock_collapsed = True

        converged = not lock_collapsed and len(final) >= min(
            BREADTH_FLOOR, MAX_ELEMENTS
        )

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
    grounds_meta: Dict[str, Any] = {
        "applied": True,
        "converged": bool(converged),
        "element_count": len(final),
    }
    if settings.ENABLE_ELEMENT_ATOMICITY:
        # Survivors are counted on FINAL — structural re-adds are wrapped
        # baseline declaratives that never passed through repair, so counting
        # on `candidate` would under-report the elements the mapper actually
        # sees. Survivors are backstopped mechanically at mapping.
        grounds_meta["atomicity"] = {
            "detected": compound_detected,
            "repaired": compound_repaired,
            "surviving": sum(1 for d in final if is_compound(d)),
        }
    baseline_claim_map.setdefault("metadata", {})["grounds"] = grounds_meta
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
    # F3 re-tag (§20.6(4)): the rebuilt elements must carry scope_flags — the
    # baseline tagging at decompose time is lost with the baseline elements.
    apply_scope_flags(elements)
    claim_map["elements"] = elements
    claim_map.setdefault("metadata", {})["element_count"] = len(elements)
