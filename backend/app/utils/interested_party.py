"""Interested-party tagger — a source controlled by the claim's subject (2026-08-13).

Design: audit/2026-08-13_assertion_evidence_design.md, section 4.

WHY THIS EXISTS, AND WHY IT CANNOT BE A PROMPT ALONE
----------------------------------------------------
Production check `TRU-018F-44AA` ("Donald Trump stopped 6 wars") returned
`supported` on every element. Two of the heaviest supports were the claimant's
own press office — whitehouse.gov's "I've solved six wars in six months" and
"365 WINS IN 365 DAYS" — each classified `primary` (correctly: they ARE official
statements) and therefore weighed 3 against PolitiFact's "Pants on Fire" at
commentary weight 1. The tier ladder encodes proximity to the event and spends
it as reliability; for a claim whose subject IS the source, proximity inverts —
the closest source is the interested one.

WHAT IT DOES, AND DELIBERATELY DOES NOT DO
------------------------------------------
Where a claim names its subjects (key_entities, PERSON/ORG) and an evidence item
comes from a domain CONTROLLED BY one of those subjects, the relationship is
scoped to "context". Tier is untouched — classification stays descriptive
(invariant #6) — and nothing is deleted; the exclusion carries a receipt
(invariant #5).

**Symmetric on purpose**: it scopes a subject's self-praise out of `supports`
exactly as it scopes a subject's self-serving denial out of `challenges`. For
"Company X polluted the river", the company's own denial becomes context with a
receipt — visible, never counted as refutation. A gate that fired one way only
would be the sycophancy mechanism invariant #7 forbids.

Two prongs, either sufficient, both conservative (absent match → no fire, the
safe direction):

  1. **Name-in-domain.** A distinctive subject token (≥4 chars, stop-listed)
     starts a label of the evidence hostname — `trumpwhitehouse.archives.gov`
     for "Donald Trump", `trump.org`, most company domains for claims naming
     the company. Label-START matching, not substring: "donald" must not match
     mcdonalds.com.
  2. **Executive-comms map.** Political communications organs → the office they
     speak for, term-matched against the subject set. Deliberately NOT in the
     map: statistics offices and central banks (ons.gov.uk, bls.gov —
     statistically independent), and legislature member sites (a congressman
     endorsing is aligned, not controlled). Incomplete by construction, exactly
     as the jurisdiction gate's domain map is.
"""

from __future__ import annotations

import re
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

#: Tokens too generic to identify a subject inside a hostname. Includes common
#: institutional words AND generic given-name/word collisions observed or
#: foreseeable in domains.
_STOP_TOKENS = frozenset(
    {
        "american",
        "association",
        "authority",
        "bank",
        "best",
        "board",
        "british",
        "bureau",
        "center",
        "centre",
        "commission",
        "committee",
        "company",
        "corp",
        "corporation",
        "council",
        "county",
        "daily",
        "data",
        "department",
        "east",
        "fact",
        "federal",
        "foundation",
        "free",
        "general",
        "global",
        "government",
        "group",
        "health",
        "home",
        "house",
        "inquiries",
        "inquiry",
        "institute",
        "international",
        "journal",
        "kingdom",
        "life",
        "live",
        "mail",
        "media",
        "minister",
        "ministry",
        "national",
        "news",
        "north",
        "office",
        "online",
        "panel",
        "party",
        "political",
        "post",
        "president",
        "press",
        "prime",
        "real",
        "regulator",
        "report",
        "research",
        "royal",
        "secretary",
        "service",
        "south",
        "state",
        "states",
        "time",
        "times",
        "today",
        "tribunal",
        "true",
        "union",
        "united",
        "university",
        "west",
        "white",
        "world",
        "york",
    }
)

#: Political communications organs → terms identifying the office/administration
#: they speak for. A domain fires only when one of its terms appears inside a
#: subject string. Officeholder surnames are maintained by hand — an absent name
#: means the executive-comms prong stays quiet (name-in-domain may still catch
#: it). ⚠️ Incomplete by construction; extend from observed failures only.
_EXECUTIVE_COMMS: Dict[str, Tuple[str, ...]] = {
    "whitehouse.gov": (
        "white house",
        "trump",
        "biden",
        "obama",
        "president of the united states",
        "us president",
        "u.s. president",
        "us government",
        "u.s. government",
        "united states government",
        "trump administration",
        "biden administration",
    ),
    "trumpwhitehouse.archives.gov": (
        "white house",
        "trump",
        "trump administration",
    ),
    "obamawhitehouse.archives.gov": (
        "white house",
        "obama",
        "obama administration",
    ),
    "bidenwhitehouse.archives.gov": (
        "white house",
        "biden",
        "biden administration",
    ),
    "state.gov": (
        "state department",
        "department of state",
        "us government",
        "u.s. government",
        "trump administration",
        "biden administration",
    ),
    "number10.gov.uk": (
        "number 10",
        "no 10",
        "downing street",
        "uk government",
        "starmer",
        "sunak",
    ),
    "pm.gov.uk": (
        "downing street",
        "uk government",
        "starmer",
        "sunak",
    ),
}


def claim_subjects(entities: Optional[Iterable[Any]]) -> List[str]:
    """Lower-cased PERSON/ORG entity texts — the claim's subject set.

    Accepts the `key_entities` shape ({"text": ..., "type": ...}) or plain
    strings (already-normalised metadata). Anything else is skipped: an absent
    or malformed subject means the gate does not arm, the safe direction.
    """
    subjects: List[str] = []
    for ent in entities or []:
        if isinstance(ent, str):
            text = ent
        elif isinstance(ent, dict):
            if str(ent.get("type", "")).upper() not in ("PERSON", "ORG"):
                continue
            text = ent.get("text") or ""
        else:
            continue
        text = text.strip().lower()
        if text and text not in subjects:
            subjects.append(text)
    return subjects


def distinctive_tokens(subjects: Iterable[str]) -> List[Tuple[str, str]]:
    """(token, owning subject) pairs distinctive enough to anchor a match.

    ≥4 characters, alphabetic, not stop-listed. Shared with the recital gate,
    which anchors attribution verbs on the same tokens.
    """
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for subject in subjects:
        for token in subject.split():
            token = "".join(ch for ch in token if ch.isalpha())
            if len(token) < 4 or token in _STOP_TOKENS or token in seen:
                continue
            seen.add(token)
            pairs.append((token, subject))
    return pairs


def _hostname(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        host = urlparse(url).hostname
    except ValueError:
        return None
    if not host:
        return None
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def _is_executive_comms(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in _EXECUTIVE_COMMS)


def interested_party_match(
    subjects: List[str],
    url: Optional[str],
    released: FrozenSet[str] = frozenset(),
) -> Optional[Dict[str, str]]:
    """The receipt entry if this URL's domain is controlled by a claim subject.

    Returns None when no prong matches — including every malformed or absent
    input — so the caller can use it directly as the gate's `fires`.

    ``released`` (from :func:`released_subjects`) are subjects whose OWN
    domain is the record of what the claim reports. They are skipped on prong 1
    only; an executive-comms domain is never released.
    """
    host = _hostname(url)
    if not host or not subjects:
        return None

    # Prong 1 — name-in-domain, label-START matching only.
    labels = [part for label in host.split(".") for part in label.split("-")]
    for token, subject in distinctive_tokens(subjects):
        if subject in released and not _is_executive_comms(host):
            continue
        if any(label.startswith(token) for label in labels):
            return {
                "subject_matched": subject,
                "domain": host,
                "prong": "name_in_domain",
            }

    # Prong 2 — executive-comms map, exact domain or subdomain.
    for domain, terms in _EXECUTIVE_COMMS.items():
        if host == domain or host.endswith("." + domain):
            for term in terms:
                for subject in subjects:
                    if term in subject:
                        return {
                            "subject_matched": subject,
                            "domain": domain,
                            "prong": "executive_comms",
                        }
    return None


# ── Per-subject release (A− M3, 2026-09-24) ─────────────────────────────────
# The gate asks whether a source is an interested account of the claim. Where
# the claim REPORTS a named organisation's own measurement or publication —
# "Cook Political Report … surveyed 1,052 likely voters" — that organisation's
# own page is the record of the result, not an interested account of it
# (record 70ad9e13 scoped Cook's own poll release to context against its own
# figures). Likewise where the claim is that a subject SAID something, the
# subject's own page is the record of the saying (2026-09-22, record 8d66d41a).
#
# The 2026-09-22 version switched the WHOLE gate off for an attribution claim,
# every subject and prong at once: "The White House published figures showing
# 6 wars ended" disarmed it, so whitehouse.gov could support "six wars ended" —
# TRU-018F-44AA again. This replaces it with a release that is:
#   * per subject — only the subject the verb attaches to (within 80 chars);
#   * prong 1 only — an executive-comms domain is never released;
#   * narrowed by the element — the element must itself name the subject or
#     the act, so decomposition cannot carry a release onto "six wars ended";
#   * ORG-only for both branches, with the verb in the subject's own clause
#     (tightened the same day after review: a person release reopened
#     TRU-018F-44AA on "Trump stopped six wars, as he said he would").
# Symmetric: a released subject's page may support or challenge.

#: Closed list. "found", "shows", "reports" deliberately absent (as 2026-09-22).
_MEASUREMENT_ACT = re.compile(
    r"\b(surveyed|polled|published|estimated|measured|counted|analy[sz]ed)\b",
    re.IGNORECASE,
)
_PUBLICATION_NOUN = re.compile(
    r"\b(polls?|surveys?|stud(?:y|ies)|research|analys[ie]s|bulletins?|index|estimates?|data)\b",
    re.IGNORECASE,
)
#: Saying verbs — mirrors recital_scope._ATTRIBUTION_SHAPED_ELEMENT.
_SAYING_ACT = re.compile(
    r"\b(said|says|stated|claim(?:s|ed)|announced|asserted|denied|"
    r"recommend(?:s|ed|ation|ations)|specif(?:ies|ied)|"
    r"publish(?:es|ed)|conclud(?:es|ed)|propos(?:es|ed|al|als)|"
    r"urg(?:es|ed)|advis(?:es|ed)|called\s+for|set\s+out)\b",
    re.IGNORECASE,
)
_ACT_WINDOW = 80
_NOUN_WINDOW = 30


#: The verb must be in the subject's OWN clause. A clause break between them
#: ("Donald Trump stopped six wars, as he said he would") means the verb is not
#: the subject's act — review 2026-09-24 showed the first version released
#: Trump's own domains on exactly that sentence.
_CLAUSE_BREAK = re.compile(
    r"[;:()\u2014\u2013]|\s-\s|,|\b(?:as|but|which|who|while|after|before|because|when|if)\b",
    re.IGNORECASE,
)
#: A coordinated list of capitalised names after the subject ("Cook Political
#: Report, GS Strategy Group and New River Strategies surveyed") is still the
#: subject's clause; its commas and "and" are not a break.
_NAME_LIST = re.compile(r"(?:\s*(?:,|\band\b)\s*(?:[A-Z][\w.&'-]*\s*)+)+")


def _subject_acts(text: str, token: str, act: "re.Pattern[str]", window: int) -> bool:
    for m in re.finditer(r"\b" + re.escape(token) + r"\b", text, re.IGNORECASE):
        tail = text[m.end() : m.end() + window]
        hit = act.search(tail)
        if not hit:
            continue
        if _CLAUSE_BREAK.search(_NAME_LIST.sub(" ", tail[: hit.start()])):
            continue
        return True
    return False


def released_subjects(
    claim_texts: Iterable[str],
    element_text: str,
    subjects: List[str],
    subject_kinds: Optional[Dict[str, str]] = None,
) -> FrozenSet[str]:
    """Subjects whose own domain is the record of what the claim reports."""
    kinds = subject_kinds or {}
    texts = [t for t in claim_texts if t]
    element = element_text or ""
    released = set()
    for token, subject in distinctive_tokens(subjects):
        # ORG-only for BOTH branches (review 2026-09-24): a person's saying is
        # the self-interested account this gate exists for, and a person
        # release reopened TRU-018F-44AA ("…, as he said he would").
        if kinds.get(subject) != "org":
            continue
        measured = any(
            _subject_acts(t, token, _MEASUREMENT_ACT, _ACT_WINDOW)
            or _subject_acts(t, token, _PUBLICATION_NOUN, _NOUN_WINDOW)
            for t in texts
        )
        said = any(_subject_acts(t, token, _SAYING_ACT, _ACT_WINDOW) for t in texts)
        if not (measured or said):
            continue
        # The element can only withhold a release the claim earned, never grant one.
        names_subject = re.search(r"\b" + re.escape(token) + r"\b", element, re.IGNORECASE)
        names_act = (
            measured
            and (_MEASUREMENT_ACT.search(element) or _PUBLICATION_NOUN.search(element))
        ) or (said and _SAYING_ACT.search(element))
        if names_subject or names_act:
            released.add(subject)
    return frozenset(released)

