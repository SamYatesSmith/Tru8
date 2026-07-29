"""Census: how many Claim Map elements are COMPOUND?

A compound element asks two things at once — "What were the targets, AND to what
extent were they met?". The mapper's two-shape rule (claim_map_analyzer.py:292)
must pick ONE shape for the whole element, so whichever half it reads, the other
half is graded by the wrong standard. The enumerative half is usually trivially
satisfiable, so the element badges `supported` while the half that actually
bears on the claim goes unchecked. That is the TRU-4B9D-65EA failure by
construction.

This counts them. Two measures, deliberately:

  CONSERVATIVE — split only where a coordinator is followed by a second
                 INTERROGATIVE HEAD (wh-word, "to what extent", or
                 auxiliary+subject inversion). Under-splits by design.
  LOOSE        — any coordinator at all. Upper bound; includes conjoined noun
                 phrases like "efficacy and evidence base", which are ONE
                 question and must NOT be split.

The truth is between them; the conservative number is the one to act on.

Usage:
    python -m scripts.compound_element_census            # census the local DB
    python -m scripts.compound_element_census --sample   # print every element
"""

import asyncio
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

COORDINATOR = re.compile(r",?\s+\b(?:and|or|but)\b\s+", re.I)

# A second question starts here. Ordered longest-first so "to what extent" wins
# over a bare "what".
_WH = (
    r"(?:to\s+what\s+extent|how\s+(?:many|much|often|long)|"
    r"what|which|why|when|where|who|whom|whose|how|whether|if)"
)
_AUX = r"(?:did|does|do|was|were|is|are|has|have|had|will|would|can|could|should)"
INTERROGATIVE_HEAD = re.compile(rf"^\s*(?:{_WH}\b|{_AUX}\s+\w+)", re.I)


def conjuncts(text: str):
    """Split an element into the questions it actually asks."""
    parts, cursor = [], 0
    for m in COORDINATOR.finditer(text):
        tail = text[m.end() :]
        if INTERROGATIVE_HEAD.match(tail):
            parts.append(text[cursor : m.start()].strip())
            cursor = m.end()
    parts.append(text[cursor:].strip())
    return [p for p in parts if p]


def is_compound_conservative(text: str) -> bool:
    return len(conjuncts(text)) > 1


def is_compound_loose(text: str) -> bool:
    return bool(COORDINATOR.search(text))


async def main() -> None:
    show_sample = "--sample" in sys.argv

    from sqlmodel import select as sm_select

    from app.core.database import async_session
    from app.models.check import Claim

    async with async_session() as session:
        rows = (await session.execute(sm_select(Claim))).scalars().all()

    total_claims = 0
    elements = []  # (claim_text, element_id, description, question_shaped)
    for claim in rows:
        cm = claim.claim_map
        if not isinstance(cm, dict):
            continue
        els = cm.get("elements") or []
        if not els:
            continue
        total_claims += 1
        for el in els:
            desc = (el.get("description") or "").strip()
            if not desc:
                continue
            elements.append(
                (
                    (claim.text or "")[:70],
                    el.get("element_id", "?"),
                    desc,
                    desc.rstrip().endswith("?"),
                )
            )

    if not elements:
        print("No decomposed claims in the local DB — nothing to census.")
        return

    cons = [e for e in elements if is_compound_conservative(e[2])]
    loose = [e for e in elements if is_compound_loose(e[2])]
    questions = [e for e in elements if e[3]]
    q_cons = [e for e in questions if is_compound_conservative(e[2])]

    def pct(a, b):
        return f"{100.0 * a / b:.1f}%" if b else "n/a"

    print("=" * 78)
    print("COMPOUND ELEMENT CENSUS — local DB")
    print("=" * 78)
    print(f"claims with a claim_map : {total_claims}")
    print(f"elements total          : {len(elements)}")
    print(
        f"  question-shaped        : {len(questions)} "
        f"({pct(len(questions), len(elements))})  <- grounds-routed/opinion"
    )
    print(
        f"  declarative            : {len(elements) - len(questions)} "
        f"({pct(len(elements) - len(questions), len(elements))})  <- factual"
    )
    print()
    print(
        f"COMPOUND, conservative  : {len(cons)} / {len(elements)}  "
        f"({pct(len(cons), len(elements))})"
    )
    print(
        f"COMPOUND, loose (upper) : {len(loose)} / {len(elements)}  "
        f"({pct(len(loose), len(elements))})"
    )
    print(
        f"  of QUESTION elements  : {len(q_cons)} / {len(questions)}  "
        f"({pct(len(q_cons), len(questions))})  <- where the two-shape rule applies"
    )
    print()

    print("-- COMPOUND (conservative) — these ask two things at once:")
    for _, eid, desc, _ in cons[:40]:
        print(f"   [{eid}] {desc}")
        for i, c in enumerate(conjuncts(desc), 1):
            print(f"         {i}. {c}")
    if len(cons) > 40:
        print(f"   ... and {len(cons) - 40} more")

    only_loose = [e for e in loose if not is_compound_conservative(e[2])]
    print(
        f"\n-- CAUGHT BY LOOSE ONLY ({len(only_loose)}) — conjoined phrases, "
        f"correctly NOT split:"
    )
    for _, eid, desc, _ in only_loose[:15]:
        print(f"   [{eid}] {desc}")

    if show_sample:
        print("\n-- ALL ELEMENTS:")
        for claim_text, eid, desc, isq in elements:
            mark = "C" if is_compound_conservative(desc) else " "
            print(f"  {mark} [{eid}] {'Q' if isq else 'D'} {desc}")


if __name__ == "__main__":
    asyncio.run(main())
