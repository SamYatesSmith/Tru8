"""Phase 1a trigger battery — extraction reframe eval (plan §16.4, 2026-07-16).

Runs the REAL extraction path (Gemini primary) with ENABLE_OPINION_REFRAME
forced ON, and asserts the §2/§16 trigger boundary mechanically:

  POSITIVE (must yield a type_hint="normative" claim, direction preserved):
    - the ORIGIN SHAPE: one sentence carrying fact + opinion → BOTH claims
    - single-sentence opinions, negative AND positive valence

  NEGATIVE (must yield ordinary claims, NO hint):
    - flat-fact falsehoods ("the 2020 election was stolen")
    - plain facts
    - codified-test predicates ("anticompetitive") — D2 criterion

  DROP (must yield no claim at all — unchanged behaviour):
    - advisory/preference questions (rule 9 exclusions)

Also runs the origin case with the flag OFF to demonstrate today's behaviour
(opinion dropped) for the before/after record.

Run:  cd backend && python -m scripts.extraction_reframe_eval
Writes backend/scripts/.extraction_reframe_eval.json
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List

from app.core.config import settings

BATTERY: List[Dict[str, Any]] = [
    # ── POSITIVE: must produce a normative-hinted claim ──────────────────────
    {
        "label": "origin/fact+opinion",
        "content": "The Warner, Paramount proposed merger is a real danger to American democracy.",
        "expect": "hinted",
        "note": "origin shape TRU-1928-D5F6 — the evaluative point must survive. "
        "The embedded fact (merger proposed) is a noun phrase, not a separate "
        "assertion — ONE comprehensive hinted claim is the correct output "
        "(rules 10/12); the empirical premise surfaces at decompose.",
    },
    {
        "label": "origin/compound-two-assertions",
        "content": "Warner Bros and Paramount proposed a merger in December 2023. "
        "The deal is a real danger to American democracy.",
        "expect": "hinted_plus_fact",
        "note": "two ASSERTED propositions — both must survive: the fact as a "
        "plain claim AND the opinion as a hinted claim",
    },
    {
        "label": "opinion/negative-valence",
        "content": "The government's immigration policy is a disaster.",
        "expect": "hinted",
    },
    {
        "label": "opinion/positive-valence",
        "content": "The government's new trade deal is a gift to freedom for British workers.",
        "expect": "hinted",
        "note": "direction must be preserved, never inverted",
    },
    {
        "label": "opinion/contested-label",
        "content": "The situation in Gaza is a genocide.",
        "expect": "hinted",
    },
    # ── NEGATIVE: ordinary claims, no hint ───────────────────────────────────
    {
        "label": "boundary-neg/false-fact",
        "content": "The 2020 US presidential election was stolen.",
        "expect": "plain",
    },
    {
        "label": "boundary-neg/plain-fact",
        "content": "UK inflation fell below 3% in 2024.",
        "expect": "plain",
    },
    {
        "label": "boundary-neg/codified-test",
        "content": "The Warner Bros-Paramount merger is anticompetitive.",
        "expect": "plain",
        "note": "D2 codified-test criterion — legal predicate, never hinted",
    },
    # ── DROP: no claim at all (rule 9 exclusions unchanged) ──────────────────
    {
        "label": "drop/advisory-question",
        "content": "What should I invest in this year?",
        "expect": "dropped",
        # VERIFIED 2026-07-16: the LLM path correctly returns 0 claims, but
        # extract_claims treats 0-claims-success as failure and cascades to
        # the rule-based fallback, which junk-extracts the raw sentence.
        # FLAG-INDEPENDENT (identical with flag off) → pre-existing defect
        # F-EXTRACT-FALLBACK, out of Phase 1a scope. Reported, not gating.
        "known_pre_existing": True,
    },
]


def _fresh_extractor():
    # Import here so the settings flag set in main() is read at __init__.
    from app.pipeline.extract import ClaimExtractor

    return ClaimExtractor()


async def _run_case(content: str) -> Dict[str, Any]:
    extractor = _fresh_extractor()
    result = await extractor.extract_claims(content, {"title": ""})
    claims = result.get("claims", []) or []
    return {
        "success": result.get("success", False),
        "claims": [
            {
                "text": c.get("text"),
                "type_hint": c.get("type_hint"),
                "confidence": c.get("confidence"),
            }
            for c in claims
        ],
    }


def _judge(expect: str, claims: List[Dict[str, Any]]) -> tuple[bool, str]:
    hinted = [c for c in claims if c.get("type_hint") == "normative"]
    if expect == "hinted":
        if not claims:
            return False, "no claims extracted (opinion still dropped)"
        if not hinted:
            return False, "claims extracted but none carries the normative hint"
        return True, f"{len(hinted)} hinted claim(s)"
    if expect == "plain":
        if not claims:
            return False, "no claims extracted (should extract a plain claim)"
        if hinted:
            return False, "hint over-fired on a non-evaluative claim"
        return True, f"{len(claims)} plain claim(s), no hint"
    if expect == "hinted_plus_fact":
        plain = [c for c in claims if not c.get("type_hint")]
        if not hinted:
            return False, "the asserted opinion did not survive with a hint"
        if not plain:
            return False, "the asserted fact did not survive as a plain claim"
        return True, f"{len(hinted)} hinted + {len(plain)} plain"
    if expect == "dropped":
        if claims:
            return False, f"{len(claims)} claim(s) extracted (should drop)"
        return True, "dropped as before"
    return False, f"unknown expectation {expect}"


async def main() -> None:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    results: List[Dict[str, Any]] = []
    passed = 0

    # ── Flag ON: the battery ─────────────────────────────────────────────────
    settings.ENABLE_OPINION_REFRAME = True
    for case in BATTERY:
        out = await _run_case(case["content"])
        ok, why = _judge(case["expect"], out["claims"])
        known = bool(case.get("known_pre_existing"))
        if ok:
            passed += 1
        results.append({**case, **out, "pass": ok, "why": why})
        print("\n" + "=" * 78)
        print(f"[{case['label']}]  {case['content']}")
        for c in out["claims"]:
            tag = " [HINTED]" if c.get("type_hint") == "normative" else ""
            print(f"    · {c['text']}{tag}")
        verdict = (
            "✅ PASS"
            if ok
            else ("⚠ KNOWN PRE-EXISTING (non-gating)" if known else "❌ FAIL")
        )
        print(f"  expect={case['expect']}  →  {verdict} ({why})")

    # ── Flag OFF: origin case, today's behaviour (before/after record) ──────
    settings.ENABLE_OPINION_REFRAME = False
    off = await _run_case(BATTERY[0]["content"])
    off_hinted = [c for c in off["claims"] if c.get("type_hint") == "normative"]
    off_ok = not off_hinted  # today's path must emit no hint
    results.append(
        {
            "label": "flag-off/origin",
            "content": BATTERY[0]["content"],
            **off,
            "pass": off_ok,
            "why": "flag off — no hint may appear",
        }
    )
    print("\n" + "=" * 78)
    print(f"[flag-off/origin]  {BATTERY[0]['content']}")
    for c in off["claims"]:
        print(f"    · {c['text']}  (hint={c.get('type_hint')})")
    print(f"  flag OFF → {'✅ no hint (as today)' if off_ok else '❌ HINT LEAKED'}")

    # ── Flag OFF: advisory control (verifier NIT-5) — RECORD the evidence that
    # the fallback junk-extraction is flag-independent (F-EXTRACT-FALLBACK),
    # not merely assert it from code inspection. Non-gating.
    off_adv = await _run_case("What should I invest in this year?")
    results.append(
        {
            "label": "flag-off/advisory-control",
            "content": "What should I invest in this year?",
            **off_adv,
            "pass": None,  # recorded evidence, not a gate
            "why": "flag-off control for F-EXTRACT-FALLBACK (pre-existing)",
        }
    )
    print("\n" + "=" * 78)
    print("[flag-off/advisory-control]  What should I invest in this year?")
    for c in off_adv["claims"]:
        print(f"    · {c['text']}  (hint={c.get('type_hint')})")
    print(
        "  flag OFF → "
        + (
            "⚠ junk-extracted (F-EXTRACT-FALLBACK, flag-independent — recorded)"
            if off_adv["claims"]
            else "dropped (fallback defect not reproduced this run)"
        )
    )

    out_path = os.path.join(os.path.dirname(__file__), ".extraction_reframe_eval.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    gating = [c for c in BATTERY if not c.get("known_pre_existing")]
    gating_passed = sum(
        1
        for r in results
        if r.get("pass")
        and not r.get("known_pre_existing")
        and r["label"] != "flag-off/origin"
    )
    total = len(BATTERY) + 1
    all_pass = gating_passed == len(gating) and off_ok
    print("\n" + "=" * 78)
    print(
        f"TRIGGER BATTERY: {passed + (1 if off_ok else 0)}/{total} pass "
        f"({gating_passed}/{len(gating)} gating + flag-off control "
        f"{'ok' if off_ok else 'FAILED'}; known-pre-existing cases non-gating)"
    )
    print("🟢 GREEN" if all_pass else "🔴 NOT GREEN")
    print(f"Saved transcript → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
