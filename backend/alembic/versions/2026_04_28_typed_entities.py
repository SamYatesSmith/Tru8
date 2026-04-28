"""Backfill claim.key_entities from List[str] -> List[{text, type}].

Revision ID: typed_entities_2026
Revises: rename_cents_pence
Create Date: 2026-04-28

NF-15 Commit 3 (typed entities proposal,
audit/pipeline-issues/2026-04-28_typed_entities_proposal.md).

Forward migration:
  - Iterate every claim with non-null key_entities.
  - If shape is List[str] (legacy), apply the heuristic labeller (copied
    here, frozen at this point in time) to assign a type to each string.
  - If shape is already List[{text, type}] (already typed), skip.
  - Write back the typed shape.
  - Idempotent: re-runnable safely.

Reverse migration:
  - List[{text, type}] -> List[str] by extracting .text.
  - LOSSY on the type field. After downgrade, retrieve.py's heuristic
    labeller would need to be reinstated.

Heuristic logic mirrors retrieve.py:1882 _label_entities_for_api as it
existed at commit cf0f959 (NF-15 Commit 2). The heuristic only emits
ORG | PERSON | ENTITY. The migration maps:
  ORG    -> ORG
  PERSON -> PERSON
  ENTITY -> OTHER   (closest typed equivalent for the "I don't know" bucket)

This is a one-time legacy backfill. After this migration runs and
Commit 4 lands, the heuristic is deleted from runtime code; the only
copy lives here.
"""

from typing import Any, List, Optional, Sequence, Union

import json
from alembic import op
from sqlalchemy import text


revision: str = "typed_entities_2026"
down_revision: Union[str, None] = "rename_cents_pence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Heuristic labeller (frozen copy of retrieve.py:1882 _label_entities_for_api)
# ---------------------------------------------------------------------------

_ORG_SUFFIXES = (
    "FC",
    "United",
    "City",
    "Rovers",
    "Wanderers",
    "Athletic",
    "Dortmund",
    "Arsenal",
    "Chelsea",
    "Munich",
    "Madrid",
    "Barcelona",
    "Milan",
    "Inter",
    "Juventus",
    "PSG",
    "Bayern",
    "Liverpool",
    "Tottenham",
    "Spurs",
    "Hotspur",
    "Rangers",
    "Celtic",
    "Club",
    "Association",
    "Federation",
    "League",
    "UEFA",
    "FIFA",
    "Inc",
    "Ltd",
    "Corp",
    "Company",
    "Organization",
    "Government",
)

_PERSON_PREFIXES = (
    "Mr",
    "Mrs",
    "Ms",
    "Dr",
    "Prof",
    "Sir",
    "Lord",
    "Lady",
    "President",
    "Prime Minister",
    "Minister",
    "Senator",
    "Governor",
)


def _heuristic_type(entity_text: str) -> str:
    """Mirror of retrieve.py:1882 ENTITY|ORG|PERSON labeller, mapped to typed
    vocabulary (ENTITY -> OTHER)."""
    entity_stripped = entity_text.strip()
    if not entity_stripped:
        return "OTHER"

    if any(entity_stripped.endswith(suffix) for suffix in _ORG_SUFFIXES):
        return "ORG"

    words = entity_stripped.split()
    if (
        len(words) >= 2
        and all(w[0].isupper() for w in words if w)
        and not any(suffix in entity_stripped for suffix in _ORG_SUFFIXES)
    ):
        return "PERSON"

    if any(entity_stripped.startswith(prefix) for prefix in _PERSON_PREFIXES):
        return "PERSON"

    return "OTHER"


# ---------------------------------------------------------------------------
# Shape detection + conversion
# ---------------------------------------------------------------------------


def _is_already_typed(value: Any) -> bool:
    """Check whether a key_entities value is already in typed shape."""
    if not isinstance(value, list) or not value:
        return False
    first = value[0]
    return isinstance(first, dict) and "text" in first and "type" in first


def _convert_legacy(legacy: List[Any]) -> List[dict]:
    """Convert List[str] (or mixed) -> List[{text, type}]."""
    out: List[dict] = []
    for item in legacy:
        if isinstance(item, str):
            text_value = item.strip()
            if text_value:
                out.append({"text": text_value, "type": _heuristic_type(text_value)})
        elif isinstance(item, dict):
            # Already a dict; pass through if shape valid, else skip
            if "text" in item and "type" in item:
                out.append({"text": str(item["text"]), "type": str(item["type"])})
    return out


def _coerce_to_strings(typed: List[Any]) -> List[str]:
    """Reverse: extract .text from typed shape (lossy on type)."""
    out: List[str] = []
    for item in typed:
        if isinstance(item, dict) and "text" in item:
            out.append(str(item["text"]))
        elif isinstance(item, str):
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Upgrade / downgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    bind = op.get_bind()

    # Select all claims with non-null key_entities
    rows = bind.execute(
        text("SELECT id, key_entities FROM claim " "WHERE key_entities IS NOT NULL")
    ).fetchall()

    converted = 0
    skipped_typed = 0
    skipped_empty = 0
    skipped_nonlist = 0

    for row in rows:
        claim_id, value = row[0], row[1]

        # JSONB returns Python objects already (list, dict, str)
        if value is None:
            continue
        if not isinstance(value, list):
            skipped_nonlist += 1
            continue
        if not value:
            skipped_empty += 1
            continue
        if _is_already_typed(value):
            skipped_typed += 1
            continue

        new_value = _convert_legacy(value)
        bind.execute(
            text("UPDATE claim SET key_entities = :v WHERE id = :id"),
            {"v": json.dumps(new_value), "id": claim_id},
        )
        converted += 1

    print(
        f"[NF-15 migration upgrade] claims processed: {len(rows)}, "
        f"converted: {converted}, already-typed: {skipped_typed}, "
        f"empty: {skipped_empty}, non-list: {skipped_nonlist}"
    )


def downgrade() -> None:
    bind = op.get_bind()

    rows = bind.execute(
        text("SELECT id, key_entities FROM claim " "WHERE key_entities IS NOT NULL")
    ).fetchall()

    converted = 0
    skipped = 0

    for row in rows:
        claim_id, value = row[0], row[1]

        if value is None:
            continue
        if not isinstance(value, list) or not value:
            skipped += 1
            continue
        if not _is_already_typed(value):
            # Already legacy shape; skip
            skipped += 1
            continue

        new_value = _coerce_to_strings(value)
        bind.execute(
            text("UPDATE claim SET key_entities = :v WHERE id = :id"),
            {"v": json.dumps(new_value), "id": claim_id},
        )
        converted += 1

    print(
        f"[NF-15 migration downgrade] claims processed: {len(rows)}, "
        f"reverted: {converted}, skipped: {skipped}"
    )
