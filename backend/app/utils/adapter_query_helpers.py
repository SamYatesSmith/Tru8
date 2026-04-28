"""Adapter query-shape helpers.

Each external API adapter has its own ideal input shape. The pipeline upstream
extracts a single ``claim_text`` plus a list of NER ``entities``; these helpers
turn that pair into the shape a particular adapter family needs.

Helpers are intentionally narrow and pure-Python — no LLM calls, no I/O. If a
helper's behaviour starts diverging across consumers, prefer adding a new helper
over parameterising an existing one.

Used by ``GovernmentAPIClient`` subclasses via their ``prepare_query`` override.
"""

from typing import Dict, List, Optional


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
