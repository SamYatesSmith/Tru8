"""List the strongest completed checks to use as live demo `/r/` links.

Read-only. Ranks completed checks by richness (claim count, signed/full-tier
manifest, web results reviewed) and prints ready-to-paste public report URLs
for the buyer-validation interviews.

Run against production (Railway):
    railway run --service Postgres python -m scripts.demo_candidates

(Env-only DB URL: prefers COST_DB_URL / DATABASE_PUBLIC_URL / DATABASE_URL —
running under the Postgres service injects the public proxy URL, so no secret
is typed.)
"""

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PUBLIC_BASE = "https://www.trueight.com"

SQL = """
SELECT
    c.id,
    c.input_type,
    COALESCE(NULLIF(c.input_url, ''), left(c.input_content, 70))        AS subject,
    (SELECT COUNT(*) FROM "claim" cl WHERE cl.check_id = c.id)          AS claims,
    (c.cost_telemetry->'search'->>'web_results_reviewed')              AS web_results,
    (c.manifest IS NOT NULL)                                           AS signed,
    c.created_at::date                                                 AS created
FROM "check" c
WHERE c.status = 'completed'
ORDER BY claims DESC NULLS LAST, (c.manifest IS NOT NULL) DESC, c.created_at DESC
LIMIT 12;
"""


async def main() -> int:
    db_url = (
        os.environ.get("COST_DB_URL")
        or os.environ.get("DATABASE_PUBLIC_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    )
    if not db_url:
        print(
            "No DB URL in env (COST_DB_URL / DATABASE_PUBLIC_URL / DATABASE_URL)",
            file=sys.stderr,
        )
        return 2
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text(SQL))).all()
    finally:
        await engine.dispose()

    if not rows:
        print("No completed checks found.")
        return 0

    print(
        "Top demo candidates (richest completed checks) — paste the URL into interviews:\n"
    )
    header = f"{'claims':>6} {'web':>4} {'signed':>6}  {'created':<10}  subject"
    print(header)
    print("-" * 96)
    for r in rows:
        cid, itype, subject, claims, web, signed, created = r
        subj = (subject or f"({itype})").replace("\n", " ")[:70]
        sgn = "yes" if signed else "-"
        web_s = web if web is not None else "-"
        print(f"{claims:>6} {str(web_s):>4} {sgn:>6}  {str(created):<10}  {subj}")
        print(f"       → {PUBLIC_BASE}/r/{cid}\n")

    print("Pick 3-4 with the most claims + signed=yes for the strongest demos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
