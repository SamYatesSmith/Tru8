"""Criterion 17 — the live pair, run locally against the wired seam.

Design: audit/2026-07-27_phase2_element_retrieval_build_design.md §6 criterion 17.

Runs three real, networked checks and reports the things criterion 17 actually
asserts — not that the mechanism exists (that is criteria 1-16, already PASS),
but that the OUTCOME changed:

  T4 vaccine (opinion)  — the element questions must be SEARCHED, and no query
                          may mirror the claim's own valence. Pre-wiring this
                          claim produced "success metrics" / "achievements".
  T2 homeopathy         — the alternative-treatments ground must be searched.
                          Pre-wiring it returned "no evidence was found".
  T3 Grenfell (control) — MUST NOT REGRESS. Guards the honest cost of the
                          change: claim-lane depth ~13 -> ~5 URLs/query.

Claims are PARAPHRASED: re-submitting identical text replays caches and would
read a stale pool. T4's original wording is recorded verbatim in
audit/2026-07-27_phase1_mechanical_honesty_design.md:14; T2/T3 are reconstructed
from their recorded descriptions, so those two are equivalents rather than
strict paraphrases of the originals.

Usage:  python -m scripts.criterion17_live_pair [t4|t2|t3|all]
"""

import asyncio
import io
import logging
import sys
import traceback
import uuid
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


# Valence tokens for T4. Pre-wiring, the pool was constituted by searching the
# judgement's own wording — invariant #7 breached at pool constitution. Any of
# these appearing in a query means the claim's valence is still steering the
# search.
T4_VALENCE = [
    "triumph",
    "success",
    "successful",
    "achievement",
    "outstanding",
    "resounding",
    "win",
    "victory",
]

CASES = {
    # (id, claim text, what criterion 17 demands of it)
    "t4": (
        "Britain's COVID-19 vaccination programme was an outstanding success",
        "element questions searched AND no query mirrors the claim's valence",
    ),
    "t2": (
        "It is indefensible for the NHS to spend taxpayers' money on homeopathy",
        "the alternative-treatments ground must actually be searched",
    ),
    "t3": (
        "The Grenfell Tower fire of June 2017 killed 72 people, and the blaze "
        "spread rapidly because of the building's combustible ACM cladding",
        "MUST NOT REGRESS — factual control on shallower claim-lane depth",
    ),
}


class _RetrieveLog(logging.Handler):
    """Capture the Phase 2 telemetry lines rather than inferring from behaviour."""

    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return
        if "[RETRIEVE]" in msg or "[QUERY_PLANNER]" in msg:
            self.lines.append(msg)


async def run_case(key: str) -> None:
    claim_text, demand = CASES[key]

    from sqlmodel import select as sm_select

    from app.core.database import async_session
    from app.models.check import Check
    from app.models.user import User
    from app.pipeline.progress import ProgressReporter
    from app.pipeline.runner import run_pipeline_phase1
    from app.services.search import SearchService

    print("\n" + "=" * 78)
    print(f"CASE {key.upper()} — {demand}")
    print(f"CLAIM: {claim_text}")
    print("=" * 78)

    # Record every query the pipeline actually issues, and the depth it asks
    # for, by wrapping the real search service (not replacing it).
    issued = []
    original_search = SearchService.search_for_evidence

    async def _recording_search(self, query, max_results=10, freshness=None, **kw):
        issued.append({"query": query, "max_results": max_results})
        return await original_search(
            self, query, max_results=max_results, freshness=freshness, **kw
        )

    SearchService.search_for_evidence = _recording_search

    handler = _RetrieveLog()
    handler.setLevel(logging.DEBUG)
    # The lane/budget telemetry is INFO; without lowering the logger level only
    # the WARNING lines arrive and the run looks lane-less when it is not.
    for name in ("app.pipeline.retrieve", "app.utils.query_planner"):
        lg = logging.getLogger(name)
        lg.addHandler(handler)
        lg.setLevel(logging.INFO)

    check_id = str(uuid.uuid4())
    try:
        async with async_session() as session:
            existing = (await session.execute(sm_select(User))).scalars().first()
            if existing:
                user_id = existing.id
            else:
                user_id = "c17-local-user"
                session.add(User(id=user_id, email="c17@local.test", credits=100))
                await session.commit()

        async with async_session() as session:
            session.add(
                Check(
                    id=check_id,
                    user_id=user_id,
                    input_type="text",
                    input_content='{"content": "%s"}' % claim_text.replace('"', ""),
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
            print("  !! phase1 returned None (paused for selection) — phase 2 not run")
            return

        _report(key, result, issued, handler.lines)

    except Exception as e:
        print(f"  !! PIPELINE RAISED: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        SearchService.search_for_evidence = original_search
        logging.getLogger("app.pipeline.retrieve").removeHandler(handler)
        logging.getLogger("app.utils.query_planner").removeHandler(handler)


def _report(key, result, issued, log_lines) -> None:
    claims = result.get("claims", []) or []
    print(f"\n-- CLAIMS: {len(claims)}")
    for c in claims:
        cm = c.get("claim_map") or {}
        elements = cm.get("elements", []) or []
        print(f"\n  CLAIM: {c.get('text','')[:120]}")
        print(f"  ELEMENTS: {len(elements)}")
        for e in elements:
            refs = e.get("evidence_refs") or []
            print(
                f"    {e.get('element_id','?'):>4} [{e.get('state','?'):<12}] "
                f"refs={len(refs):<3} {e.get('description','')[:88]}"
            )
        orient = cm.get("orientation") or {}
        print(
            f"  ORIENTATION: {orient if isinstance(orient,str) else orient.get('summary', orient)}"
        )

    print(f"\n-- QUERIES ACTUALLY ISSUED: {len(issued)}")
    for q in issued:
        print(f"    [{q['max_results']:>2} results] {q['query']}")

    print("\n-- PHASE 2 TELEMETRY")
    for line in log_lines:
        if any(
            k in line
            for k in (
                "Element lanes wired",
                "Query lanes",
                "Fetch budget",
                "Lane shortfall",
                "Claim-level lane only",
                "element plans",
            )
        ):
            print(f"    {line}")

    # ---- criterion 17 assertions, evaluated mechanically ----
    print("\n-- CRITERION 17 VERDICT")
    all_q = " ".join(q["query"].lower() for q in issued)

    if key == "t4":
        hits = sorted({w for w in T4_VALENCE if w in all_q})
        print(f"    valence tokens in queries: {hits if hits else 'NONE'}")
        print(
            f"    -> valence steering: {'FAIL — ' + ', '.join(hits) if hits else 'PASS'}"
        )
        wired = [l for l in log_lines if "Element lanes wired" in l]
        print(f"    -> element lanes wired: {'PASS' if wired else 'FAIL (no lanes)'}")

    if key == "t2":
        alt = [
            q["query"]
            for q in issued
            if any(
                t in q["query"].lower()
                for t in ("alternative", "complementary", "conventional", "instead")
            )
        ]
        print(f"    alternative-treatment queries: {len(alt)}")
        for q in alt:
            print(f"      - {q}")
        print(f"    -> e03-equivalent searched: {'PASS' if alt else 'FAIL'}")

    if key == "t3":
        print(
            "    baseline recorded pre-wiring: 2 elements, +13 / -1, "
            "'predominantly supports all 2'"
        )
        print(
            "    -> compare element count, refs and states above; "
            "REGRESSION IS A JUDGEMENT CALL, not asserted here"
        )


async def main() -> None:
    which = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    keys = list(CASES) if which == "all" else [which]
    for k in keys:
        if k not in CASES:
            print(f"unknown case {k!r}; choose from {list(CASES)} or 'all'")
            continue
        await run_case(k)


if __name__ == "__main__":
    asyncio.run(main())
