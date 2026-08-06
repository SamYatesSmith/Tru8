"""Claim Map Analyzer — decompose claims into elements and map evidence.

Two LLM stages:
  1. Decomposition: claim text → normalised_claim + claim_type + 1-5 elements
  2. Evidence mapping: elements + evidence → evidence_refs + states + uncertainty

Supports both per-claim and batch modes:
  - Per-claim: decompose_claim() / map_evidence_to_elements() — 1 LLM call each
  - Batch: decompose_claims_batch() / map_evidence_batch() — 1 LLM call per stage
    with automatic fallback to per-claim on parse failure

Orientation line is derived mechanically (no LLM).

Canonical contract: audit/track-b/2026-02-12_claim-map-contract.md
"""

import asyncio
import json
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
import sentry_sdk

from app.core.config import settings
from app.services.google_ai import call_google_ai, call_google_ai_with_usage
from app.models.claim_map import (
    ClaimElement,
    ClaimMap,
    ClaimMapMetadata,
    ClaimType,
    ElementState,
    EvidenceRef,
    EvidenceRelationship,
)
from app.utils.atomicity import is_mixed_shape
from app.utils.scope_sensitivity import apply_scope_flags
from app.utils.jurisdiction_scope import (
    claim_target_country,
    evidence_country,
    is_out_of_jurisdiction,
)
from app.utils.temporal_scope import Period, element_period, read_evidence_periods

logger = logging.getLogger(__name__)

# ── Valid enum values for validation ────────────────────────────────────────

_VALID_CLAIM_TYPES = {e.value for e in ClaimType}
_VALID_STATES = {e.value for e in ElementState}
_VALID_RELATIONSHIPS = {e.value for e in EvidenceRelationship}

# The mapping schema types uncertainty as plain string (see schema note below),
# so when the prompt says "<one sentence or null>" the LLM emits the LITERAL
# string "null". Mechanical normalisation — never rely on the prompt for this.
_UNCERTAINTY_SENTINELS = {"null", "none", "n/a", "na", ""}


def _clean_uncertainty(value) -> Optional[str]:
    """Normalise LLM sentinel strings ("null", "none", …) to real None."""
    if not value or not isinstance(value, str):
        return None
    return None if value.strip().lower() in _UNCERTAINTY_SENTINELS else value


# Causal-link detector (§4d fix 2). Deliberately broad — verbs + connectives —
# mirroring the claim-integrity probe's CAUSE_RE (its precedent). A mechanical
# tag: it decides WHERE the mapping SPECIFICITY CHECK rule applies (causal-link
# elements only), it never judges the evidence itself.
_CAUSAL_LINK_RE = re.compile(
    r"\bcaus\w*|\bdriv(?:e|es|en|ing)\b|\bled to\b|\blead(?:s|ing)? to\b"
    r"|\bresult(?:s|ed|ing)? (?:in|from)\b|\bdue to\b|\bbecause\b"
    r"|\bcontribut\w+ (?:to|factor)|\btrigger\w*|\bresponsible for\b"
    r"|\battribut\w+ to\b",
    re.IGNORECASE,
)


def _is_causal_link(description: str) -> bool:
    """True when an element description asserts a causal relationship."""
    if not description or not isinstance(description, str):
        return False
    return bool(_CAUSAL_LINK_RE.search(description))


def _element_lines(
    elements: List[Dict[str, Any]], grounds: bool = False, indent: str = ""
) -> str:
    """Render elements for a mapping prompt, with the mechanical tags.

    ONE renderer for all three prompt sites (map / completion / recovery) so a
    tag can never be live on some surfaces and dead on others — the Phase 2
    lesson: don't generalise one probe to N surfaces.

    [COMPOUND] (Phase 3a) marks an element asking two questions of DIFFERENT
    shapes. The mapper is told to pick one shape per element, so such an
    element has two right answers and gets graded by whichever half it read —
    usually the trivially-satisfiable one. Computed mechanically here rather
    than left for the LLM to notice; the addendum tells it to grade tagged
    elements by the stricter whether/extent rule.
    """
    # Tagged ONLY on grounds-routed claims: the two-shape rule the tag steers
    # lives in GROUNDS_MAPPING_ADDENDUM, which only those prompts carry. An
    # untagged surface must never emit a token nothing explains.
    tag_compound = grounds and bool(
        getattr(settings, "ENABLE_ELEMENT_ATOMICITY", False)
    )
    lines = []
    for e in elements:
        desc = e.get("description", "")
        line = f"{indent}- {e['element_id']}: {desc}"
        if _is_causal_link(desc):
            line += " [CAUSAL LINK]"
        if tag_compound and is_mixed_shape(desc):
            line += " [COMPOUND]"
        lines.append(line)
    return "\n".join(lines)


# ── Response schemas for Gemini structured output ───────────────────────────
# Constrains mapper output at the API level. Mirrors the structure the prompt
# already requires; defensive parsing in _validate_evidence_refs still strips
# hallucinated evidence_ids (the schema can't enforce per-call enum membership).
#
# uncertainty is omitted from the schema entirely (rather than typed as nullable)
# because Gemini's response_schema handling of nullable is inconsistent across
# SDK versions. The defensive parser already treats missing uncertainty as None
# (claim_map_analyzer.py: `mapped.get("uncertainty") or None`).

_MAPPING_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "element_id": {"type": "string"},
                    "evidence_refs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "evidence_id": {"type": "string"},
                                "relationship": {
                                    "type": "string",
                                    # sorted, not list(set): set order follows
                                    # the per-process hash seed, which made the
                                    # request body non-deterministic across
                                    # interpreters (broke replay-bench cassette
                                    # matching). Enum order has no API meaning.
                                    "enum": sorted(_VALID_RELATIONSHIPS),
                                },
                                "reasoning": {"type": "string"},
                            },
                            "required": [
                                "evidence_id",
                                "relationship",
                                "reasoning",
                            ],
                        },
                    },
                    "state": {
                        "type": "string",
                        "enum": sorted(_VALID_STATES),
                    },
                    "uncertainty": {"type": "string"},
                    # F3 B2 (R-G2): short factual name of what the supporting
                    # evidence covers when the element's own scope is broader
                    # (e.g. "England and Wales" for a "Britain" element). Plain
                    # string like uncertainty; the LLM emits literal "null" when
                    # absent, normalised on parse.
                    "scope_caveat": {"type": "string"},
                },
                "required": ["element_id", "evidence_refs", "state"],
            },
        },
    },
    "required": ["elements"],
}

_BATCH_MAPPING_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_index": {"type": "integer"},
                    "elements": _MAPPING_RESPONSE_SCHEMA["properties"]["elements"],
                },
                "required": ["claim_index", "elements"],
            },
        },
    },
    "required": ["claims"],
}


# ── Prompts ─────────────────────────────────────────────────────────────────

DECOMPOSITION_PROMPT = """\
You are an analytical decomposition engine. Given a claim, you must:

1. **Normalise** the claim into a clear, standalone assertion.
2. **Classify** the claim type from exactly one of: empirical, definitional, \
causal_interpretive, predictive, normative_flagged.
3. **Decompose** the claim into 1-5 required elements — the things that must \
hold for the claim to stand. Each element should be a distinct, testable \
sub-assertion. Atomic claims may have just 1 element.

Respond with JSON only:
{
  "normalised_claim": "<string>",
  "claim_type": "<ClaimType>",
  "elements": [
    {"description": "<what must hold>"},
    ...
  ]
}

Rules:
- Minimum 1 element, maximum 5.
- Each element description must be a single clear sentence.
- claim_type must be exactly one of the five listed values.
- If the claim asserts causation (X causes/drives/leads to Y), include the \
causal link itself as one element, alongside the cause and the effect.
- If the claim makes an explicit comparison (e.g. "compared to X", "more than", \
"since <year>"), EVERY element that asserts the compared quantity or trend must \
state that comparison baseline explicitly in its description.
- Do NOT include evidence_refs, state, or uncertainty — those come later.
"""

MAPPING_PROMPT = """\
You are an evidence mapping engine. You are given:
1. A list of elements (sub-assertions) of a claim.
2. A list of evidence items, each with an evidence_id, title, and snippet.

For each element, map relevant evidence and assign a state. EVERY evidence_ref \
MUST include all three fields: evidence_id, relationship, reasoning.

Respond with JSON only:
{
  "elements": [
    {
      "element_id": "<e1..e5>",
      "evidence_refs": [
        {"evidence_id": "ev-abc", "relationship": "supports", "reasoning": "Reports GDP rose 0.1% in Q3, confirming growth occurred"},
        {"evidence_id": "ev-def", "relationship": "challenges", "reasoning": "States growth was 0.1%, contradicting the claimed 0.6%"}
      ],
      "state": "supported|disputed|unresolved",
      "uncertainty": "<one sentence or null>"
    }
  ]
}

Rules:
- Only use evidence_ids from the provided list. Do NOT invent IDs.
- relationship must be exactly one of: supports, challenges, context.
- reasoning is REQUIRED on every evidence_ref. One sentence: what the evidence \
says and why the relationship applies. Cite specific figures, dates, or entities.
- state must be exactly one of: supported, disputed, unresolved.
- "supported" = predominantly supportive evidence, no significant challenges.
- "disputed" = both supporting and challenging evidence present.
- "unresolved" = no meaningful supporting or challenging evidence.
- uncertainty is optional (null if not applicable), max one sentence.
- Every element_id from the input must appear in the output.
- SCOPE CHECK: Before assigning "supports", verify that the evidence's geographic \
and temporal scope matches the element's scope. Evidence about one country does NOT \
support a claim about "worldwide" or "global" figures. Evidence from one time period \
does NOT support a claim about a different time period. When an element's OWN scope is \
BROADER than the reach of its supporting evidence (e.g. the element says "Britain" but \
the sources address only England and Wales), still map the genuine supports, but set \
that element's "scope_caveat" to a SHORT factual name of what the evidence actually \
covers (e.g. "England and Wales"). Otherwise set "scope_caveat" to null. Do NOT restate \
or judge the claim in scope_caveat — describe only the evidence's reach.
- SPECIFICITY CHECK: An element tagged [CAUSAL LINK] asserts a SPECIFIC causal \
relationship — a named cause driving a named effect, often over a specific period. \
Evidence that only describes a general mechanism, teaches how such processes work \
(educational or explanatory material), or supplies background/reference content does \
NOT support that specific causal assertion — map it as "context", not "supports". \
Reserve "supports"/"challenges" for evidence bearing on whether THIS cause is driving \
THIS effect as asserted.
- STATE RULE: An element can only be "supported" if at least one evidence_ref has \
relationship = "supports". If all refs are "context", the state MUST be "unresolved".
- STATE-BEARING COMPLETENESS: An element's state (supported / disputed / unresolved) \
is computed mechanically by COUNTING its supporting vs challenging evidence. You MUST \
therefore map EVERY item that genuinely supports or challenges an element's specific \
assertion — a complete census, NOT a representative 1-2 sample. Omitting genuine \
supports or challenges produces a WRONG state: mapping 1 of 8 supporting sources \
alongside a lone challenger makes a well-supported fact look "disputed". Map each item \
to the SINGLE element it most directly addresses; an item appears under multiple \
elements ONLY when it genuinely addresses distinct sub-questions (e.g. a study \
reporting both prevalence AND mechanism). Do NOT duplicate the same item across \
elements, and do not force-fit. Items with no supporting, challenging, or genuine \
context relationship to any element are correctly left unmapped — tagged "unmapped" \
downstream and surfaced to the user separately.
- CONTEXT DISCIPLINE: The "context" relationship is for evidence that frames the \
element's domain without confirming or contradicting it. Use sparingly. A general \
topical mention is NOT context — true context provides background that helps \
interpret the supports/challenges evidence for THAT specific element. If an item is \
merely "broadly on topic" with no element-specific signal, omit it from that element \
rather than padding it as context.
- PRECISION: When comparing numbers, treat round figures (e.g. "sixty percent") as \
approximate. A source saying "59%" does not challenge a claim of "approximately 60%". \
But a source saying "25%" DOES challenge a claim of "18%".
- DATA PROVENANCE: Each evidence item shows [Tier] and [Type]. When an element asserts \
a specific figure, date, or quantity, prioritise primary/reporting tier evidence that \
cites the same figure. Commentary or opinion discussing the broader topic is "context" \
for that element, not "supports" or "challenges", unless it directly confirms or \
contradicts the specific figure. Example: an element states "expenditure exceeded £37bn"; \
an opinion piece saying "the programme was controversial" is "context", while an official \
report stating "the two-year budget was £37 billion" is "supports".
- TOPIC vs FIGURE: Distinguish between evidence about a topic and evidence about a \
specific statistic within that topic. An element asserting a number requires evidence \
that addresses the number itself, not merely the surrounding subject. Evidence that \
discusses the subject without mentioning the figure should be mapped as "context" — \
but only when it genuinely helps the reader interpret the element (per CONTEXT \
DISCIPLINE above), otherwise omit.
"""

# §20 slice 3 (P4 fix): appended to MAPPING_PROMPT ONLY when the claim_map was
# rebuilt by the opinion grounds stage (metadata.grounds.applied — written
# solely by that stage, which runs solely flag-on + normative-hinted). Question
# -shaped elements otherwise get coerced, inconsistent stance labels (P4,
# plan §15.8). Counts/states stay mechanical — this changes label SEMANTICS,
# not the counting machinery, so state derivation/orientation are untouched.
#
# P21 Bug A (2026-07-25): the original single rule ("supports" = the evidence
# ANSWERS the question) was right for enumerative grounds and WRONG for
# whether/extent grounds — a study finding no effect "answered" the question
# and so scored a backwards +SUPPORTED badge (live battery T8, e02). The
# decompose prompt commissions BOTH shapes (opinion_symmetry.py:55-66 — open
# questions that must not presuppose an answer), so the rule is now shape-aware
# rather than uniformly directional: forcing a direction onto "What were the
# stated targets?" would have manufactured a label the question cannot carry.
# The state gloss moved with it — "supported = the ground is well-documented"
# re-licensed the answered reading two sentences below the fix.
GROUNDS_MAPPING_ADDENDUM = """\

ELEMENT SHAPE NOTE: This claim's elements are OPEN QUESTIONS — neutral \
empirical grounds chosen to inform a judgement — not assertions. TWO kinds of \
question appear here and they take the relationships differently. Decide which \
kind a question is BEFORE mapping evidence to it.
(1) WHETHER / TO WHAT EXTENT questions — the question asks if something is the \
case, or how much of it is (e.g. "What is the clinical effectiveness of X?", \
"What does the evidence indicate about whether X?").
- "supports" = the evidence shows the asked-about ground IS the case.
- "challenges" = the evidence shows the ground is NOT the case IN THE WORLD — \
it does not hold, it does not occur, or the opposite is documented. Evidence \
answering such a question in the NEGATIVE is "challenges", NEVER "supports" — \
a study finding no effect challenges a question about effectiveness, it does \
not support it.
(2) WHAT / HOW MANY / WHICH questions — the question asks for an amount, a \
record or an enumeration, with no single state of affairs to establish (e.g. \
"What are the documented casualties?", "What were the stated targets?").
- "supports" = the evidence substantively supplies what the question asks for \
(a casualty report is "supports" for the casualty question).
- "challenges" = the evidence disputes that answer — contradicting reported \
figures, or giving a materially different record.
- "context" (either kind) = relevant to the question but does not settle it \
(same discipline as above).
SILENCE IS NOT A CHALLENGE: a source that simply FAILS TO ANSWER a question — \
it discusses the topic but supplies no figure, finding or record — is \
"context" when it genuinely helps the reader interpret the question, and is \
otherwise left unmapped. NEVER map "the evidence does not provide this" as \
"challenges". "challenges" requires the evidence to say something CONTRARY: \
that the ground does not hold in the world, or that a reported record is \
wrong. A question with no substantive answer is MEANT to come out \
"unresolved" — that is an honest result, and manufacturing a challenge to \
fill it misreports the record.
ELEMENTS TAGGED [COMPOUND]: this element asks TWO questions of different \
kinds, so it has no single shape. Grade it by rule (1) — WHETHER / TO WHAT \
EXTENT — for the WHOLE element. Evidence that answers only the easier \
enumerative half (supplying a figure, list or record) does NOT establish the \
element: it is "context" at most. "supports" requires the evidence to bear on \
the harder half — the outcome, the extent, or the comparison. If it does not, \
the element is MEANT to come out "unresolved".
States are computed MECHANICALLY from these counts, so always map the \
relationship the evidence actually bears, never the state you expect: \
"supported" = the ground holds, or its answer is documented and unchallenged; \
"disputed" = challenging evidence is present and not outweighed — INCLUDING a \
ground the evidence uniformly shows is NOT the case, which is the correct and \
honest outcome, not a failure; "unresolved" = no substantive answer found. Do \
NOT treat a question as an assertion to confirm, and NEVER infer or signal \
whether the parent claim is true — map only what the evidence shows about EACH \
ground.
GROUND PRECISION: map a source to a ground ONLY when it substantively \
addresses what THAT question asks. A statement about intent does not answer a \
question about physical extent or casualty figures; an official denial of one \
ground is not "supports" for a different ground. If a source addresses a \
different element's question, map it there instead (per the census rule \
above); if it addresses none substantively, leave it unmapped.
"""


def _grounds_applied(claim_map: Dict[str, Any]) -> bool:
    """True iff this claim_map's elements are QUESTION-shaped grounds.

    §20 slice 2 originally read only `applied`, which asks whether the grounds
    STAGE RAN — not whether the elements it left behind are questions. On the
    lock-collapse path the value-predicate lock empties the rebuilt set and
    `apply_grounds_stage` restores the BASELINE ASSERTION elements, yet still
    marks `applied: True`. Every consumer of this predicate then mistreated
    those assertions: they were given `GROUNDS_MAPPING_ADDENDUM` (which tells
    the mapper to grade whether/extent questions), judged against the
    question-shaped `GROUNDS_MIN_WEIGHTED_SUPPORT` floor, and had their
    orientation suppressed as if summing them would read as a verdict on an
    opinion. Carried from Phase 1 §4b to be fixed once, here, for all sites.

    NOT `applied and converged`, which §4b tentatively suggested: `converged`
    is also False for a set that is genuinely question-shaped but thinner than
    BREADTH_FLOOR (`test_thin_set_discloses_not_fails`). Keying on it would
    strip the addendum, the floor and the suppression from real questions —
    a worse bug than the one being fixed. The collapse is therefore disclosed
    on its own key.

    Back-compatible by construction: a claim_map stored before `collapsed`
    existed has no such key, reads as not-collapsed, and keeps exactly its
    current behaviour.

    Total over hostile shapes: this runs on EVERY mapping call, so a corrupt
    metadata must degrade to False, never raise (slice-3 verify OBSERVATION-2).
    """
    metadata = claim_map.get("metadata")
    if not isinstance(metadata, dict):
        return False
    grounds = metadata.get("grounds")
    if not isinstance(grounds, dict):
        return False
    if grounds.get("collapsed") is True:
        return False
    return grounds.get("applied") is True


BATCH_DECOMPOSITION_PROMPT = """\
You are an analytical decomposition engine. Given multiple claims, for EACH claim:

1. Normalise the claim into a clear, standalone assertion.
2. Classify the claim type from exactly one of: empirical, definitional, \
causal_interpretive, predictive, normative_flagged.
3. Decompose the claim into 1-5 required elements — the things that must \
hold for the claim to stand. Each element should be a distinct, testable \
sub-assertion. Atomic claims may have just 1 element.

Respond with JSON only:
{
  "claims": [
    {
      "claim_index": 0,
      "normalised_claim": "<string>",
      "claim_type": "<ClaimType>",
      "elements": [{"description": "<what must hold>"}, ...]
    }
  ]
}

Rules:
- One entry per claim_index. Do NOT skip any claims.
- Minimum 1 element, maximum 5 per claim.
- Each element description must be a single clear sentence.
- claim_type must be exactly one of the five listed values.
- If a claim asserts causation (X causes/drives/leads to Y), include the \
causal link itself as one element, alongside the cause and the effect.
- If a claim makes an explicit comparison (e.g. "compared to X", "more than", \
"since <year>"), EVERY element that asserts the compared quantity or trend must \
state that comparison baseline explicitly in its description.
- Do NOT include evidence_refs, state, or uncertainty — those come later.
"""

BATCH_MAPPING_PROMPT = """\
You are an evidence mapping engine. You are given multiple claims, each with:
1. A list of elements (sub-assertions).
2. A list of evidence items with evidence_id, title, and snippet.

For each claim, map relevant evidence to its elements and assign states. \
EVERY evidence_ref MUST include all three fields: evidence_id, relationship, reasoning.

Respond with JSON only:
{
  "claims": [
    {
      "claim_index": 0,
      "elements": [
        {
          "element_id": "<e1..e5>",
          "evidence_refs": [
            {"evidence_id": "ev-abc", "relationship": "supports", "reasoning": "Reports GDP rose 0.1% in Q3, confirming growth occurred"},
            {"evidence_id": "ev-def", "relationship": "challenges", "reasoning": "States growth was 0.1%, contradicting the claimed 0.6%"}
          ],
          "state": "supported|disputed|unresolved",
          "uncertainty": "<one sentence or null>"
        }
      ]
    }
  ]
}

Rules:
- One entry per claim_index. Do NOT skip any claims.
- Only use evidence_ids from the provided evidence for THAT claim. Do NOT mix across claims.
- relationship must be exactly one of: supports, challenges, context.
- reasoning is REQUIRED on every evidence_ref. One sentence: what the evidence \
says and why the relationship applies. Cite specific figures, dates, or entities.
- state must be exactly one of: supported, disputed, unresolved.
- "supported" = predominantly supportive evidence, no significant challenges.
- "disputed" = both supporting and challenging evidence present.
- "unresolved" = no meaningful supporting or challenging evidence.
- uncertainty is optional (null if not applicable), max one sentence.
- Every element_id from the input must appear in the output for that claim.
- SCOPE CHECK: Before assigning "supports", verify that the evidence's geographic \
and temporal scope matches the element's scope. Evidence about one country does NOT \
support a claim about "worldwide" or "global" figures. Evidence from one time period \
does NOT support a claim about a different time period. When an element's OWN scope is \
BROADER than the reach of its supporting evidence (e.g. the element says "Britain" but \
the sources address only England and Wales), still map the genuine supports, but set \
that element's "scope_caveat" to a SHORT factual name of what the evidence actually \
covers (e.g. "England and Wales"). Otherwise set "scope_caveat" to null. Do NOT restate \
or judge the claim in scope_caveat — describe only the evidence's reach.
- SPECIFICITY CHECK: An element tagged [CAUSAL LINK] asserts a SPECIFIC causal \
relationship — a named cause driving a named effect, often over a specific period. \
Evidence that only describes a general mechanism, teaches how such processes work \
(educational or explanatory material), or supplies background/reference content does \
NOT support that specific causal assertion — map it as "context", not "supports". \
Reserve "supports"/"challenges" for evidence bearing on whether THIS cause is driving \
THIS effect as asserted.
- STATE RULE: An element can only be "supported" if at least one evidence_ref has \
relationship = "supports". If all refs are "context", the state MUST be "unresolved".
- STATE-BEARING COMPLETENESS: An element's state (supported / disputed / unresolved) \
is computed mechanically by COUNTING its supporting vs challenging evidence. You MUST \
therefore map EVERY item that genuinely supports or challenges an element's specific \
assertion — a complete census, NOT a representative 1-2 sample. Omitting genuine \
supports or challenges produces a WRONG state: mapping 1 of 8 supporting sources \
alongside a lone challenger makes a well-supported fact look "disputed". Map each item \
to the SINGLE element it most directly addresses; an item appears under multiple \
elements ONLY when it genuinely addresses distinct sub-questions (e.g. a study \
reporting both prevalence AND mechanism). Do NOT duplicate the same item across \
elements, and do not force-fit. Items with no supporting, challenging, or genuine \
context relationship to any element are correctly left unmapped — tagged "unmapped" \
downstream and surfaced to the user separately.
- CONTEXT DISCIPLINE: The "context" relationship is for evidence that frames the \
element's domain without confirming or contradicting it. Use sparingly. A general \
topical mention is NOT context — true context provides background that helps \
interpret the supports/challenges evidence for THAT specific element. If an item is \
merely "broadly on topic" with no element-specific signal, omit it from that element \
rather than padding it as context.
- PRECISION: When comparing numbers, treat round figures (e.g. "sixty percent") as \
approximate. A source saying "59%" does not challenge a claim of "approximately 60%". \
But a source saying "25%" DOES challenge a claim of "18%".
- DATA PROVENANCE: Each evidence item shows [Tier] and [Type]. When an element asserts \
a specific figure, date, or quantity, prioritise primary/reporting tier evidence that \
cites the same figure. Commentary or opinion discussing the broader topic is "context" \
for that element, not "supports" or "challenges", unless it directly confirms or \
contradicts the specific figure. Example: an element states "expenditure exceeded £37bn"; \
an opinion piece saying "the programme was controversial" is "context", while an official \
report stating "the two-year budget was £37 billion" is "supports".
- TOPIC vs FIGURE: Distinguish between evidence about a topic and evidence about a \
specific statistic within that topic. An element asserting a number requires evidence \
that addresses the number itself, not merely the surrounding subject. Evidence that \
discusses the subject without mentioning the figure should be mapped as "context" — \
but only when it genuinely helps the reader interpret the element (per CONTEXT \
DISCIPLINE above), otherwise omit.
"""


COMPLETION_PROMPT = """\
You are completing an evidence mapping pass. The main mapper has \
already assigned evidence to each element, but may have MISSED \
genuine supports or challenges. Your job: examine EVERY leftover \
item and map any that supports, challenges, or genuinely \
contextualises a specific element.

WHY THIS MATTERS: an element's state (supported / disputed / \
unresolved) is computed mechanically by COUNTING its supporting vs \
challenging evidence. A single missed support can make a \
well-supported element look "disputed". Completeness of \
supports/challenges is therefore REQUIRED — this is NOT an optional \
context-only pass. Map every leftover that directly substantiates or \
contradicts an element, so the state reflects the FULL weight of \
evidence in the pool.

Output JSON:
{
  "elements": [
    {
      "element_id": "<e1..e5>",
      "additional_refs": [
        {"evidence_id": "ev-abc", "relationship": "supports|challenges|context", "reasoning": "<one sentence>"}
      ]
    }
  ]
}

Rules:
- Only include items from the LEFTOVER list. Do not re-include items \
already mapped by the main pass.
- Map EVERY leftover item that DIRECTLY supports or challenges an \
element's specific assertion (its figure, date, entity, or event) as \
"supports" / "challenges". These change the element's state and must \
be complete — do not sample.
- For an element tagged [CAUSAL LINK], evidence that only describes a \
general mechanism or educational/reference material is "context", never \
"supports" — reserve directional labels for evidence bearing on whether \
THAT specific cause is driving THAT specific effect.
- Use "context" only for items that frame an element without \
confirming or contradicting it, and keep context SPARSE — only where \
it genuinely helps interpret the supports/challenges evidence. Do not \
relabel a genuine support/challenge as context.
- Map each item to the SINGLE element it most directly addresses; do \
not duplicate the same item across elements.
- An item about a different topic entirely should be omitted (left \
unmapped), not force-fitted.
- Reasoning is REQUIRED on every additional_ref. One sentence \
explaining the relationship.
- Omit elements that have no additional refs — don't return empty \
additional_refs arrays.
- relationship must be exactly one of: supports, challenges, context.
"""


# ── Orientation line derivation (pure function, no LLM) ────────────────────

# Prose mappings for orientation templates — centres evidence as the actor.
# "challenged_only" is a prose-only refinement of `disputed` (2026-07-09): the
# state vocabulary is contract-locked, but a disputed element whose refs carry
# challenges and ZERO supports must not be described as "both supports and
# conflicts" — that manufactures false balance on a one-sided record.
_SINGLE_PHRASE = {
    "supported": "predominantly supports it",
    "disputed": "both supports and conflicts with it",
    "challenged_only": "challenges it, with none supporting",
    "unresolved": "is insufficient to assess it",
    "contextual": "provides context for it without directly substantiating",
}

_UNANIMOUS_PHRASE = {
    "supported": "predominantly supports",
    "disputed": "both supports and conflicts with",
    "challenged_only": "challenges",
    "unresolved": "is insufficient to assess",
    "contextual": "provides context for",
}

_ITEM_PHRASE = {
    "supported": "predominantly supported",
    "disputed": "with conflicting evidence",
    "challenged_only": "challenged with none supporting",
    "unresolved": "lacking sufficient evidence",
    "contextual": "informed by contextual evidence",
}


def _orientation_prose_state(elem: ClaimElement) -> Optional[str]:
    """Map an element to its orientation prose key.

    Identical to the element state except for one refinement: a `disputed`
    element with challenging refs and no supporting refs renders as
    "challenged_only". Mechanical — reads evidence_refs (the contract's
    source of truth), no LLM. Context refs neither support nor challenge.
    """
    state = elem.get("state")
    if not state:
        return None
    sv = state.value if hasattr(state, "value") else state
    if sv == "disputed":
        rels = set()
        for ref in elem.get("evidence_refs") or []:
            rel = ref.get("relationship")
            rels.add(rel.value if hasattr(rel, "value") else rel)
        if "challenges" in rels and "supports" not in rels:
            return "challenged_only"
    return sv


def derive_orientation(elements: List[ClaimElement]) -> str:
    """Derive orientation line mechanically from element states.

    Contract Section 5: deterministic, no LLM. Derived from element states
    plus evidence_refs relationships (both mechanical) — refs distinguish a
    genuinely split `disputed` from a challenges-only one. Every orientation
    starts with "Of {N} elements examined" — framing Tru8 as examiner of
    evidence, not arbiter of truth.
    """
    total = len(elements)
    if total == 0:
        return "No elements to assess."

    state_values = [s for s in (_orientation_prose_state(e) for e in elements) if s]
    if not state_values:
        return "No element states have been assigned."

    counts = Counter(state_values)

    # Single element
    if total == 1:
        state = state_values[0]
        phrase = _SINGLE_PHRASE.get(state, state)
        return f"Of 1 element examined, retrieved evidence {phrase}."

    # Unanimous
    if len(counts) == 1:
        state = state_values[0]
        if state == "unresolved":
            return f"Of {total} elements examined, retrieved evidence is insufficient to assess any."
        if state == "contextual":
            return f"Of {total} elements examined, retrieved evidence provides context for all without directly substantiating."
        if state == "challenged_only":
            return f"Of {total} elements examined, retrieved evidence challenges all {total}, with none supporting."
        phrase = _UNANIMOUS_PHRASE.get(state, state)
        return f"Of {total} elements examined, retrieved evidence {phrase} all {total}."

    # Find majority (strictly more than any other single state)
    most_common = counts.most_common()
    top_count = most_common[0][1]
    # Check if there's a tie for the top
    tied = [s for s, c in most_common if c == top_count]

    if len(tied) == 1:
        # Majority exists — list all groups descriptively
        parts = []
        for state, count in most_common:
            phrase = _ITEM_PHRASE.get(state, state)
            parts.append(f"{count} {phrase}")
        remainder = "; ".join(parts)
        return f"Of {total} elements examined, {remainder}."

    # No majority (tied or all different)
    parts = []
    for state, count in most_common:
        phrase = _ITEM_PHRASE.get(state, state)
        parts.append(f"{count} {phrase}")
    joined = ", ".join(parts)
    return f"Of {total} elements examined, evidence is mixed: {joined}."


def compute_orientation_basis(elements: List[ClaimElement]) -> dict:
    """Compute structured orientation breakdown from element states.

    Returns machine-readable state distribution — companion to the prose
    orientation line. Pure function, no LLM.
    """
    state_distribution: Dict[str, int] = {
        "supported": 0,
        "disputed": 0,
        "unresolved": 0,
        "contextual": 0,
    }
    for elem in elements:
        state = elem.get("state")
        if state is not None:
            sv = state.value if hasattr(state, "value") else state
            if sv in state_distribution:
                state_distribution[sv] += 1
    return {
        "total_elements": len(elements),
        "state_distribution": state_distribution,
    }


def apply_orientation(claim_map: Dict[str, Any]) -> None:
    """Write `orientation` + `orientation_basis` onto a claim_map (mutates).

    Single decision point for both fields (Phase 1, 2026-07-27). The two calls
    were previously duplicated verbatim at five sites; they are now here, so a
    grounds-aware rule cannot drift between them.

    **Prose orientation is suppressed (None) for grounds-routed claims.** Those
    elements are open QUESTIONS derived FROM an evaluative claim, so summing
    them ("evidence predominantly supports all 4") reads as a verdict on the
    opinion — invariant #7. Witnessed live both ways: TRU-4B9D-65EA read as an
    endorsement of "was a triumph", TRU-171A-9EF9 as "mixed" where 12-13
    sources agreed with the claim. There is no wording that escapes it; the
    aggregation itself carries the implication, so the line goes.

    **`orientation_basis` is ALWAYS computed, including when the prose is
    suppressed.** It is part of the manifest canonical payload
    (`manifest_signer.py:76`) whereas the prose is explicitly excluded as
    free-text narrative, so suppressing only the prose keeps signed manifests
    byte-stable and preserves the mechanical audit trail.
    """
    elements = claim_map.get("elements") or []
    claim_map["orientation_basis"] = compute_orientation_basis(elements)
    claim_map["orientation"] = (
        None if _grounds_applied(claim_map) else derive_orientation(elements)
    )


# Tier weights for authority-weighted state derivation (V1 plan post-acceptance
# fix, 2026-05-08). primary > reporting > commentary so a single low-tier
# challenger cannot flip an element to disputed when authoritative sources
# support it. Mirrors the tier classification produced by evidence_classifier.
_STATE_TIER_WEIGHTS = {"primary": 3, "reporting": 2, "commentary": 1}

# F3 Phase B1 (R-U1): descriptive caveat for a `supported` element that makes a
# universal claim ("only"/"first"/"no other") which positive evidence cannot
# establish. Tier-gated: suppressed when a primary-tier source backs it (a
# complete-registry / official-list source legitimately settles a universal).
# Wording locked by founder 2026-07-07 (design §7, Option A). Describes the
# evidential limit — never adjudicates the claim.
_UNIVERSAL_CAVEAT = (
    "'only'/'first'-type claim — evidence is consistent "
    "but cannot establish a universal"
)

# F3 Phase B2 (R-G2): reach caveat template. {reach} = the mapper's short factual
# name of what the supporting evidence covers; {term} = display form of the
# tagger's matched composite-geography term. Wording locked by founder
# 2026-07-07 (design §7, Option A). Describes the evidence's reach, never
# re-scopes the claim.
_REACH_CAVEAT = "evidence covers {reach}, narrower than '{term}'"

# Display form for composite-geography lexicon terms (title-case mangles the
# acronyms). Anything not listed is Title Cased.
_SCOPE_TERM_DISPLAY = {
    "uk": "the UK",
    "usa": "the USA",
    "eu": "the EU",
    "european union": "the European Union",
    "united kingdom": "the United Kingdom",
    "united states": "the United States",
    "the americas": "the Americas",
    "british isles": "the British Isles",
}


def _display_scope_term(term: str) -> str:
    return _SCOPE_TERM_DISPLAY.get(term, term.title())


def _state_floor_for(claim_map: Dict[str, Any]) -> int:
    """Tier-weighted support floor for this claim's elements (Phase 1, 2026-07-27).

    Grounds-routed claims carry QUESTION-shaped elements, for which the
    `all_supports` rule (>=1 support, 0 challenges -> supported) is close to no
    bar at all: TRU-4B9D-65EA badged two questions `supported` off ONE source
    each while their own summaries said the evidence supplied nothing. Factual
    claims return 0 and are therefore byte-identical to pre-Phase-1 behaviour.

    Single source of this decision — the three state-derivation call sites read
    it rather than each testing `_grounds_applied` themselves.
    """
    if not _grounds_applied(claim_map):
        return 0
    return max(0, int(getattr(settings, "GROUNDS_MIN_WEIGHTED_SUPPORT", 3) or 0))


def _derive_element_state_with_authority(
    elem: ClaimElement,
    evidence_list: List[Dict[str, Any]],
    min_weighted_support: int = 0,
) -> Tuple[ElementState, dict]:
    """Override the LLM mapper's state with a tier-weighted majority rule.

    Surfaces the issue exposed by TRU-EF20 / Reform UK 5 seats: a single
    outlier source ("4 seats" on Statista) was tagged as challenges by
    the mapper, and the LLM's state assignment flipped the element to
    `disputed` despite multiple authoritative sources confirming. This
    function applies a mechanical, no-LLM rule.

    Rules (counts of evidence_refs by relationship):

      n_supports == 0 AND n_challenges == 0 → unresolved
      n_supports == 0 AND n_challenges  > 0 → disputed
      n_challenges == 0 AND n_supports  > 0 → supported
      weighted_supports   ≥ 2 × weighted_challenges → supported (caveat if challenges)
      weighted_challenges ≥ 2 × weighted_supports   → disputed
      otherwise (close split)                       → disputed

    Then, only when ``min_weighted_support`` > 0 (grounds/question elements —
    see ``_state_floor_for``): a `supported` state whose weighted supports fall
    below the floor is downgraded to `unresolved`, rule
    ``grounds_support_floor``. Default 0 → every other caller is unaffected.

    Tier weights: primary=3, reporting=2, commentary=1. Items whose
    evidence_id can't be resolved against ``evidence_list`` default to
    weight=1. ``context``-relationship refs are counted but neither
    support nor challenge.

    Returns (state, state_basis_dict). The state_basis is attached to
    ``elem["basis"]["state_derivation"]`` by the caller for transparency
    (UI may use it to surface caveat notes; debugging uses it to audit
    why an element ended up in a particular state).
    """
    refs = elem.get("evidence_refs", []) or []
    ev_index = {
        ev.get("evidence_id"): ev for ev in evidence_list if ev.get("evidence_id")
    }

    supports_refs: List[Dict[str, Any]] = []
    challenges_refs: List[Dict[str, Any]] = []
    context_count = 0

    for ref in refs:
        rel = (
            ref.get("relationship")
            if isinstance(ref, dict)
            else getattr(ref, "relationship", None)
        )
        rel_val = (
            rel.value
            if hasattr(rel, "value")
            else str(rel) if rel is not None else None
        )
        if rel_val == "supports":
            supports_refs.append(ref)
        elif rel_val == "challenges":
            challenges_refs.append(ref)
        elif rel_val == "context":
            context_count += 1

    def _ref_evidence_id(ref) -> str:
        return (
            ref.get("evidence_id", "")
            if isinstance(ref, dict)
            else getattr(ref, "evidence_id", "")
        )

    def _ref_weight(ref) -> int:
        ev = ev_index.get(_ref_evidence_id(ref))
        if not ev:
            return 1
        tier = ev.get("tier") or "commentary"
        return _STATE_TIER_WEIGHTS.get(tier, 1)

    weighted_supports = sum(_ref_weight(r) for r in supports_refs)
    weighted_challenges = sum(_ref_weight(r) for r in challenges_refs)

    n_supports = len(supports_refs)
    n_challenges = len(challenges_refs)

    if n_supports == 0 and n_challenges == 0:
        # Distinguish truly-empty (no refs at all) from context-only
        # (context refs present, no supports/challenges). 2026-05-12:
        # pre-fix both collapsed to "unresolved" + rule "no_evidence",
        # which misrepresented context-tier evidence as absent.
        if context_count > 0:
            state = ElementState.contextual
            rule = "context_only"
        else:
            state = ElementState.unresolved
            rule = "no_evidence"
    elif n_supports == 0:
        state = ElementState.disputed
        rule = "all_challenges"
    elif n_challenges == 0:
        state = ElementState.supported
        rule = "all_supports"
    elif weighted_supports >= 2 * weighted_challenges:
        state = ElementState.supported
        rule = "supports_dominant_2x"
    elif weighted_challenges >= 2 * weighted_supports:
        state = ElementState.disputed
        rule = "challenges_dominant_2x"
    else:
        state = ElementState.disputed
        rule = "close_split"

    # Phase 1 mechanical honesty (2026-07-27): a QUESTION-shaped element must
    # clear a tier-weighted floor before it may read "supported". Applies only
    # when the caller passes a floor (grounds claims — see `_state_floor_for`);
    # the default 0 leaves every other path byte-identical.
    #
    # Downgrade target is `unresolved`, NOT `contextual`, and that diverges
    # deliberately from the 2026-05-12 rule (SeekerView.tsx:57-60) which keeps
    # context-only ASSERTIONS out of the gap count because their pool is not
    # empty. For a QUESTION, "topical material but no answer" is exactly an
    # unknown worth re-searching, so it must reach the Seeker.
    if (
        min_weighted_support > 0
        and state == ElementState.supported
        and weighted_supports < min_weighted_support
    ):
        state = ElementState.unresolved
        rule = "grounds_support_floor"

    caveat: Optional[str] = None
    if state == ElementState.supported and n_challenges > 0:
        domains = []
        for ref in challenges_refs:
            eid = (
                ref.get("evidence_id", "")
                if isinstance(ref, dict)
                else getattr(ref, "evidence_id", "")
            )
            ev = ev_index.get(eid) or {}
            url = ev.get("url") or ""
            if url:
                try:
                    from urllib.parse import urlparse

                    domain = urlparse(url).netloc.replace("www.", "").lower()
                except Exception:
                    domain = ""
                if domain:
                    domains.append(domain)
        if domains:
            label = "source disagrees" if n_challenges == 1 else "sources disagree"
            caveat = f"{n_challenges} {label}: {', '.join(domains[:3])}"
        else:
            caveat = (
                f"{n_challenges} outlier challenge{'s' if n_challenges != 1 else ''}"
            )
    elif state == ElementState.disputed and n_supports > 0 and n_challenges > 0:
        # Close split — surface the breakdown so UI can show "mixed evidence"
        caveat = (
            f"mixed: {n_supports} support / {n_challenges} disagree "
            f"(weighted {weighted_supports} vs {weighted_challenges})"
        )

    # F3 scope caveats. Fire ONLY on a `supported` element with the caveat
    # channel free (caveat is None ⇒ the unanimous-supported path F3 targets;
    # a disagreement caveat always keeps priority). The state is never changed
    # — these describe the evidential limit, they do not adjudicate (design §7,
    # decision #7). scope_flags is set by app.utils.scope_sensitivity at
    # decompose; absent ⇒ not scope-sensitive. Reach (R-G2, more specific) is
    # tried before universal (R-U1) when an element carries both.
    scope_basis: Optional[Dict[str, Any]] = None
    if caveat is None and state == ElementState.supported:
        flags = elem.get("scope_flags") or {}
        geographic_terms = flags.get("geographic") or []
        universal_terms = flags.get("universal") or []
        reach = elem.get("scope_reach")  # mapper's narrower-reach assessment

        # F3 B2 (R-G2): reach caveat. The mapper judged the supporting evidence
        # NARROWER than the element's scope AND the tagger independently flagged
        # a composite-geography term (LLM ∧ lexicon agreement cuts LLM false
        # positives). Template the founder-locked wording from both.
        term = _display_scope_term(geographic_terms[0]) if geographic_terms else ""
        # Echo guard: skip when the mapper's "reach" just restates the scope
        # term ("evidence covers Britain, narrower than 'Britain'" is nonsense).
        reach_echoes_term = bool(reach) and reach.strip().lower() in {
            geographic_terms[0] if geographic_terms else None,
            term.lower(),
            term.lower().removeprefix("the "),
        }
        if reach and geographic_terms and not reach_echoes_term:
            caveat = _REACH_CAVEAT.format(reach=reach, term=term)
            scope_basis = {
                "trigger": "reach",
                "geographic_terms": geographic_terms,
                "reach": reach,
                "caveated": True,
            }
        # F3 B1 (R-U1): universal caveat. A universal ("only"/"first"/"no
        # other") that positive instances cannot establish. TIER-GATED: a
        # primary-tier supporter (a complete registry / official list)
        # legitimately settles a universal, so it is exempt.
        elif universal_terms:
            has_primary_support = any(
                (ev_index.get(_ref_evidence_id(r)) or {}).get("tier") == "primary"
                for r in supports_refs
            )
            if not has_primary_support:
                caveat = _UNIVERSAL_CAVEAT
            scope_basis = {
                "trigger": "universal",
                "terms": universal_terms,
                "primary_support": has_primary_support,
                "caveated": caveat == _UNIVERSAL_CAVEAT,
            }

    state_basis = {
        "supports_count": n_supports,
        "challenges_count": n_challenges,
        "context_count": context_count,
        "weighted_supports": weighted_supports,
        "weighted_challenges": weighted_challenges,
        "rule_applied": rule,
        "caveat": caveat,
    }
    if scope_basis is not None:
        state_basis["scope"] = scope_basis
    return state, state_basis


def _domain_of(url: str) -> str:
    """Bare domain (no leading www.) for a URL; '' when unparseable."""
    if not url:
        return ""
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc.replace("www.", "").lower()
    except Exception:
        return ""


# Tier buckets for the support/challenge structure. Mirrors the classifier's
# vocabulary; any missing/unknown tier is bucketed as "commentary" so the
# counts always sum to the side's item count.
_STRUCTURE_TIERS = ("primary", "reporting", "commentary")


def _compute_relationship_structure(
    rel_refs: List[Dict[str, Any]],
    ev_index: Dict[str, Dict[str, Any]],
    derivative_ids: set,
) -> dict:
    """Mechanical, no-LLM structural summary of the evidence on ONE side
    (supports or challenges) of an element.

    Reports STRUCTURE ONLY — count, distinct source domains, tier mix, and
    derivation (how much of the apparent breadth merely re-reports a primary
    source). It assigns NO "thin"/"echo" verdict and NO score; the
    presentation layer decides how to flag the structure. This keeps the
    pipeline neutral — it describes our collection, never the claim.

    Surfaces echo / thin-support patterns so a researcher can see when
    apparent support is narrow or derivative rather than independent.

    Fields:
      count             — refs on this side
      distinct_domains  — distinct source domains among them
      tier_counts       — {primary, reporting, commentary}; missing→commentary
      derivation.originals        — primary items here that have ≥1 derivative
      derivation.derivative_count — items here that re-report a primary (their
                                    id appears in some item's derivation_chain)
      repetition.max_cluster_on_side — largest single unanchored-repetition
                                    cluster represented on THIS side (F4)
      repetition.distinct_domains — distinct source domains among that cluster's
                                    on-side members (independence proxy)
    """
    tier_counts = {t: 0 for t in _STRUCTURE_TIERS}
    domains = set()
    originals = 0
    derivative_count = 0
    # F4: on-side members of each unanchored-repetition cluster, by domain.
    repetition_domains: Dict[int, List[str]] = defaultdict(list)

    for ref in rel_refs:
        eid = (
            ref.get("evidence_id", "")
            if isinstance(ref, dict)
            else getattr(ref, "evidence_id", "")
        )
        ev = ev_index.get(eid)
        if not ev:
            # Unresolved reference — bucket as commentary so the tier counts
            # still sum to `count` rather than silently dropping the item.
            tier_counts["commentary"] += 1
            continue

        tier = ev.get("tier") or "commentary"
        if tier not in tier_counts:
            tier = "commentary"
        tier_counts[tier] += 1

        domain = _domain_of(ev.get("url") or "")
        if domain:
            domains.add(domain)

        if tier == "primary" and (ev.get("derivation_chain") or []):
            originals += 1
        if eid and eid in derivative_ids:
            derivative_count += 1

        rep_id = ev.get("repetition_cluster_id")
        if rep_id:
            repetition_domains[rep_id].append(domain)

    # Summarise the dominant repetition cluster on this side.
    max_cluster_on_side = 0
    rep_distinct_domains = 0
    for members in repetition_domains.values():
        if len(members) > max_cluster_on_side:
            max_cluster_on_side = len(members)
            rep_distinct_domains = len({d for d in members if d})

    return {
        "count": len(rel_refs),
        "distinct_domains": len(domains),
        # The one domain, when this side is single-outlet — lets the
        # presentation layer distinguish a publisher platform from a lone
        # website (§4d fix 5). Empty unless exactly one distinct domain.
        "sole_domain": next(iter(domains)) if len(domains) == 1 else "",
        "tier_counts": tier_counts,
        "derivation": {
            "originals": originals,
            "derivative_count": derivative_count,
        },
        "repetition": {
            "max_cluster_on_side": max_cluster_on_side,
            "distinct_domains": rep_distinct_domains,
        },
    }


def _compute_element_basis(
    elem: ClaimElement, evidence_list: List[Dict[str, Any]]
) -> dict:
    """Compute basis metadata for an element's state.

    Aggregates relationship counts, tier counts, and classification method
    counts from the evidence items referenced by this element, plus a
    mechanical support/challenge STRUCTURE summary (counts, domain breadth,
    tier mix, derivation) used to surface echo / thin-support patterns. The
    structure carries no verdict — see ``_compute_relationship_structure``.
    """
    refs = elem.get("evidence_refs", [])
    if not refs:
        return {
            "evidence_count": 0,
            "relationship_breakdown": {},
            "tier_breakdown": {},
            "classification_breakdown": {},
            "content_basis_breakdown": {},
            "support_structure": _compute_relationship_structure([], {}, set()),
            "challenge_structure": _compute_relationship_structure([], {}, set()),
        }

    # Build evidence_id → evidence_item index
    ev_index: Dict[str, Dict[str, Any]] = {}
    for ev in evidence_list:
        eid = ev.get("evidence_id")
        if eid:
            ev_index[eid] = ev

    # Union of every derivation chain in the pool — an item whose id appears
    # here re-reports a primary source (echo), per the corroboration engine.
    derivative_ids = set()
    for ev in evidence_list:
        for did in ev.get("derivation_chain") or []:
            if did:
                derivative_ids.add(did)

    relationship_counts: Dict[str, int] = {}
    tier_counts: Dict[str, int] = {}
    classification_counts: Dict[str, int] = {}
    content_basis_counts: Dict[str, int] = {}
    supports_refs: List[Dict[str, Any]] = []
    challenges_refs: List[Dict[str, Any]] = []

    for ref in refs:
        # Relationship breakdown
        rel = ref.get("relationship")
        if rel is not None:
            rel_val = rel.value if hasattr(rel, "value") else str(rel)
            relationship_counts[rel_val] = relationship_counts.get(rel_val, 0) + 1
            if rel_val == "supports":
                supports_refs.append(ref)
            elif rel_val == "challenges":
                challenges_refs.append(ref)

        # Look up the full evidence item
        eid = ref.get("evidence_id", "")
        ev_item = ev_index.get(eid)
        if ev_item:
            # Tier breakdown
            tier = ev_item.get("tier")
            if tier:
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

            # Classification method breakdown
            method = ev_item.get("classification_method")
            if method:
                classification_counts[method] = classification_counts.get(method, 0) + 1

            # Content basis breakdown (PQ-07)
            cb = ev_item.get("content_basis")
            if cb:
                content_basis_counts[cb] = content_basis_counts.get(cb, 0) + 1

    return {
        "evidence_count": len(refs),
        "relationship_breakdown": relationship_counts,
        "tier_breakdown": tier_counts,
        "classification_breakdown": classification_counts,
        "content_basis_breakdown": content_basis_counts,
        "support_structure": _compute_relationship_structure(
            supports_refs, ev_index, derivative_ids
        ),
        "challenge_structure": _compute_relationship_structure(
            challenges_refs, ev_index, derivative_ids
        ),
    }


# ── ClaimMapAnalyzer ────────────────────────────────────────────────────────


def _format_period(period: "Period") -> str:
    """Human-readable period for the receipt: "2024-09", or "2024" if year-only."""
    if period.month is None:
        return str(period.year)
    return f"{period.year}-{period.month:02d}"


class ClaimMapAnalyzer:
    """Decomposes claims into elements and maps evidence to them."""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.google_ai_api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
        self.decomposition_model = settings.DECOMPOSITION_MODEL
        self.decomposition_temperature = settings.DECOMPOSITION_TEMPERATURE
        self.analyzer_model = settings.ANALYZER_MODEL
        self.analyzer_temperature = settings.ANALYZER_TEMPERATURE
        self.analyzer_max_tokens = settings.ANALYZER_MAX_TOKENS
        self.max_elements = settings.MAX_ELEMENTS_PER_CLAIM
        self.snippet_length = settings.EVIDENCE_SNIPPET_LENGTH
        self.google_model = getattr(
            settings, "GOOGLE_LLM_MODEL", "gemini-2.5-flash-lite"
        )
        self.mapping_google_model = getattr(
            settings, "MAPPING_GOOGLE_MODEL", self.google_model
        )
        # Thinking-token cap for mapping calls (None = dynamic, current
        # behaviour; 0 = off; >0 = cap). Applied ONLY to mapping labels —
        # decomposition/completion/recovery run on flash-lite (no thinking).
        self.mapping_thinking_budget = getattr(
            settings, "MAPPING_THINKING_BUDGET", None
        )
        self.timeout = 30  # decomposition, recovery (flash-lite, fast)
        self.mapping_timeout = 55  # evidence mapping (flash thinking model, slow)
        self._token_usage = {"input_tokens": 0, "output_tokens": 0}
        # Per-stage observability (Phase 1.3): track which model served each
        # label and whether the OpenAI fallback fired. Read by the runner to
        # populate pipeline_metrics.by_stage.
        self._models_used: Dict[str, str] = {}
        self._fallback_fired: Dict[str, str] = {}

    def get_token_usage(self) -> Dict[str, int]:
        """Return accumulated token usage across all LLM calls."""
        return self._token_usage

    def get_models_used(self) -> Dict[str, str]:
        """Return mapping of label → last model that served the call.

        Phase 1.3: distinguishes Google primary from OpenAI fallback runs
        per pipeline label (decomposition, mapping, batch_mapping, etc).
        """
        return dict(self._models_used)

    def get_fallback_status(self) -> Dict[str, str]:
        """Return mapping of label → fallback reason for any label whose
        Google call failed and triggered the OpenAI path.

        Empty dict means Google primary served every call.
        """
        return dict(self._fallback_fired)

    def _record_fallback(self, label: str, reason: str) -> None:
        """Record that the Google primary failed for this label.

        ``reason`` is "timeout" or "exception". Called from _call_llm before
        the OpenAI fallback attempt; the actual model used is recorded
        separately via _accumulate when the OpenAI call returns.
        """
        self._fallback_fired[label] = reason

    # ── Public: Phase 1 — Decomposition ─────────────────────────────────

    @staticmethod
    def _context_block(source_context: Optional[str], claim_text: str = "") -> str:
        """Claim-integrity B (audit/CLAIM_INTEGRITY.md §4a): decompose sees the
        original submission so elements anchor to the USER'S stated timeframe
        and scope instead of inventing vague windows (probe: 2/7 → 7/7).
        Empty when absent or identical to the claim (E-recombined case)."""
        ctx = (source_context or "").strip()
        if not ctx or ctx == claim_text.strip():
            return ""
        return (
            f"\n\nOriginal submission (context — anchor elements to its stated "
            f"timeframe and geographic scope; do not add assertions the "
            f'claim itself does not make):\n"{ctx[:1200]}"'
        )

    async def decompose_claim(
        self,
        claim_text: str,
        claim_id: str,
        source_context: Optional[str] = None,
    ) -> ClaimMap:
        """Decompose a claim into elements and classify its type.

        Returns a partial ClaimMap (evidence_refs empty, states null, no orientation).
        On parse failure: single-element fallback with raw claim text, type=empirical.
        """
        prompt = (
            f"{DECOMPOSITION_PROMPT}\n\nClaim: {claim_text}"
            f"{self._context_block(source_context, claim_text)}"
        )
        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.decomposition_temperature,
            max_tokens=2000,
            label="decomposition",
        )

        if parsed is not None:
            try:
                return self._parse_decomposition_response(parsed, claim_id)
            except Exception as e:
                logger.warning(f"Decomposition parse failed for claim {claim_id}: {e}")

        # Fallback: single element with raw claim text
        logger.warning(f"Using fallback decomposition for claim {claim_id}")
        return self._fallback_decomposition(claim_text, claim_id)

    # ── Public: Phase 2 — Evidence Mapping ──────────────────────────────

    async def map_evidence_to_elements(
        self, claim_map: ClaimMap, evidence_list: List[Dict[str, Any]]
    ) -> ClaimMap:
        """Map evidence to elements, assign states and uncertainty.

        Completes the ClaimMap: fills evidence_refs, state, uncertainty,
        orientation, and mapping metadata.
        """
        if not evidence_list:
            # No evidence: mark all elements as unresolved
            for elem in claim_map["elements"]:
                elem["evidence_refs"] = []
                elem["state"] = ElementState.unresolved
                elem["uncertainty"] = "No evidence was retrieved for this element."
            apply_orientation(claim_map)
            claim_map["metadata"]["mapping_model"] = "none"
            claim_map["metadata"]["element_count"] = len(claim_map["elements"])
            claim_map["metadata"]["completed_at"] = datetime.now(
                timezone.utc
            ).isoformat()
            return claim_map

        # Build context for LLM. Causal-link elements are tagged so the
        # SPECIFICITY CHECK rule applies to them (§4d fix 2).
        elements_desc = _element_lines(
            claim_map["elements"], grounds=_grounds_applied(claim_map)
        )
        evidence_desc = "\n".join(
            f"- {ev.get('evidence_id', 'unknown')}: "
            f"[{ev.get('title', 'Untitled')}] "
            f"[Tier: {ev.get('tier') or 'unclassified'}] "
            f"[Type: {ev.get('evidence_type') or 'unclassified'}] "
            f"{(ev.get('snippet') or ev.get('text') or '')[:self.snippet_length]}"
            for ev in evidence_list
        )

        prompt = (
            f"{MAPPING_PROMPT}"
            f"{GROUNDS_MAPPING_ADDENDUM if _grounds_applied(claim_map) else ''}\n\n"
            f"Claim: {claim_map['normalised_claim']}\n\n"
            f"Elements:\n{elements_desc}\n\n"
            f"Evidence:\n{evidence_desc}"
        )

        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.analyzer_temperature,
            max_tokens=self.analyzer_max_tokens,
            label="mapping",
        )

        if parsed is not None:
            try:
                self._parse_mapping_response(parsed, claim_map, evidence_list)
                # Retry once if reasoning is null (output budget issue)
                if self._has_null_reasoning(claim_map):
                    logger.warning(
                        f"[CLAIM_MAP] Null reasoning detected for "
                        f"{claim_map['claim_id']}, retrying"
                    )
                    retry_parsed = await self._call_llm(
                        prompt=prompt,
                        temperature=self.analyzer_temperature,
                        max_tokens=self.analyzer_max_tokens,
                        label="mapping",
                    )
                    if retry_parsed is not None:
                        try:
                            self._parse_mapping_response(
                                retry_parsed, claim_map, evidence_list
                            )
                        except Exception:
                            pass  # Keep original result if retry also fails

                # Step 2 (2026-05-12): per-element mapper completion pass.
                # NF-19 mitigation. The main mapper is instructed to be
                # conservative (MAPPING_PROMPT line 296: "Padding every
                # element with the same items is a quality failure"); this
                # second pass re-examines leftovers with a more permissive
                # eye for context-tier matches. See COMPLETION_PROMPT.
                await self._complete_unmapped_evidence(claim_map, evidence_list)
            except Exception as e:
                logger.warning(
                    f"Mapping parse failed for claim {claim_map['claim_id']}: {e}"
                )
                self._fallback_mapping(claim_map)
        else:
            self._fallback_mapping(claim_map)

        # Derive orientation mechanically
        apply_orientation(claim_map)

        # Set mapping metadata
        model_used = "fallback" if parsed is None else self._last_model_used
        claim_map["metadata"]["mapping_model"] = model_used
        claim_map["metadata"]["element_count"] = len(claim_map["elements"])
        claim_map["metadata"]["completed_at"] = datetime.now(timezone.utc).isoformat()

        return claim_map

    # ── Public: Batch Decomposition ─────────────────────────────────

    async def decompose_claims_batch(
        self, claims: List[Dict[str, str]], source_context: Optional[str] = None
    ) -> Dict[str, ClaimMap]:
        """Decompose multiple claims in a single LLM call.

        Parameters:
            claims: list of {"text": str, "claim_id": str}
            source_context: original submission text (claim-integrity B) —
                anchors elements to the user's stated timeframe/scope.

        Returns:
            Dict mapping claim_id to ClaimMap.

        Falls back to per-claim calls on batch parse failure.
        """
        if len(claims) == 1:
            cm = await self.decompose_claim(
                claims[0]["text"], claims[0]["claim_id"], source_context
            )
            return {claims[0]["claim_id"]: cm}

        # Build numbered claim list
        claim_lines = "\n".join(f"[{i}] {c['text']}" for i, c in enumerate(claims))
        prompt = (
            f"{BATCH_DECOMPOSITION_PROMPT}\n\nClaims:\n{claim_lines}"
            f"{self._context_block(source_context)}"
        )

        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.decomposition_temperature,
            max_tokens=2500,
            label="batch_decomposition",
        )

        results: Dict[str, ClaimMap] = {}
        failed_claims: List[Dict[str, str]] = []

        if parsed is not None and isinstance(parsed.get("claims"), list):
            # Index batch response by claim_index
            batch_by_idx = {
                item.get("claim_index"): item
                for item in parsed["claims"]
                if isinstance(item, dict) and item.get("claim_index") is not None
            }

            for i, c in enumerate(claims):
                item = batch_by_idx.get(i)
                if item is not None:
                    try:
                        results[c["claim_id"]] = self._parse_decomposition_response(
                            item, c["claim_id"]
                        )
                        continue
                    except Exception as e:
                        logger.warning(
                            f"Batch decomposition parse failed for claim {c['claim_id']}: {e}"
                        )
                failed_claims.append(c)
        else:
            logger.warning(
                "[CLAIM_MAP] Batch decomposition returned invalid shape, "
                "falling back to per-claim calls"
            )
            failed_claims = list(claims)

        # Retry failed claims individually
        if failed_claims:
            logger.info(
                f"[CLAIM_MAP] Retrying {len(failed_claims)} claims via per-claim decomposition"
            )
            import asyncio

            async def _retry_one(c: Dict[str, str]) -> None:
                results[c["claim_id"]] = await self.decompose_claim(
                    c["text"], c["claim_id"], source_context
                )

            await asyncio.gather(*[_retry_one(c) for c in failed_claims])

        return results

    # ── Public: Batch Evidence Mapping ────────────────────────────────

    async def map_evidence_batch(self, claim_data: List[Dict[str, Any]]) -> None:
        """Map evidence to elements for multiple claims in a single LLM call.

        Parameters:
            claim_data: list of {"claim_map": ClaimMap, "evidence": List[Dict]}

        Mutates each claim_map in place (same as map_evidence_to_elements).
        Falls back to per-claim calls on batch parse failure.
        """
        # Separate claims with and without evidence
        with_evidence = []
        for item in claim_data:
            cm = item["claim_map"]
            ev = item["evidence"]
            if not ev:
                # No evidence: mark all elements as unresolved immediately
                for elem in cm["elements"]:
                    elem["evidence_refs"] = []
                    elem["state"] = ElementState.unresolved
                    elem["uncertainty"] = "No evidence was retrieved for this element."
                apply_orientation(cm)
                cm["metadata"]["mapping_model"] = "none"
                cm["metadata"]["element_count"] = len(cm["elements"])
                cm["metadata"]["completed_at"] = datetime.now(timezone.utc).isoformat()
            else:
                with_evidence.append(item)

        # §20 slice 3: grounds-rebuilt claim_maps (question-shaped elements)
        # need the GROUNDS_MAPPING_ADDENDUM, which only the single-claim prompt
        # carries — route them individually; the rest batch as today. A multi-
        # claim article check CAN contain a hinted claim (Rule 6 hints
        # per-claim). Flag off → no grounds key → nothing partitioned.
        grounds_items = [i for i in with_evidence if _grounds_applied(i["claim_map"])]
        with_evidence = [
            i for i in with_evidence if not _grounds_applied(i["claim_map"])
        ]
        for item in grounds_items:
            await self.map_evidence_to_elements(item["claim_map"], item["evidence"])

        if not with_evidence:
            return

        if len(with_evidence) == 1:
            item = with_evidence[0]
            await self.map_evidence_to_elements(item["claim_map"], item["evidence"])
            return

        # Build batch prompt with per-claim sections
        sections = []
        for i, item in enumerate(with_evidence):
            cm = item["claim_map"]
            ev = item["evidence"]

            # grounds=False is correct here, not an oversight: grounds claims
            # are partitioned OUT of the batch above and routed through the
            # single-claim mapper, which is the only prompt carrying
            # GROUNDS_MAPPING_ADDENDUM. Tagging here would emit a token
            # BATCH_MAPPING_PROMPT never explains.
            elements_desc = _element_lines(cm["elements"], grounds=False, indent="  ")
            evidence_desc = "\n".join(
                f"  - {ev_item.get('evidence_id', 'unknown')}: "
                f"[{ev_item.get('title', 'Untitled')}] "
                f"[Tier: {ev_item.get('tier', 'unknown')}] "
                f"[Type: {ev_item.get('evidence_type', 'unknown')}] "
                f"{(ev_item.get('snippet') or ev_item.get('text') or '')[:self.snippet_length]}"
                for ev_item in ev
            )

            sections.append(
                f"=== CLAIM {i} ===\n"
                f"Claim: \"{cm['normalised_claim']}\"\n"
                f"Elements:\n{elements_desc}\n"
                f"Evidence:\n{evidence_desc}"
            )

        prompt = BATCH_MAPPING_PROMPT + "\n\n" + "\n\n".join(sections)

        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.analyzer_temperature,
            max_tokens=12000,
            label="batch_mapping",
        )

        failed_indices: List[int] = []

        if parsed is not None and isinstance(parsed.get("claims"), list):
            batch_by_idx = {
                item.get("claim_index"): item
                for item in parsed["claims"]
                if isinstance(item, dict) and item.get("claim_index") is not None
            }

            for i, item in enumerate(with_evidence):
                mapped = batch_by_idx.get(i)
                if mapped is not None and isinstance(mapped.get("elements"), list):
                    try:
                        self._parse_mapping_response(
                            mapped, item["claim_map"], item["evidence"]
                        )
                        continue
                    except Exception as e:
                        logger.warning(
                            f"Batch mapping parse failed for claim "
                            f"{item['claim_map']['claim_id']}: {e}"
                        )
                failed_indices.append(i)
        else:
            logger.warning(
                "[CLAIM_MAP] Batch mapping returned invalid shape, "
                "falling back to per-claim calls"
            )
            failed_indices = list(range(len(with_evidence)))

        # Step 2 (2026-05-12): completion pass for successfully batch-mapped
        # claims. Failed claims hit map_evidence_to_elements (per-claim retry
        # below) which invokes completion pass internally. Run completions
        # in parallel to keep wall-time bounded (max single-call time, not
        # sum). Each guarded by its own timeout — a slow completion can't
        # block the whole batch.
        failed_set = set(failed_indices)
        successful_items = [
            item for i, item in enumerate(with_evidence) if i not in failed_set
        ]
        if successful_items:
            import asyncio as _asyncio

            _COMPLETION_TIMEOUT = 25  # seconds per claim; fails open

            async def _run_completion(item):
                try:
                    await _asyncio.wait_for(
                        self._complete_unmapped_evidence(
                            item["claim_map"], item["evidence"]
                        ),
                        timeout=_COMPLETION_TIMEOUT,
                    )
                except _asyncio.TimeoutError:
                    logger.warning(
                        f"[MAP COMPLETION] Claim "
                        f"{item['claim_map'].get('claim_id', '?')}: "
                        f"timeout after {_COMPLETION_TIMEOUT}s — "
                        f"preserving main-pass mapping"
                    )
                except Exception as e:
                    logger.warning(
                        f"[MAP COMPLETION] Claim "
                        f"{item['claim_map'].get('claim_id', '?')}: "
                        f"unexpected error — {e} — preserving main-pass mapping"
                    )

            await _asyncio.gather(*[_run_completion(it) for it in successful_items])

        # Derive orientation + set metadata for successfully batch-mapped claims
        # (failed claims get this via per-claim map_evidence_to_elements)
        model_used = self._last_model_used
        for i, item in enumerate(with_evidence):
            if i not in failed_set:
                cm = item["claim_map"]
                apply_orientation(cm)
                cm["metadata"]["mapping_model"] = model_used
                cm["metadata"]["element_count"] = len(cm["elements"])
                cm["metadata"]["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Retry failed claims individually
        if failed_indices:
            logger.info(
                f"[CLAIM_MAP] Retrying {len(failed_indices)} claims via per-claim mapping"
            )
            import asyncio

            async def _retry_map(idx: int) -> None:
                item = with_evidence[idx]
                await self.map_evidence_to_elements(item["claim_map"], item["evidence"])

            await asyncio.gather(*[_retry_map(i) for i in failed_indices])

    # ── LLM call (Google primary, OpenAI fallback) ──────────────────────

    async def _call_llm(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        label: str,
    ) -> Optional[Dict[str, Any]]:
        """Call LLM with Google primary, OpenAI fallback.

        Returns parsed JSON or None.  Token usage is accumulated internally
        on ``self._token_usage`` — read via ``get_token_usage()`` after all
        stages complete.
        """
        self._last_model_used = "unknown"

        # Mapping calls use the thinking model which needs more time
        is_mapping = label in ("mapping", "batch_mapping")
        google_timeout = self.mapping_timeout if is_mapping else self.timeout

        # Select response_schema for mapping calls — constrains output structure
        # at the API level so the model can't return malformed JSON. Other
        # labels (decomposition, batch_decomposition) pass None.
        response_schema: Optional[Dict[str, Any]] = None
        if label == "mapping":
            response_schema = _MAPPING_RESPONSE_SCHEMA
        elif label == "batch_mapping":
            response_schema = _BATCH_MAPPING_RESPONSE_SCHEMA

        # Try Google first — with a time cap that leaves room for OpenAI fallback
        if self.google_ai_api_key:
            try:
                model_to_use = (
                    self.mapping_google_model if is_mapping else self.google_model
                )
                parsed, usage = await asyncio.wait_for(
                    self._call_google(
                        prompt,
                        temperature,
                        max_tokens,
                        model=model_to_use,
                        timeout=google_timeout,
                        response_schema=response_schema,
                        thinking_budget=(
                            self.mapping_thinking_budget if is_mapping else None
                        ),
                    ),
                    timeout=google_timeout + 5,
                )
                if parsed is not None:
                    self._last_model_used = model_to_use
                    self._models_used[label] = model_to_use
                    self._accumulate(usage)
                    _u = usage or {}
                    logger.info(
                        f"[CLAIM_MAP] {label} completed via Google Gemini "
                        f"(in={_u.get('input_tokens', 0)}, "
                        f"out={_u.get('output_tokens', 0)}, "
                        f"thinking={_u.get('thinking_tokens', 0)})"
                    )
                    return parsed
            except asyncio.TimeoutError:
                logger.warning(
                    f"[CLAIM_MAP] Google {label} timed out after {google_timeout}s, "
                    "trying OpenAI",
                    extra={
                        "event_type": "google_ai_fallback_fired",
                        "stage": label,
                        "fallback_reason": "timeout",
                        "timeout_seconds": google_timeout,
                    },
                )
                self._record_fallback(label, reason="timeout")
                if settings.SENTRY_DSN:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("event_type", "google_ai_fallback_fired")
                        scope.set_tag("stage", label)
                        scope.set_tag("fallback_reason", "timeout")
                        scope.set_extra("timeout_seconds", google_timeout)
                        sentry_sdk.capture_message(
                            f"Google AI fallback fired ({label}, timeout)",
                            level="warning",
                        )
            except Exception as e:
                logger.warning(
                    f"[CLAIM_MAP] Google {label} failed: {e}",
                    extra={
                        "event_type": "google_ai_fallback_fired",
                        "stage": label,
                        "fallback_reason": "exception",
                        "exception_type": type(e).__name__,
                    },
                )
                self._record_fallback(label, reason="exception")
                if settings.SENTRY_DSN:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("event_type", "google_ai_fallback_fired")
                        scope.set_tag("stage", label)
                        scope.set_tag("fallback_reason", "exception")
                        scope.set_tag("exception_type", type(e).__name__)
                        sentry_sdk.capture_message(
                            f"Google AI fallback fired ({label}, {type(e).__name__})",
                            level="warning",
                        )

        # Fall back to OpenAI (guaranteed to run if Google times out)
        if self.openai_api_key:
            try:
                model = (
                    self.decomposition_model
                    if label in ("decomposition", "batch_decomposition")
                    else self.analyzer_model
                )
                parsed, usage = await self._call_openai(
                    prompt, temperature, max_tokens, model
                )
                if parsed is not None:
                    self._last_model_used = model
                    self._models_used[label] = model
                    self._accumulate(usage)
                    logger.info(f"[CLAIM_MAP] {label} completed via OpenAI")
                    return parsed
            except Exception as e:
                logger.warning(f"[CLAIM_MAP] OpenAI {label} failed: {e}")

        logger.error(f"[CLAIM_MAP] Both LLM providers failed for {label}")
        return None

    def _accumulate(self, usage: Optional[Dict[str, int]]) -> None:
        """Add usage to running total."""
        if usage:
            self._token_usage["input_tokens"] += usage.get("input_tokens", 0)
            self._token_usage["output_tokens"] += usage.get("output_tokens", 0)
            # Thinking tokens arrive only from thinking-model calls (mapping
            # labels on gemini-2.5-flash). Track separately when present so
            # the dict shape is unchanged for non-thinking runs.
            if usage.get("thinking_tokens"):
                self._token_usage["thinking_tokens"] = self._token_usage.get(
                    "thinking_tokens", 0
                ) + usage.get("thinking_tokens", 0)

    async def _call_google(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        response_schema: Optional[Dict[str, Any]] = None,
        thinking_budget: Optional[int] = None,
    ) -> tuple:
        return await call_google_ai_with_usage(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout or self.timeout,
            model=model or self.google_model,
            response_schema=response_schema,
            thinking_budget=thinking_budget,
        )

    async def _call_openai(
        self, prompt: str, temperature: float, max_tokens: int, model: str
    ) -> tuple:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                },
            )
        if response.status_code != 200:
            logger.error(f"OpenAI API error: {response.status_code}")
            return None, None
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        usage_raw = result.get("usage", {})
        usage = {
            "input_tokens": usage_raw.get("prompt_tokens", 0),
            "output_tokens": usage_raw.get("completion_tokens", 0),
        }
        return json.loads(content), usage

    # ── Parse helpers ───────────────────────────────────────────────────

    def _parse_decomposition_response(
        self, raw: Dict[str, Any], claim_id: str
    ) -> ClaimMap:
        """Validate decomposition response and build partial ClaimMap."""
        normalised = raw.get("normalised_claim", "")
        if not normalised:
            raise ValueError("Missing normalised_claim")

        # Validate claim_type
        raw_type = raw.get("claim_type", "empirical")
        if raw_type not in _VALID_CLAIM_TYPES:
            logger.warning(f"Invalid claim_type '{raw_type}', defaulting to empirical")
            raw_type = "empirical"

        # Parse elements (enforce 1-5 cap)
        raw_elements = raw.get("elements", [])
        if not raw_elements:
            raise ValueError("No elements in decomposition response")

        raw_elements = raw_elements[: self.max_elements]

        elements: List[ClaimElement] = []
        for i, elem in enumerate(raw_elements, start=1):
            desc = elem.get("description", "")
            if not desc:
                continue
            elements.append(
                ClaimElement(
                    element_id=f"e{i}",
                    description=desc,
                    evidence_refs=[],
                    state=None,
                    uncertainty=None,
                )
            )

        if not elements:
            raise ValueError("All elements had empty descriptions")

        # F3 Phase A: tag scope-sensitive wording mechanically at decompose
        # time (design audit/2026-07-07_f3_design_review.md §3.1). Inert to the
        # mapper prompt (id+description only); read by Phase B state derivation.
        apply_scope_flags(elements)

        return ClaimMap(
            claim_id=claim_id,
            normalised_claim=normalised,
            claim_type=ClaimType(raw_type),
            elements=elements,
            orientation=None,
            metadata=ClaimMapMetadata(
                decomposition_model=self._last_model_used,
                mapping_model=None,
                element_count=len(elements),
                completed_at=None,
            ),
        )

    def _parse_mapping_response(
        self,
        raw: Dict[str, Any],
        claim_map: ClaimMap,
        evidence_list: List[Dict[str, Any]],
    ) -> None:
        """Parse mapping response and merge into existing ClaimMap (mutates in place)."""
        raw_elements = raw.get("elements", [])
        if not raw_elements:
            raise ValueError("No elements in mapping response")

        # Index by element_id for lookup
        raw_by_id = {e.get("element_id"): e for e in raw_elements}

        for elem in claim_map["elements"]:
            eid = elem["element_id"]
            mapped = raw_by_id.get(eid)
            if not mapped:
                # LLM omitted this element — mark unresolved
                elem["evidence_refs"] = []
                elem["state"] = ElementState.unresolved
                elem["uncertainty"] = None
                # Use the shared basis builder (empty-refs path) so every
                # element — even LLM-omitted ones — carries a uniform basis
                # incl. support_structure/challenge_structure for the frontend.
                elem["basis"] = _compute_element_basis(elem, evidence_list)
                continue

            # Validate and filter evidence_refs
            raw_refs = mapped.get("evidence_refs", [])
            elem["evidence_refs"] = self._validate_evidence_refs(
                raw_refs, evidence_list
            )

            # F1 (2026-08-05): scope out evidence about a DIFFERENT period.
            # Runs before the basis and the state derivation below, because
            # state is COUNTED from these relationships — scoping afterwards
            # would leave the state derived from evidence we had already
            # judged not to bear on the element.
            temporal_receipt = self._apply_temporal_scope(elem, evidence_list)

            # 2026-08-06: the same treatment for the OTHER mismatch production
            # showed us — another country's official statistics used to support or
            # challenge a claim scoped to ours. Runs here for the same reason as
            # the temporal gate: state is counted from these relationships.
            jurisdiction_receipt = self._apply_jurisdiction_scope(
                elem, evidence_list, claim_map
            )

            # Validate state — LLM's value is the seed, but the
            # mechanical override below is authoritative. Kept for
            # observability (state_basis records the LLM's call too).
            raw_state = mapped.get("state", "unresolved")
            if raw_state not in _VALID_STATES:
                raw_state = "unresolved"

            # Uncertainty (optional)
            elem["uncertainty"] = _clean_uncertainty(mapped.get("uncertainty"))

            # F3 B2 (R-G2): the mapper's assessment of what the supporting
            # evidence actually covers, when narrower than the element's scope
            # ("England and Wales" for a "Britain" element). Same null-sentinel
            # normalisation as uncertainty. Read by the derivation to build the
            # reach caveat, gated on the tagger's geographic flag.
            elem["scope_reach"] = _clean_uncertainty(mapped.get("scope_caveat"))

            # PQ-03: Attach evidence basis metadata
            elem["basis"] = _compute_element_basis(elem, evidence_list)

            # Invariant #5 — every exclusion has a receipt. Scoping an item to
            # "context" is an exclusion from the state count, so it is recorded
            # where the rest of the derivation is visible rather than applied
            # silently.
            if temporal_receipt:
                elem["basis"]["temporal_scope"] = temporal_receipt
            if jurisdiction_receipt:
                elem["basis"]["jurisdiction_scope"] = jurisdiction_receipt

            # Authority-weighted state override (V1 acceptance fix
            # 2026-05-08, after TRU-EF20 surfaced an outlier source
            # flipping settled facts to disputed).
            mech_state, state_basis = _derive_element_state_with_authority(
                elem, evidence_list, _state_floor_for(claim_map)
            )
            state_basis["llm_state"] = raw_state
            elem["basis"]["state_derivation"] = state_basis
            elem["state"] = mech_state
            if mech_state.value != raw_state:
                logger.info(
                    f"[STATE OVERRIDE] elem={elem.get('element_id')}: "
                    f"llm={raw_state} → mechanical={mech_state.value} "
                    f"(rule={state_basis['rule_applied']}, "
                    f"supports={state_basis['weighted_supports']}, "
                    f"challenges={state_basis['weighted_challenges']})"
                )

    def _apply_temporal_scope(
        self,
        elem: Dict[str, Any],
        evidence_list: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Scope directional refs whose evidence is about a different period.

        Returns a receipt when anything was scoped, else None.

        Symmetric by design: `supports` is scoped exactly as `challenges` is. A
        source about June bears on a September element in neither direction,
        and a gate that only removed challenges would be a sycophancy
        mechanism — the thing invariant #7 exists to forbid.

        Fires only where the element pins ONE month-level period and the
        evidence carries periods of which none match. Evidence carrying no
        period at all is left exactly as the mapper labelled it; see
        app/utils/temporal_scope.

        A period is "carried" if the text states it, or (2026-08-06) if a bare
        month resolves against a trusted publication date. The gate fired zero
        times across the whole replay corpus on the stated-only rule, while
        production supplied a live miss of each kind.

        Rollback: ENABLE_TEMPORAL_SCOPE_GATE=False disables the gate entirely;
        ENABLE_TEMPORAL_PUBLICATION_RESOLUTION=False keeps it but stops it
        inferring a period the source never stated.
        """
        if not getattr(settings, "ENABLE_TEMPORAL_SCOPE_GATE", True):
            return None

        target = element_period(elem.get("description"))
        if target is None:
            return None

        resolve_publication = getattr(
            settings, "ENABLE_TEMPORAL_PUBLICATION_RESOLUTION", True
        )
        by_id = {
            ev.get("evidence_id"): ev for ev in evidence_list if ev.get("evidence_id")
        }
        scoped: List[Dict[str, Any]] = []

        for ref in elem.get("evidence_refs") or []:
            relationship = ref.get("relationship")
            value = getattr(relationship, "value", relationship)
            if value not in ("supports", "challenges"):
                continue

            ev = by_id.get(ref.get("evidence_id"))
            if not ev:
                continue

            text = " ".join(
                part
                for part in (ev.get("title"), ev.get("snippet") or ev.get("text"))
                if part
            )
            # 2026-08-06: a bare month ("in September") is placed in time using
            # the item's own publication date. Withholding the date here is the
            # rollback for that inferring half alone — the lexical half
            # (two-digit years) stays on with the gate itself.
            reading = read_evidence_periods(
                text,
                published_date=(
                    ev.get("published_date") if resolve_publication else None
                ),
                date_basis=ev.get("date_basis") if resolve_publication else None,
            )
            if not reading.all_periods or target in reading.all_periods:
                continue

            ref["relationship"] = EvidenceRelationship.context
            entry = {
                "evidence_id": ref.get("evidence_id"),
                "was": value,
                "element_period": _format_period(target),
            }
            # Invariant #5 again, one level deeper: when the decision rested on
            # an INFERRED period rather than a stated one, the receipt has to
            # say so, and name the provenance it trusted to do it.
            if not reading.stated and reading.inferred:
                entry["period_from"] = "published_date"
                entry["date_basis"] = ev.get("date_basis")
            scoped.append(entry)

        if not scoped:
            return None

        logger.info(
            f"[TEMPORAL SCOPE] elem={elem.get('element_id')}: "
            f"{len(scoped)} ref(s) scoped to context — "
            f"element pins {_format_period(target)}"
        )
        return {
            "element_period": _format_period(target),
            "scoped_count": len(scoped),
            "scoped": scoped,
        }

    def _apply_jurisdiction_scope(
        self,
        elem: Dict[str, Any],
        evidence_list: List[Dict[str, Any]],
        claim_map: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Scope directional refs that are another country's official sources.

        Returns a receipt when anything was scoped, else None.

        Production check `757f02c2` returned a true, ONS-verbatim UK CPI claim as
        `disputed` on a single challenge from the IRISH CSO. The snippet named
        neither Ireland nor the UK, so only the domain carried the mismatch and the
        mapper had nothing to go on — NF-11's original shape.

        Symmetric by design, exactly as the temporal gate is: another country's
        national statistics bear on our figure in neither direction, and a gate
        that only removed challenges would be a sycophancy mechanism.

        Never fires on foreign PRESS (an Irish paper reporting on UK inflation is
        legitimate evidence), never on supranational bodies, and never when the
        item's own text names the claim's jurisdiction. See
        app/utils/jurisdiction_scope for the full reasoning.

        Rollback: ENABLE_JURISDICTION_SCOPE_GATE=False.
        """
        if not getattr(settings, "ENABLE_JURISDICTION_SCOPE_GATE", True):
            return None

        jurisdiction = (claim_map.get("metadata") or {}).get("jurisdiction")
        target = claim_target_country(jurisdiction)
        if target is None:
            return None

        by_id = {
            ev.get("evidence_id"): ev for ev in evidence_list if ev.get("evidence_id")
        }
        scoped: List[Dict[str, Any]] = []

        for ref in elem.get("evidence_refs") or []:
            relationship = ref.get("relationship")
            value = getattr(relationship, "value", relationship)
            if value not in ("supports", "challenges"):
                continue

            ev = by_id.get(ref.get("evidence_id"))
            if not ev:
                continue

            text = " ".join(
                part
                for part in (ev.get("title"), ev.get("snippet") or ev.get("text"))
                if part
            )
            if not is_out_of_jurisdiction(target, ev.get("url"), text):
                continue

            ref["relationship"] = EvidenceRelationship.context
            scoped.append(
                {
                    "evidence_id": ref.get("evidence_id"),
                    "was": value,
                    "claim_jurisdiction": target,
                    "source_country": evidence_country(ev.get("url")),
                }
            )

        if not scoped:
            return None

        logger.info(
            f"[JURISDICTION SCOPE] elem={elem.get('element_id')}: "
            f"{len(scoped)} ref(s) scoped to context — "
            f"claim pins {target}"
        )
        return {
            "claim_jurisdiction": target,
            "scoped_count": len(scoped),
            "scoped": scoped,
        }

    def _validate_evidence_refs(
        self,
        refs: List[Dict[str, str]],
        evidence_list: List[Dict[str, Any]],
    ) -> List[EvidenceRef]:
        """Filter out hallucinated evidence_ids and invalid relationships."""
        valid_ids = {
            ev.get("evidence_id") for ev in evidence_list if ev.get("evidence_id")
        }
        validated = []
        for ref in refs:
            eid = ref.get("evidence_id", "")
            rel = ref.get("relationship", "")
            if eid not in valid_ids:
                logger.debug(f"Stripping hallucinated evidence_id: {eid}")
                continue
            if rel not in _VALID_RELATIONSHIPS:
                logger.debug(f"Stripping invalid relationship: {rel}")
                continue
            validated.append(
                EvidenceRef(
                    evidence_id=eid,
                    relationship=EvidenceRelationship(rel),
                    reasoning=ref.get("reasoning") or None,
                )
            )
        return validated

    # ── Fallbacks ───────────────────────────────────────────────────────

    def _fallback_decomposition(self, claim_text: str, claim_id: str) -> ClaimMap:
        """Return single-element ClaimMap when decomposition fails."""
        elements = [
            ClaimElement(
                element_id="e1",
                description=claim_text,
                evidence_refs=[],
                state=None,
                uncertainty=None,
            )
        ]
        # F3 Phase A: tag the fallback element too (the raw claim text often
        # carries the scope word — e.g. "Britain is the only country…").
        apply_scope_flags(elements)
        return ClaimMap(
            claim_id=claim_id,
            normalised_claim=claim_text,
            claim_type=ClaimType.empirical,
            elements=elements,
            orientation=None,
            metadata=ClaimMapMetadata(
                decomposition_model="fallback",
                mapping_model=None,
                element_count=1,
                completed_at=None,
            ),
        )

    async def _complete_unmapped_evidence(
        self,
        claim_map: ClaimMap,
        evidence_list: List[Dict[str, Any]],
    ) -> None:
        """NF-19 SOLVE (2026-06-16): relationship-census backstop.

        The mapper's element state is derived mechanically by COUNTING
        supporting vs challenging evidence_refs. If the main pass maps
        only a representative subset, that count is taken over a
        non-representative sample and the state is WRONG (the original
        TRU-EF20 failure: 1 of ~10 supports mapped alongside a lone
        challenger → "disputed" instead of "supported"). The fix is to
        guarantee the state is counted over a COMPLETE supports/challenges
        census, not the display sample. See
        audit/2026-06-16_nf19_design_review.md (Option D).

        This pass is that guarantee. It:
          1. Computes the set of evidence items not referenced by ANY
             element after the main pass (the leftovers).
          2. Whenever there is ≥1 leftover, calls the LLM with
             COMPLETION_PROMPT — which classifies leftover
             supports/challenges comprehensively (NOT context-only) so no
             genuine support/challenge is omitted from the census.
          3. Merges the additional refs into each element's
             evidence_refs (deduping by evidence_id). The merge is
             relationship-agnostic — supports/challenges are merged, not
             just context.
          4. Re-derives each element's state via
             _derive_element_state_with_authority over the now-complete
             refs — a 1-support/1-challenge close-split correctly becomes
             "supported" once the other supports are merged.
          5. Logs census completeness (how many leftovers remained
             unmapped) so under-mapping is measurable, not silent.

        Mutates claim_map in place. No-op on:
          - empty leftover set (every item already mapped)
          - LLM failure (preserves main-pass output)
          - JSON parse failure (preserves main-pass output)

        Cost: ~$0.001 per claim on Flash Lite. Adds one LLM call per
        claim that has ≥1 leftover item (most claims) — the correctness
        of the element state is worth the call; revisit with a gate only
        if COGS telemetry demands it.

        Counterpart to ``map_evidence_to_specific_elements`` (coverage
        recovery operates on NEW evidence from re-search); this
        operates on ALREADY-RETRIEVED evidence the mapper skipped.
        """
        # NF-19 (2026-06-16): this is the relationship-CENSUS backstop, not a
        # cost-gated extra. A single missed support can flip an element's
        # mechanical state (close-split → disputed), so we run whenever ANY
        # item is unmapped. (Was 3 — a cost/leverage gate that let 1-2 missed
        # supports corrupt the state. The census→state aggregation below is
        # mechanical; the prompt only judges per-item relationship.)
        MIN_LEFTOVER_FOR_COMPLETION = 1

        all_elements = claim_map["elements"]
        if not all_elements or not evidence_list:
            return

        # Identify items already referenced by ANY element from the
        # main mapping pass.
        referenced_ids: set = set()
        for elem in all_elements:
            for ref in elem.get("evidence_refs", []) or []:
                eid = (
                    ref.get("evidence_id")
                    if isinstance(ref, dict)
                    else getattr(ref, "evidence_id", None)
                )
                if eid:
                    referenced_ids.add(eid)

        leftover = [
            ev
            for ev in evidence_list
            if ev.get("evidence_id") and ev["evidence_id"] not in referenced_ids
        ]

        if len(leftover) < MIN_LEFTOVER_FOR_COMPLETION:
            logger.info(
                f"[MAP COMPLETION] Claim {claim_map.get('claim_id', '?')}: "
                f"no leftover items — census already complete"
            )
            return

        # Build prompt. Tag causal-link elements so the COMPLETION_PROMPT
        # specificity rule can bite (§4d fix 2) — completion adds state-bearing
        # supports/challenges, so a generic item must not land as supports here.
        elements_desc = _element_lines(
            all_elements, grounds=_grounds_applied(claim_map)
        )
        leftover_desc = "\n".join(
            f"- {ev.get('evidence_id', 'unknown')}: "
            f"[{ev.get('title', 'Untitled')}] "
            f"[Tier: {ev.get('tier') or 'unclassified'}] "
            f"[Type: {ev.get('evidence_type') or 'unclassified'}] "
            f"{(ev.get('snippet') or ev.get('text') or '')[:self.snippet_length]}"
            for ev in leftover
        )
        prompt = (
            f"{COMPLETION_PROMPT}\n\n"
            f"Claim: {claim_map['normalised_claim']}\n\n"
            f"Elements:\n{elements_desc}\n\n"
            f"LEFTOVER Evidence (not referenced by the main pass):\n"
            f"{leftover_desc}"
        )

        logger.info(
            f"[MAP COMPLETION] Claim {claim_map.get('claim_id', '?')}: "
            f"{len(leftover)} leftover items, {len(all_elements)} elements"
        )

        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.analyzer_temperature,
            max_tokens=self.analyzer_max_tokens,
            label="map_completion",
        )

        if parsed is None:
            logger.info(
                f"[MAP COMPLETION] Claim {claim_map.get('claim_id', '?')}: "
                f"LLM returned None — preserving main-pass mapping"
            )
            return

        try:
            raw_elements = parsed.get("elements", [])
            raw_by_id = {e.get("element_id"): e for e in raw_elements}

            total_added = 0
            for elem in all_elements:
                eid = elem["element_id"]
                mapped = raw_by_id.get(eid)
                if not mapped:
                    continue

                raw_refs = mapped.get("additional_refs", [])
                if not raw_refs:
                    continue

                # Validate against the LEFTOVER set (not the full
                # evidence_list) so the LLM can't reuse already-mapped IDs.
                new_refs = self._validate_evidence_refs(raw_refs, leftover)
                if not new_refs:
                    continue

                # Dedupe by evidence_id against existing refs (defensive —
                # shouldn't happen since leftover excludes referenced IDs).
                existing_ref_ids = {
                    (
                        r.get("evidence_id")
                        if isinstance(r, dict)
                        else getattr(r, "evidence_id", None)
                    )
                    for r in elem.get("evidence_refs", []) or []
                }
                new_refs_filtered = [
                    r
                    for r in new_refs
                    if (
                        r.get("evidence_id")
                        if isinstance(r, dict)
                        else getattr(r, "evidence_id", None)
                    )
                    not in existing_ref_ids
                ]

                if not new_refs_filtered:
                    continue

                elem["evidence_refs"] = (
                    list(elem.get("evidence_refs", []) or []) + new_refs_filtered
                )
                total_added += len(new_refs_filtered)

                # Re-derive state with the merged refs. Recompute basis
                # too so the per-element metrics reflect the completion
                # pass's additions.
                elem["basis"] = _compute_element_basis(elem, evidence_list)
                mech_state, state_basis = _derive_element_state_with_authority(
                    elem, evidence_list, _state_floor_for(claim_map)
                )
                # Preserve the main pass's llm_state record if present.
                prior_basis = (
                    elem["basis"].get("state_derivation")
                    if isinstance(elem.get("basis"), dict)
                    else None
                )
                if prior_basis and prior_basis.get("llm_state"):
                    state_basis["llm_state"] = prior_basis["llm_state"]
                elem["basis"]["state_derivation"] = state_basis
                elem["state"] = mech_state

                ref_ids = [
                    (
                        r.get("evidence_id")
                        if isinstance(r, dict)
                        else getattr(r, "evidence_id", None)
                    )
                    for r in new_refs_filtered
                ]
                logger.info(
                    f"[MAP COMPLETION] {eid}: +{len(new_refs_filtered)} refs "
                    f"{ref_ids}, state→{mech_state.value} "
                    f"(rule={state_basis['rule_applied']})"
                )

            # NF-19 census-completeness instrumentation: how many leftovers
            # the census still left unmapped. A high residual on claims with
            # rich pools is the signal that the census prompt is under-mapping
            # supports/challenges (the failure mode this pass exists to catch)
            # — measurable here rather than silently corrupting state.
            now_referenced: set = set()
            for elem in all_elements:
                for ref in elem.get("evidence_refs", []) or []:
                    rid = (
                        ref.get("evidence_id")
                        if isinstance(ref, dict)
                        else getattr(ref, "evidence_id", None)
                    )
                    if rid:
                        now_referenced.add(rid)
            still_unmapped = sum(
                1 for ev in leftover if ev.get("evidence_id") not in now_referenced
            )
            logger.info(
                f"[MAP COMPLETION] Claim {claim_map.get('claim_id', '?')}: "
                f"census added {total_added} refs across {len(all_elements)} "
                f"elements from {len(leftover)} leftovers; "
                f"{still_unmapped} leftover(s) remain unmapped (genuinely "
                f"off-element or census miss)"
            )

        except Exception as e:
            logger.warning(
                f"[MAP COMPLETION] Claim {claim_map.get('claim_id', '?')}: "
                f"parse failed — {e} — preserving main-pass mapping"
            )

    async def map_evidence_to_specific_elements(
        self,
        claim_map: ClaimMap,
        unresolved_element_ids: List[str],
        new_evidence: List[Dict[str, Any]],
    ) -> None:
        """Map new evidence to elements, with full cross-element visibility.

        Used by coverage recovery. Shows ALL elements in the LLM prompt so
        evidence can be mapped across element boundaries. Only updates state
        for unresolved (target) elements; resolved elements get new refs
        merged but keep their existing state.

        Mutates claim_map in place.
        """
        if not new_evidence or not unresolved_element_ids:
            return

        target_set = set(unresolved_element_ids)
        all_elements = claim_map["elements"]

        # Build context for LLM -- include ALL elements for cross-element
        # mapping. Tag causal-link elements so the MAPPING_PROMPT specificity
        # rule bites on recovery evidence too (§4d fix 2).
        elements_desc = _element_lines(
            all_elements, grounds=_grounds_applied(claim_map)
        )

        # Neutralise element hints in recovery evidence IDs so the LLM
        # doesn't anchor on them (e.g. ev-rec-e1_3_abc → ev-rec-3_abc).
        # Keep a mapping to translate the LLM's output back to real IDs.
        _ELEMENT_HINT_RE = re.compile(r"^(ev-rec-)e\d+_")
        neutral_to_real: Dict[str, str] = {}
        evidence_lines = []
        for ev in new_evidence:
            real_id = ev.get("evidence_id", "unknown")
            neutral_id = _ELEMENT_HINT_RE.sub(r"\1", real_id)
            neutral_to_real[neutral_id] = real_id
            evidence_lines.append(
                f"- {neutral_id}: "
                f"[{ev.get('title', 'Untitled')}] "
                f"[Tier: {ev.get('tier') or 'unclassified'}] "
                f"[Type: {ev.get('evidence_type') or 'unclassified'}] "
                f"{(ev.get('snippet') or ev.get('text') or '')[:self.snippet_length]}"
            )
        evidence_desc = "\n".join(evidence_lines)

        prompt = (
            f"{MAPPING_PROMPT}"
            f"{GROUNDS_MAPPING_ADDENDUM if _grounds_applied(claim_map) else ''}\n\n"
            f"Claim: {claim_map['normalised_claim']}\n\n"
            f"Elements:\n{elements_desc}\n\n"
            f"Evidence:\n{evidence_desc}"
        )

        logger.info(
            f"[RECOVERY MAP] Claim {claim_map.get('claim_id', '?')}: "
            f"{len(new_evidence)} evidence, {len(all_elements)} elements "
            f"({len(target_set)} unresolved), "
            f"neutralised {sum(1 for n, r in neutral_to_real.items() if n != r)} IDs"
        )

        parsed = await self._call_llm(
            prompt=prompt,
            temperature=self.analyzer_temperature,
            max_tokens=self.analyzer_max_tokens,
            label="recovery_mapping",
        )

        if parsed is not None:
            try:
                raw_elements = parsed.get("elements", [])
                raw_by_id = {e.get("element_id"): e for e in raw_elements}

                for elem in all_elements:
                    eid = elem["element_id"]
                    mapped = raw_by_id.get(eid)
                    if not mapped:
                        continue

                    # Restore real evidence IDs from neutralised ones
                    raw_refs = mapped.get("evidence_refs", [])
                    for ref in raw_refs:
                        nid = ref.get("evidence_id", "")
                        ref["evidence_id"] = neutral_to_real.get(nid, nid)

                    # Merge new evidence_refs with existing ones
                    new_refs = self._validate_evidence_refs(raw_refs, new_evidence)
                    existing_refs = elem.get("evidence_refs", [])
                    elem["evidence_refs"] = existing_refs + new_refs

                    is_target = eid in target_set
                    ref_ids = [r.get("evidence_id", "?") for r in new_refs]
                    logger.info(
                        f"[RECOVERY MAP] {eid} ({'target' if is_target else 'resolved'}): "
                        f"+{len(new_refs)} refs {ref_ids}, "
                        f"state={'updating' if is_target else 'preserved'}"
                    )

                    # Only update state for unresolved (target) elements
                    if is_target:
                        raw_state = mapped.get("state", "unresolved")
                        if raw_state not in _VALID_STATES:
                            raw_state = "unresolved"
                        elem["uncertainty"] = _clean_uncertainty(
                            mapped.get("uncertainty")
                        )
                        # Authority-weighted override (parity with the main
                        # mapping path). Recovery only sees new_evidence for
                        # tier lookup; refs that pre-date this round resolve
                        # to weight=1 (acceptable: the override is still
                        # majority-rule, just not fully tier-weighted across
                        # the merged ref set).
                        mech_state, state_basis = _derive_element_state_with_authority(
                            elem, new_evidence, _state_floor_for(claim_map)
                        )
                        state_basis["llm_state"] = raw_state
                        elem.setdefault("basis", {})["state_derivation"] = state_basis
                        elem["state"] = mech_state
                        logger.info(
                            f"[RECOVERY MAP] {eid}: state → {mech_state.value} "
                            f"(llm={raw_state}, rule={state_basis['rule_applied']})"
                        )

            except Exception as e:
                logger.warning(
                    f"Recovery mapping parse failed for claim {claim_map['claim_id']}: {e}"
                )
        else:
            logger.warning(
                f"[RECOVERY MAP] Claim {claim_map.get('claim_id', '?')}: LLM returned None"
            )

        # Re-derive orientation from all element states
        apply_orientation(claim_map)

    def _has_null_reasoning(self, claim_map: ClaimMap) -> bool:
        """Check if any evidence_ref has null reasoning."""
        for elem in claim_map["elements"]:
            for ref in elem.get("evidence_refs", []):
                if ref.get("reasoning") is None:
                    return True
        return False

    def _fallback_mapping(self, claim_map: ClaimMap) -> None:
        """Mark all elements as unresolved when mapping fails."""
        for elem in claim_map["elements"]:
            elem["evidence_refs"] = []
            elem["state"] = ElementState.unresolved
            elem["uncertainty"] = None
