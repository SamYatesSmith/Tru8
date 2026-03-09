"""M-04: Tests for manifest signing and verification.

Covers:
- Canonical payload construction
- Pipeline fingerprint computation
- Element canonical ID normalisation
- HMAC-SHA256 signing
- Signature verification
- Key rotation
- Data integrity detection
"""

import base64
import hashlib
import os
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# canonical_element_id
# ---------------------------------------------------------------------------


class TestCanonicalElementId:
    def test_basic_normalisation(self):
        from app.core.manifest_signer import canonical_element_id

        eid = canonical_element_id("GDP grew 2.1%")
        assert len(eid) == 16
        assert all(c in "0123456789abcdef" for c in eid)

    def test_case_insensitive(self):
        from app.core.manifest_signer import canonical_element_id

        assert canonical_element_id("GDP grew 2.1%") == canonical_element_id(
            "gdp grew 2.1%"
        )

    def test_whitespace_collapse(self):
        from app.core.manifest_signer import canonical_element_id

        assert canonical_element_id("GDP  grew  2.1%") == canonical_element_id(
            "GDP grew 2.1%"
        )

    def test_unicode_normalisation(self):
        from app.core.manifest_signer import canonical_element_id

        # NFKC: ﬁ → fi
        assert canonical_element_id("ﬁnance") == canonical_element_id("finance")

    def test_strip_whitespace(self):
        from app.core.manifest_signer import canonical_element_id

        assert canonical_element_id("  GDP grew  ") == canonical_element_id("GDP grew")

    def test_different_descriptions_differ(self):
        from app.core.manifest_signer import canonical_element_id

        assert canonical_element_id("GDP grew 2.1%") != canonical_element_id(
            "Unemployment fell 0.5%"
        )


# ---------------------------------------------------------------------------
# Pipeline fingerprint
# ---------------------------------------------------------------------------


class TestPipelineFingerprint:
    def test_fingerprint_length(self):
        from app.core.manifest_signer import compute_pipeline_fingerprint

        fp = compute_pipeline_fingerprint()
        assert len(fp) == 12
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_deterministic(self):
        from app.core.manifest_signer import compute_pipeline_fingerprint

        assert compute_pipeline_fingerprint() == compute_pipeline_fingerprint()

    def test_fingerprint_changes_with_model(self):
        from app.core.manifest_signer import compute_pipeline_fingerprint

        fp1 = compute_pipeline_fingerprint()
        with patch("app.core.manifest_signer.settings") as mock_settings:
            mock_settings.PRIMARY_LLM_PROVIDER = "openai"
            mock_settings.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            mock_settings.MAPPING_GOOGLE_MODEL = "different-model"
            mock_settings.DECOMPOSITION_MODEL = "gpt-4o"
            mock_settings.ANALYZER_MODEL = "gpt-4o"
            fp2 = compute_pipeline_fingerprint()
        assert fp1 != fp2


# ---------------------------------------------------------------------------
# Canonical data builder
# ---------------------------------------------------------------------------


class TestBuildCanonicalData:
    def _make_claims_data(self):
        return [
            {
                "text": "GDP grew 2.1% in Q4",
                "claim_text_hash": "abc123",
                "claimMap": {
                    "elements": [
                        {
                            "description": "GDP grew 2.1%",
                            "state": "supported",
                            "basis": {
                                "evidence_count": 3,
                                "tier_breakdown": {"primary": 1, "reporting": 2},
                            },
                            "evidence_refs": [
                                {"evidence_id": "ev-111"},
                                {"evidence_id": "ev-222"},
                            ],
                        }
                    ],
                    "orientation_basis": {
                        "total_elements": 1,
                        "state_distribution": {"supported": 1},
                    },
                },
                "evidence": [
                    {
                        "evidence_id": "ev-111",
                        "tier": "primary",
                        "evidence_type": "data",
                        "content_basis": "full",
                        "classification_method": "llm",
                    },
                    {
                        "evidence_id": "ev-222",
                        "tier": "reporting",
                        "evidence_type": "news",
                        "content_basis": "snippet",
                        "classification_method": "heuristic",
                    },
                ],
            }
        ]

    def test_canonical_data_structure(self):
        from app.core.manifest_signer import build_canonical_data

        data = build_canonical_data(
            check_id="check-1",
            claims_data=self._make_claims_data(),
            executed_tier="full",
            landscape={"elementCount": 1},
        )
        assert data["v"] == 1
        assert data["check_id"] == "check-1"
        assert data["executed_tier"] == "full"
        assert len(data["claims"]) == 1
        assert "pipeline_fingerprint" in data

    def test_excludes_narrative_fields(self):
        from app.core.manifest_signer import build_canonical_data

        import json

        data = build_canonical_data(
            check_id="check-1",
            claims_data=self._make_claims_data(),
            executed_tier="full",
            landscape={},
        )
        canonical_json = json.dumps(data, sort_keys=True)
        # These narrative fields must not appear
        assert (
            "orientation" not in canonical_json or "orientation_basis" in canonical_json
        )
        assert "reasoning" not in canonical_json
        assert "bounty_text" not in canonical_json
        assert "uncertainty" not in canonical_json

    def test_includes_basis_metadata(self):
        from app.core.manifest_signer import build_canonical_data

        data = build_canonical_data(
            check_id="check-1",
            claims_data=self._make_claims_data(),
            executed_tier="full",
            landscape={},
        )
        elem = data["claims"][0]["elements"][0]
        assert "basis" in elem
        assert elem["basis"]["evidence_count"] == 3

    def test_includes_evidence_meta(self):
        from app.core.manifest_signer import build_canonical_data

        data = build_canonical_data(
            check_id="check-1",
            claims_data=self._make_claims_data(),
            executed_tier="full",
            landscape={},
        )
        assert "ev-111" in data["evidence_meta"]
        assert data["evidence_meta"]["ev-111"]["tier"] == "primary"
        assert data["evidence_meta"]["ev-111"]["content_basis"] == "full"

    def test_deterministic_ordering(self):
        from app.core.manifest_signer import (
            build_canonical_data,
            compute_canonical_hash,
        )

        data1 = build_canonical_data(
            check_id="check-1",
            claims_data=self._make_claims_data(),
            executed_tier="full",
            landscape={"x": 1},
        )
        data2 = build_canonical_data(
            check_id="check-1",
            claims_data=self._make_claims_data(),
            executed_tier="full",
            landscape={"x": 1},
        )
        assert compute_canonical_hash(data1) == compute_canonical_hash(data2)


# ---------------------------------------------------------------------------
# Signing and verification
# ---------------------------------------------------------------------------


class TestSigning:
    @pytest.fixture
    def signing_key(self):
        return os.urandom(32)

    @pytest.fixture
    def kid(self):
        return "tru8-2026-03"

    def test_sign_manifest_structure(self, signing_key, kid):
        from app.core.manifest_signer import sign_manifest

        manifest = sign_manifest(
            landscape_hash="abc123def456",
            signed_at="2026-03-09T12:00:00Z",
            signing_key=signing_key,
            kid=kid,
            executed_tier="full",
        )
        assert manifest["landscape_hash"] == "abc123def456"
        assert manifest["signed_at"] == "2026-03-09T12:00:00Z"
        assert manifest["kid"] == kid
        assert manifest["scheme"] == "hmac-sha256"
        assert manifest["canonical_version"] == 1
        assert manifest["signature"].startswith("hmac-sha256:")
        assert manifest["executed_tier"] == "full"
        assert "pipeline_fingerprint" in manifest

    def test_verify_valid_signature(self, signing_key, kid):
        from app.core.manifest_signer import sign_manifest, verify_manifest

        b64_key = base64.b64encode(signing_key).decode()

        manifest = sign_manifest(
            landscape_hash="abc123",
            signed_at="2026-03-09T12:00:00Z",
            signing_key=signing_key,
            kid=kid,
            executed_tier="full",
        )

        with patch("app.core.manifest_signer.settings") as mock_settings:
            mock_settings.MANIFEST_KID = kid
            mock_settings.MANIFEST_SIGNING_KEY = b64_key
            mock_settings.MANIFEST_SIGNING_KEYS = "{}"
            result = verify_manifest(manifest)

        assert result["valid"] is True

    def test_verify_tampered_hash(self, signing_key, kid):
        from app.core.manifest_signer import sign_manifest, verify_manifest

        b64_key = base64.b64encode(signing_key).decode()

        manifest = sign_manifest(
            landscape_hash="abc123",
            signed_at="2026-03-09T12:00:00Z",
            signing_key=signing_key,
            kid=kid,
            executed_tier="full",
        )
        manifest["landscape_hash"] = "tampered"

        with patch("app.core.manifest_signer.settings") as mock_settings:
            mock_settings.MANIFEST_KID = kid
            mock_settings.MANIFEST_SIGNING_KEY = b64_key
            mock_settings.MANIFEST_SIGNING_KEYS = "{}"
            result = verify_manifest(manifest)

        assert result["valid"] is False
        assert result["reason"] == "signature_invalid"

    def test_verify_unknown_key(self):
        from app.core.manifest_signer import verify_manifest

        manifest = {
            "landscape_hash": "abc",
            "signed_at": "2026-03-09T12:00:00Z",
            "kid": "unknown-kid",
            "signature": "hmac-sha256:fake",
        }

        with patch("app.core.manifest_signer.settings") as mock_settings:
            mock_settings.MANIFEST_KID = "tru8-2026-03"
            mock_settings.MANIFEST_SIGNING_KEY = ""
            mock_settings.MANIFEST_SIGNING_KEYS = "{}"
            result = verify_manifest(manifest)

        assert result["valid"] is False
        assert result["reason"] == "unknown_key"

    def test_key_rotation(self, signing_key, kid):
        """Sign with old key, rotate to new key, verify with old key still works."""
        import json

        from app.core.manifest_signer import sign_manifest, verify_manifest

        old_key = signing_key
        old_kid = "tru8-2026-01"
        new_kid = "tru8-2026-03"
        b64_old = base64.b64encode(old_key).decode()
        new_key = os.urandom(32)
        b64_new = base64.b64encode(new_key).decode()

        manifest = sign_manifest(
            landscape_hash="abc123",
            signed_at="2026-01-15T12:00:00Z",
            signing_key=old_key,
            kid=old_kid,
            executed_tier="full",
        )

        # Keys dict includes both old and new
        keys_json = json.dumps({old_kid: b64_old, new_kid: b64_new})

        with patch("app.core.manifest_signer.settings") as mock_settings:
            mock_settings.MANIFEST_KID = new_kid
            mock_settings.MANIFEST_SIGNING_KEY = b64_new
            mock_settings.MANIFEST_SIGNING_KEYS = keys_json
            result = verify_manifest(manifest)

        assert result["valid"] is True


# ---------------------------------------------------------------------------
# create_manifest_for_check
# ---------------------------------------------------------------------------


class TestCreateManifest:
    def test_returns_none_when_disabled(self):
        from app.core.manifest_signer import create_manifest_for_check

        with patch("app.core.manifest_signer.settings") as mock_settings:
            mock_settings.MANIFEST_SIGNING_ENABLED = False
            result = create_manifest_for_check(
                check_id="check-1",
                claims_data=[],
                executed_tier="full",
                landscape={},
            )
        assert result is None

    def test_returns_manifest_when_enabled(self):
        from app.core.manifest_signer import create_manifest_for_check

        key = os.urandom(32)
        b64_key = base64.b64encode(key).decode()

        with patch("app.core.manifest_signer.settings") as mock_settings:
            mock_settings.MANIFEST_SIGNING_ENABLED = True
            mock_settings.MANIFEST_SIGNING_KEY = b64_key
            mock_settings.MANIFEST_KID = "tru8-2026-03"
            mock_settings.MANIFEST_SIGNING_KEYS = "{}"
            mock_settings.PRIMARY_LLM_PROVIDER = "google"
            mock_settings.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            mock_settings.MAPPING_GOOGLE_MODEL = "gemini-2.5-flash"
            mock_settings.DECOMPOSITION_MODEL = "gpt-4o"
            mock_settings.ANALYZER_MODEL = "gpt-4o"

            result = create_manifest_for_check(
                check_id="check-1",
                claims_data=[{"text": "test", "claimMap": {}, "evidence": []}],
                executed_tier="full",
                landscape={"elementCount": 0},
            )
        assert result is not None
        assert result["scheme"] == "hmac-sha256"
        assert result["kid"] == "tru8-2026-03"
        assert "landscape_hash" in result
