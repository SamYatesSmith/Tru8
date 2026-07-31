"""Phase 3 gating measurement — does the mapper file NON-ANSWERING sources as `supports`?

The witness (`TRU-4B9D-65EA`, "The UK COVID vaccine rollout was a triumph") is
damning precisely because the mapper CONTRADICTS ITSELF: all four grounds came
back `+SUPPORTED` while every one of the mapper's own `reasoning` strings said
the evidence does not answer — "not fully detailed", "not provided, nor is a
direct comparison", "does not specify", "not explicitly provided".

That self-contradiction is the handle. An element badged `supported` whose
supporting refs are, in the mapper's own prose, non-answering is Bug B's
surviving half. Phase 1 could not fix it (its floor counts refs, and 4 refs
clear any floor). Phase 3a could not fix it (that closed COMPOUND elements;
these are atomic). It is the mapper's answeredness judgement itself.

WHAT THIS MEASURES, and what it deliberately does not:
  * It measures the RATE on the real post-Phase-2 pool, because that is the
    number that decides build-vs-decline. The factual-path atomicity census is
    the precedent: measured at 0.8% and DECLINED rather than built on
    principle.
  * It does NOT use its phrase list as a proposed fix. A blocklist cannot close
    an open set (the evaluative-head lesson), so the list here is tuned for
    RECALL and every supporting ref's reasoning is printed verbatim underneath
    the number. The count is a signpost; the printed prose is the evidence.

Grounds-routed (question-shaped) elements only — the factual path is assertion-
shaped, where "supports" carries its ordinary meaning and is not a defect.

Usage:
    docker-compose up -d          # needs Postgres; the pipeline writes a Check
    python -m scripts.mapper_answeredness_census [--claims 4]

Writes scripts/.mapper_answeredness_census.json (full transcript, appended).
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import re
import sys
import traceback
import uuid
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

OUT = Path(__file__).resolve().parent / ".mapper_answeredness_census.json"

# Both valences deliberately. The invariant is two-sided: a positive head
# ("triumph") over-supporting is sycophancy, a negative head ("disaster")
# over-supporting is the same defect pointed the other way. Measuring only
# negative claims would report half the problem.
BATTERY = [
    ("pos", "Britain's COVID-19 vaccination rollout was a triumph"),
    ("neg", "Spending NHS money on homeopathy is indefensible"),
    ("pos", "The 2012 London Olympics were a resounding success for the UK"),
    ("neg", "The rollout of Universal Credit was a disaster for claimants"),
    ("neg", "HS2 has been a catastrophic waste of public money"),
    ("pos", "The UK's furlough scheme was an outstanding policy success"),
]

# RECALL-tuned. Over-matching is acceptable and expected: every hit is printed
# for eyeball, so a false positive costs a line of output, while a miss would
# understate the defect and wrongly argue for decline.
NON_ANSWER = re.compile(
    r"\bdoes not (?:specify|state|provide|address|detail|quantify|mention|compare|answer)\b"
    r"|\bnot (?:explicitly |fully |directly )?(?:provided|specified|stated|detailed|addressed|quantified|mentioned|available)\b"
    r"|\bno (?:direct )?(?:comparison|figure|data|evidence|breakdown|detail)s? (?:is|are|was|were)?\s*(?:provided|given|available|found)?\b"
    r"|\bdoes not (?:itself )?(?:establish|demonstrate|show|confirm)\b"
    r"|\bwithout (?:providing|specifying|quantifying)\b"
    r"|\bis silent on\b|\bstops short of\b|\bfalls short of\b"
    r"|\bonly (?:indirectly|partially|tangentially)\b"
    r"|\bdoes not engage with\b|\bleaves open\b",
    re.IGNORECASE,
)


async def run_claim(claim_text: str) -> dict | None:
    """Run one real, networked check and return its claim maps."""
    from sqlmodel import select as sm_select

    from app.core.database import async_session
    from app.models.check import Check
    from app.models.user import User
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import run_pipeline_phase1

    check_id = str(uuid.uuid4())
    async with async_session() as session:
        existing = (await session.execute(sm_select(User))).scalars().first()
        if existing:
            user_id = existing.id
        else:
            user_id = "answeredness-local-user"
            session.add(User(id=user_id, email="answer@local.test", credits=500))
            await session.commit()

    async with async_session() as session:
        session.add(
            Check(
                id=check_id,
                user_id=user_id,
                input_type="text",
                input_content=json.dumps({"content": claim_text}),
                status="processing",
            )
        )
        await session.commit()

    result = await run_pipeline_phase1(
        check_id=check_id,
        user_id=user_id,
        input_data={"input_type": "text", "content": claim_text},
        progress_reporter=ProgressReporter(check_id),
    )
    if result is None:
        print("    !! paused for selection — phase 2 did not run, claim skipped")
        return None
    return result


def census_one(result: dict) -> dict:
    """Extract grounds elements and score their supporting refs."""
    rows = []
    for claim in result.get("claims", []) or []:
        cm = claim.get("claim_map") or {}
        grounds = ((cm.get("metadata") or {}).get("grounds") or {}).get("applied")
        if not grounds:
            continue
        for el in cm.get("elements", []) or []:
            refs = el.get("evidence_refs") or []
            supports = [
                r for r in refs if (r.get("relationship") or "").lower() == "supports"
            ]
            flagged = [
                r for r in supports if NON_ANSWER.search(r.get("reasoning") or "")
            ]
            rows.append(
                {
                    "element_id": el.get("element_id"),
                    "description": el.get("description", ""),
                    "state": el.get("state"),
                    "n_refs": len(refs),
                    "n_supports": len(supports),
                    "n_non_answering": len(flagged),
                    "supports": [
                        {
                            "flagged": bool(
                                NON_ANSWER.search(r.get("reasoning") or "")
                            ),
                            "reasoning": r.get("reasoning") or "",
                        }
                        for r in supports
                    ],
                }
            )
    return {"elements": rows}


def report(all_rows: list[dict]) -> None:
    els = [r for c in all_rows for r in c["census"]["elements"]]
    if not els:
        print("\nNo grounds elements produced — nothing to measure.")
        return

    supported = [e for e in els if (e["state"] or "").lower() == "supported"]
    # The defect: badged supported, and EVERY supporting ref is non-answering.
    hollow = [
        e
        for e in supported
        if e["n_supports"] > 0 and e["n_non_answering"] == e["n_supports"]
    ]
    partial = [
        e
        for e in supported
        if e["n_supports"] > 0 and 0 < e["n_non_answering"] < e["n_supports"]
    ]
    tot_sup = sum(e["n_supports"] for e in els)
    tot_flag = sum(e["n_non_answering"] for e in els)

    print("\n" + "=" * 78)
    print("PHASE 3 GATING MEASUREMENT — mapper answeredness")
    print("=" * 78)
    print(f"  grounds elements                         {len(els)}")
    print(f"  ... badged `supported`                   {len(supported)}")
    print(f"  ... HOLLOW (supported, every support non-answering)  {len(hollow)}")
    print(f"  ... partly hollow (some supports non-answering)      {len(partial)}")
    print(f"  supporting refs total                    {tot_sup}")
    print(f"  ... non-answering by the mapper's own prose          {tot_flag}")
    if len(supported):
        print(
            f"\n  HOLLOW RATE (of supported elements)      {len(hollow)/len(supported):.1%}"
        )
    if tot_sup:
        print(f"  NON-ANSWERING RATE (of supporting refs)  {tot_flag/tot_sup:.1%}")

    print("\n" + "-" * 78)
    print("EVERY hollow element, with the mapper's own words (this is the evidence;")
    print("the percentages above are only a signpost to it):")
    print("-" * 78)
    for e in hollow:
        print(f"\n  [{e['state']}] {e['element_id']} — {e['description']}")
        for s in e["supports"]:
            print(f"      · {s['reasoning'][:190]}")
    if not hollow:
        print("\n  none")


async def main_async(n_claims: int) -> int:
    battery = BATTERY[:n_claims]
    all_rows = []
    for valence, claim in battery:
        print("\n" + "=" * 78)
        print(f"[{valence}] {claim}")
        print("=" * 78)
        try:
            result = await run_claim(claim)
        except Exception as e:
            print(f"    !! PIPELINE RAISED: {type(e).__name__}: {e}")
            traceback.print_exc()
            continue
        if result is None:
            continue
        c = census_one(result)
        n = len(c["elements"])
        print(f"    grounds elements: {n}")
        if n == 0:
            print("    (not grounds-routed — claim did not take the normative path)")
        all_rows.append({"valence": valence, "claim": claim, "census": c})

    report(all_rows)
    OUT.write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
    print(f"\nTranscript: {OUT}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--claims", type=int, default=len(BATTERY))
    return asyncio.run(main_async(p.parse_args().claims))


if __name__ == "__main__":
    raise SystemExit(main())
