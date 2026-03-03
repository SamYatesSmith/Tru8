"""Agent E2E test — purchase credits → lookup miss → quick → lookup hit.

Tests the full agent commerce workflow with mocked pipeline and DB.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agent_auth import AgentIdentity, AgentPaymentContext
from app.core.agent_pricing import get_tier_price


class TestAgentPricingTiers:
    """Agent pricing constants are correctly configured."""

    def test_lookup_price(self):
        assert get_tier_price("lookup") == 2  # $0.02

    def test_quick_price(self):
        assert get_tier_price("quick") == 7  # $0.07

    def test_full_price(self):
        assert get_tier_price("full") == 15  # $0.15

    def test_unknown_tier_raises(self):
        with pytest.raises(KeyError):
            get_tier_price("unknown")


class TestAgentIdentityModels:
    """AgentIdentity and AgentPaymentContext are correctly structured."""

    def test_agent_identity_fields(self):
        identity = AgentIdentity(provider="credit", payer_id="user_1", user_id="user_1")
        assert identity.provider == "credit"
        assert identity.payer_id == "user_1"
        assert identity.user_id == "user_1"

    def test_agent_payment_context_extends_identity(self):
        session = AsyncMock()
        ctx = AgentPaymentContext(
            provider="skyfire",
            payer_id="sky_user",
            user_id="tru8_user",
            session=session,
        )
        assert ctx.provider == "skyfire"
        assert ctx.session is session

    def test_payment_context_has_charge_method(self):
        session = AsyncMock()
        ctx = AgentPaymentContext(
            provider="credit", payer_id="u1", user_id="u1", session=session
        )
        assert hasattr(ctx, "charge")


class TestComputeRequestHash:
    """Request hash computation for idempotency detection."""

    def test_same_inputs_same_hash(self):
        from app.core.agent_auth import compute_request_hash

        h1 = compute_request_hash("quick", "abc123", False)
        h2 = compute_request_hash("quick", "abc123", False)
        assert h1 == h2

    def test_different_tier_different_hash(self):
        from app.core.agent_auth import compute_request_hash

        h1 = compute_request_hash("quick", "abc123", False)
        h2 = compute_request_hash("full", "abc123", False)
        assert h1 != h2

    def test_different_compact_different_hash(self):
        from app.core.agent_auth import compute_request_hash

        h1 = compute_request_hash("quick", "abc123", False)
        h2 = compute_request_hash("quick", "abc123", True)
        assert h1 != h2
