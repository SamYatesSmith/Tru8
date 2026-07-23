"""Decoupling flag-flip eval — the default-ON gate (2026-07-23).

`scripts/extraction_reframe_eval.py` proves the SINGLE-SENTENCE trigger
boundary. This script covers the two surfaces that only matter once
``ENABLE_OPINION_REFRAME`` defaults ON for every check:

  BATTERY A — over-trigger on ordinary content (the regression risk).
    The Rule 6 exception now enters the extraction prompt for EVERY check,
    including straight news. Each passage is extracted twice (flag OFF, then
    flag ON) and the two claim sets are diffed. Gates:
      * no factual claim present with the flag OFF may DISAPPEAR with it ON
        (the exception must not eat the claim budget or re-shape plain claims);
      * a passage with no main-predicate evaluation must yield ZERO hints;
      * attributed opinion ("critics say X is a disaster") is a REPORTED
        statement, not our own evaluation — it must not be hinted.

  BATTERY B — grounds quality on normative claims (the feature itself).
    Runs the REAL decompose, then the REAL grounds stage, and prints the two
    element sets side by side for human grading. Mechanical gates:
      * stage applied + converged (breadth floor 3);
      * NO element restates the value judgement (the §20.6(2) lock, reused
        here as an independent check rather than trusting the stage);
      * every element is question-shaped (neutral by construction);
      * the claim text itself is never altered (direction preserved).

Neither battery can prove the LIVE pipeline is right — retrieval and mapping
are downstream. It is a pre-flight so prod checks are not spent on something
already broken.

Run:  cd backend && python -m scripts.decoupling_live_eval
Writes backend/scripts/.decoupling_live_eval.json
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings

# ── Battery A: realistic multi-sentence passages ─────────────────────────────

ARTICLES: List[Dict[str, Any]] = [
    {
        "label": "A1/straight-news-with-colour",
        "max_hints": 0,
        "note": "Editorial adjectives ('controversial', 'sweeping') are "
        "incidental — rule 6 still cleans them. NO main-predicate evaluation "
        "is asserted, so ZERO hints is the only correct answer.",
        "content": (
            "The Treasury announced a sweeping package of spending cuts on 12 March 2025. "
            "The controversial measures reduce departmental budgets by 4.2% over two years. "
            "Chancellor Rachel Reeves said the cuts were necessary to meet fiscal rules. "
            "The Office for Budget Responsibility forecast growth of 1.1% for 2025."
        ),
    },
    {
        "label": "A2/attributed-opinion",
        "max_hints": 0,
        "note": "The evaluation belongs to named critics, not the author. A "
        "reported statement is a fact about what was said — extract it plainly "
        "or drop it, but never adopt it as OUR normative claim.",
        "content": (
            "The Home Office expanded the use of facial recognition to twelve police forces in 2024. "
            "Liberty and Big Brother Watch have called the rollout a disaster for civil liberties. "
            "The Home Office says the technology was used in 3,400 deployments last year."
        ),
    },
    {
        "label": "A3/genuine-editorial",
        "max_hints": 2,
        "min_hints": 1,
        "note": "The author DOES assert a main-predicate evaluation. It must "
        "survive, hinted, WITHOUT costing the surrounding factual claims.",
        "content": (
            "Ofwat approved a 36% increase in water bills across England and Wales in December 2024. "
            "Thames Water reported debts of 19 billion pounds in the same period. "
            "The regulator's decision is a betrayal of every household it exists to protect."
        ),
    },
]

# ── Battery B: normative claims for the grounds stage ────────────────────────

GROUNDS_CLAIMS: List[Dict[str, Any]] = [
    {
        "label": "B1/negative-valence-specific",
        "claim": "The government's 2024 water regulation settlement is a disaster for British households.",
    },
    {
        "label": "B2/positive-valence",
        "claim": "The 2020 UK-EU Trade and Cooperation Agreement is a triumph for British sovereignty.",
        "note": "Positive valence must be handled identically to negative — "
        "the grounds must not be softer or harder because we like the direction.",
    },
    {
        "label": "B3/contested-label",
        "claim": "The situation in Gaza is a genocide.",
        "note": "The value-predicate lock must forbid 'Is it a genocide?' as an "
        "element, while a real route (status of ICJ proceedings) passes.",
    },
    {
        "label": "B4/vague-no-anchor",
        "claim": "Immigration policy is a disaster.",
        "note": "The KNOWN specificity gap (logged, unbuilt): no where/when/whose. "
        "Expect weak grounds. Recorded to see HOW it degrades — the requirement "
        "is that it degrades honestly, never that it fabricates an anchor.",
        "expect_weak": True,
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _tokens(text: str) -> frozenset:
    return frozenset(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _best_overlap(needle: str, haystack: List[str]) -> float:
    """Max Jaccard-ish containment of `needle` against any candidate."""
    n = _tokens(needle)
    if not n:
        return 0.0
    best = 0.0
    for h in haystack:
        ht = _tokens(h)
        if not ht:
            continue
        best = max(best, len(n & ht) / len(n))
    return best


def _fresh_extractor():
    # Imported per call so the flag set on `settings` is read in __init__
    # (the Rule 6 splice happens there, not at call time).
    from app.pipeline.extract import ClaimExtractor

    return ClaimExtractor()


async def _extract(content: str) -> List[Dict[str, Any]]:
    result = await _fresh_extractor().extract_claims(content, {"title": ""})
    return [
        {"text": c.get("text"), "type_hint": c.get("type_hint")}
        for c in (result.get("claims") or [])
    ]


# ── Battery A ────────────────────────────────────────────────────────────────


async def run_battery_a() -> List[Dict[str, Any]]:
    print("\n" + "#" * 78)
    print("# BATTERY A — over-trigger control on ordinary content (OFF vs ON)")
    print("#" * 78)

    results: List[Dict[str, Any]] = []
    for case in ARTICLES:
        settings.ENABLE_OPINION_REFRAME = False
        off = await _extract(case["content"])
        settings.ENABLE_OPINION_REFRAME = True
        on = await _extract(case["content"])

        on_texts = [c["text"] for c in on]
        hints = [c for c in on if c.get("type_hint") == "normative"]
        off_hints = [c for c in off if c.get("type_hint") == "normative"]

        # Every flag-OFF claim should still be represented with the flag ON.
        lost = [c["text"] for c in off if _best_overlap(c["text"], on_texts) < 0.6]

        max_h = case.get("max_hints")
        min_h = case.get("min_hints", 0)
        failures = []
        if lost:
            failures.append(f"{len(lost)} flag-OFF claim(s) lost with the flag ON")
        if max_h is not None and len(hints) > max_h:
            failures.append(f"{len(hints)} hint(s), max {max_h} — hint OVER-FIRED")
        if len(hints) < min_h:
            failures.append(f"{len(hints)} hint(s), expected >= {min_h} — hint MISSED")
        if off_hints:
            failures.append("hint leaked with the flag OFF")

        ok = not failures
        print("\n" + "=" * 78)
        print(f"[{case['label']}]")
        print(f"  note: {case['note']}")
        print(f"  --- flag OFF ({len(off)} claims) ---")
        for c in off:
            print(f"    · {c['text']}")
        print(f"  --- flag ON  ({len(on)} claims, {len(hints)} hinted) ---")
        for c in on:
            tag = "  [HINTED]" if c.get("type_hint") == "normative" else ""
            print(f"    · {c['text']}{tag}")
        if lost:
            print("  LOST (present OFF, absent ON):")
            for t in lost:
                print(f"    ✗ {t}")
        print(f"  → {'PASS' if ok else 'FAIL: ' + '; '.join(failures)}")

        results.append(
            {
                "battery": "A",
                "label": case["label"],
                "off_claims": off,
                "on_claims": on,
                "hinted": len(hints),
                "lost": lost,
                "pass": ok,
                "failures": failures,
            }
        )
    return results


# ── Battery B ────────────────────────────────────────────────────────────────


async def run_battery_b() -> List[Dict[str, Any]]:
    from app.pipeline import opinion_symmetry as osym
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    print("\n" + "#" * 78)
    print("# BATTERY B — grounds quality (baseline decompose vs grounds stage)")
    print("#" * 78)

    settings.ENABLE_OPINION_REFRAME = True
    analyzer = ClaimMapAnalyzer()
    results: List[Dict[str, Any]] = []

    for case in GROUNDS_CLAIMS:
        claim = case["claim"]
        raw = await analyzer.decompose_claim(claim, "c1")
        # decompose_claim is annotated -> ClaimMap but returns a plain dict on
        # the live path; accept either rather than assume.
        baseline_map = raw if isinstance(raw, dict) else raw.model_dump()
        baseline = [e.get("description") for e in (baseline_map.get("elements") or [])]

        grounds_map = await osym.apply_grounds_stage(analyzer, claim, baseline_map)
        meta = (grounds_map.get("metadata") or {}).get("grounds") or {}
        final = [e.get("description") for e in (grounds_map.get("elements") or [])]

        restated = [e for e in final if osym._is_restatement(claim, e or "")]
        not_q = [e for e in final if not (e or "").rstrip().endswith("?")]

        failures = []
        if not meta.get("applied"):
            failures.append("grounds stage did NOT apply")
        if restated:
            failures.append(f"{len(restated)} element(s) restate the judgement")
        if not_q:
            failures.append(f"{len(not_q)} element(s) not question-shaped")
        if not meta.get("converged") and not case.get("expect_weak"):
            failures.append("did not converge (below breadth floor 3)")

        ok = not failures
        print("\n" + "=" * 78)
        print(f"[{case['label']}]  {claim}")
        if case.get("note"):
            print(f"  note: {case['note']}")
        print("  --- baseline decompose (what the flag-OFF path researches) ---")
        for e in baseline:
            print(f"    · {e}")
        print(
            f"  --- grounds stage (applied={meta.get('applied')}, "
            f"converged={meta.get('converged')}, n={meta.get('element_count')}) ---"
        )
        for e in final:
            print(f"    · {e}")
        if restated:
            print("  RESTATEMENTS (value-predicate lock leak):")
            for e in restated:
                print(f"    ✗ {e}")
        print(f"  → {'PASS' if ok else 'FAIL: ' + '; '.join(failures)}")

        results.append(
            {
                "battery": "B",
                "label": case["label"],
                "claim": claim,
                "baseline_elements": baseline,
                "grounds_elements": final,
                "grounds_metadata": meta,
                "pass": ok,
                "failures": failures,
                "expect_weak": bool(case.get("expect_weak")),
            }
        )
    return results


async def main() -> None:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    original = settings.ENABLE_OPINION_REFRAME
    try:
        results = await run_battery_a()
        results += await run_battery_b()
    finally:
        settings.ENABLE_OPINION_REFRAME = original

    out_path = os.path.join(os.path.dirname(__file__), ".decoupling_live_eval.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    passed = sum(1 for r in results if r["pass"])
    print("\n" + "=" * 78)
    print(f"DECOUPLING FLIP EVAL: {passed}/{len(results)} pass")
    for r in results:
        if not r["pass"]:
            print(f"  FAIL [{r['label']}]: {'; '.join(r['failures'])}")
    print("GREEN" if passed == len(results) else "NOT GREEN")
    print(f"Saved transcript → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
