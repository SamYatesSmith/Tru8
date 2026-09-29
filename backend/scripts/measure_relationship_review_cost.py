"""Measure the relationship review's real token cost per check (2026-09-29)."""
import asyncio, glob, json, os, sys
sys.path.insert(0, os.getcwd())
from app.core.config import settings
settings.RELATIONSHIP_REVIEW_MODEL = "gemini-3.7-flash"
settings.ENABLE_RELATIONSHIP_REVIEW = True
settings.RELATIONSHIP_REVIEW_DEMOTE_UNKNOWN = True
settings.RELATIONSHIP_REVIEW_DIRECTIONS = "supports"
settings.RELATIONSHIP_REVIEW_CALL_TIMEOUT_S = 40
from scripts.eval_relationship_review import _to_internal
from app.services.relationship_scope_review import plan_review, review_relationship_scope
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
IN, OUT, FX = 0.75, 3.75, 0.78  # USD per 1M tokens (intro price to 31 Dec 2026); USD->GBP
rows = []
async def main(d):
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        a = ClaimMapAnalyzer()
        pairs = calls = 0
        for cm, ev in _to_internal(json.load(open(f, encoding="utf-8"))):
            planned, _ = plan_review(cm, ev)
            pairs += len(planned); calls += -(-len(planned) // 6)
            if planned:
                await review_relationship_scope(a, cm, ev)
        u = a.get_token_usage()
        out = u.get("output_tokens", 0) + u.get("thinking_tokens", 0)
        usd = u.get("input_tokens", 0) / 1e6 * IN + out / 1e6 * OUT
        rows.append(dict(check=os.path.basename(f)[:8], pairs=pairs, calls=calls, inp=u.get("input_tokens", 0), out=out, pence=usd * FX * 100))
        print(rows[-1], flush=True)
asyncio.run(main(sys.argv[1]))
json.dump(rows, open(sys.argv[2], "w"), indent=1)
p = sorted(r["pence"] for r in rows)
tot = sum(p)
print(f"checks={len(p)} total={tot:.2f}p mean={tot/len(p):.2f}p median={p[len(p)//2]:.2f}p max={p[-1]:.2f}p; per call={tot/max(1,sum(r['calls'] for r in rows)):.2f}p; 2027 price x2")
