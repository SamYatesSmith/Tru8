"""Census: does Tru8 spend retrieval on elements that are TRIVIALLY TRUE?

Founder's challenge, 2026-07-31: on "Great white sharks are starting to inhabit
British waters", decompose produced the element "Great white sharks are a
species of shark." Are we really breaking claims down that far, and then
spending a retrieval lane researching it?

That specific element came from the `--no-context` control arm of
`element_count_drift_probe.py` — the PRE-`fa35465` call shape, not current
behaviour. But the concern generalises, and the register logged near-tautology
elements ("Teacher-training courses exist.", "The learning-styles theory
exists.") on 2026-07-25, which is AFTER that fix. So this is measured, not
assumed.

Cost of a trivial element is not zero and not only cosmetic:
  * it consumes one of MAX_ELEMENTS (5) — a slot a real sub-question could use;
  * it consumes a retrieval lane (Phase 2: ~2 queries + fetch slots);
  * it will almost always come back `supported`, which inflates the element
    tally an orientation line is derived from.

SPLIT BY DATE, because that is the question that matters: claim-integrity
source-context anchoring (`fa35465`) shipped 2026-07-21. Elements decomposed
before and after it are counted separately, so "did we fix it?" is answered
with a number rather than a hope.

Patterns are RECALL-tuned and every hit is printed. A trivial element is a
judgement call, so the list is a signpost and the printed text is the evidence.

Usage:  python -m scripts.trivial_element_census
"""

from __future__ import annotations

import asyncio
import io
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# fa35465 — claim integrity: decompose started receiving the submission as
# source_context, which is what stopped it padding with definitional filler.
ANCHORING_SHIPPED = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)

TRIVIAL = [
    ("bare existence", re.compile(r"\bexist(?:s|ed)?\s*\.?\s*$", re.I)),
    (
        "category/definition",
        re.compile(
            r"\bis\s+(?:a|an)\s+(?:species|type|kind|form|category|class)\s+of\b"
            r"|\bis\s+(?:geographically\s+)?defined\s+as\b"
            r"|\bis\s+the\s+term\s+for\b|\brefers\s+to\s+the\b",
            re.I,
        ),
    ),
    (
        "bare occurrence",
        re.compile(r"\b(?:occurred|took\s+place|happened|was\s+held)\s*\.?\s*$", re.I),
    ),
    (
        "bare institutional identity",
        re.compile(
            r"\bis\s+(?:a|an|the)\s+(?:UK|US|British|American|government|public|"
            r"national|international)?\s*(?:government\s+)?"
            r"(?:body|agency|department|organisation|organization|institution|"
            r"charity|company|regulator)\s*\.?\s*$",
            re.I,
        ),
    ),
]


def classify(text: str) -> str | None:
    for label, pat in TRIVIAL:
        if pat.search(text):
            return label
    return None


async def main() -> int:
    from sqlmodel import select as sm_select

    from app.core.database import async_session
    from app.models.check import Claim

    async with async_session() as session:
        rows = (await session.execute(sm_select(Claim))).scalars().all()

    before, after = [], []
    n_claims = 0
    for claim in rows:
        cm = claim.claim_map
        if not isinstance(cm, dict):
            continue
        els = cm.get("elements") or []
        if not els:
            continue
        n_claims += 1
        ts = claim.created_at
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        bucket = after if (ts and ts >= ANCHORING_SHIPPED) else before
        for el in els:
            desc = (el.get("description") or "").strip()
            if not desc:
                continue
            bucket.append((claim.text or "", desc, classify(desc)))

    if not (before or after):
        print("No decomposed claims in the local DB — nothing to census.")
        return 0

    def pct(a, b):
        return f"{100.0 * a / b:.1f}%" if b else "n/a"

    print("=" * 78)
    print("TRIVIAL ELEMENT CENSUS — local DB")
    print("=" * 78)
    for label, bucket in (
        ("BEFORE anchoring (pre-2026-07-21)", before),
        ("AFTER  anchoring (fa35465 onward)", after),
    ):
        hits = [b for b in bucket if b[2]]
        print(f"\n{label}")
        print(f"  elements : {len(bucket)}")
        print(f"  trivial  : {len(hits)}  ({pct(len(hits), len(bucket))})")
        by_kind: dict[str, int] = {}
        for _, _, k in hits:
            by_kind[k] = by_kind.get(k, 0) + 1
        for k, v in sorted(by_kind.items(), key=lambda x: -x[1]):
            print(f"      {k:32} {v}")

    print("\n" + "-" * 78)
    print("EVERY hit, newest bucket first — the text IS the evidence:")
    print("-" * 78)
    for label, bucket in (
        ("AFTER  anchoring", after),
        ("BEFORE anchoring", before),
    ):
        hits = [b for b in bucket if b[2]]
        print(f"\n### {label} — {len(hits)} hit(s)")
        for claim_text, desc, kind in hits[:40]:
            print(f"  [{kind}] {desc}")
            print(f"      on claim: {claim_text[:88]}")
        if not hits:
            print("  none")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
