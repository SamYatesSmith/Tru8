"""Jurisdiction-scope tagger — the mechanical analogue of F1 (2026-08-06).

Design: audit/2026-08-06_f1_temporal_gate_extension.md, "Live proof attempt".

WHY THIS EXISTS, AND WHY IT CANNOT BE A PROMPT
----------------------------------------------
Production check `757f02c2` returned a TRUE, ONS-verbatim claim — "UK consumer
price inflation fell to 1.7 percent in the twelve months to September 2024" — as
`disputed`. Its sole `challenges` item was the **Irish** Central Statistics
Office, reporting "CPI rose by 2.7% between September 2024 and September 2025".

The F1 temporal gate correctly declined to touch it: that snippet names September
2024 repeatedly, so no period mismatch exists. The mismatch is jurisdictional, and
here is the decisive detail —

    the snippet never says "Ireland", or "Irish", or anything else locating it.

Only the DOMAIN reveals the country. A mapping prompt cannot be asked to notice
what its input does not contain, which is the NF-11 lesson in its original form:
fragile behaviour needs a mechanical rule, not a prompt.

WHAT IT DOES, AND DELIBERATELY DOES NOT DO
------------------------------------------
Where a claim is scoped to ONE country-level jurisdiction and an evidence item is
a NATIONAL OFFICIAL source of a DIFFERENT country, the relationship is scoped to
"context". It never deletes evidence and never sets a state directly — state is
derived downstream from relationships, so the effect carries a receipt like every
other exclusion (invariant #5).

**Symmetric on purpose**, for the same reason F1 is: it scopes `supports` exactly
as it scopes `challenges`. Another country's national statistics bear on a UK
figure in neither direction, and a gate that only removed challenges would be a
sycophancy mechanism — precisely what invariant #7 forbids.

Three deliberate limits, each holding down the false-positive rate, because
over-firing hides genuine evidence:

  1. **Official sources only.** An Irish newspaper reporting ON UK inflation is
     legitimate evidence and is NOT touched. Only national statistics offices,
     central banks and government domains are in the map — the shape of the actual
     failure. Foreign PRESS is not a jurisdiction mismatch.
  2. **Country-level claims only.** `VALID_JURISDICTIONS` is UK/US/EU/Global;
     only UK and US name a single country. `EU` is excluded because a member
     state's figures are partly in scope for an EU-wide claim (that is a
     composition problem, not a jurisdiction one), and `Global` because any
     country's data can be an instance of a global claim.
  3. **The mention guard.** If the item's own text names the claim's jurisdiction,
     it is left alone — a foreign statistics office publishing an international
     comparison that includes the UK is talking about the UK. This mirrors F1's
     "one matching mention is enough".

Supranational bodies (World Bank, IMF, OECD, WHO, UN, Eurostat) are deliberately
ABSENT from the map: they report on many countries including ours, so their data
about the UK is legitimate and must never be scoped out on domain alone.
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

#: Claim-level jurisdictions that name exactly one country. `article_classifier`
#: only ever emits UK / US / EU / Global; the latter two are not country-level and
#: are absent on purpose (see limit 2 above).
_COUNTRY_LEVEL_JURISDICTIONS: Dict[str, str] = {"UK": "UK", "US": "US"}

#: National OFFICIAL domains → the country they speak for. Statistics offices,
#: central banks and government hosts only. Deliberately NOT press, and
#: deliberately NOT supranational bodies.
#:
#: ⚠️ Incomplete by construction, exactly as the evidence-classifier allowlist is:
#: there are ~200 countries and this covers the ones whose statistics releases
#: actually surface in retrieval for UK/US economic claims. An absent domain means
#: the gate does not fire — the safe direction.
NATIONAL_OFFICIAL_DOMAINS: Dict[str, str] = {
    # Ireland — the observed failure (check 757f02c2)
    "cso.ie": "IE",
    "gov.ie": "IE",
    "centralbank.ie": "IE",
    # United Kingdom
    "ons.gov.uk": "UK",
    "gov.uk": "UK",
    "parliament.uk": "UK",
    "bankofengland.co.uk": "UK",
    "legislation.gov.uk": "UK",
    # United States
    "bls.gov": "US",
    "census.gov": "US",
    "bea.gov": "US",
    "federalreserve.gov": "US",
    "cbo.gov": "US",
    # Canada
    "statcan.gc.ca": "CA",
    "canada.ca": "CA",
    "bankofcanada.ca": "CA",
    # Australia / New Zealand
    "abs.gov.au": "AU",
    "gov.au": "AU",
    "rba.gov.au": "AU",
    "stats.govt.nz": "NZ",
    "govt.nz": "NZ",
    # Euro-area national offices (NOT Eurostat — that is supranational)
    "destatis.de": "DE",
    "bundesbank.de": "DE",
    "insee.fr": "FR",
    "banque-france.fr": "FR",
    "istat.it": "IT",
    "ine.es": "ES",
    "cbs.nl": "NL",
    "ssb.no": "NO",
    "scb.se": "SE",
    "dst.dk": "DK",
    # Rest of world
    "mospi.gov.in": "IN",
    "rbi.org.in": "IN",
    "stat.go.jp": "JP",
    "boj.or.jp": "JP",
    "statssa.gov.za": "ZA",
    "gov.za": "ZA",
    "ibge.gov.br": "BR",
    "inegi.org.mx": "MX",
}

#: Text that locates an item in the claim's jurisdiction. Used ONLY to SUPPRESS
#: the gate, never to fire it, so a loose match here is the safe direction.
#:
#: "US" is matched case-sensitively and the bare pronoun "us" is excluded — a
#: case-insensitive match would fire on ordinary prose and suppress the gate
#: everywhere, which is safe but useless.
#: Two patterns per country: words that are unambiguous in any case, and tokens
#: that are only a country when capitalised. Folding them into one
#: case-insensitive pattern would make "us" the pronoun read as the country, and
#: one case-SENSITIVE pattern would miss a lowercase "united states".
_MENTION_PATTERNS: Dict[str, Tuple[re.Pattern, Optional[re.Pattern]]] = {
    "UK": (
        re.compile(
            r"\b(uk|u\.k\.|united kingdom|britain|british|england|english|"
            r"scotland|scottish|wales|welsh|northern ireland)\b",
            re.I,
        ),
        None,
    ),
    "US": (
        re.compile(
            r"\b(u\.s\.a\.?|usa|united states|america|american|federal reserve)\b",
            re.I,
        ),
        # "US" the country vs "us" the pronoun — capitalisation is the only signal.
        re.compile(r"\bU\.?S\.?\b"),
    ),
}


def claim_target_country(jurisdiction: Optional[str]) -> Optional[str]:
    """The single country a claim is scoped to, or None if it is not so scoped.

    None for `EU`, `Global`, unknown values and absent values alike — in every one
    of those cases the gate must not fire.
    """
    if not jurisdiction:
        return None
    return _COUNTRY_LEVEL_JURISDICTIONS.get(jurisdiction.strip().upper())


def evidence_country(url: Optional[str]) -> Optional[str]:
    """The country an evidence URL speaks *officially* for, or None.

    None is the overwhelmingly common answer — press, academia, commentary and any
    unlisted host all return None, and None means the gate leaves the item alone.
    """
    if not url:
        return None

    host = (urlparse(url).hostname or "").lower().strip(".")
    if not host:
        return None

    for domain, country in NATIONAL_OFFICIAL_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return country

    # A bare `.gov` TLD is US federal/state; `gov.uk`, `gov.au`, `govt.nz` end in
    # their own ccTLD and are matched above, so they cannot reach this line.
    if host.endswith(".gov"):
        return "US"

    return None


def mentions_jurisdiction(text: Optional[str], country: str) -> bool:
    """Does the item's own text locate itself in the claim's jurisdiction?"""
    patterns = _MENTION_PATTERNS.get(country)
    if patterns is None or not text:
        return False
    any_case, cased = patterns
    if any_case.search(text) is not None:
        return True
    return cased is not None and cased.search(text) is not None


def is_out_of_jurisdiction_for_country(
    target_country: str,
    source_country: Optional[str],
    evidence_text: Optional[str],
) -> bool:
    """As `is_out_of_jurisdiction`, but for an ALREADY-RESOLVED source country.

    The mapping pipeline resolves each item's country once per claim and caches
    it, so re-deriving it from the URL per element and per gate is wasted work.
    This is the single implementation; the URL-taking form below delegates here.
    """
    if source_country is None or source_country == target_country:
        return False
    return not mentions_jurisdiction(evidence_text, target_country)


def is_out_of_jurisdiction(
    target_country: str,
    url: Optional[str],
    evidence_text: Optional[str],
) -> bool:
    """True when the item is another country's official source and says nothing
    about the claim's jurisdiction.

    Silence about the country is NOT what fires this — the domain is. Silence in
    the *other* direction (an item that never names our jurisdiction) is what
    removes the suppression, which is why the observed failure is caught: the CSO
    snippet names neither Ireland nor the UK.
    """
    return is_out_of_jurisdiction_for_country(
        target_country, evidence_country(url), evidence_text
    )
