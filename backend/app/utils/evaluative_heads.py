"""Evaluative-head detector — F-VERDICT / P13 (2026-07-26).

Design: `audit/2026-07-26_evaluative_head_design.md`. A mechanical tagger that
detects a value judgement sitting in MAIN-PREDICATE position, used as a SECOND
signal for the decoupling grounds gate when the LLM `type_hint` under-fires.

Why it exists — two witnessed live failures of the LLM hint
(`_OPINION_REFRAME_RULE`, `extract.py:118-135`), whose worked examples both use
a contentful subject + copula:

  * **Idea/proposition as subject** (`TRU-52FB-DDC3`, F-VERDICT). "The
    learning-styles theory is indefensible" read as an *epistemic* claim, so no
    hint fired, decompose ran its baseline path, and the judgement was returned
    as an element marked ``+SUPPORTED`` by 11 sources. Tru8 rendered a VERDICT
    on a value judgement — invariant #7 and the product lock, both breached.
    There is no downstream guard for this: the only value-predicate lock in the
    codebase (``opinion_symmetry._is_restatement``) lives INSIDE the grounds
    stage and never runs when the hint misses.

  * **Extraposition** (`TRU-7EF2-087A`, P13 witness b). "It is indefensible for
    X to Y" has no contentful grammatical subject, so Rule 6's "incidental
    subjective adjectives are still cleaned" licence fires and the judgement is
    DELETED from the claim text. This voided a live-verification attempt — an
    already-paid cost, not a hypothetical.

The two shapes fail differently, which is why one call site cannot cover both:
in the first the evaluative head survives in ``claim.text`` (detect per claim);
in the second it survives ONLY in the source text (detect there, then restore).

Bias — recall via structure, precision via lexicon
-------------------------------------------------
The detector is OR-ed with the LLM hint and never unsets it, so its MISSES are
exactly today's behaviour and only its FALSE FIRES are new. That asymmetry sets
the design: fire unhedged on any main-predicate lexicon match (structure is
permissive), but admit only unambiguous value heads (lexicon is strict). The
lexicon grows witness-by-witness — one line plus one test — driven by the
residual-miss telemetry at `runner.py`, never by guesswork.

Over-correction guard (the headline risk on this track, cleared at the cost of
four live checks) is structurally unreachable from here: this module changes no
prompt bytes and no state derivation, and the battery's empirical negatives
("Thames Water discharged 72 billion litres…", "MMR uptake fell below…") carry
verb predicates with no copular evaluative head, so it CANNOT fire on them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

# ── Lexicon ─────────────────────────────────────────────────────────────────
# Closed, conservative, deliberately small. Both valences are listed: the
# invariant forbids distortion in EITHER direction, so a positive judgement
# ("a triumph") must route to neutral grounds exactly as a negative one does.
#
# Adjective and noun forms are enumerated explicitly — no stemming, which would
# widen the surface unpredictably.
#
# EXCLUDED BY DESIGN:
#   * Codified/adjudicable predicates — "illegal", "unconstitutional",
#     "anticompetitive", "defamatory". Rule 6 (`extract.py:127-130`) already
#     classes these as NOT evaluative; they have a legal test, so they are
#     researchable as plain claims.
#   * Dual-use lexemes — "failure", "success", "wrong", "bad", "gift". These
#     appear constantly in ordinary empirical prose ("heart failure is the
#     leading cause of…"), and a false fire is the only new behaviour this
#     module can produce.
#   * Impact adjectives — "disastrous", "catastrophic" (verification 2026-07-26).
#     Dropped after the independent verifier false-fired them on ordinary
#     empirical prose: "The 2010 harvest was disastrous for wheat yields",
#     "Coral bleaching is catastrophic for reef fish populations". These state a
#     MEASURED impact, not a judgement. Neither live witness (F-VERDICT, P13)
#     used them — they were guesswork, which this module's own growth rule
#     forbids. Re-add only on a real witness.
# The two head classes are kept SEPARATE, not merged into one list, because the
# extraposed frame behaves differently for each (re-verification round 4,
# 2026-07-26). A nominal head can take a `to`-prepositional phrase — "It is a
# disaster TO FARMERS" is a predicate nominal, not a judgement about a
# proposition — whereas an adjectival head cannot, so for adjectives a bare `to`
# reliably marks a complement clause.
#
# Three successive attempts to police this with a blocklist after `to` all
# failed, each admitting the shape the last one missed: `for` without `to`, then
# `to` without a determiner, then `to` + a determiner-less noun phrase (bare
# plurals, adjective-initial NPs, pronouns, possessives, unlisted quantifiers —
# 16/16 false fires, every one reaching RESTORATION, which rewrites the user's
# claim set). The set of noun-phrase-initial words is open, so no list can close
# it. Splitting by head class closes the CLASS: the determiner slot and the
# bare-`to` arm now never co-occur, and that combination was the whole defect.
_ADJECTIVAL_HEADS: List[str] = [
    # Negative — adjectival
    "indefensible",
    "inexcusable",
    "unconscionable",
    "unjustifiable",
    "disgraceful",
    "shameful",
    "appalling",
    "outrageous",
    "scandalous",
    "abhorrent",
    "deplorable",
    "reprehensible",
    "immoral",
    "unethical",
    "shambolic",
    # Positive — the invariant is symmetric
    "admirable",
    "commendable",
    "praiseworthy",
]

_NOMINAL_HEADS: List[str] = [
    # Negative
    "disaster",
    "catastrophe",
    "scandal",
    "disgrace",
    "fiasco",
    "farce",
    "shambles",
    "travesty",
    "betrayal",
    # Positive — the invariant is symmetric
    "triumph",
    "masterstroke",
]

_EVALUATIVE_HEADS: List[str] = _ADJECTIVAL_HEADS + _NOMINAL_HEADS

# Copulas that put the head in main-predicate position. Perfect and past forms
# are explicitly in scope — "has been a disaster" is as much a main-predicate
# judgement as "is a disaster".
_COPULA = r"(?:is|are|was|were|has\s+been|have\s+been|had\s+been|remains?)"

# Attribution frames. When the judgement is REPORTED rather than asserted, the
# claim is a plain factual claim about what someone said, and the decoupling
# track deliberately leaves those alone (Battery A's attributed-opinion result:
# 0 hints, correct).
#
# The guard searches the WHOLE sentence, not just the text before the head
# (verification 2026-07-26): post-posed attribution is the dominant journalistic
# form and bypassed a backward-only guard entirely — "The rollout has been a
# disaster, according to the NAO", '"The scheme is a fiasco," said the local MP',
# "It is indefensible …, say critics" (which reached the RESTORATION path).
# Searching both directions over-suppresses, and that is the correct error: a
# suppression is today's behaviour, whereas a false fire is new behaviour. This
# was proved rather than assumed — for 27 probe strings, seam output with the
# flag ON and OFF was byte-identical in 26, the exception being the one that
# legitimately fired (re-verification 2026-07-26).
#
# The hole is WIDE, not the single cute example it looks like. 13/14 genuine
# author judgements were suppressed, driven by the non-attributive senses of the
# bare stems `tell`/`told`/`found`/`suggest`/`warned`/`condemned`/`criticised`:
#   "It is indefensible that the minister said nothing."
#   "The figures tell a clear story: the rollout is a fiasco."
#   "Ministers were warned in 2018, and the delay is inexcusable."
# Two-clause "X happened, and Y is inexcusable" is especially exposed and is a
# very common shape for exactly the judgements this module exists to catch.
#
# The guard also still LEAKS in the other direction — `noted`/`observed`/
# `maintains`/`contends`/`stated`/`opined`/`complained` and non-verb frames
# ("In her view…", "For many voters…") bypass it. Simultaneously too wide and
# too narrow is the structural limit of a word list; closing it properly needs
# syntax, not more words. Deliberately not chased: an attributed judgement that
# fires is a category error, not the over-correction risk that governs here.
#
# NOTE: UK spellings only (`criticise`), consistent with house style — a
# US-spelled input escapes the guard.
_ATTRIBUTION = (
    # Bare stems are included where the noun reading is not a live risk, so the
    # inverted journalistic form ("…, say critics") is covered.
    #
    # The singular stems "claim", "report", "find" are excluded as common nouns
    # ("The claim is indefensible." fires). But their INFLECTIONS — claims,
    # reports, finds, found — are present and are equally common as nouns, so
    # the exclusion is partial, not the clean rule an earlier version of this
    # comment described (re-verification round 3, 2026-07-26): "The claims are
    # indefensible." and "The reports are a disgrace." suppress. Kept as-is
    # because the inflected forms carry real attribution ("The report claims the
    # scheme is a disaster") and the failure is a suppression — today's
    # behaviour — but the asymmetry is deliberate and recorded, not accidental.
    r"(?:say|says|said|saying|claimed|claims|argue|argued|argues|called|"
    r"describes?|described|according\s+to|reported|reports|insist|insisted|"
    r"insists|wrote|writes|conclude|concluded|concludes|found|finds|tell|told|"
    r"tells|believes?|fears?|feared|warn|warned|warns|accuse|accused|accuses|"
    r"branded|denounce|denounced|condemn|condemned|criticise|criticised|"
    r"criticises|allege|alleged|alleges|suggest|suggested|suggests)"
)


def _alt(heads: List[str]) -> str:
    """Regex alternation, longest-first so a longer head wins the match."""
    return "|".join(sorted(heads, key=len, reverse=True))


_HEADS_ALT = _alt(_EVALUATIVE_HEADS)
_ADJ_ALT = _alt(_ADJECTIVAL_HEADS)
_NOM_ALT = _alt(_NOMINAL_HEADS)

# Intensifiers that sit between the determiner and the head. `\w+ly` alone
# missed the commonest shape — "a COMPLETE disaster" (verification 2026-07-26),
# where the intensifier is not an -ly adverb.
_INTENSIFIER = (
    r"(?:complete|total|utter|absolute|unmitigated|real|genuine|outright|"
    r"downright|sheer|\w+ly)"
)

# The head must sit in FINAL predicate position — end of string, or immediately
# before punctuation.
#
# This boundary is the single most important guard in the module (verification
# 2026-07-26). Without it, a nominal head used as a NOUN MODIFIER matched, and
# 10/10 realistic empirical sentences false-fired: "is the disaster response
# body created in 1979", "was a catastrophe that killed at least 3,787 people",
# "is a disaster-prone state", "is a catastrophe reinsurer". Those are
# accountability-journalism inputs — core Tru8 subject matter — and routing them
# to neutral grounds is exactly the over-correction the live battery cleared.
#
# The cost is recall on trailing modifiers ("was a disaster for taxpayers" no
# longer fires). That cost is the right one to pay: a miss is today's behaviour.
_TERMINAL = r"(?=\s*(?:[.,;:!?\"')\]]|$))"

# Coordinators, subordinators and participles that start a NEW clause. The
# `for … to` window must not span one. The `[^.!?,;:]` class already forbids
# crossing a comma, so this list only ever matters for COMMA-LESS coordination —
# which is why an earlier, shorter list looked adequate while missing 6/6 ("It
# was a disaster for the region SO ministers agreed TO intervene").
_CLAUSE_BREAK = (
    r"\b(?:and|but|which|causing|leading|led|so|while|with|yet|after|before|"
    r"despite|though|although|since|because|until|unless)\b"
)

# Determiners and quantifiers, used ONLY as a narrowing lookahead inside
# `for … to`. This is not the discredited use: `_DET` failed as a PRIMARY
# discriminator after a bare `to` (the set it must exclude is open), but as a
# secondary narrowing inside an already-anchored `for … to` frame it costs
# nothing measurable. It was shipped in round 4 and silently lost in round 5 —
# restored here.
_DET = (
    r"(?:the\b|an?\b|his\b|her\b|its\b|their\b|our\b|my\b|many\b|most\b|"
    r"some\b|all\b|both\b|these\b|those\b)"
)

# A `for … to` complement, bounded so the frame cannot be completed by a `to`
# belonging to an unrelated later clause.
_FOR_TO = rf"for\b(?:(?!{_CLAUSE_BREAK})[^.!?,;:])*?\bto\s+(?!{_DET})\w+"

# The complement clause that makes an extraposed frame extraposed, SPLIT BY HEAD
# CLASS. A bare preposition is not enough on its own — "It is a disaster FOR THE
# REGION." is a predicate nominal plus a prepositional phrase, not a judgement
# about a proposition — but the right guard depends on what the head is:
#
#   * `that` — always a complement clause. Unambiguous.
#   * `for … to` — anchored at both ends and window-bounded. Unambiguous.
#   * bare `to` — REMOVED ENTIRELY, for both head classes.
#
# The bare-`to` arm asks "is the word after `to` a verb?", which a regex cannot
# decide. Four successive attempts to police it failed, each closing the
# witnessed instances and leaving the class open: `for` without `to`; `to`
# without a determiner; `to` + a determiner-less noun phrase (16/16 — bare
# plurals, adjective-initial NPs, pronouns, possessives, unlisted quantifiers);
# and finally, after splitting by head class, the same hole surviving on the
# ADJECTIVAL side via experiencer PPs (7/7 — "It is outrageous TO ME.", "It is
# appalling TO FARMERS."). That last one disproves the premise the split rested
# on: an adjectival head CAN take a `to`-PP after all.
#
# So the arm goes. Every remaining complement is anchored by a token that
# cannot be a preposition-plus-noun-phrase, and the undecidable question is
# never asked. Both live witnesses survive without it — F-VERDICT is
# predicative, P13 (b) is `for … to`.
#
# Cost, measured and accepted: a genuine bare-`to` infinitive misses ("It is a
# disgrace to admit this now.", "It is immoral to test on animals."). Recall
# only — a miss is provably today's behaviour, proved byte-for-byte in round 2
# (26/27 seam outputs identical with the flag ON and OFF).
#
# `for … to` is then split by head class, because it is a WEAKER form of the
# same undecidable question and the two classes can afford different answers:
#
#   * NOMINAL — `that` ONLY. The nominal `for … to` arm leaked 2/10 on
#     determiner-less objects ("It is a scandal for people living next to
#     landfill sites."), held up only by the `_DET` blocklist — the same
#     open-set guard that failed three times. Dropping it leaves the nominal
#     frame with a single wholly unambiguous complement and NO blocklist
#     anywhere in it. Cost: "It is a scandal for ministers to ignore the
#     findings." misses. Recall only, and no live witness uses it.
#   * ADJECTIVAL — keeps `for … to`, because P13 witness (b) IS that shape
#     ("It is indefensible FOR a government TO fund homeopathy"). `_DET` stays
#     here as a narrowing lookahead; this is the one remaining place the module
#     depends on a word list, and it is load-bearing for a live witness.
#
# THE LAST WORD-LIST GUARD LEAKS, AND THAT IS DELIBERATE (verification round 6).
# `_DET` catches only "to THE x", so determiner-less post-modifiers walk through
# — "It is indefensible for people living next to landfill sites." matches with
# a misparsed complement (8/8 measured). Lengthening `_DET` was rejected: it
# would buy parse accuracy that changes no outcome while re-introducing the
# open-set dependency that took four rounds to remove.
#
# The residue is bounded by CONSTRUCTION, not by probe luck. The extraposed
# frame requires `It is <evaluative head>` BEFORE any complement is parsed, so
# the sentence is already a value judgement by the time the complement matters.
# A misparse can therefore change WHICH judgement is caught, never WHETHER a
# factual claim is. Measured against the noun-modifier shapes that broke the
# predicative branch in round 1: 9/9 blocked, including "It is a disaster relief
# fund for flood victims.", "It is a fact that Thames Water discharged 72
# billion litres.", "It is reported that MMR uptake fell below 90%."
#
# This is why the two branches carry different guards. The PREDICATIVE branch
# CAN match empirical prose (a noun modifier can occupy the head position), so
# it is guarded by `_TERMINAL` — a closed, decidable question. Every genuinely
# harmful defect in six rounds lived there, and it has not leaked since round 2.
# The EXTRAPOSED branch cannot, so an open-set guard is survivable here and
# nowhere else.
_COMPLEMENT_ADJ = rf"(?:that\b|{_FOR_TO})"
_COMPLEMENT_NOM = r"(?:that\b)"

# Predicative: "<subject> is/was/has been [arguably] [a] [complete] disaster"
# The intensifier slot appears on BOTH sides of the determiner — English allows
# either order ("is arguably a disaster" / "is a complete disaster") and pinning
# it to one side missed the other (re-verification 2026-07-26). The optional
# quote/bracket admits 'is a "disaster".'
_PREDICATIVE_RE = re.compile(
    rf"\b{_COPULA}\s+(?:{_INTENSIFIER}\s+)?(?:an?\s+|the\s+)?"
    rf"(?:{_INTENSIFIER}\s+)?({_HEADS_ALT}){_TERMINAL}",
    re.IGNORECASE,
)

# Quotes and brackets are stripped to whitespace BEFORE matching rather than
# admitted into the pattern. An optional opening mark in the regex let
# `_TERMINAL` accept the CLOSING mark as valid terminal punctuation, so a
# scare-quoted noun modifier walked past the guard that kills the unquoted form
# — 'The scheme is a "disaster" relief fund.' fired (re-verification round 3).
# Normalising first means the head is judged on what actually follows it.
# Word-internal apostrophes are preserved so possessives do not fragment —
# curly `’` gets the same lookaround treatment as straight `'` so smart
# apostrophes survive too (round 4: `‘’` were missing entirely while `“”` were
# handled, an unintended asymmetry given how common smart quotes are in fetched
# HTML).
_QUOTE_RE = re.compile(r"[\"“”‘()\[\]]|(?<![A-Za-z])['’]|['’](?![A-Za-z])")

# Extraposed: "It is [a] indefensible|disgrace that/for/to …" — the shape whose
# judgement Rule 6 deletes outright. No terminal guard here: the head is
# followed by a complement clause by definition, and the frame is unambiguous
# (re-verification could not make this branch false-fire).
#
# The determiner slot is load-bearing. Without it the NOMINAL extraposed shape
# ("It is a disgrace/scandal/travesty/farce that …") fell between the two
# branches — the predicative branch rejects `head + that` on the terminal guard,
# and this one had nowhere to put the article. That was a recall REGRESSION
# introduced by the terminal guard, caught in re-verification: 5/5 of those
# fired before it and 0/5 after. It is also the module's own core shape, and
# routing it here (rather than as "predicative") means restoration now covers
# it — the more correct outcome.
# Two patterns, because the complements now genuinely differ by head class.
# (They were briefly collapsed into one when both allowed `that | for … to`;
# that unification was correct at the time and is wrong now.)
#
# The adjectival frame has no determiner slot — an adjective takes no article.
_EXTRAPOSED_ADJ_RE = re.compile(
    rf"\bit\s+(?:is|was)\s+(?:{_INTENSIFIER}\s+)?({_ADJ_ALT})\s+{_COMPLEMENT_ADJ}",
    re.IGNORECASE,
)

_EXTRAPOSED_NOM_RE = re.compile(
    rf"\bit\s+(?:is|was)\s+(?:{_INTENSIFIER}\s+)?(?:an?\s+|the\s+)?"
    rf"(?:{_INTENSIFIER}\s+)?({_NOM_ALT})\s+{_COMPLEMENT_NOM}",
    re.IGNORECASE,
)

_ATTRIBUTION_RE = re.compile(rf"\b{_ATTRIBUTION}\b", re.IGNORECASE)

# Sentence splitter — the attribution guard is sentence-local so that a
# neighbouring sentence's unrelated "reported" does not suppress a genuine
# judgement. Requires a capital/quote after the boundary so abbreviations do NOT
# split (verification 2026-07-26: "According to the NAO, the U.S. rollout was a
# disaster" split at "U.S. ", stranding the guard in the discarded fragment).
# Mirrors `extract.py::_SENTENCE_BOUNDARY_RE`.
# Quotes are stripped before this runs, so a quote can never appear after a
# boundary — the lookahead is `[A-Z]` only. An earlier version carried a
# `["'(]` alternation that was dead code; it is deleted rather than made live,
# because making it live cost two safe behaviours (round 5).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


@dataclass(frozen=True)
class EvaluativeHead:
    """A value judgement found in main-predicate position.

    ``shape`` is ``"predicative"`` ("X is indefensible") or ``"extraposed"``
    ("It is indefensible that X") — the caller needs the distinction because
    only the extraposed shape loses its head during extraction.
    """

    head: str
    shape: str


def _is_attributed(sentence: str) -> bool:
    """True when this sentence frames the judgement as REPORTED.

    Reported stances stay plain claims (the decoupling track's own rule), so a
    judgement introduced or closed by "said" / "according to" must not arm the
    grounds gate. Searches the whole sentence — see `_ATTRIBUTION` for why
    over-suppression is the correct error here.
    """
    return bool(_ATTRIBUTION_RE.search(sentence))


def find_evaluative_head(text: Optional[str]) -> Optional[EvaluativeHead]:
    """Return the main-predicate value judgement in ``text``, or None.

    Pure and idempotent. Checks the extraposed shape first — "It is indefensible
    that…" also matches the predicative copula pattern, and the extraposed label
    is the one that tells the caller the head is at risk of deletion.
    """
    if not text:
        return None

    # Strip quotes BEFORE splitting. Round 5 tried the reverse, to make the
    # splitter's quote alternation live rather than dead code, and it cost two
    # behaviours: an abbreviation followed by a quote split and stranded the
    # attribution guard, and quoted speech un-merged from its "He said."
    # so an attributed quotation escaped suppression. Both were safe under
    # strip-first. The dead alternation was cosmetic; these were not.
    normalised = _QUOTE_RE.sub(" ", text.strip())

    for sentence in _SENTENCE_SPLIT_RE.split(normalised):
        if not sentence.strip() or _is_attributed(sentence):
            continue

        for pattern in (_EXTRAPOSED_ADJ_RE, _EXTRAPOSED_NOM_RE):
            extraposed = pattern.search(sentence)
            if extraposed:
                return EvaluativeHead(
                    head=extraposed.group(1).lower(), shape="extraposed"
                )

        predicative = _PREDICATIVE_RE.search(sentence)
        if predicative:
            return EvaluativeHead(
                head=predicative.group(1).lower(), shape="predicative"
            )

    return None


def has_evaluative_head(text: Optional[str]) -> bool:
    """Convenience predicate over :func:`find_evaluative_head`."""
    return find_evaluative_head(text) is not None
