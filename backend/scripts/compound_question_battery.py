"""How many GROUNDS questions are compound? Real decompositions, 20 claims.

The local DB holds only declarative (factual-path) elements, so it cannot answer
this. The mapper's two-shape rule (claim_map_analyzer.py:292) applies to
QUESTION-shaped elements — the ones the grounds stage builds for evaluative
claims — and a compound question defeats it by construction: one element, two
shapes, one rule, so whichever half is read the other is graded wrong.

This runs the real decompose + grounds path on a spread of evaluative claims and
counts. No retrieval, no mapping — decomposition only.

Usage:  python -m scripts.compound_question_battery
"""

import asyncio
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

CLAIMS = [
    "The UK's HS2 rail project was a catastrophic waste of money",
    "Brexit has been an economic disaster for Britain",
    "The 2008 bank bailouts were the right decision",
    "Social media has been terrible for teenage mental health",
    "Remote working has made companies less productive",
    "The NHS is the best healthcare system in the world",
    "Nuclear power is the safest form of energy generation",
    "The war on drugs has been a complete failure",
    "Electric vehicles are worse for the environment than petrol cars",
    "University degrees are no longer worth the money",
    "The London congestion charge has been a great success",
    "Amazon's treatment of warehouse workers is indefensible",
    "Modern architecture has ruined British city centres",
    "The furlough scheme was an outstanding policy response",
    "Privatising British Rail was a mistake",
    "The Australian wildfire response in 2020 was woefully inadequate",
    "Football's VAR system has improved the game",
    "Cycling investment in London has been money well spent",
    "The Post Office Horizon scandal was handled disgracefully",
    "Streaming services have been bad for the music industry",
]

COORDINATOR = re.compile(r",?\s+\b(?:and|or|but)\b\s+", re.I)
_WH = (
    r"(?:to\s+what\s+extent|how\s+(?:many|much|often|long|effective)|"
    r"what|which|why|when|where|who|whom|whose|how|whether|if)"
)
_AUX = r"(?:did|does|do|was|were|is|are|has|have|had|will|would|can|could|should)"
INTERROGATIVE_HEAD = re.compile(rf"^\s*(?:{_WH}\b|{_AUX}\s+\w+)", re.I)

# Shape of each conjunct, per the mapper's two-shape rule.
DIRECTIONAL = re.compile(
    r"\b(to\s+what\s+extent|whether|did|does|do|was|were|is|are|has|have|had)\b", re.I
)
ENUMERATIVE = re.compile(r"\b(what|which|how\s+(?:many|much))\b", re.I)


def conjuncts(text: str):
    parts, cursor = [], 0
    for m in COORDINATOR.finditer(text):
        if INTERROGATIVE_HEAD.match(text[m.end() :]):
            parts.append(text[cursor : m.start()].strip())
            cursor = m.end()
    parts.append(text[cursor:].strip())
    return [p for p in parts if p]


def shape(text: str) -> str:
    """Which half of the two-shape rule would grade this?"""
    head = text[:60]
    if re.match(r"^\s*(to\s+what\s+extent|whether)", head, re.I):
        return "directional"
    if ENUMERATIVE.match(head.strip()):
        return "enumerative"
    if DIRECTIONAL.match(head.strip()):
        return "directional"
    return "enumerative" if ENUMERATIVE.search(head) else "directional"


async def ground_one(analyzer, claim: str, idx: int):
    from app.pipeline.opinion_symmetry import apply_grounds_stage

    try:
        baseline = await analyzer.decompose_claim(claim, f"battery-{idx}")
        bl = (
            baseline.model_dump() if hasattr(baseline, "model_dump") else dict(baseline)
        )
        rebuilt = await apply_grounds_stage(analyzer, claim, bl)
        descs = [
            (e.get("description") or "").strip()
            for e in (rebuilt.get("elements") or [])
        ]
        return claim, [d for d in descs if d]
    except Exception as e:  # a battery run must never die on one claim
        print(f"  !! {claim[:50]}: {type(e).__name__}: {e}")
        return claim, []


async def main() -> None:
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    analyzer = ClaimMapAnalyzer()

    results = []
    for start in range(0, len(CLAIMS), 5):
        chunk = CLAIMS[start : start + 5]
        results += await asyncio.gather(
            *(ground_one(analyzer, c, start + i) for i, c in enumerate(chunk))
        )
        print(f"  ...{min(start + 5, len(CLAIMS))}/{len(CLAIMS)} claims decomposed")

    all_elems = [(c, d) for c, ds in results for d in ds]
    questions = [(c, d) for c, d in all_elems if d.rstrip().endswith("?")]
    compound = [(c, d) for c, d in questions if len(conjuncts(d)) > 1]
    mixed = [(c, d) for c, d in compound if len({shape(p) for p in conjuncts(d)}) > 1]

    def pct(a, b):
        return f"{100.0 * a / b:.1f}%" if b else "n/a"

    print("\n" + "=" * 78)
    print("COMPOUND QUESTION BATTERY — grounds-routed elements, real decompositions")
    print("=" * 78)
    print(f"claims decomposed  : {len([r for r in results if r[1]])}/{len(CLAIMS)}")
    print(f"elements produced  : {len(all_elems)}")
    print(
        f"question-shaped    : {len(questions)} ({pct(len(questions), len(all_elems))})"
    )
    print()
    print(
        f"COMPOUND questions : {len(compound)} / {len(questions)}  "
        f"({pct(len(compound), len(questions))})"
    )
    print(
        f"  ...of which MIXED-SHAPE: {len(mixed)} / {len(questions)}  "
        f"({pct(len(mixed), len(questions))})"
    )
    print("     ^ these are the dangerous ones: one element, two grading rules,")
    print("       so the easy half can badge the whole element `supported`.")
    print()

    print("-- COMPOUND questions found:")
    for c, d in compound:
        tag = "MIXED-SHAPE" if (c, d) in mixed else "same shape"
        print(f"\n   claim: {c[:66]}")
        print(f"   [{tag}] {d}")
        for i, p in enumerate(conjuncts(d), 1):
            print(f"       {i}. ({shape(p)}) {p}")

    if not compound:
        print("   none")


if __name__ == "__main__":
    asyncio.run(main())
