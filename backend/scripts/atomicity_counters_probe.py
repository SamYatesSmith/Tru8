"""Did the MECHANICAL repair fire, or did the prompt rule alone do the work?

The battery reports 0% compound after Phase 3a. That is the right outcome
either way, but it does not say WHICH mechanism produced it — and a green that
rests entirely on a prompt rule is exactly the failure NF-11 records.

Reads the deterministic counters the stage writes to
``metadata.grounds.atomicity`` (detected / repaired / surviving), which do not
depend on log configuration.

Usage:  python -m scripts.atomicity_counters_probe
"""

import asyncio
import io
import logging
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format="%(message)s")

CLAIMS = [
    "The UK's HS2 rail project was a catastrophic waste of money",
    "Privatising British Rail was a mistake",
    "The 2008 bank bailouts were the right decision",
    "The furlough scheme was an outstanding policy response",
    "Nuclear power is the safest form of energy generation",
    "Brexit has been an economic disaster for Britain",
    "The Australian wildfire response in 2020 was woefully inadequate",
    "The NHS is the best healthcare system in the world",
]


async def one(analyzer, claim: str, idx: int):
    from app.pipeline.opinion_symmetry import apply_grounds_stage

    try:
        baseline = await analyzer.decompose_claim(claim, f"probe-{idx}")
        bl = (
            baseline.model_dump() if hasattr(baseline, "model_dump") else dict(baseline)
        )
        rebuilt = await apply_grounds_stage(analyzer, claim, bl)
        meta = (rebuilt.get("metadata") or {}).get("grounds") or {}
        return claim, meta.get("atomicity"), len(rebuilt.get("elements") or [])
    except Exception as e:
        return claim, {"error": f"{type(e).__name__}: {e}"}, 0


async def main() -> None:
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    analyzer = ClaimMapAnalyzer()
    results = []
    for start in range(0, len(CLAIMS), 4):
        chunk = CLAIMS[start : start + 4]
        results += await asyncio.gather(
            *(one(analyzer, c, start + i) for i, c in enumerate(chunk))
        )

    print("\n" + "=" * 78)
    print("ATOMICITY COUNTERS — did the mechanical repair fire?")
    print("=" * 78)
    det = rep = surv = 0
    for claim, a, n in results:
        print(f"  {str(a):<58} [{n} elems] {claim[:40]}")
        if isinstance(a, dict) and "error" not in a:
            det += a.get("detected", 0)
            rep += a.get("repaired", 0)
            surv += a.get("surviving", 0)
    print(f"\n  TOTAL detected={det}  repaired={rep}  surviving={surv}")
    if det == 0:
        print("\n  ⚠ Repair never fired — the PROMPT rule alone produced the 0%.")
        print(
            "    The mechanical guarantee is unexercised live (pinned only by tests)."
        )
    else:
        print(f"\n  ✓ Mechanical repair fired on {det} element(s), fixed {rep}.")


if __name__ == "__main__":
    asyncio.run(main())
