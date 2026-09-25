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
#:
#: 2026-09-22: extended to the FORMAL-PUBLICATION speech acts. An inquiry,
#: regulator or study does not "say" its findings, it recommends, specifies,
#: publishes or concludes them — and an element built on one ("The Inquiry
#: specified a statutory barring system") is attribution-shaped in exactly the
#: same way. Production record `8d66d41a` filed the Thirlwall Inquiry's OWN
#: report as context against its own printed sentence because these verbs were
#: absent here.
#:
#: Deliberately NOT included: "found", "shows", "reports". Those read as the
#: finding itself at least as often as the act of stating it, and widening the
#: disarm on an ambiguous verb costs more than the recitals it would spare.
_ATTRIBUTION_SHAPED_ELEMENT = re.compile(
    r"\b(said|says|stated|claim(?:s|ed)|announced|asserted|denied|"
    r"according\s+to|"
    r"recommend(?:s|ed|ation|ations)|specif(?:ies|ied)|"
    r"publish(?:es|ed)|conclud(?:es|ed)|propos(?:es|ed|al|als)|"
    r"urg(?:es|ed)|advis(?:es|ed)|called\s+for|set\s+out)\b",
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
    text: Optional[str],
    patterns: List[re.Pattern],
    release: Optional["DirectionRelease"] = None,
) -> Tuple[str, Optional[Dict[str, str]]]:
    """One text's verdict: veto beats fire beats silence. R6 (`release`) skips
    a match that cannot be what the reference rests on."""
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
        for match in pattern.finditer(text):
            if release is not None and release.releases(text, match):
                continue
            return _FIRE, {
                "marker": match.group(0)[:60].lower(),
                "excerpt": _excerpt(text, match.start(), match.end()),
            }
    return _SILENT, None


# ── Evidence-text narrowing (A− recital review, 2026-09-24) ───────────────────
# Record 1ca0070f / cb939365 / 1c90a8bb: 9 of the 12 recital fires on the 19
# graded records were wrong, all through the EVIDENCE-TEXT path, each on a
# sentence the support did not rest on. These rules narrow that path only; the
# reasoning path and the subject-free restatement path are untouched, and every
# rule releases supports and challenges alike (invariant #7).
#   R0  a match cannot cross a sentence or bullet boundary
#   R1  "according to the article / <a domain>" is the source naming itself
#   R2  declined or negated speech ("declines to say") asserts nothing
#   R5  passive voice ("X's donation was announced") never anchors
#   R3  the claim reports an ORG's own publication (main verb) — handled by the
#       caller passing that subject's tokens as released
#   R4  an actor announcing their OWN transactional act, where the claim's verb
#       is performative or the same text states the claim's figure in its own
#       voice (review: "Trump announced he ended the war" stays gated — "ended"
#       is not a transactional act)
_SENTENCE_BREAK = re.compile(r"[.!?][\"')\]\u2019\u201d]?\s|\n|\s[-\u2022]\s")
_SELF_REFERENCE = re.compile(
    r"^according\s+to\s+(?:the\s+(?:article|report|piece|story|source|post|page)\b|"
    r"this\s+(?:article|report|piece|story)\b|[\w-]+(?:\.[\w-]+)*\.(?:com|org|net|news|io|gov|uk|ie|eu)\b)",
    re.IGNORECASE,
)
_NEGATED_SPEECH = re.compile(
    r"\b(?:declin\w*|refus\w*|would\s+not|did\s+not|does\s+not|won't|wouldn't|didn't|doesn't)\b",
    re.IGNORECASE,
)
_PASSIVE_SPEECH = re.compile(
    r"\b(?:was|were|been|being|is|are|be)\s+(?:\w+ly\s+)?(?:announc\w*|said|claimed|declared|asserted|touted)\s*$",
    re.IGNORECASE,
)
_SELF_ASSESSMENT = re.compile(
    r"\b(?:claim\w*|tout\w*|boast\w*|insist\w*)\b", re.IGNORECASE
)
_TRANSACTION_ACT = re.compile(
    r"\b(donat\w*|gift\w*|pledg\w*|match\w*|resign\w*|appoint\w*|acqui\w*|purchas\w*)",
    re.IGNORECASE,
)
_TRANSFER_STEMS = frozenset({"donat", "gift", "pledg", "match"})
_MONEY_FROM = re.compile(
    r"\d[\d.,]*\s*(?:m|bn|million|billion)?\b[^.]{0,40}\bfrom\b", re.IGNORECASE
)
_PERFORMATIVE_CLAIM = re.compile(
    r"\b(?:pledg\w*|announc\w*|appoint\w*|resign\w*|nominat\w*)\b", re.IGNORECASE
)
#: Elements that assess the act ("the biggest ever") are not released by R4.
_SELF_ASSESSING_ELEMENT = re.compile(
    r"\b(?:biggest|largest|record|most|first|ever|unprecedented|highest|lowest|best|worst)\b",
    re.IGNORECASE,
)
_SPEECH_OR_SOURCE = re.compile(
    rf"\b(?:{_ATTRIBUTION_VERBS}|stated|according\s+to)\b", re.IGNORECASE
)
_FIGURE = re.compile(r"\d[\d.,]*\d|\d")


def _act_stems(text: str) -> set:
    stems = {m.group(1).lower()[:5] for m in _TRANSACTION_ACT.finditer(text or "")}
    if stems & _TRANSFER_STEMS or _MONEY_FROM.search(text or ""):
        stems |= _TRANSFER_STEMS
    return stems


def _sentence_around(text: str, start: int, end: int) -> str:
    breaks = [m.end() for m in _SENTENCE_BREAK.finditer(text[:start])]
    lo = breaks[-1] if breaks else 0
    nxt = _SENTENCE_BREAK.search(text, end)
    hi = nxt.start() + 1 if nxt else len(text)
    return text[lo:hi]


def _own_voice_figure(text: str, claim_texts: Iterable[str]) -> bool:
    """The text states one of the claim's figures in a sentence that attributes
    nothing — the source reports the number itself, not someone's account of it."""
    figures = {
        f.replace(",", "")
        for c in claim_texts
        for f in _FIGURE.findall(c or "")
        if len(f.replace(",", "").replace(".", "")) >= 2
        and not re.fullmatch(r"(?:19|20)\d\d", f)
    }
    if not figures:
        return False
    for sentence in _SENTENCE_BREAK.split(text or ""):
        if _SPEECH_OR_SOURCE.search(sentence):
            continue
        if figures & {f.replace(",", "") for f in _FIGURE.findall(sentence)}:
            return True
    return False


class EvidenceNarrowing:
    """What the evidence-text path needs to apply R0–R5."""

    def __init__(
        self,
        claim_texts: Iterable[str] = (),
        element_text: str = "",
        released_tokens: Iterable[str] = (),
    ):
        self.claim_texts = [c for c in claim_texts if c]
        self.element_text = element_text or ""
        self.released_tokens = {t.lower() for t in released_tokens}

    def skip(self, text: str, match: "re.Match[str]", token: str, kind: str) -> bool:
        span = match.group(0)
        if _SENTENCE_BREAK.search(span):  # R0
            return True
        if token.lower() in self.released_tokens:  # R3
            return True
        if kind == "according":
            return bool(_SELF_REFERENCE.match(span))  # R1
        if kind != "verb":
            return False
        if _NEGATED_SPEECH.search(span):  # R2
            return True
        if _PASSIVE_SPEECH.search(span):  # R5
            return True
        return self._transactional(text, match)  # R4

    def _transactional(self, text: str, match: "re.Match[str]") -> bool:
        sentence = _sentence_around(text, match.start(), match.end())
        if _SELF_ASSESSMENT.search(sentence):
            return False
        if _SELF_ASSESSING_ELEMENT.search(self.element_text):
            return False
        claim_stems = (
            set().union(*(_act_stems(c) for c in self.claim_texts))
            if self.claim_texts
            else set()
        )
        if not (_act_stems(sentence) & claim_stems):
            return False
        performative = any(_PERFORMATIVE_CLAIM.search(c) for c in self.claim_texts)
        return performative or _own_voice_figure(text, self.claim_texts)


def _tagged_patterns(
    tokens: Iterable[Tuple[str, str]]
) -> List[Tuple[re.Pattern, str, str]]:
    """`_subject_patterns`, each tagged with its token and kind."""
    tagged: List[Tuple[re.Pattern, str, str]] = []
    compiled = _subject_patterns(tokens)
    kinds = ("verb", "quote", "according")
    for i, (token, _s) in enumerate(tokens):
        for j, kind in enumerate(kinds):
            tagged.append((compiled[i * 3 + j], token, kind))
    return tagged


def _assess_evidence(
    text: Optional[str],
    tagged: List[Tuple[re.Pattern, str, str]],
    narrowing: "EvidenceNarrowing",
    release: Optional["DirectionRelease"] = None,
) -> Tuple[str, Optional[Dict[str, str]]]:
    """`_assess` for the EVIDENCE text, with R0–R6 applied per match."""
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
    for pattern, token, kind in tagged:
        # Overlapping search: a skipped match that started at an EARLIER token
        # occurrence ("Delo gave ... / Delo announced", skipped by R0) must not
        # hide the real one starting at the next occurrence.
        pos = 0
        while True:
            match = pattern.search(text, pos)
            if match is None:
                break
            pos = match.start() + 1
            if narrowing.skip(text, match, token, kind):
                continue
            if release is not None and release.releases(text, match):
                continue
            return _FIRE, {
                "marker": match.group(0)[:60].lower(),
                "excerpt": _excerpt(text, match.start(), match.end()),
            }
    return _SILENT, None


# ── Direction release, R6 (2026-09-25) ────────────────────────────────────────
# Design: audit/2026-09-25_recital_direction_release_design.md; review:
# audit/2026-09-25_recital_direction_release_review.md (classifier reworked).
#
# A reference can only REST on a recital that points its own way. On corpus
# claim TRU-018F-44AA all four recital fires were fact-check CHALLENGES whose
# attribution sentence was the claim itself, restated so it could be rebutted:
# "Trump says he's ended eight wars. His numbers are off". The challenge rests
# on the rebuttal; demoting it made a false claim look less challenged than it
# was (invariant #7).
#
# Released, on a `challenges` ref ONLY:
#   a subject-anchored match, spoken BY that subject (not "critics of Trump
#   say"), not itself a denial or a lower-figure / "only" account, in a text
#   that presents THAT subject solely as the claim's proponent: it reports
#   them restating the claim (a self-report: "he has", "to have", "of having",
#   sharing >= 2 content stems with the claim or element, same polarity) and
#   never contradicting it.
# Everything else fires exactly as before. A self-serving contrary account
# ("Biden says inflation was caused by Putin") is not a self-report of the
# claim; a denial never releases.
#
# The supports mirror (a support resting on a DENIAL) is deliberately NOT
# built: the review showed every polarity heuristic reaching the trap through
# it. Releasing only challenges whose text restates the claim cannot release a
# recital support.
_SELF_REPORT_HEAD = re.compile(
    r"^[\s,:'\"‘’“”]*(?:to\s+(?:have\s+)?[a-z]|of\s+having\b|"
    r"(?:that\s+)?(?:he|she|i)\b)",
    re.IGNORECASE,
)
_SELF_REPORT_PRONOUN = re.compile(
    r"\b(?:he|she|i)(?:['’](?:s|ve|d|m|ll)\b|"
    r"\s+(?:has|have|had|was|is|would|will|did)\b)",
    re.IGNORECASE,
)
_ENDS_TO_HAVE = re.compile(r"\bto\s+have\s*$", re.IGNORECASE)
#: Negation that can deny a predicate. "no" and "without" are excluded: they
#: negate a noun ("no president could", "without a single casualty").
_NEGATION = re.compile(
    r"\b(?:not|never|neither|nor|den(?:y|ies|ied))\b|n['’]t\b", re.IGNORECASE
)
#: A downtoner makes a self-report contrary to the claim: "he has only ended
#: two wars" does not restate "stopped 6 wars".
_DOWNTONER = re.compile(
    r"\b(?:only|just|merely|barely|fewer|less\s+than)\b", re.IGNORECASE
)
#: Words allowed between the subject token and the speech verb while the
#: subject is still the SPEAKER. Anything else ("Trump's aides say") means
#: someone else speaks.
_SPEAKER_BRIDGE = re.compile(
    r"^(?:['’]s)?(?:\s+(?:has|have|had|was|is|repeatedly|also|again|then|"
    r"later|himself|herself|once|now|\w+ly))*\s*$",
    re.IGNORECASE,
)
#: A word just before the token that makes it an object, not the speaker.
_OBJECT_LEAD = re.compile(
    r"\b(?:of|for|against|about|by|to|with|on|at|from|than|over|under|toward|"
    r"towards)\s+(?:(?:president|former|mr|mrs|ms|dr|the)\.?\s+){0,3}$",
    re.IGNORECASE,
)
_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
_STOP = frozenset(
    "the a an and or of to in on at for by with from that this these those his her "
    "their its our was were is are be been has have had he she they we i it as than "
    "into over under about after before during while which who whom what when where "
    "why how all any some such very more most also only just said says say saying "
    "claim claims claimed stated not never no nor neither without".split()
)
#: Voice. A self-report is passive when a be-verb precedes its first shared
#: stem AND one of its first two shared words is a participle ("she was the
#: one physically abused"); "he was responsible for ending" stays active. The
#: claim's own voice is read from "<be> <participle> by".
_BE_VERB = re.compile(r"\b(?:was|were|been|being|is|are)\b", re.IGNORECASE)
_PARTICIPLE = re.compile(r"(?:ed|en)$", re.IGNORECASE)
_PASSIVE_CLAIM = re.compile(
    r"\b(?:was|were|been|being|is|are)\s+(?:\w+ly\s+)?\w+(?:ed|en)\s+by\b",
    re.IGNORECASE,
)
_SELF_REPORT_WINDOW = 120
_NEGATION_WINDOW = 4
_MIN_SHARED_STEMS = 2
_RESTATES, _CONTRARY = "restates", "contrary"


def _stem(word: str) -> str:
    w = word.lower()
    if w in _NUMBER_WORDS:
        return str(_NUMBER_WORDS[w])
    for suffix in ("ing", "ed", "es", "s"):
        if len(w) > len(suffix) + 2 and w.endswith(suffix):
            w = w[: -len(suffix)]
            break
    return w[:6]


def _numbers(text: str) -> List[float]:
    out: List[float] = []
    for word in re.findall(r"\d[\d,]*(?:\.\d+)?|[A-Za-z]+", text or ""):
        low = word.lower()
        if low in _NUMBER_WORDS:
            out.append(float(_NUMBER_WORDS[low]))
        elif word[0].isdigit():
            try:
                value = float(word.replace(",", ""))
            except ValueError:
                continue
            if not 1900 <= value <= 2100:  # a year is not a count
                out.append(value)
    return out


class DirectionRelease:
    """R6: whether a `challenges` ref's subject-anchored match is the claim
    restated by its proponent, and so never the basis of that challenge."""

    def __init__(
        self,
        direction: Optional[str],
        claim_texts: Iterable[str] = (),
        element_text: str = "",
        tokens: Iterable[Tuple[str, str]] = (),
    ):
        self.direction = direction
        texts = [c for c in claim_texts if c]
        self.tokens = [(t, s) for t, s in tokens if t]
        self._subject_words = {
            w for _t, s in self.tokens for w in re.findall(r"[a-z0-9]+", s.lower())
        } | {t.lower() for t, _s in self.tokens}
        # Polarity from the NORMALISED claim (texts[0]) only.
        self.claim_negated = bool(texts) and bool(_NEGATION.search(texts[0]))
        self.claim_passive = bool(texts) and bool(_PASSIVE_CLAIM.search(texts[0]))
        self.claim_stems = {
            _stem(w)
            for w in re.findall(r"[A-Za-z0-9]+", " ".join(texts + [element_text or ""]))
            if w.lower() not in _STOP
            and w.lower() not in self._subject_words
            and (w.isdigit() or len(w) >= 3)
        }
        claim_numbers = _numbers(" ".join(texts))
        self.claim_min_number = min(claim_numbers) if claim_numbers else None
        tagged = _tagged_patterns(self.tokens)
        subjects = [s for _t, s in self.tokens for _ in range(3)]
        self._tagged = [
            (pattern, token, kind, subject)
            for (pattern, token, kind), subject in zip(tagged, subjects)
        ]
        self._owner = {
            pattern.pattern: (token, kind, subject)
            for pattern, token, kind, subject in self._tagged
        }
        self._stance_cache: Dict[str, Dict[str, set]] = {}

    # ── one match ─────────────────────────────────────────────────────────────
    def _speaker_is_subject(
        self, text: str, match: "re.Match[str]", token: str, kind: str
    ) -> bool:
        if kind != "verb":
            # "quotes … Trump" / "according to Trump": no self-report shape.
            return False
        span = match.group(0)
        tok = re.match(rf"{re.escape(token)}\b", span, re.IGNORECASE)
        if tok is None:
            return False
        bridge = re.sub(
            rf"\b(?:{_ATTRIBUTION_VERBS})\b\s*$",
            "",
            span[tok.end() :],
            flags=re.IGNORECASE,
        )
        # The subject's own other words ("Donald [Trump] claims") are not a
        # different speaker.
        for word in self._subject_words:
            bridge = re.sub(rf"\b{re.escape(word)}\b", "", bridge, flags=re.IGNORECASE)
        if not _SPEAKER_BRIDGE.match(bridge):
            return False
        before = text[max(0, match.start() - 40) : match.start()]
        # "Donald Trump" anchors on its last token too: strip the subject's
        # other words before reading the word that leads the name.
        if self._subject_words:
            before = re.sub(
                r"(?:\b(?:"
                + "|".join(re.escape(w) for w in sorted(self._subject_words))
                + r")\s+)+$",
                "",
                before,
                flags=re.IGNORECASE,
            )
        return not _OBJECT_LEAD.search(before)

    @staticmethod
    def _speech_skipped(span: str) -> bool:
        """R0 (sentence crossing), R2 (declined/negated speech), R5 (passive)."""
        return bool(
            _SENTENCE_BREAK.search(span)
            or _NEGATED_SPEECH.search(span)
            or _PASSIVE_SPEECH.search(span)
        )

    def classify(self, text: str, match: "re.Match[str]") -> Optional[str]:
        """_RESTATES / _CONTRARY for a self-report of the claim, else None."""
        breaks = _SENTENCE_BREAK.search(text, match.end())
        tail = text[match.end() : breaks.start() if breaks else len(text)]
        if _ENDS_TO_HAVE.search(match.group(0)) or _SELF_REPORT_HEAD.search(tail):
            content = tail
        else:
            pronoun = _SELF_REPORT_PRONOUN.search(tail[:_SELF_REPORT_WINDOW])
            if pronoun is None:
                return None
            content = tail[pronoun.start() :]
        # Keep "n't" attached, so "didn't" stays one negated word.
        words = re.findall(r"[A-Za-z0-9]+(?:['’]t\b)?", content)
        shared: List[str] = []
        shared_words: List[str] = []
        first_shared_at: Optional[int] = None
        for idx, word in enumerate(words):
            low = word.lower()
            if low in _STOP or low in self._subject_words or _NEGATION.search(word):
                continue
            stem = _stem(word)
            if stem in self.claim_stems and stem not in shared:
                shared.append(stem)
                shared_words.append(word)
                if first_shared_at is None:
                    first_shared_at = idx
        if len(shared) < _MIN_SHARED_STEMS:
            return None
        head = words[: first_shared_at or 0][-_NEGATION_WINDOW:]
        if bool(_NEGATION.search(" ".join(head))) != self.claim_negated:
            return _CONTRARY
        # Voice: "she was the one abused" reverses "Heard abused Depp".
        passive = bool(_BE_VERB.search(" ".join(head))) and any(
            _PARTICIPLE.search(w) for w in shared_words[:2]
        )
        if passive != self.claim_passive:
            return _CONTRARY
        if _DOWNTONER.search(content):
            return _CONTRARY
        if self.claim_min_number is not None and any(
            n < self.claim_min_number for n in _numbers(content)
        ):
            return _CONTRARY
        return _RESTATES

    # ── one text ──────────────────────────────────────────────────────────────
    def _stances(self, text: str) -> Dict[str, set]:
        """Per subject: the self-report kinds this text attributes to them."""
        if text in self._stance_cache:
            return self._stance_cache[text]
        kinds: Dict[str, set] = {}
        for pattern, token, kind, subject in self._tagged:
            pos = 0
            while True:
                match = pattern.search(text, pos)
                if match is None:
                    break
                pos = match.start() + 1
                if self._speech_skipped(match.group(0)):
                    continue
                if not self._speaker_is_subject(text, match, token, kind):
                    continue
                found = self.classify(text, match)
                if found:
                    kinds.setdefault(subject, set()).add(found)
        self._stance_cache[text] = kinds
        return kinds

    def releases(self, text: str, match: "re.Match[str]") -> bool:
        """True when this attribution cannot be what the challenge rests on."""
        if self.direction != "challenges" or not self.claim_stems:
            return False
        owner = self._owner.get(match.re.pattern)
        if owner is None:
            return False
        token, kind, subject = owner
        # Only the subject's own speech is released; "aides of Trump say"
        # fires as before. A denial by the subject needs no separate check:
        # it puts _CONTRARY into the stance, which then never equals {_RESTATES}.
        if not self._speaker_is_subject(text, match, token, kind):
            return False
        return self._stances(text).get(subject) == {_RESTATES}


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

# A reported study finding may naturally repeat the proposition it establishes.
# This is a narrow candidate-only exemption from lexical overlap, not from
# explicit attribution or distancing, and not a certification of the result.
_STUDY_FRAME = re.compile(r"\b(?:trial|study|survey|analysis|experiment)\b", re.I)
_RESULT_VERB = re.compile(
    r"\b(?:found|observed|reported|demonstrated|reduced|increased|showed)\b", re.I
)
_FINDING_DETAIL = re.compile(
    r"\b(?:randomi[sz]ed|observational|survey|experiment|cohort|"
    r"found|observed|reported|demonstrated|showed)\b",
    re.I,
)
_NON_RESULT = re.compile(
    r"\b(?:claim\w*|says?|said|saying|according\s+to|allegedly|purportedly|"
    r"supposedly|hypothes\w*|expect\w*|predict\w*|will|would|could|may|might|"
    r"aim\w*|plan\w*|whether|protocol|not|no|never)\b|[\"“”]",
    re.I,
)


def _reports_overlapping_result(evidence_text: str, claim_sq: str) -> bool:
    """Require finding framing in the overlapping sentence, not elsewhere."""
    for sentence in re.split(r"(?<=[.!?])\s+|[\r\n]+", evidence_text):
        if (
            _STUDY_FRAME.search(sentence)
            and _RESULT_VERB.search(sentence)
            and any(
                _squash(m[0]) not in claim_sq
                for m in _FINDING_DETAIL.finditer(sentence)
            )
            and not _NON_RESULT.search(sentence)
            and _longest_common_run(claim_sq, _squash(sentence))
            >= max(_MIN_MATCH_CHARS, int(len(claim_sq) * _RESTATEMENT_RATIO))
        ):
            return True
    return False


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
    evidence_text: Optional[str],
    claim_text: Optional[str],
    *,
    allow_reported_results: bool = False,
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

    if allow_reported_results and _reports_overlapping_result(evidence_text, claim_sq):
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
    *,
    allow_reported_results: bool = False,
    narrowing: Optional["EvidenceNarrowing"] = None,
    release: Optional["DirectionRelease"] = None,
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

        verdict, entry = _assess(reasoning, patterns, release)
        if verdict == _VETOED:
            return None
        if verdict == _FIRE and entry is not None:
            entry["found_in"] = "reasoning"
            return entry

        if narrowing is not None:
            verdict, entry = _assess_evidence(
                evidence_text, _tagged_patterns(tokens), narrowing, release
            )
        else:
            verdict, entry = _assess(evidence_text, patterns, release)
        if verdict == _FIRE and entry is not None:
            entry["found_in"] = "evidence"
            return entry

    # Subject-free fallback. Runs when the claim names nobody, and also when it
    # names someone but the attribution wording never appeared — a source can
    # recite a claim without naming who made it.
    return claim_restatement_match(
        evidence_text, claim_text, allow_reported_results=allow_reported_results
    )
