"""Local repro of the prod hang: text-mode tectonic check through the REAL runner.

Creates a Check row locally, runs run_pipeline_phase1 (which for focused mode
continues into phase 2), prints every stage + full traceback on failure.
"""

import asyncio
import io
import sys
import traceback
import uuid
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

TECTONIC = (
    "Compared to the last 50 years, tectonic plate movement is extremely "
    "active currently, causing a large rise in volcanic eruptions and earthquakes"
)


async def main() -> None:
    from sqlmodel import select as sm_select

    from app.core.database import async_session
    from app.models.check import Check
    from app.models.user import User
    from app.pipeline.runner import run_pipeline_phase1
    from app.pipeline.progress import ProgressReporter

    check_id = str(uuid.uuid4())

    async with async_session() as session:
        existing = (await session.execute(sm_select(User))).scalars().first()
        if existing:
            user_id = existing.id
        else:
            user_id = "repro-local-user"
            session.add(User(id=user_id, email="repro@local.test", credits=100))
            await session.commit()

    async with async_session() as session:
        check = Check(
            id=check_id,
            user_id=user_id,
            input_type="text",
            input_content='{"content": "%s"}' % TECTONIC.replace('"', ""),
            status="processing",
        )
        session.add(check)
        await session.commit()
    print(f"[REPRO] Check row created: {check_id}")

    reporter = ProgressReporter(check_id)
    input_data = {"input_type": "text", "content": TECTONIC}

    try:
        result = await run_pipeline_phase1(
            check_id=check_id,
            user_id=user_id,
            input_data=input_data,
            progress_reporter=reporter,
        )
        print("[REPRO] PHASE1(+2) RETURNED OK")
        if result:
            print("  claims:", len(result.get("claims", [])))
            for c in result.get("claims", []):
                print("   -", c.get("text", "")[:100])
                cm = c.get("claim_map") or {}
                for e in cm.get("elements", []):
                    print("      *", e.get("description", "")[:110])
    except Exception as e:
        print(f"[REPRO] PIPELINE RAISED: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
