"""Adapter query-shape helpers.

Each external API adapter has its own ideal input shape. The pipeline upstream
extracts a single ``claim_text`` plus a list of NER ``entities``; these helpers
turn that pair into the shape a particular adapter family needs.

Helpers are intentionally narrow and pure-Python — no LLM calls, no I/O. If a
helper's behaviour starts diverging across consumers, prefer adding a new helper
over parameterising an existing one.

Used by ``GovernmentAPIClient`` subclasses via their ``prepare_query`` override.

NF-15 boundary note:
    The extract LLM stores entities as ``{text, type}`` (TypedEntity). At
    ``retrieve.py:1937`` they are remapped to ``{text, label}`` before being
    passed to adapter ``prepare_query`` calls — so consumers here read
    ``label``. Values match the NF-15 vocabulary
    ``{ORG, PERSON, LAW, EVENT, PRODUCT, LOCATION, AMOUNT, DATE, OTHER}``.
"""

import re
from typing import Dict, List, Optional, Tuple


# Priority order for "topic-like" entity labels. Earlier labels win.
# LAW (e.g. "Climate Change Act 2008") is the strongest topic signal for
# parliamentary / government search APIs; GPE/PERSON are deliberately omitted
# because place and person names rarely capture the topic of a claim.
_TOPIC_LABEL_PRIORITY = ("LAW", "EVENT", "WORK_OF_ART", "PRODUCT", "ORG")


def extract_topic_phrase(
    claim_text: str,
    entities: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Return the strongest topic-like entity text, or ``claim_text`` as fallback.

    Algorithm:
      1. Walk ``_TOPIC_LABEL_PRIORITY`` in order.
      2. For the first label with any matches, return the longest matching
         entity's text (longer phrases are more specific topic signals).
      3. If no priority label matches, return ``claim_text`` unchanged so the
         caller retains current behaviour.

    Used by Hansard and GOV.UK Content API — both are topic-keyword search APIs.
    """
    if not entities:
        return claim_text

    by_label: Dict[str, List[str]] = {}
    for ent in entities:
        label = ent.get("label")
        text = (ent.get("text") or "").strip()
        if label and text:
            by_label.setdefault(label, []).append(text)

    for label in _TOPIC_LABEL_PRIORITY:
        candidates = by_label.get(label)
        if candidates:
            return max(candidates, key=len)

    return claim_text


def extract_entity_name(
    claim_text: str,
    entities: Optional[List[Dict[str, str]]] = None,
    label: str = "ORG",
) -> Optional[str]:
    """Return the longest entity matching ``label``, or ``None`` if absent.

    Unlike ``extract_topic_phrase``, this returns ``None`` on miss rather than
    falling back to claim text. Adapters that need a specific entity type
    (Companies House → ORG, Football-Data → ORG, Transfermarkt → PERSON) should
    skip the API call entirely when the entity is absent — searching with the
    full sentence produces zero hits and pollutes the cache.

    ``claim_text`` is unused but kept in the signature for symmetry with the
    other helpers, so all helpers share a uniform calling convention from
    ``prepare_query`` overrides.
    """
    del claim_text  # signature symmetry only

    if not entities:
        return None

    matches = [
        (ent.get("text") or "").strip()
        for ent in entities
        if ent.get("label") == label and (ent.get("text") or "").strip()
    ]
    if not matches:
        return None

    return max(matches, key=len)


def extract_location_and_date(
    entities: Optional[List[Dict[str, str]]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(location, date)`` extracted from typed entities.

    Either field may be ``None``. Used by climate adapters (NOAA CDO,
    WeatherAPI, Open-Meteo) which need a place + a time window to produce
    meaningful API responses; without both, the call should be skipped.

    Selection rules:
      * ``location``: the longest entity with ``label == "LOCATION"``. Longer
        names are more specific (e.g. "Greater London" beats "London"), and
        weather APIs handle the more specific form better.
      * ``date``: the longest entity with ``label == "DATE"``. Same reasoning
        — "July 2022" beats "2022" for narrowing the window.

    The function does not rejoin the values into a single string; callers
    typically use both halves: one for the API ``location`` parameter, one
    for the ``date``/``startdate``/``enddate`` parameter. Adapters that need
    a single deterministic cache key can join them themselves
    (e.g. ``f"{loc}|{date}"``).

    Returns ``(None, None)`` when neither label is present, signalling the
    caller's ``prepare_query`` should return ``""`` to trigger the
    empty-skip path in ``search_with_cache``.
    """
    if not entities:
        return None, None

    locations: List[str] = []
    dates: List[str] = []
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        label = ent.get("label")
        text = (ent.get("text") or "").strip()
        if not text:
            continue
        if label == "LOCATION":
            locations.append(text)
        elif label == "DATE":
            dates.append(text)

    location = max(locations, key=len) if locations else None
    date = max(dates, key=len) if dates else None
    return location, date


def extract_claim_year(
    entities: Optional[List[Dict[str, str]]] = None
) -> Optional[int]:
    """Return the 4-digit year from the claim's DATE entity, or ``None``.

    Reads the longest ``label == "DATE"`` entity (via
    :func:`extract_location_and_date`) and pulls the first 19xx/20xx year out
    of it. Returns ``None`` when there is no DATE entity or it carries no
    parseable year (e.g. "last summer").

    Used by recency-windowed adapters (academic paper search) to widen their
    publication-year filter so a historically-dated claim's own era is
    included. A fixed ``now-2y`` window otherwise silently excludes the
    claim's own sources — a 2021 claim queried 2024-2026 and never saw the
    2021 paper it is about. Same NF-18 Bug-2 / NF-20 historical-recency class
    that NOAA already fixed by anchoring its window to the DATE entity.
    """
    _, date_text = extract_location_and_date(entities)
    if not date_text:
        return None
    match = re.search(r"\b(?:19|20)\d{2}\b", date_text)
    return int(match.group(0)) if match else None


def extract_concept_keyword(
    claim_text: str,
    mapping: Dict[str, str],
    entities: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """Match a domain concept in the claim against a ``{keyword: code}`` map.

    Used by adapters that need a structured code (FRED series ID, ONS dataset
    ID, WHO indicator code). When the claim mentions a known concept
    keyword, return the mapped code; otherwise ``None`` to signal the caller
    should skip the call rather than search with the full sentence.

    Two-pass match:
      1. **Typed-OTHER pass**: the LLM (NF-15) classifies abstract domain
         concepts as ``label == "OTHER"`` (vs ``LOCATION`` / ``ORG`` etc).
         Walk those first — most precise signal, no false positives from
         word fragments scattered across the claim.
      2. **Claim-text fallback**: if no OTHER entity matches, scan the raw
         claim text. Catches cases where the LLM emitted a related entity
         under a different label, or didn't name the concept at all.

    Matches are case-insensitive substring against the keyword. The mapping
    is provided per-adapter (FRED has its own dict, ONS has its own, etc).
    Mapping iteration order is preserved on Python 3.7+ dicts, so callers
    can put more-specific keywords first to win against shorter prefixes
    (e.g. "GDP growth" before "GDP").
    """
    # Pass 1 — typed OTHER entities (most precise)
    if entities:
        for ent in entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("label") != "OTHER":
                continue
            etext = (ent.get("text") or "").lower().strip()
            if not etext:
                continue
            for keyword, code in mapping.items():
                if keyword.lower() in etext:
                    return code

    # Pass 2 — claim-text scan (fallback when LLM mislabels or omits)
    claim_lower = (claim_text or "").lower()
    for keyword, code in mapping.items():
        if keyword.lower() in claim_lower:
            return code

    return None
