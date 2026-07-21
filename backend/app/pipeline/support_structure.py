"""Thin / echo sourcing reads over an element's persisted ``basis``.

This is the backend port of ``web/lib/support-structure.ts`` — the SAME
thin/echo thresholds, kept in one place so the claim-level top-up endpoint
("Strengthen this claim") selects exactly the elements the digest surfaces a
"Get more" trigger on. When you change a threshold here, change it there too
(and vice-versa); ``tests/unit/pipeline/test_thin_support.py`` locks the two in
parity with a shared case table.

It describes the SOURCES on a side (supports/challenges) — never the claim's
truth. The pipeline stays judgment-free; these are presentation-time reads over
the mechanical structure the pipeline already computed.
"""

from __future__ import annotations

from typing import Any


# The note payloads — kind + label + detail — locked CHARACTER-FOR-CHARACTER to
# ``evidenceQualityNote`` in ``support-structure.ts``. Precedence: echo →
# repetition → thin(commentary) → thin(single-outlet). Grey, no verdict.
_ECHO_NOTE = {
    "kind": "echo",
    "label": "Mostly one source repeated",
    "detail": "Several of these sources repeat a single original report.",
}
_REPETITION_NOTE = {
    "kind": "repetition",
    "label": "Same wording, no primary",
    "detail": "Several sources share the same wording; no primary source found behind them.",
}
_THIN_COMMENTARY_NOTE = {
    "kind": "thin",
    "label": "Thin sourcing",
    "detail": "Only commentary-grade sources — no primary or reporting evidence.",
}
_THIN_SINGLE_OUTLET_NOTE = {
    "kind": "thin",
    "label": "Thin sourcing",
    "detail": "All from a single website.",
}
_THIN_PORTFOLIO_NOTE = {
    "kind": "thin",
    "label": "Thin sourcing",
    "detail": "All via a single publisher platform, which may host multiple journals.",
}

# Publisher platforms that host many independent journals under one domain
# (§4d fix 5). A single-outlet side on one of these is not the same epistemic
# concern as one website — the note wording says so, no counting changes.
PORTFOLIO_HOSTS = {
    "nature.com",
    "sciencedirect.com",
    "springer.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "academic.oup.com",
    "journals.plos.org",
}


def side_quality_note(side: Any) -> dict | None:
    """The thin/echo/repetition note for one side, or ``None`` if it's healthy.

    Parity twin of ``evidenceQualityNote`` (``support-structure.ts``) — same
    thresholds, same precedence, same labels:
      - echo       → an original repeated by ≥2 derivative sources
      - repetition → ≥3 sources on this side recite the SAME wording across ≥2
                     domains with NO primary here (talking-point, finding F4)
      - thin       → commentary-grade only (no primary/reporting), OR
                     ≥2 items all from a single outlet.
    An empty / absent side has no note. Returns a fresh dict so callers can't
    mutate the shared payload. It describes the SOURCES, never the claim's truth.
    """
    if not isinstance(side, dict):
        return None

    count = side.get("count") or 0
    if not count:
        return None

    tier_counts = side.get("tier_counts") or {}

    derivation = side.get("derivation") or {}
    if (derivation.get("originals") or 0) >= 1 and (
        derivation.get("derivative_count") or 0
    ) >= 2:
        return dict(_ECHO_NOTE)

    # Unanchored repetition (F4): several sources on this side share the same
    # wording, across ≥2 domains, with no primary source here.
    repetition = side.get("repetition") or {}
    if (
        (repetition.get("max_cluster_on_side") or 0) >= 3
        and (repetition.get("distinct_domains") or 0) >= 2
        and (tier_counts.get("primary") or 0) == 0
    ):
        return dict(_REPETITION_NOTE)

    commentary_only = (tier_counts.get("primary") or 0) == 0 and (
        tier_counts.get("reporting") or 0
    ) == 0
    if commentary_only:
        return dict(_THIN_COMMENTARY_NOTE)

    single_outlet = count >= 2 and (side.get("distinct_domains") or 0) <= 1
    if single_outlet:
        if (side.get("sole_domain") or "") in PORTFOLIO_HOSTS:
            return dict(_THIN_PORTFOLIO_NOTE)
        return dict(_THIN_SINGLE_OUTLET_NOTE)

    return None


def side_has_quality_note(side: Any) -> bool:
    """True when one side's sourcing is thin or echoey (see ``side_quality_note``)."""
    return side_quality_note(side) is not None


def element_has_quality_note(basis: Any) -> bool:
    """True when EITHER side of the element carries a thin/echo note."""
    if not isinstance(basis, dict):
        return False
    return side_has_quality_note(
        basis.get("support_structure")
    ) or side_has_quality_note(basis.get("challenge_structure"))


def _state_str(state: Any) -> str | None:
    """Normalise a stored/enum state to its lowercase string form."""
    if state is None:
        return None
    return state.value if hasattr(state, "value") else str(state)


def element_is_thin(element: Any) -> bool:
    """A "thin" element the user can top up (NOT a gap the Seeker owns).

    Thin iff it has ≥1 mapped source AND is not ``disputed`` AND any of:
      - ≤ 2 mapped sources, OR
      - state is ``unresolved`` / unset, OR
      - either side carries a thin/echo note.

    Excludes 0-source gaps (Seeker re-search owns those), ``disputed``
    (evidence-rich, not thin), and well-covered elements.
    """
    if not isinstance(element, dict):
        return False

    refs = element.get("evidence_refs") or []
    if not refs:  # gap → Seeker's territory, not a top-up
        return False

    state = _state_str(element.get("state"))
    if state == "disputed":  # evidence-rich, contested — not thin
        return False

    if len(refs) <= 2:
        return True
    if state in (None, "unresolved"):
        return True
    if element_has_quality_note(element.get("basis")):
        return True

    return False


def thin_element_ids(claim_map: Any) -> list[str]:
    """Ids of every thin element in a claim map (order preserved)."""
    if not isinstance(claim_map, dict):
        return []
    ids: list[str] = []
    for elem in claim_map.get("elements", []):
        if element_is_thin(elem):
            eid = elem.get("element_id")
            if eid:
                ids.append(eid)
    return ids
