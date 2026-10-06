"""Replay one corpus claim (cassette, free) and print element states + refs."""
import asyncio, json, sys, logging
from pathlib import Path
sys.path.insert(0, ".")
from scripts.replay_bench import runner as R
import app.pipeline.runner as P

CAPT = {}
_orig = P.run_pipeline
async def cap(*a, **k):
    r = await _orig(*a, **k); CAPT["r"] = r; return r
_orig2 = P.run_pipeline_phase2
async def cap2(*a, **k):
    r = await _orig2(*a, **k); CAPT["r"] = r; return r
P.run_pipeline = cap; P.run_pipeline_phase2 = cap2

async def main(cid):
    from scripts.replay_bench.fixtures import DomainStatusFixture
    corpus = Path("tests/replay_corpus")
    with DomainStatusFixture() as fx:
        await R.run_one_async(corpus, cid, fx, cassette_mode="replay")
    r = CAPT.get("r") or {}
    for c in r.get("claims", []):
        cm = c.get("claim_map") or {}
        print("CLAIM:", (cm.get("normalised_claim") or c.get("text"))[:200])
        ev = {e.get("evidence_id"): (e.get("url") or "")[:70] for e in (r.get("evidence", {}) or {}).get(str(c.get("position", 0)), [])}
        for el in cm.get("elements", []):
            print(f"  [{el.get('state')}] {el.get('description','')[:150]}")
            for ref in el.get("evidence_refs", []):
                print(f"      {ref.get('relationship'):9s} {ev.get(ref.get('evidence_id'), ref.get('evidence_id'))}  {(ref.get('reasoning') or '')[:90]}")
        print("  orientation:", (cm.get("orientation") or "")[:200])

logging.disable(logging.CRITICAL)
asyncio.run(main(sys.argv[1]))
