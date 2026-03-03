"""Route drift test — verify /agent/{tier} and /agent/x402/{tier} have identical response shapes.

This test ensures schema parity between the two payment rails by comparing
their OpenAPI schemas (when x402 is enabled) or at minimum verifying that
both routers define the same tier endpoints.
"""

import pytest
from unittest.mock import patch


class TestRouteDrift:
    """Agent and x402 routers expose matching tier endpoints."""

    def test_agent_router_has_three_tiers(self):
        """Verify /agent router has lookup, quick, full endpoints."""
        from app.api.v1.agent import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/lookup" in paths
        assert "/quick" in paths
        assert "/full" in paths

    def test_x402_router_has_three_tiers(self):
        """Verify /agent/x402 router has lookup, quick, full endpoints."""
        from app.api.v1.agent_x402 import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/lookup" in paths
        assert "/quick" in paths
        assert "/full" in paths

    def test_x402_has_challenge_endpoint(self):
        """x402 router has challenge endpoint not in agent router."""
        from app.api.v1.agent_x402 import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/challenge" in paths

    def test_x402_has_result_endpoint(self):
        """x402 router has SIWE result retrieval endpoint."""
        from app.api.v1.agent_x402 import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/result/{check_id}" in paths

    def test_agent_router_has_retrieval(self):
        """Agent router has result retrieval endpoint."""
        from app.api.v1.agent import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/result/{check_id}" in paths

    def test_request_models_match(self):
        """Both routers accept the same request body shape."""
        from app.api.v1.agent import AgentClaimRequest
        from app.api.v1.agent_x402 import X402ClaimRequest

        # Both should have claim and compact fields
        agent_fields = set(AgentClaimRequest.model_fields.keys())
        x402_fields = set(X402ClaimRequest.model_fields.keys())
        assert agent_fields == x402_fields

    def test_quick_limitations_match(self):
        """Both routers report the same quick mode limitations."""
        from app.api.v1.agent import QUICK_LIMITATIONS as agent_limits
        from app.api.v1.agent_x402 import QUICK_LIMITATIONS as x402_limits

        assert agent_limits == x402_limits
