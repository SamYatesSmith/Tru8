"""Artefact-0 v2 — mechanical symmetry stage (Decoupling build plan §13).

v1 proved prompt-only symmetry FAILS: even a prompt ordered to be symmetric
produced claim-confirmatory route sets on every evaluative case (red-team =
skewed_to_confirm), and it also over-fired on plain facts.

v2 tests the fix: a mechanical SECOND STAGE, scoped to normative_flagged claims
only (approach (i)+(iii) in the plan):

    decompose (candidate)  ──▶  is normative_flagged?
                                   │ no ──▶ done (empirical, no critic — fixes over-fire)
                                   │ yes
                                   ▼
    completeness-critic  ──▶  revise (must fold in the missing disconfirming
                              dimensions; must not drop a structural element)
                                   ▼
    re-run completeness-critic on the REVISED routes

Green light = the re-critic verdict flips skewed_to_confirm → balanced AND the
revised routes visibly contain the previously-missing disconfirming dimensions
(e.g. Gaza intent/mens rea, counterbalancing media, policy successes).

Run:
    python -m scripts.decompose_symmetry_eval_v2
Writes backend/scripts/.decompose_symmetry_eval_v2.json.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

# Reuse the v1 artefacts (candidate prompt, red-team critic, battery, helpers).
from scripts.decompose_symmetry_eval import (
    BATTERY,
    CANDIDATE_PROMPT,
    _decompose,
    _extract,
    _redteam,
)

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

# ── The revise stage (the mechanical second pass under test) ─────────────────
REVISE_PROMPT = """\
You are refining a research design so it is BALANCED. You are given:
- an evaluative claim,
- an initial set of empirical dimensions chosen to investigate it,
- a neutral reviewer's critique naming dimensions that are MISSING (especially
  ones whose findings could count AGAINST the claim).

Produce the FINAL set of 1-5 empirical dimensions a NEUTRAL analyst would
examine. Requirements:
- You MUST incorporate the disconfirming dimensions the reviewer named.
- You MUST NOT drop a necessary structural dimension (if assessing the claim
  logically requires a dimension — e.g. intent for a genocide claim — keep it,
  even if the initial set omitted it).
- Keep every dimension NEUTRAL and two-directional (an open empirical question
  or "the level and direction of X"), never a directional assertion.
- Never restate the value judgement itself as a dimension.
- Maximum 5. If forced to choose, keep the most decision-relevant dimensions and
  ensure BOTH confirming and disconfirming considerations are represented.

Respond with JSON only:
{"elements": [{"description": "<empirical dimension>"}, ...]}
"""


async def _revise(
    analyzer: ClaimMapAnalyzer,
    claim: str,
    elements: List[str],
    critique: Dict[str, Any],
) -> List[str]:
    dims = "\n".join(f"- {e}" for e in elements)
    missing = "\n".join(
        f"- {m}" for m in (critique.get("missing_disconfirming_dimensions") or [])
    )
    parsed = await analyzer._call_llm(
        prompt=(
            f"{REVISE_PROMPT}\n\nClaim: {claim}\n\n"
            f"Initial dimensions:\n{dims}\n\n"
            f"Reviewer critique (verdict={critique.get('verdict')}):\n{missing}"
        ),
        temperature=analyzer.decomposition_temperature,
        max_tokens=1500,
        label="decomp_revise",
    )
    return _extract(parsed)["elements"]


async def main() -> None:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    analyzer = ClaimMapAnalyzer()
    results: List[Dict[str, Any]] = []
    flips = 0
    normative_total = 0

    for case in BATTERY:
        claim, label = case["claim"], case["label"]
        cand = await _decompose(analyzer, CANDIDATE_PROMPT, claim, "decomp_candidate")

        rec: Dict[str, Any] = {
            "label": label,
            "claim": claim,
            "claim_type": cand["claim_type"],
            "v1_elements": cand["elements"],
        }

        print("\n" + "=" * 78)
        print(f"[{label}]  {claim}")
        print(f"  type={cand['claim_type']}")

        if cand["claim_type"] != "normative_flagged":
            # Scoped: empirical/other claims skip the critic entirely.
            print("  (empirical — no symmetry stage; skipped)")
            rec["skipped"] = True
            results.append(rec)
            continue

        normative_total += 1
        critic1 = await _redteam(analyzer, claim, cand["elements"])
        v1_verdict = (critic1 or {}).get("verdict")
        revised = await _revise(analyzer, claim, cand["elements"], critic1 or {})
        critic2 = await _redteam(analyzer, claim, revised)
        v2_verdict = (critic2 or {}).get("verdict")

        flipped = v1_verdict == "skewed_to_confirm" and v2_verdict == "balanced"
        if flipped:
            flips += 1

        rec.update(
            {
                "v1_verdict": v1_verdict,
                "v2_elements": revised,
                "v2_verdict": v2_verdict,
                "v2_missing": (critic2 or {}).get("missing_disconfirming_dimensions"),
                "flipped_to_balanced": flipped,
            }
        )
        results.append(rec)

        print(f"  v1 routes ({v1_verdict}):")
        for e in cand["elements"]:
            print(f"      - {e}")
        print(f"  v2 routes ({v2_verdict}){'  ✅ FLIPPED' if flipped else ''}:")
        for e in revised:
            print(f"      + {e}")
        if (critic2 or {}).get("missing_disconfirming_dimensions"):
            print("  v2 residual missing:")
            for m in critic2["missing_disconfirming_dimensions"]:
                print(f"      x {m}")

    out_path = os.path.join(
        os.path.dirname(__file__), ".decompose_symmetry_eval_v2.json"
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 78)
    print(
        f"SYMMETRY FLIP: {flips}/{normative_total} normative claims moved "
        f"skewed_to_confirm → balanced after the revise stage."
    )
    print(f"Saved transcript → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
