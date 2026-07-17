"""Phase 1b DISCRIMINATING EVAL — question-shaped vs assertion-shaped elements.

Tests the §19 diagnosis. The halted stage (option C) emits ASSERTIONS and
produced a denialist brief on "Gaza is a genocide". The v4 eval — same
direction-forcing machinery, but QUESTION-shaped output — went green twice and
produced the balanced routes Artefact-1 measured.

Hypothesis: the toxicity comes from the assertion SHAPE, not from direction.
A counter-direction question ("what measures were taken to minimise casualties?")
invites evidence either way; a counter-direction assertion ("Israel took measures
to minimise casualties") is a talking point handed to a mapper that only looks
for support.

This runs the REAL shipped stage (app/pipeline/opinion_symmetry) with ONE
variable changed: the three prompts are monkeypatched to emit open questions.
Machinery (union guard, structural coverage, bounded rebalance, fail-safes,
_claim_dominated) is byte-identical to the assertion arm. So a difference in
output is attributable to shape alone.

Run:  cd backend && python -m scripts.opinion_symmetry_eval_questions
Writes backend/scripts/.opinion_symmetry_eval_questions.json

⛔ HISTORICAL WITNESS (frozen 2026-07-17, plan §20 slice 1). This was the
DISCRIMINATING run that corrected §19's diagnosis: with direction machinery
byte-identical and ONLY the output shape changed to questions, the Gaza
denialist brief disappeared (0/4/1 → 2/2/1) — proving the primary toxin was
assertion shape, while also exposing the three §20.2 survivors (whataboutism
via the forced counter-slot, claim-side zeroing, one-directional balance
gate). The transcript `.opinion_symmetry_eval_questions.json` is the witness —
do not overwrite. The monkeypatched symbols no longer exist; code kept
verbatim as the record.
"""

from __future__ import annotations

import sys

sys.exit(
    "HISTORICAL WITNESS — frozen at plan §20 slice 1 (2026-07-17). "
    "The discriminating shape-vs-direction run; see the module docstring and "
    ".opinion_symmetry_eval_questions.json (do not overwrite)."
)

import asyncio
import json
import os
import re
from typing import Any, Dict, List

from app.pipeline import opinion_symmetry
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.pipeline.opinion_symmetry import _claim_dominated, apply_symmetry_stage

from scripts.opinion_symmetry_eval import BATTERY

# ── The ONE variable: output shape = open questions, not assertions ───────────

DECOMPOSE_Q = """\
You are decomposing an EVALUATIVE claim into the empirical questions a NEUTRAL
analyst would investigate to inform (never settle) the judgement.

Output 3-5 OPEN QUESTIONS about the claim's NAMED SUBJECT, selected
SYMMETRICALLY:
- Include questions whose answers could build the case FOR the claim AND
  questions whose answers could build the case AGAINST it (mitigating factors,
  safeguards, countervailing forces, base rates, alternative explanations).
- Each question must be OPEN and empirically answerable — it must NOT presuppose
  its own answer, and must NOT assert anything. Ask what the evidence shows;
  never state what it shows.
- Every question must be specifically about the claim's named subject, never its
  general topic area.
- NEVER ask whether the value judgement itself is true (e.g. for "X is a
  disaster", "Is X a disaster?" is FORBIDDEN — ask about the specific measurable
  grounds instead).

Respond with JSON only:
{"elements": [{"description": "<open question>"}, ...]}
"""

ASSESS_Q = """\
You are auditing a research design. You are given an evaluative claim and a
numbered list of empirical questions chosen to investigate it.

For EACH question, give TWO labels:

direction — relative to the claim:
- "claim"   — an affirmative answer would build the case FOR the claim.
- "counter" — an affirmative answer would build the case AGAINST the claim
              (a mitigating factor, safeguard, or countervailing force).
- "neutral" — a two-directional question whose evidence could cut either way.

on_subject — true if the question is specifically about the claim's NAMED
subject (the particular entity, policy, event, or situation the claim names);
false if it addresses the general topic area without being about that subject.
A comparison of the named subject to precedents / base rates IS on_subject.

Respond with JSON only, in the SAME ORDER as the input:
{"assessments": [{"direction": "claim"|"neutral"|"counter", "on_subject": true|false}, ...]}
The array length MUST equal the number of questions given.
"""

REBALANCE_Q = """\
You are balancing a research design. You are given an evaluative claim, the
questions being KEPT, and the number of additional slots available.

Produce that many ADDITIONAL empirical questions that:
- are specifically about the claim's NAMED SUBJECT, never its general topic;
- are OPEN questions that do not presuppose their own answer and assert nothing;
- deliberately cover COUNTER-direction considerations (mitigating factors,
  safeguards, base rates, alternative explanations) not already covered;
- never ask whether the value judgement itself is true.

Respond with JSON only:
{"elements": [{"description": "<open question>"}, ...]}
"""

COVERAGE_Q = """\
You are checking coverage of a research design. You are given the FINAL set of
questions, and a numbered list of CANDIDATE questions.

For EACH candidate, say whether its substance is already covered by at least one
final question — i.e. investigating the final set would necessarily answer the
candidate's underlying question, even if worded differently.

Respond with JSON only, in the SAME ORDER as the candidates:
{"covered": [true|false, ...]}
The array length MUST equal the number of candidates given.
"""


def _patch_to_questions() -> None:
    opinion_symmetry.NORMATIVE_DECOMPOSE_PROMPT = DECOMPOSE_Q
    opinion_symmetry.ASSESS_PROMPT = ASSESS_Q
    opinion_symmetry.REBALANCE_PROMPT = REBALANCE_Q
    opinion_symmetry.COVERAGE_PROMPT = COVERAGE_Q


def _has_value_word(text: str, words: List[str]) -> bool:
    t = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", t) for w in words)


async def main() -> None:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    _patch_to_questions()
    print("ARM: question-shaped elements (direction machinery UNCHANGED)")

    analyzer = ClaimMapAnalyzer()
    results: List[Dict[str, Any]] = []
    passed = 0

    for case in BATTERY:
        claim = case["claim"]
        baseline = await analyzer.decompose_claim(claim, "eval")
        cm = await apply_symmetry_stage(analyzer, claim, baseline)

        elems = cm.get("elements") or []
        dirs = [e.get("basis", {}).get("direction") for e in elems]
        sym = cm.get("metadata", {}).get("symmetry", {})
        balanced = not _claim_dominated([d for d in dirs if d])
        vw_hits = [
            e["description"]
            for e in elems
            if _has_value_word(e.get("description", ""), case["value_words"])
        ]
        ok = balanced and len(elems) >= 3 and not vw_hits
        if ok:
            passed += 1

        print("\n" + "=" * 78)
        print(f"[{claim}]")
        print(
            f"  directions={sym.get('directions')}  balanced={balanced}  "
            f"converged={sym.get('converged')}  rounds={sym.get('rounds')}  "
            f"{'PASS' if ok else 'FAIL'}"
        )
        for e, d in zip(elems, dirs):
            print(f"      [{str(d)[:7]:7s}] {e.get('description', '')[:110]}")
        if vw_hits:
            print(f"  VALUE-WORD LEAK: {vw_hits}")

        results.append(
            {
                "claim": claim,
                "arm": "questions",
                "directions": sym.get("directions"),
                "balanced": balanced,
                "converged": sym.get("converged"),
                "value_word_leak": vw_hits,
                "elements": [
                    {"description": e.get("description"), "direction": d}
                    for e, d in zip(elems, dirs)
                ],
                "pass": ok,
            }
        )

    out_path = os.path.join(
        os.path.dirname(__file__), ".opinion_symmetry_eval_questions.json"
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 78)
    print(
        f"QUESTION ARM: {passed}/{len(BATTERY)} pass (balanced + breadth + no value-word)"
    )
    print(
        "NOTE: the gate is NOT the finding. Read the Gaza element text — the "
        "question is whether it reads as a research design or a denialist brief."
    )
    print(f"Saved transcript -> {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
