"""Capture report content without account data; keep legacy v1 signatures verifiable."""

import copy
import hashlib
import json
from types import SimpleNamespace

from sqlalchemy import select

from app.models import Claim, Evidence
from app.core.manifest_signer import (
    build_canonical_data,
    compute_canonical_hash,
    create_manifest_for_check,
    verify_manifest,
)


async def capture_report(session, check) -> dict:
    claims = (
        (
            await session.execute(
                select(Claim)
                .where(Claim.check_id == check.id)
                .order_by(Claim.position, Claim.id)
            )
        )
        .scalars()
        .all()
    )
    data = []
    for claim in claims:
        evidence = (
            (
                await session.execute(
                    select(Evidence)
                    .where(Evidence.claim_id == claim.id)
                    .order_by(Evidence.id)
                )
            )
            .scalars()
            .all()
        )
        cm = claim.claim_map
        if isinstance(cm, str):
            cm = json.loads(cm)
        data.append(
            {
                "id": claim.id,
                "position": claim.position,
                "text": claim.text,
                "claim_text_hash": claim.claim_text_hash,
                "claimMap": copy.deepcopy(cm),
                "evidence": [
                    e.model_dump(mode="json", exclude={"claim_id"}) for e in evidence
                ],
            }
        )
    return {
        "format_version": 1,
        "check": {
            "id": check.id,
            "executed_tier": check.executed_tier,
            "provider_status": copy.deepcopy(check.provider_status),
        },
        "claims": data,
        "manifest": copy.deepcopy(check.manifest),
    }


def snapshot_hash(snapshot: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def signature_inputs(snapshot: dict):
    # EXACT shape of verify._load_claims_for_verify: do not alter old v1 semantics
    # (including its snake/camel behaviour) while introducing revision history.
    claims = [
        {
            "text": c["text"],
            "claim_text_hash": c["claim_text_hash"],
            "claimMap": c["claimMap"],
            "evidence": [
                {
                    key: ev.get(key)
                    for key in (
                        "evidence_id",
                        "tier",
                        "evidence_type",
                        "content_basis",
                        "classification_method",
                        "url",
                    )
                }
                for ev in c["evidence"]
            ],
        }
        for c in snapshot["claims"]
    ]
    from app.api.v1.response_builder import _compute_landscape

    landscape = _compute_landscape(claims, SimpleNamespace(**snapshot["check"]))
    orientation = next(
        (
            c["claimMap"]["orientation_basis"]
            for c in claims
            if c.get("claimMap") and c["claimMap"].get("orientation_basis")
        ),
        None,
    )
    return dict(
        check_id=snapshot["check"]["id"],
        claims_data=claims,
        executed_tier=snapshot["check"]["executed_tier"],
        landscape=landscape,
        orientation_basis=orientation,
    )


def verify_snapshot(snapshot: dict) -> dict:
    stored = snapshot.get("manifest")
    if not stored:
        return {"valid": False, "reason": "unsigned"}
    result = verify_manifest(stored)
    if not result["valid"]:
        return result
    canonical = build_canonical_data(
        **signature_inputs(snapshot),
        pipeline_fingerprint=stored.get("pipeline_fingerprint")
    )
    if compute_canonical_hash(canonical) != stored.get("landscape_hash"):
        return {"valid": False, "reason": "data_modified"}
    return {"valid": True}


def sign_snapshot(snapshot: dict):
    return create_manifest_for_check(**signature_inputs(snapshot))
