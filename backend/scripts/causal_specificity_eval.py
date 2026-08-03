"""Targeted A/B eval for §4d fix 2 — the mapping SPECIFICITY CHECK rule.

Fix 2 tags causal-link elements ``[CAUSAL LINK]`` and adds a SPECIFICITY CHECK
that maps general-mechanism / educational / reference evidence as ``context``
(not ``supports``) on such elements. This proves the rule bites on generic
items WITHOUT dragging legitimate specific supports along.

It runs the SAME element + evidence pool through two live mapping prompts:
  - OLD: the mapping prompt with the SPECIFICITY CHECK stripped and no
         ``[CAUSAL LINK]`` tag (pre-fix behaviour).
  - NEW: the current prompt + tag (post-fix).
k repeats each; reports the relationship each item received per condition.

Results dot-file: backend/scripts/.causal_specificity_eval.json.
Run: cd backend && python -m scripts.causal_specificity_eval [--repeats 3]
Needs a live Gemini key (GOOGLE_AI_API_KEY).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from app.pipeline.claim_map_analyzer import MAPPING_PROMPT, ClaimMapAnalyzer

OUT_PATH = Path(__file__).parent / ".causal_specificity_eval.json"

# The founder's e04: a specific causal-trend element.
ELEMENT = {
    "element_id": "e1",
    "description": (
        "Elevated tectonic plate activity is currently driving a large rise "
        "in volcanic eruptions"
    ),
}

# One legitimate specific support, two generic items the fix should demote.
EVIDENCE = [
    {
        "evidence_id": "ev-specific",
        "title": "Study: global volcanic eruption frequency and plate-boundary stress, 2000-2020",
        "tier": "primary",
        "evidence_type": "study",
        "snippet": (
            "Analysis of the Smithsonian eruption record finds documented "
            "eruptions rose over 2000-2020 and attributes the trend to measured "
            "increases in plate-boundary strain over the same period."
        ),
    },
    {
        "evidence_id": "ev-mechanism",
        "title": "How tectonic activity produces volcanic eruptions — an explainer",
        "tier": "reporting",
        "evidence_type": "article",
        "snippet": (
            "When tectonic plates shift at their boundaries, magma is forced "
            "upward and volcanic eruptions follow. This piece explains the "
            "causal chain from plate movement to eruptions in general terms. "
            "It gives no dates, no counts, and no claim about any current trend."
        ),
    },
    {
        "evidence_id": "ev-worksheet",
        "title": "Plate Tectonics Explained — Grades 6-12 Classroom Worksheet",
        "tier": "commentary",
        "evidence_type": "educational",
        "snippet": (
            "An educational overview of how tectonic plates move and how "
            "earthquakes and volcanoes form. Includes review questions for "
            "students. No dates or trend figures."
        ),
    },
]

# The SPECIFICITY CHECK block (character-exact) so we can strip it for OLD.
_SPECIFICITY_BLOCK = (
    "- SPECIFICITY CHECK: An element tagged [CAUSAL LINK] asserts a SPECIFIC causal "
    "relationship — a named cause driving a named effect, often over a specific period. "
    "Evidence that only describes a general mechanism, teaches how such processes work "
    "(educational or explanatory material), or supplies background/reference content does "
    'NOT support that specific causal assertion — map it as "context", not "supports". '
    'Reserve "supports"/"challenges" for evidence bearing on whether THIS cause is driving '
    "THIS effect as asserted.\n"
)


def _evidence_desc() -> str:
    return "\n".join(
        f"- {e['evidence_id']}: [{e['title']}] "
        f"[Tier: {e['tier']}] [Type: {e['evidence_type']}] {e['snippet']}"
        for e in EVIDENCE
    )


def _build_prompt(*, new: bool) -> str:
    base = MAPPING_PROMPT if new else MAPPING_PROMPT.replace(_SPECIFICITY_BLOCK, "")
    tag = " [CAUSAL LINK]" if new else ""
    elements_desc = f"- {ELEMENT['element_id']}: {ELEMENT['description']}{tag}"
    return (
        f"{base}\n\n"
        f"Claim: {ELEMENT['description']}\n\n"
        f"Elements:\n{elements_desc}\n\n"
        f"Evidence:\n{_evidence_desc()}"
    )


async def _run(condition: str, new: bool, repeats: int) -> dict:
    analyzer = ClaimMapAnalyzer()
    prompt = _build_prompt(new=new)
    per_item: dict[str, Counter] = {e["evidence_id"]: Counter() for e in EVIDENCE}
    for _ in range(repeats):
        parsed = await analyzer._call_llm(
            prompt=prompt,
            temperature=analyzer.analyzer_temperature,
            max_tokens=analyzer.analyzer_max_tokens,
            label="mapping",
        )
        refs = []
        if parsed and isinstance(parsed.get("elements"), list) and parsed["elements"]:
            refs = parsed["elements"][0].get("evidence_refs") or []
        seen = set()
        for r in refs:
            eid = r.get("evidence_id")
            rel = r.get("relationship")
            if eid in per_item:
                per_item[eid][rel] += 1
                seen.add(eid)
        for eid in per_item:
            if eid not in seen:
                per_item[eid]["unmapped"] += 1
    return {eid: dict(c) for eid, c in per_item.items()}


async def main(repeats: int) -> None:
    old = await _run("old", new=False, repeats=repeats)
    new = await _run("new", new=True, repeats=repeats)
    result = {"repeats": repeats, "old": old, "new": new}
    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"\nCausal-specificity eval ({repeats} repeats each)\n" + "=" * 60)
    for eid in (e["evidence_id"] for e in EVIDENCE):
        print(f"\n{eid}")
        print(f"  OLD: {old[eid]}")
        print(f"  NEW: {new[eid]}")
    print("\nExpected: ev-specific stays supports; ev-mechanism / ev-worksheet")
    print("move towards context under NEW (generic mechanism, no specific trend).")
    print(f"\nWritten to {OUT_PATH.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    asyncio.run(main(args.repeats))
