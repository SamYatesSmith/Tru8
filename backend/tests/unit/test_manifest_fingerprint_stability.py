"""A model migration must not invalidate previously-signed checks (2026-08-25).

`build_canonical_data` embedded `compute_pipeline_fingerprint()`, computed live
from the server's CURRENT settings, while every other field in the payload is a
property of the check read back from stored data. So changing a model string
changed the canonical hash of every historic check, and `GET /verify/{id}`
returned `data_modified` — accusing us of tampering — for all of them. Nothing
raised. The public verification endpoint simply began giving a confident wrong
answer.

These tests pin the fix ahead of the Gemini 2.5 -> 3.x migration. The first one
is the regression itself; the last two exist so the fix cannot be mistaken for
"verification got weaker".
"""

import pytest
from unittest.mock import patch

from app.core.manifest_signer import (
    build_canonical_data,
    compute_canonical_hash,
    compute_pipeline_fingerprint,
)


CLAIMS = [
    {
        "claimMap": {
            "normalised_claim": "UK CPI was below 2% in September 2024",
            "elements": [
                {
                    "element_id": "e1",
                    "description": "UK CPI was below 2% in September 2024",
                    "state": "supported",
                    "evidence_refs": [{"evidence_id": "ev-1"}],
                }
            ],
        }
    }
]
LANDSCAPE = {"totalEvidence": 1}


def _canon(fingerprint=None):
    return build_canonical_data(
        check_id="chk-1",
        claims_data=CLAIMS,
        executed_tier="full",
        landscape=LANDSCAPE,
        pipeline_fingerprint=fingerprint,
    )


class TestSurvivesModelMigration:
    def test_signed_under_25_still_verifies_under_3x(self):
        """The exact scenario: sign on 2.5, verify after the switch to 3.x."""
        with patch("app.core.manifest_signer.settings") as st:
            st.PRIMARY_LLM_PROVIDER = "google"
            st.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            st.MAPPING_GOOGLE_MODEL = "gemini-2.5-flash"
            st.DECOMPOSITION_MODEL = "x"
            st.ANALYZER_MODEL = "y"
            signed_fingerprint = compute_pipeline_fingerprint()
            signed_hash = compute_canonical_hash(_canon())  # signing: computes live

        # ... the migration happens; the server now runs Gemini 3.x ...
        with patch("app.core.manifest_signer.settings") as st:
            st.PRIMARY_LLM_PROVIDER = "google"
            st.GOOGLE_LLM_MODEL = "gemini-3.5-flash-lite"
            st.MAPPING_GOOGLE_MODEL = "gemini-3.5-flash-lite"
            st.DECOMPOSITION_MODEL = "x"
            st.ANALYZER_MODEL = "y"
            assert compute_pipeline_fingerprint() != signed_fingerprint
            # Verification passes the STORED fingerprint back in.
            verify_hash = compute_canonical_hash(_canon(signed_fingerprint))

        assert (
            verify_hash == signed_hash
        ), "a historic check reads as data_modified after a model change"

    def test_the_old_behaviour_would_have_failed(self):
        """Guards the guard: prove the scenario above is a real regression.

        If recomputing live still produced a matching hash, the test above would
        pass for the wrong reason and pin nothing.
        """
        with patch("app.core.manifest_signer.settings") as st:
            st.PRIMARY_LLM_PROVIDER = "google"
            st.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            st.MAPPING_GOOGLE_MODEL = "gemini-2.5-flash"
            st.DECOMPOSITION_MODEL = "x"
            st.ANALYZER_MODEL = "y"
            signed_hash = compute_canonical_hash(_canon())

        with patch("app.core.manifest_signer.settings") as st:
            st.PRIMARY_LLM_PROVIDER = "google"
            st.GOOGLE_LLM_MODEL = "gemini-3.5-flash-lite"
            st.MAPPING_GOOGLE_MODEL = "gemini-3.5-flash-lite"
            st.DECOMPOSITION_MODEL = "x"
            st.ANALYZER_MODEL = "y"
            live_hash = compute_canonical_hash(_canon())  # the OLD path

        assert live_hash != signed_hash


class TestTamperDetectionIntact:
    """The fix must not be a weakening. The fingerprint is still signed data."""

    def test_altered_fingerprint_still_fails_verification(self):
        with patch("app.core.manifest_signer.settings") as st:
            st.PRIMARY_LLM_PROVIDER = "google"
            st.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            st.MAPPING_GOOGLE_MODEL = "gemini-2.5-flash"
            st.DECOMPOSITION_MODEL = "x"
            st.ANALYZER_MODEL = "y"
            real = compute_pipeline_fingerprint()
            signed_hash = compute_canonical_hash(_canon())
        forged = compute_canonical_hash(_canon("deadbeefcafe"))
        assert forged != signed_hash
        assert compute_canonical_hash(_canon(real)) == signed_hash

    def test_altered_element_state_still_fails_verification(self):
        """The thing verification actually exists to catch."""
        with patch("app.core.manifest_signer.settings") as st:
            st.PRIMARY_LLM_PROVIDER = "google"
            st.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            st.MAPPING_GOOGLE_MODEL = "gemini-2.5-flash"
            st.DECOMPOSITION_MODEL = "x"
            st.ANALYZER_MODEL = "y"
            fp = compute_pipeline_fingerprint()
            signed_hash = compute_canonical_hash(_canon(fp))

            tampered = [
                {
                    "claimMap": {
                        **CLAIMS[0]["claimMap"],
                        "elements": [
                            {
                                **CLAIMS[0]["claimMap"]["elements"][0],
                                "state": "disputed",
                            }
                        ],
                    }
                }
            ]
            tampered_hash = compute_canonical_hash(
                build_canonical_data(
                    check_id="chk-1",
                    claims_data=tampered,
                    executed_tier="full",
                    landscape=LANDSCAPE,
                    pipeline_fingerprint=fp,
                )
            )
        assert tampered_hash != signed_hash


class TestBackCompatible:
    def test_manifest_without_stored_fingerprint_uses_live(self):
        """Pre-fix manifests lack the key; None must mean 'behave as before'."""
        with patch("app.core.manifest_signer.settings") as st:
            st.PRIMARY_LLM_PROVIDER = "google"
            st.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            st.MAPPING_GOOGLE_MODEL = "gemini-2.5-flash"
            st.DECOMPOSITION_MODEL = "x"
            st.ANALYZER_MODEL = "y"
            assert (
                _canon(None)["pipeline_fingerprint"] == compute_pipeline_fingerprint()
            )
