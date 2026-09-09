"""Durable admission, completion and reconciliation for strengthening.

Lock order: Check -> ResearchOperation -> User. Network/model work holds no DB
transaction. The partial unique index is the cross-process admission backstop.
"""

import asyncio
import logging
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import async_session
from app.models import (
    Check,
    Claim,
    Evidence,
    ResearchOperation,
    ReportRevision,
    User,
    UsageEvent,
)
from app.models.check import _utcnow_naive, generate_uuid
from app.models.usage_event import KIND_RESEARCH_REFUND
from app.pipeline.support_structure import thin_element_ids
from app.services.evidence_payload import evidence_from_mapping
from app.services.report_revisions import (
    capture_report,
    snapshot_hash,
    sign_snapshot,
    verify_snapshot,
)
from app.services.usage_ledger import enforce_usage_limit, record_usage

logger = logging.getLogger(__name__)
ACTIVE = ("pending", "running")
_tasks: set[asyncio.Task] = set()


def status_payload(op):
    return {
        "operationId": op.id,
        "status": op.stage if op.status in ACTIVE else op.status,
        "message": op.message,
        "newEvidenceCount": op.new_evidence_count,
        "elementIds": op.element_ids,
        "revisionId": op.result_revision_id,
    }


async def admit_research(
    session, user, check_id, claim_id, mode, request_key, element_id=None
):
    if not request_key or len(request_key) > 128:
        raise HTTPException(400, "Idempotency-Key must contain 1–128 characters")
    check = (
        await session.execute(
            select(Check)
            .where(Check.id == check_id, Check.user_id == user.id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not check:
        raise HTTPException(404, "Check not found")
    scope = f"{claim_id}:{mode}:{element_id or ''}"
    prior = (
        await session.execute(
            select(ResearchOperation).where(
                ResearchOperation.check_id == check_id,
                ResearchOperation.request_key == request_key,
            )
        )
    ).scalar_one_or_none()
    if prior:
        if prior.request_scope != scope:
            raise HTTPException(
                409, "Idempotency-Key was used for a different research request"
            )
        return prior, False
    active = (
        await session.execute(
            select(ResearchOperation).where(
                ResearchOperation.check_id == check_id,
                ResearchOperation.status.in_(ACTIVE),
            )
        )
    ).scalar_one_or_none()
    if active:
        if active.deadline_at <= _utcnow_naive():
            await _fail_locked(
                session,
                active,
                "Research was interrupted. Your credit has been refunded.",
            )
        else:
            raise HTTPException(409, "Research is already in progress for this report")
    if check.status != "completed":
        raise HTTPException(409, "Re-search is only available on completed checks")
    baseline = await capture_report(session, check)
    claim = next((c for c in baseline["claims"] if c["id"] == claim_id), None)
    if not claim or not claim.get("claimMap"):
        raise HTTPException(404, "Claim map not found")
    cm = claim["claimMap"]
    elements = cm.get("elements", [])
    if mode == "gaps":
        targets = [e["element_id"] for e in elements if not e.get("evidence_refs")]
    elif mode == "thin":
        targets = thin_element_ids(cm)
    elif mode == "element":
        targets = (
            [element_id]
            if any(e.get("element_id") == element_id for e in elements)
            else []
        )
    else:
        raise HTTPException(400, "Unknown research mode")
    if not targets:
        raise HTTPException(409, "No matching elements to research")
    if baseline.get("manifest") and not verify_snapshot(baseline)["valid"]:
        raise HTTPException(
            409,
            "The current signed report could not be verified; it has not been changed",
        )
    locked_user = await enforce_usage_limit(session, user, context="re_search")
    debit = record_usage(
        session,
        locked_user,
        kind="top_up" if mode == "thin" else "re_search",
        check_id=check_id,
    )
    # Explicit flush gives the FK a persisted debit in the same transaction.
    await session.flush()
    op = ResearchOperation(
        check_id=check_id,
        claim_id=claim_id,
        request_key=request_key,
        request_scope=scope,
        element_ids=sorted(set(targets)),
        debit_id=debit.id,
        baseline=baseline,
        baseline_hash=snapshot_hash(baseline),
        deadline_at=_utcnow_naive()
        + timedelta(seconds=settings.RESEARCH_WATCHDOG_SECONDS),
    )
    session.add(op)
    await session.flush()
    return op, True


async def _fail_locked(session, op, message):
    if op.status not in ACTIVE:
        return
    # Terminal status and compensating event commit together: a repeated timeout,
    # process sweep or client poll cannot refund twice or refund the parent check.
    debit = await session.get(UsageEvent, op.debit_id) if op.debit_id else None
    if debit:
        user = (
            await session.execute(
                select(User).where(User.id == debit.user_id).with_for_update()
            )
        ).scalar_one()
        session.add(
            UsageEvent(
                id=generate_uuid(),
                user_id=debit.user_id,
                check_id=op.check_id,
                kind=KIND_RESEARCH_REFUND,
                credits=-debit.credits,
                drew_trial=debit.drew_trial,
            )
        )
        if debit.drew_trial:
            user.credits += debit.credits
        user.total_credits_used = max(0, user.total_credits_used - debit.credits)
    op.status, op.stage, op.message = "error", "error", message
    op.finished_at = _utcnow_naive()
    session.add(op)


async def fail_operation(operation_id, message):
    async with async_session() as session:
        op = await session.get(ResearchOperation, operation_id)
        if not op:
            return
        await session.execute(
            select(Check).where(Check.id == op.check_id).with_for_update()
        )
        await session.refresh(op, with_for_update=True)
        await _fail_locked(session, op, message)
        await session.commit()


async def update_stage(operation_id, stage, message):
    async with async_session() as session:
        await session.execute(
            update(ResearchOperation)
            .where(
                ResearchOperation.id == operation_id,
                ResearchOperation.status == "running",
                ResearchOperation.deadline_at > _utcnow_naive(),
            )
            .values(stage=stage, message=message)
        )
        await session.commit()


async def commit_result(session, operation_id, claim_map, candidates):
    op = await session.get(ResearchOperation, operation_id)
    if not op:
        raise RuntimeError("Research operation no longer exists")
    check = (
        await session.execute(
            select(Check).where(Check.id == op.check_id).with_for_update()
        )
    ).scalar_one()
    await session.refresh(op, with_for_update=True)
    if op.status != "running" or op.deadline_at <= _utcnow_naive():
        raise RuntimeError("Research expired before it could be saved")
    claim = (
        await session.execute(
            select(Claim).where(Claim.id == op.claim_id).with_for_update()
        )
    ).scalar_one()
    current = await capture_report(session, check)
    if snapshot_hash(current) != op.baseline_hash:
        raise RuntimeError("The report changed during research; please try again")
    if candidates:
        prior = ReportRevision(
            check_id=op.check_id, operation_id=op.id, phase="before", snapshot=current
        )
        session.add(prior)
        for candidate in candidates:
            session.add(evidence_from_mapping(op.claim_id, candidate))
        claim.claim_map = claim_map
        session.add(claim)
        await session.flush()
        revised = await capture_report(session, check)
        manifest = sign_snapshot(revised)
        if not manifest and (
            current.get("manifest") or settings.MANIFEST_SIGNING_ENABLED
        ):
            raise RuntimeError("Updated report could not be signed")
        check.manifest = manifest
        session.add(check)
        revised["manifest"] = manifest
        after = ReportRevision(
            check_id=op.check_id, operation_id=op.id, phase="after", snapshot=revised
        )
        session.add(after)
        op.result_revision_id = after.id
    op.status, op.stage = "completed", "completed"
    op.message = (
        f"Found {len(candidates)} new sources" if candidates else "No new sources found"
    )
    op.new_evidence_count = len(candidates)
    op.finished_at = _utcnow_naive()
    session.add(op)
    await session.flush()
    if op.deadline_at <= _utcnow_naive():
        raise RuntimeError("Research expired before it could be saved")
    await session.commit()


async def execute_operation(operation_id):
    owns_operation = False
    try:
        async with async_session() as session:
            result = await session.execute(
                update(ResearchOperation)
                .where(
                    ResearchOperation.id == operation_id,
                    ResearchOperation.status == "pending",
                    ResearchOperation.deadline_at > _utcnow_naive(),
                )
                .values(status="running")
                .returning(ResearchOperation)
            )
            op = result.scalar_one_or_none()
            if not op:
                return  # Another worker owns it, or reconciliation already ended it.
            await session.commit()
            owns_operation = True
        remaining = (op.deadline_at - _utcnow_naive()).total_seconds()
        from app.pipeline.re_search import research_claim

        claim = next(c for c in op.baseline["claims"] if c["id"] == op.claim_id)

        async def work():
            mapped, candidates = await research_claim(
                claim,
                op.element_ids,
                lambda stage, message: update_stage(op.id, stage, message),
            )
            async with async_session() as session:
                await commit_result(session, op.id, mapped, candidates)

        await asyncio.wait_for(work(), timeout=max(0, remaining))
    except asyncio.CancelledError:
        if owns_operation:
            await asyncio.shield(
                fail_operation(
                    operation_id,
                    "Research was interrupted. Your credit has been refunded.",
                )
            )
        raise
    except Exception:
        logger.exception("Research operation %s failed", operation_id)
        if owns_operation:
            await fail_operation(
                operation_id,
                "Research could not complete. Your credit has been refunded; the previous report is unchanged.",
            )


def launch_operation(operation_id):
    task = asyncio.create_task(execute_operation(operation_id))
    _tasks.add(task)

    def done(t):
        _tasks.discard(t)
        if not t.cancelled() and t.exception():
            logger.error(
                "Research failure reconciliation failed", exc_info=t.exception()
            )

    task.add_done_callback(done)


async def reconcile_expired():
    async with async_session() as session:
        ids = (
            (
                await session.execute(
                    select(ResearchOperation.id).where(
                        ResearchOperation.status.in_(ACTIVE),
                        ResearchOperation.deadline_at <= _utcnow_naive(),
                    )
                )
            )
            .scalars()
            .all()
        )
    for operation_id in ids:
        await fail_operation(
            operation_id,
            "Research timed out or was interrupted. Your credit has been refunded.",
        )


async def reconciliation_loop():
    while True:
        try:
            await reconcile_expired()
        except Exception:
            logger.exception("Research reconciliation failed; will retry")
        await asyncio.sleep(30)


async def stop_research_tasks():
    tasks = list(_tasks)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
