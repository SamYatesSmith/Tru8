"""Recital tagger — assertion is not evidence (2026-08-13).

Design: audit/2026-08-13_assertion_evidence_design.md, section 3.

WHY THIS EXISTS, AND WHY A PROMPT RULE IS NOT ENOUGH
----------------------------------------------------
Production check `TRU-018F-44AA` ("Donald Trump stopped 6 wars") badged its
causal elements `supported` on evidence whose OWN mapping reasoning read:

    "This news report states Trump claimed to have 'settled six wars'"
    "touted Trump's success in purportedly ending eight global conflicts"
    "directly quotes President Trump saying, 'I've solved six wars'"

Evidence that a claim WAS MADE is evidence of the making, not of the content.
Mapping recitals as `supports` turns a claim's virality into its evidence base
— for any claim prominent enough to be checked, which is precisely the class a
user brings here. Three of the four graded outreach records (2026-08-12) show
the same signature. NF-11's lesson stands: fragile behaviour needs a
mechanical rule; the prompt half (Phase 2) does the finer judgement, this
module guarantees the floor.

WHAT IT DOES, AND DELIBERATELY DOES NOT DO
------------------------------------------
Where the claim names its subjects and a directional reference rests on
attribution — the subject SAYING the thing, rather than anyone establishing it
— the relationship is scoped to "context", with a receipt (invariant #5).
Nothing is deleted. **Symmetric**: a recital-based challenge is scoped exactly
as a recital-based support (invariant #7 forbids one-way gates).

Signals, in priority order:

  1. **The reference's own `reasoning` string** — the mapper is contractually
     required to explain every ref in one sentence, and in the incident every
     recital-support's reasoning carried the attribution verb. The mapper's
     stated reason is the most honest signal available: if the model itself
     says the evidence is a recital, the label must not say `supports`.
     Authoritative when it speaks: a veto in the reasoning ends the matter.
  2. **The evidence text** (title + snippet/distilled) — consulted only when
     the reasoning is silent both ways.

Three guards hold down false positives, because over-firing hides genuine
evidence and under-crediting distorts as much as over-crediting:

  * **Subject anchoring.** Attribution verbs fire only next to a distinctive
    subject token ("Trump claimed…", "quotes President Trump saying"), so "the
    ONS says inflation fell" — a source reporting its own finding — is never
    touched. Distancing adverbs (purportedly/allegedly/supposedly) are
    inherently non-endorsing and need no anchor.
  * **Verification vetoes.** "records show", "fact-check", "contradicts",
    "confirmed" etc. in the same text suppress the fire — the source did its
    own work, and judging HOW well is the prompt half's job, not this one's.
  * **Attribution-shaped elements are exempt.** An element asserting that
    someone SAID something ("the minister stated X") is legitimately supported
    by a report of the saying; the gate never arms for it.

Known limit, stated rather than hidden: reasoning wording is model-shaped, not
contract-locked. If a future mapping model stops writing attribution verbs the
reasoning half goes quiet — the safe direction, but silent; the evidence-text
half and the corpus assertions are the backstop.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple

#: Verbs that attribute content to a speaker. Matched only ANCHORED to a
#: distinctive subject token — see _subject_patterns.
_ATTRIBUTION_VERBS = (
    r"claim(?:s|ed)?(?:\s+to\s+have)?|says?|said|saying|announc(?:es|ed|ing)|"
    r"tout(?:s|ed|ing)|boast(?:s|ed|ing)|assert(?:s|ed|ing)|declar(?:es|ed|ing)|"
    r"insist(?:s|ed|ing)"
)

#: Distancing adverbs — a writer flagging non-endorsement. Fire unanchored.
_DISTANCING = re.compile(r"\b(purportedly|allegedly|supposedly)\b", re.IGNORECASE)

#: Verification framing — the source did its own work; suppress the fire.
_VETO = re.compile(
    r"\b(confirm\w*|verif\w*|corroborat\w*|records?\s+show\w*|data\s+show\w*|"
    r"figures\s+show\w*|found\s+that|contradict\w*|disput\w*|challeng\w*|"
    r"refut\w*|debunk\w*|fact[-\s]?check\w*)\b",
    re.IGNORECASE,
)

#: An element that itself asserts a SAYING is legitimately supported by a
#: report of the saying — the gate must not arm for it.
_ATTRIBUTION_SHAPED_ELEMENT = re.compile(
    r"\b(said|says|stated|claim(?:s|ed)|announced|asserted|denied|"
    r"according\s+to)\b",
    re.IGNORECASE,
)

_EXCERPT_CHARS = 90


def element_asserts_attribution(description: Optional[str]) -> bool:
    """True when the element's own content is that something was said."""
    return bool(description and _ATTRIBUTION_SHAPED_ELEMENT.search(description))


def _subject_patterns(tokens: Iterable[Tuple[str, str]]) -> List[re.Pattern]:
    """Compiled attribution patterns anchored on each distinctive token."""
    patterns: List[re.Pattern] = []
    for token, _subject in tokens:
        tok = re.escape(token)
        patterns.append(
            re.compile(
                rf"\b{tok}\b.{{0,40}}?\b(?:{_ATTRIBUTION_VERBS})\b",
                re.IGNORECASE | re.DOTALL,
            )
        )
        patterns.append(
            re.compile(
                rf"\b(?:quotes?|quoting)\b.{{0,60}}?\b{tok}\b",
                re.IGNORECASE | re.DOTALL,
            )
        )
        patterns.append(
            re.compile(
                rf"\baccording\s+to\b.{{0,30}}?\b{tok}\b",
                re.IGNORECASE | re.DOTALL,
            )
        )
    return patterns


def _excerpt(text: str, start: int, end: int) -> str:
    lo = max(0, start - 20)
    hi = min(len(text), end + (_EXCERPT_CHARS - (end - start) - 20))
    return text[lo:hi].strip()


_FIRE, _VETOED, _SILENT = "fire", "veto", "silent"


def _assess(
    text: Optional[str], patterns: List[re.Pattern]
) -> Tuple[str, Optional[Dict[str, str]]]:
    """One text's verdict: veto beats fire beats silence."""
    if not text:
        return _SILENT, None
    if _VETO.search(text):
        return _VETOED, None
    match = _DISTANCING.search(text)
    if match:
        return _FIRE, {
            "marker": match.group(1).lower(),
            "excerpt": _excerpt(text, match.start(), match.end()),
        }
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _FIRE, {
                "marker": match.group(0)[:60].lower(),
                "excerpt": _excerpt(text, match.start(), match.end()),
            }
    return _SILENT, None


#: Minimum normalised length before a claim is ELIGIBLE to match on at all.
#: Short claims share wording with ordinary prose and would over-fire.
_MIN_CLAIM_CHARS = 40
#: Minimum length of the MATCH itself. Deliberately lower than the eligibility
#: floor: conflating the two was a real bug (2026-08-25). The gate is handed the
#: NORMALISED claim ("The year 2026 will be the quietest year for wildfires in
#: Europe"), not the words a reciting source actually copies, so a genuine
#: recital matches a long shared phrase rather than the whole string — 35 of 52
#: chars on the case that motivated this. A 40-char match floor silently missed
#: it while the ratio said 67%.
_MIN_MATCH_CHARS = 28
#: Share of the claim that must appear contiguously in the evidence.
_RESTATEMENT_RATIO = 0.6


def _squash(text: Optional[str]) -> str:
    """Lowercase, keep only a-z0-9, drop ALL whitespace.

    Dropping whitespace is deliberate, not lazy: the tweet that motivated this
    path writes "wild fires" where the claim writes "wildfires". Any
    word-boundary comparison misses that; a despaced character comparison does
    not.
    """
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _longest_common_run(a: str, b: str) -> int:
    """Length of the longest contiguous substring shared by a and b."""
    if not a or not b:
        return 0
    # Rolling DP over one row — a and b are a claim and a snippet, so this is
    # thousands of ops, not millions.
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def claim_restatement_match(
    evidence_text: Optional[str], claim_text: Optional[str]
) -> Optional[Dict[str, str]]:
    """Receipt entry when the evidence simply RESTATES the claim, else None.

    The subject-anchored path above cannot reach a claim that names nobody:
    `recital_match` needs distinctive subject tokens, and a claim like "2026 is
    the quietest year for wildfires in Europe" has none, so the gate never
    armed. That left a prompt rule as the only defence — and prompt rules are
    model-shaped, which is exactly what NF-11 says not to rely on. Measured
    2026-08-25: on identical input, gemini-2.5-flash labelled the reciting
    tweet `context` 10/10 while gemini-3.5-flash-lite labelled it `supports`
    10/10. Same code, same prompt, opposite answer.

    This path asks a question that needs no subject at all: does this source
    just say the claim back? A near-verbatim restatement of the claim is
    evidence that the claim was made, never that it is true.

    Deliberately HIGH PRECISION, LOW RECALL. It catches verbatim and
    near-verbatim recitals and nothing cleverer. Paraphrase is left to the
    prompt half — this is the mechanical floor, not the whole judgement, and
    over-firing would hide genuine evidence (invariant #7 cuts both ways).

    The verification veto still applies first, so a factcheck that quotes the
    claim in order to demolish it is untouched — which is how Carbon Brief's
    "Factcheck: No, Europe is not having its 'quietest' year" stays a challenge.
    """
    if not evidence_text or not claim_text:
        return None
    if _VETO.search(evidence_text):
        return None

    claim_sq = _squash(claim_text)
    if len(claim_sq) < _MIN_CLAIM_CHARS:
        return None
    ev_sq = _squash(evidence_text)
    if not ev_sq:
        return None

    run = _longest_common_run(claim_sq, ev_sq)
    if run < max(_MIN_MATCH_CHARS, int(len(claim_sq) * _RESTATEMENT_RATIO)):
        return None

    return {
        "marker": "restates the claim",
        "excerpt": (evidence_text or "").strip()[:_EXCERPT_CHARS],
        "found_in": "evidence",
        "matched_chars": str(run),
        "claim_chars": str(len(claim_sq)),
    }


def recital_match(
    reasoning: Optional[str],
    evidence_text: Optional[str],
    tokens: List[Tuple[str, str]],
    claim_text: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """The receipt entry if this reference rests on recital, else None.

    The reasoning is authoritative when it speaks in either direction; the
    evidence text is consulted only when the reasoning is silent both ways.
    When the claim names no subject, the subject-anchored path cannot run at
    all — `claim_text` then carries the whole gate via
    `claim_restatement_match`.
    """
    if tokens:
        patterns = _subject_patterns(tokens)

        verdict, entry = _assess(reasoning, patterns)
        if verdict == _VETOED:
            return None
        if verdict == _FIRE and entry is not None:
            entry["found_in"] = "reasoning"
            return entry

        verdict, entry = _assess(evidence_text, patterns)
        if verdict == _FIRE and entry is not None:
            entry["found_in"] = "evidence"
            return entry

    # Subject-free fallback. Runs when the claim names nobody, and also when it
    # names someone but the attribution wording never appeared — a source can
    # recite a claim without naming who made it.
    return claim_restatement_match(evidence_text, claim_text)
