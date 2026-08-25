"""M-04: Manifest signing and verification.

Tamper-evident signed manifests for evidence research checks.
Uses HMAC-SHA256 with key rotation support.

Key design decisions (from Track M plan, all LOCKED):
- Canonical hash excludes free-text narrative (orientation, reasoning, bounty_text, uncertainty)
- Includes stable, decision-critical fields only
- Pipeline fingerprint tracks model + config state
- Keys rotate every 90 days; old keys valid 180 days for verification
"""

import base64
import hashlib
import hmac
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline fingerprint
# ---------------------------------------------------------------------------


def compute_pipeline_fingerprint() -> str:
    """SHA256 hash of model configuration — changes when models change.

    Stored in manifests so consumers can detect pipeline version drift.
    """
    config = {
        "primary_llm": settings.PRIMARY_LLM_PROVIDER,
        "google_model": settings.GOOGLE_LLM_MODEL,
        "mapping_google_model": settings.MAPPING_GOOGLE_MODEL,
        "decomposition_model": settings.DECOMPOSITION_MODEL,
        "analyzer_model": settings.ANALYZER_MODEL,
    }
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Element canonical ID (shared with M-06 convergence)
# ---------------------------------------------------------------------------


def canonical_element_id(description: str) -> str:
    """Content-addressed element identity from description text.

    Uses same normalisation as compute_claim_text_hash():
    NFKC → lowercase → collapse whitespace → strip → SHA256[:16].
    """
    normalised = unicodedata.normalize("NFKC", description)
    normalised = normalised.lower().strip()
    normalised = re.sub(r"\s+", " ", normalised)
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Canonical data builder (shared by signing + verification)
# ---------------------------------------------------------------------------


def build_canonical_data(
    check_id: str,
    claims_data: List[Dict[str, Any]],
    executed_tier: Optional[str],
    landscape: Optional[Dict[str, Any]],
    orientation_basis: Optional[Dict[str, Any]] = None,
    pipeline_fingerprint: Optional[str] = None,
) -> dict:
    """Build deterministic canonical payload from decision-critical fields.

    This is the SINGLE SOURCE OF TRUTH for what gets hashed.
    Both signing (from response dict) and verification (from DB rows)
    MUST call this function to ensure consistency.

    ``pipeline_fingerprint`` (2026-08-25): pass the value stored on the manifest
    when VERIFYING; omit it when SIGNING, so it is computed from live settings.

    Why this parameter exists — it is the difference between a verification
    endpoint that works after a model migration and one that silently lies.
    Every other field in this payload is a property OF THE CHECK, read back from
    stored data. ``pipeline_fingerprint`` was the sole exception: recomputed from
    whatever the SERVER is configured with at the moment of the request. So the
    hash of a two-month-old check changed the instant a model string changed,
    and ``GET /verify/{id}`` returned ``data_modified`` — accusing us of
    tampering — for every check ever signed. Nothing raised; the endpoint just
    started giving a confident wrong answer.

    Tamper detection is unaffected. The fingerprint is still inside the signed
    payload, so altering the stored value changes the canonical hash and fails
    verification exactly as before. Reading it back is what makes it behave like
    every other signed field rather than like server state.

    Includes (stable, decision-critical):
      - check_id
      - claim_text_hash per claim
      - element canonical_id (description hash) + state + basis per element
      - sorted evidence_ids from all evidence_refs
      - per-evidence: tier, evidence_type, content_basis, classification_method
      - landscape metrics
      - executed_tier
      - pipeline_fingerprint
      - orientation_basis

    Excludes (narrative/mutable — plan KD3):
      - orientation (free text)
      - evidence_ref.reasoning (free text)
      - bounty_text (user-mutable)
      - uncertainty (free text)
      - normalised_claim (redundant with hash)
    """
    claims_canon = []
    all_evidence_meta = (
        {}
    )  # evidence_id → {tier, type, content_basis, classification_method}

    for c in claims_data:
        cm = c.get("claimMap") or c.get("claim_map") or {}
        elements_canon = []
        evidence_ids = set()

        for e in cm.get("elements") or []:
            desc = e.get("description", "")
            ceid = canonical_element_id(desc)

            elem_canon = {
                "canonical_id": ceid,
                "state": e.get("state"),
            }
            # PQ-03: Include basis metadata (mechanically computed, deterministic)
            basis = e.get("basis")
            if basis:
                elem_canon["basis"] = basis

            elements_canon.append(elem_canon)

            for ref in e.get("evidenceRefs") or e.get("evidence_refs") or []:
                eid = ref.get("evidenceId") or ref.get("evidence_id")
                if eid:
                    evidence_ids.add(eid)

        # Claim text hash
        claim_text = c.get("text", "")
        claim_hash = c.get("claimTextHash") or c.get("claim_text_hash")
        if not claim_hash and claim_text:
            from app.models.check import compute_claim_text_hash

            claim_hash = compute_claim_text_hash(claim_text)

        claims_canon.append(
            {
                "claim_text_hash": claim_hash,
                "elements": sorted(elements_canon, key=lambda x: x["canonical_id"]),
                "evidence_ids": sorted(evidence_ids),
            }
        )

    # Collect per-evidence classification metadata
    for c in claims_data:
        for ev in c.get("evidence") or []:
            eid = ev.get("evidenceId") or ev.get("evidence_id")
            if eid and eid not in all_evidence_meta:
                all_evidence_meta[eid] = {
                    "tier": ev.get("tier"),
                    "evidence_type": ev.get("evidenceType") or ev.get("evidence_type"),
                    "content_basis": ev.get("contentBasis") or ev.get("content_basis"),
                    "classification_method": (
                        ev.get("classificationMethod")
                        or ev.get("classification_method")
                    ),
                }

    canon = {
        "v": 1,
        "check_id": check_id,
        "claims": sorted(claims_canon, key=lambda c: c["claim_text_hash"] or ""),
        "evidence_meta": dict(sorted(all_evidence_meta.items())),
        "landscape": landscape or {},
        "executed_tier": executed_tier,
        # None => signing path (or a pre-2026-08-25 manifest with no stored
        # value, which falls back to the old behaviour rather than breaking).
        "pipeline_fingerprint": (
            pipeline_fingerprint
            if pipeline_fingerprint is not None
            else compute_pipeline_fingerprint()
        ),
    }
    if orientation_basis:
        canon["orientation_basis"] = orientation_basis

    return canon


def compute_canonical_hash(canonical_data: dict) -> str:
    """SHA256 hash of canonical JSON — full 64 hex characters."""
    canonical_json = json.dumps(canonical_data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical_json.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------


def get_signing_key_bytes(kid: str) -> Optional[bytes]:
    """Retrieve signing key by key ID. Supports rotated keys."""
    raw = settings.MANIFEST_SIGNING_KEYS
    try:
        keys = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        keys = {}

    # Also check current key
    if kid == settings.MANIFEST_KID and settings.MANIFEST_SIGNING_KEY:
        return base64.b64decode(settings.MANIFEST_SIGNING_KEY)

    b64_key = keys.get(kid)
    if not b64_key:
        return None
    return base64.b64decode(b64_key)


def sign_manifest(
    landscape_hash: str,
    signed_at: str,
    signing_key: bytes,
    kid: str,
    executed_tier: Optional[str],
) -> dict:
    """Create signed manifest dict.

    The manifest is stored on Check.manifest as JSONB.
    Application-immutable after creation.
    """
    message = f"{landscape_hash}:{signed_at}".encode()
    signature = hmac.new(signing_key, message, hashlib.sha256).hexdigest()
    return {
        "landscape_hash": landscape_hash,
        "signature": f"hmac-sha256:{signature}",
        "signed_at": signed_at,
        "kid": kid,
        "scheme": "hmac-sha256",
        "canonical_version": 1,
        "pipeline_fingerprint": compute_pipeline_fingerprint(),
        "executed_tier": executed_tier,
    }


def create_manifest_for_check(
    check_id: str,
    claims_data: List[Dict[str, Any]],
    executed_tier: Optional[str],
    landscape: Optional[Dict[str, Any]],
    orientation_basis: Optional[Dict[str, Any]] = None,
) -> Optional[dict]:
    """Build and sign a manifest for a completed check.

    Returns None if signing is disabled or key is not configured.
    """
    if not settings.MANIFEST_SIGNING_ENABLED:
        return None

    signing_key = get_signing_key_bytes(settings.MANIFEST_KID)
    if not signing_key:
        logger.warning(
            f"Manifest signing enabled but no key found for kid={settings.MANIFEST_KID}"
        )
        return None

    canonical_data = build_canonical_data(
        check_id=check_id,
        claims_data=claims_data,
        executed_tier=executed_tier,
        landscape=landscape,
        orientation_basis=orientation_basis,
    )
    landscape_hash = compute_canonical_hash(canonical_data)
    signed_at = datetime.now(timezone.utc).isoformat()

    return sign_manifest(
        landscape_hash=landscape_hash,
        signed_at=signed_at,
        signing_key=signing_key,
        kid=settings.MANIFEST_KID,
        executed_tier=executed_tier,
    )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_manifest(stored_manifest: dict) -> dict:
    """Verify signature authenticity on a stored manifest.

    Returns {"valid": True} or {"valid": False, "reason": str}.
    Does NOT verify data integrity — caller must separately
    recompute canonical hash and compare to stored landscape_hash.
    """
    kid = stored_manifest.get("kid")
    if not kid:
        return {"valid": False, "reason": "missing_kid"}

    key = get_signing_key_bytes(kid)
    if not key:
        return {"valid": False, "reason": "unknown_key"}

    landscape_hash = stored_manifest.get("landscape_hash", "")
    signed_at = stored_manifest.get("signed_at", "")
    stored_sig = stored_manifest.get("signature", "")

    expected_sig = hmac.new(
        key, f"{landscape_hash}:{signed_at}".encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(f"hmac-sha256:{expected_sig}", stored_sig):
        return {"valid": False, "reason": "signature_invalid"}

    return {"valid": True}
