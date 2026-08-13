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

from typing import Any, Dict, Iterable, List, Optional, Tuple
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
        "party",
        "post",
        "president",
        "press",
        "prime",
        "real",
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


def interested_party_match(
    subjects: List[str], url: Optional[str]
) -> Optional[Dict[str, str]]:
    """The receipt entry if this URL's domain is controlled by a claim subject.

    Returns None when no prong matches — including every malformed or absent
    input — so the caller can use it directly as the gate's `fires`.
    """
    host = _hostname(url)
    if not host or not subjects:
        return None

    # Prong 1 — name-in-domain, label-START matching only.
    labels = [part for label in host.split(".") for part in label.split("-")]
    for token, subject in distinctive_tokens(subjects):
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
