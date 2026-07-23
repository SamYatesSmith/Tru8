"""T2 outage repro — exact-input test, no assumptions (2026-07-23).

Hypothesis under test (founder's "could it be simple — 'the …'?"): the T2
submission was copy-pasted from the assistant's chat summary, so the text began
with a literal U+2026 ellipsis and LACKED the subject ("The 2020 UK-EU"):

    "…Trade and Cooperation Agreement is a triumph for British sovereignty."

This script runs that EXACT string (A) and the intended full claim (B, control)
through every stage that runs before RETRIEVE — extraction (flag ON, live
Gemini), single-thesis recombination, grounds decompose, scope tagging — with a
hard per-stage timeout so a hang is CAUGHT, not suffered. It prints entities
verbatim, because entities feed adapter prepare_query at retrieval.

What this can and cannot prove: it exercises the real pre-retrieval path
locally; it cannot reproduce prod retrieval itself (search keys / OOM
conditions differ). If A diverges from B before retrieval, the divergence is
the lead. If A == B and both are clean, the ellipsis hypothesis is WEAKENED
and the Railway logs remain the decisive evidence.

Run:  cd backend && python -m scripts.repro_t2_ellipsis
Writes backend/scripts/.repro_t2_ellipsis.json
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import traceback
from typing import Any, Dict

from app.core.config import settings

TEXT_A = "…Trade and Cooperation Agreement is a triumph for British sovereignty."
TEXT_B = (
    "The 2020 UK-EU Trade and Cooperation Agreement is a triumph for British "
    "sovereignty."
)

STAGE_TIMEOUT_S = 90


async def _stage(name: str, coro) -> Dict[str, Any]:
    t0 = time.monotonic()
    try:
        result = await asyncio.wait_for(coro, timeout=STAGE_TIMEOUT_S)
        return {
            "stage": name,
            "ok": True,
            "s": round(time.monotonic() - t0, 1),
            "result": result,
        }
    except asyncio.TimeoutError:
        return {
            "stage": name,
            "ok": False,
            "s": STAGE_TIMEOUT_S,
            "error": "TIMEOUT — this stage hangs",
        }
    except Exception as e:
        return {
            "stage": name,
            "ok": False,
            "s": round(time.monotonic() - t0, 1),
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc()[-1500:],
        }


async def run_variant(label: str, text: str) -> Dict[str, Any]:
    from app.pipeline import opinion_symmetry as osym
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
    from app.pipeline.extract import (
        ClaimExtractor,
        recombine_single_thesis,
        is_single_declarative_sentence,
    )

    print("\n" + "=" * 78)
    print(f"[{label}] {text!r}")
    out: Dict[str, Any] = {"label": label, "text": text, "stages": []}

    # 0 — mechanical single-sentence gate (no LLM)
    single = is_single_declarative_sentence(text)
    print(f"  is_single_declarative_sentence = {single}")
    out["single_sentence"] = single

    # 1 — extraction (live LLM, flag as deployed)
    st = await _stage("extract", ClaimExtractor().extract_claims(text, {"title": ""}))
    out["stages"].append(st)
    if not st["ok"]:
        print(f"  extract → {st['error']}")
        return out
    claims = st["result"].get("claims") or []
    print(
        f"  extract ({st['s']}s): success={st['result'].get('success')} claims={len(claims)}"
    )
    for c in claims:
        print(f"    · text={c.get('text')!r}")
        print(
            f"      hint={c.get('type_hint')}  entities={[(e.get('text'), e.get('type')) for e in (c.get('key_entities') or [])]}"
        )
    if not claims:
        print("  !! ZERO claims — this is the F-EXTRACT-FALLBACK seam in prod")
        return out

    # 2 — recombination (mechanical)
    recombined = recombine_single_thesis(text, claims)
    claim = recombined or claims[0]
    print(
        f"  recombined={'yes' if recombined else 'no (single claim or rule skipped)'}"
    )
    print(f"  final claim text: {claim.get('text')!r}")
    print(f"  final type_hint:  {claim.get('type_hint')}")
    out["final_claim"] = {
        k: claim.get(k) for k in ("text", "type_hint", "key_entities")
    }

    # 3 — grounds gate + decompose (live LLM), as phase 2 would run it
    normative = bool(
        settings.ENABLE_OPINION_REFRAME and claim.get("type_hint") == "normative"
    )
    print(f"  grounds gate fires = {normative}")
    analyzer = ClaimMapAnalyzer()
    st = await _stage("decompose", analyzer.decompose_claim(claim["text"], "c1"))
    out["stages"].append(st)
    if not st["ok"]:
        print(f"  decompose → {st['error']}")
        return out
    raw = st["result"]
    cmap = raw if isinstance(raw, dict) else raw.model_dump()
    elements = [e.get("description") for e in (cmap.get("elements") or [])]
    print(f"  decompose ({st['s']}s): {len(elements)} elements")
    for e in elements:
        print(f"    · {e}")

    if normative:
        st = await _stage(
            "grounds", osym.apply_grounds_stage(analyzer, claim["text"], cmap)
        )
        out["stages"].append(st)
        if not st["ok"]:
            print(f"  grounds → {st['error']}")
            return out
        final = [e.get("description") for e in (st["result"].get("elements") or [])]
        meta = (st["result"].get("metadata") or {}).get("grounds")
        print(f"  grounds ({st['s']}s): {meta}")
        for e in final:
            print(f"    · {e}")
        out["grounds_elements"] = final

    return out


async def main() -> None:
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    print(f"ENABLE_OPINION_REFRAME = {settings.ENABLE_OPINION_REFRAME} (as deployed)")
    results = [
        await run_variant("A/ellipsis-fragment (suspected T2 input)", TEXT_A),
        await run_variant("B/full-claim (intended T2)", TEXT_B),
    ]

    out_path = os.path.join(os.path.dirname(__file__), ".repro_t2_ellipsis.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False, default=str)
    print("\n" + "=" * 78)
    bad = [s for r in results for s in r["stages"] if not s["ok"]]
    if bad:
        for s in bad:
            print(f"DIVERGENCE: {s['stage']} → {s['error']}")
    else:
        print("No pre-retrieval stage failed or hung on either variant.")
    print(f"Saved → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
