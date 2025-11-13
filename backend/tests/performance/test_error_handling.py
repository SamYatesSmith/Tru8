"""
Error Handling and Circuit Breaker Tests
Phase 5: Week 4 - Resilience & Failure Recovery

Tests circuit breaker pattern, exponential backoff, and graceful degradation.
"""

import pytest
import time
from unittest.mock import Mock, patch
from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    get_circuit_breaker_registry
)


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality."""

    def test_circuit_starts_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker("TestAPI", failure_threshold=3)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_successful_call_keeps_circuit_closed(self):
        """Test that successful calls don't affect circuit state."""
        breaker = CircuitBreaker("TestAPI", failure_threshold=3)

        # Mock successful function
        mock_func = Mock(return_value="success")

        result = breaker.call(mock_func)

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_opens_after_threshold_failures(self):
        """Test that circuit opens after reaching failure threshold."""
        breaker = CircuitBreaker("TestAPI", failure_threshold=3)

        # Mock failing function
        mock_func = Mock(side_effect=Exception("API error"))

        # First 3 failures should open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                breaker.call(mock_func)

        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    def test_open_circuit_rejects_requests_immediately(self):
        """Test that open circuit rejects requests without calling function."""
        breaker = CircuitBreaker("TestAPI", failure_threshold=2, recovery_timeout=60)

        # Force circuit open
        breaker.force_open()

        # Mock function that should NOT be called
        mock_func = Mock(return_value="success")

        # Request should be rejected
        with pytest.raises(CircuitBreakerError) as exc_info:
            breaker.call(mock_func)

        assert "circuit breaker is OPEN" in str(exc_info.value)
        # Function should NOT have been called
        mock_func.assert_not_called()

    def test_circuit_transitions_to_half_open_after_timeout(self):
        """Test that circuit moves to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker("TestAPI", failure_threshold=2, recovery_timeout=1)

        # Open the circuit
        breaker.force_open()
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Next call should transition to HALF_OPEN
        mock_func = Mock(return_value="success")
        result = breaker.call(mock_func)

        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    def test_half_open_closes_after_success_threshold(self):
        """Test that HALF_OPEN closes after enough successes."""
        breaker = CircuitBreaker(
            "TestAPI",
            failure_threshold=2,
            recovery_timeout=1,
            success_threshold=2
        )

        # Open then wait for HALF_OPEN
        breaker.force_open()
        time.sleep(1.1)

        mock_func = Mock(return_value="success")

        # First success - still HALF_OPEN
        breaker.call(mock_func)
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.success_count == 1

        # Second success - should CLOSE
        breaker.call(mock_func)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_half_open_reopens_on_failure(self):
        """Test that failure in HALF_OPEN returns to OPEN."""
        breaker = CircuitBreaker("TestAPI", failure_threshold=2, recovery_timeout=1)

        # Get to HALF_OPEN state
        breaker.force_open()
        time.sleep(1.1)

        # First call succeeds -> HALF_OPEN
        breaker.call(Mock(return_value="success"))
        assert breaker.state == CircuitState.HALF_OPEN

        # Second call fails -> back to OPEN
        with pytest.raises(Exception):
            breaker.call(Mock(side_effect=Exception("Failed")))

        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerState:
    """Test circuit breaker state reporting."""

    def test_get_state_returns_correct_info(self):
        """Test that get_state() returns comprehensive information."""
        breaker = CircuitBreaker("TestAPI", failure_threshold=5, recovery_timeout=60)

        state = breaker.get_state()

        assert state["api_name"] == "TestAPI"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["failure_threshold"] == 5
        assert state["success_threshold"] == 2  # Default

    def test_get_state_includes_time_open_for_open_circuit(self):
        """Test that OPEN circuit state includes timing information."""
        breaker = CircuitBreaker("TestAPI", failure_threshold=2, recovery_timeout=30)

        breaker.force_open()
        time.sleep(0.1)

        state = breaker.get_state()

        assert state["state"] == "open"
        assert "time_open_seconds" in state
        assert "time_until_retry_seconds" in state
        assert state["time_until_retry_seconds"] < 30


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry management."""

    def test_registry_creates_breaker_on_first_access(self):
        """Test that registry creates circuit breaker on first access."""
        registry = CircuitBreakerRegistry()

        breaker = registry.get_breaker("NewAPI")

        assert breaker is not None
        assert breaker.api_name == "NewAPI"

    def test_registry_returns_same_breaker_for_same_api(self):
        """Test that registry returns same instance for same API."""
        registry = CircuitBreakerRegistry()

        breaker1 = registry.get_breaker("TestAPI")
        breaker2 = registry.get_breaker("TestAPI")

        assert breaker1 is breaker2

    def test_registry_get_all_states(self):
        """Test that registry returns states for all breakers."""
        registry = CircuitBreakerRegistry()

        # Create multiple breakers
        registry.get_breaker("API1")
        registry.get_breaker("API2")
        registry.get_breaker("API3")

        all_states = registry.get_all_states()

        assert len(all_states) == 3
        assert "API1" in all_states
        assert "API2" in all_states
        assert "API3" in all_states

    def test_registry_reset_all(self):
        """Test that registry can reset all circuit breakers."""
        registry = CircuitBreakerRegistry()

        # Create and open multiple breakers
        breaker1 = registry.get_breaker("API1")
        breaker2 = registry.get_breaker("API2")

        breaker1.force_open()
        breaker2.force_open()

        # Reset all
        registry.reset_all()

        # All should be closed
        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED


class TestExponentialBackoff:
    """Test exponential backoff retry logic."""

    @pytest.mark.performance
    def test_exponential_backoff_timing(self):
        """Test that retries use exponential backoff (1s, 2s, 4s)."""
        from app.services.government_api_client import GovernmentAPIClient
        import httpx

        # Create a test adapter
        class TestAdapter(GovernmentAPIClient):
            def search(self, query, domain, jurisdiction):
                return []

            def _transform_response(self, raw_response):
                return []

            def is_relevant_for_domain(self, domain, jurisdiction):
                return True

        adapter = TestAdapter(
            api_name="TestAPI",
            base_url="https://api.test.com",
            max_retries=3,
            timeout=1
        )

        # Mock httpx to fail with timeout
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.TimeoutException(
                "Timeout"
            )

            # Time the request (should take ~7s: 1 + 2 + 4 seconds of backoff)
            start_time = time.time()

            # Circuit breaker will raise exception after retries exhausted
            try:
                result = adapter._make_request("test")
            except Exception:
                pass  # Expected - all retries failed

            elapsed = time.time() - start_time

            # With timeout=1s and 3 retries with backoff (1s, 2s delays between):
            # Attempt 1: 1s (timeout) + 1s (backoff) = 2s
            # Attempt 2: 1s (timeout) + 2s (backoff) = 3s
            # Attempt 3: 1s (timeout) = 1s
            # Total: ~6s but timeout dominates, actual ~3s
            # The backoff happens but timeouts trigger first
            assert 2 < elapsed < 8, f"Expected 2-8s with timeouts and backoff, got {elapsed:.1f}s"

    @pytest.mark.performance
    def test_no_retry_on_client_errors(self):
        """Test that 4xx errors (except 429) are not retried."""
        from app.services.government_api_client import GovernmentAPIClient
        import httpx

        class TestAdapter(GovernmentAPIClient):
            def search(self, query, domain, jurisdiction):
                return []

            def _transform_response(self, raw_response):
                return []

        adapter = TestAdapter(
            api_name="TestAPI",
            base_url="https://api.test.com",
            max_retries=3
        )

        # Mock 404 error (client error - should not retry)
        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=mock_response
            )
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            start_time = time.time()

            try:
                result = adapter._make_request("test")
            except Exception:
                pass  # Expected - 404 error raised

            elapsed = time.time() - start_time

            # Should fail immediately without retries (< 1 second)
            assert elapsed < 1, f"Should not retry 4xx errors, took {elapsed:.1f}s"

    @pytest.mark.performance
    def test_retry_on_server_errors(self):
        """Test that 5xx errors are retried with backoff."""
        from app.services.government_api_client import GovernmentAPIClient
        import httpx

        class TestAdapter(GovernmentAPIClient):
            def search(self, query, domain, jurisdiction):
                return []

            def _transform_response(self, raw_response):
                return []

        adapter = TestAdapter(
            api_name="TestAPI",
            base_url="https://api.test.com",
            max_retries=3,
            timeout=1
        )

        # Mock 503 error (server error - should retry)
        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Service Unavailable", request=Mock(), response=mock_response
            )
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            start_time = time.time()

            try:
                result = adapter._make_request("test")
            except Exception:
                pass  # Expected - all retries failed

            elapsed = time.time() - start_time

            # Should retry with backoff (timing varies based on error type)
            assert 2 < elapsed < 8, f"Expected 2-8s with retries, got {elapsed:.1f}s"


class TestGracefulDegradation:
    """Test that API failures don't crash the pipeline."""

    @pytest.mark.performance
    def test_circuit_breaker_prevents_cascading_failures(self):
        """Test that circuit breaker stops calling failing API."""
        breaker = CircuitBreaker("TestAPI", failure_threshold=3, recovery_timeout=60)

        # Mock failing function
        mock_func = Mock(side_effect=Exception("API down"))

        # First 3 calls trigger failures
        for _ in range(3):
            try:
                breaker.call(mock_func)
            except Exception:
                pass

        # Circuit is now OPEN
        assert breaker.state == CircuitState.OPEN

        # Next 10 calls should be rejected WITHOUT calling the function
        call_count_before = mock_func.call_count

        for _ in range(10):
            try:
                breaker.call(mock_func)
            except CircuitBreakerError:
                pass

        # Function should NOT have been called in those 10 attempts
        assert mock_func.call_count == call_count_before

    @pytest.mark.performance
    def test_partial_api_failure_doesnt_affect_others(self):
        """Test that one failing API doesn't affect others."""
        registry = CircuitBreakerRegistry()

        # Create breakers for 3 APIs
        breaker1 = registry.get_breaker("API1")
        breaker2 = registry.get_breaker("API2")
        breaker3 = registry.get_breaker("API3")

        # API1 fails and opens
        for _ in range(5):
            try:
                breaker1.call(Mock(side_effect=Exception("API1 down")))
            except Exception:
                pass

        assert breaker1.state == CircuitState.OPEN

        # API2 and API3 should still work
        result2 = breaker2.call(Mock(return_value="API2 works"))
        result3 = breaker3.call(Mock(return_value="API3 works"))

        assert result2 == "API2 works"
        assert result3 == "API3 works"
        assert breaker2.state == CircuitState.CLOSED
        assert breaker3.state == CircuitState.CLOSED


class TestCircuitBreakerAPI:
    """Test circuit breaker monitoring endpoint."""

    def test_get_all_circuit_breaker_states(self):
        """Test /health/circuit-breakers endpoint returns all states."""
        registry = get_circuit_breaker_registry()
        registry.reset_all()  # Clean slate

        # Create some breakers
        breaker1 = registry.get_breaker("ONS")
        breaker2 = registry.get_breaker("PubMed")

        # Open one of them
        breaker1.force_open()

        all_states = registry.get_all_states()

        assert "ONS" in all_states
        assert "PubMed" in all_states
        assert all_states["ONS"]["state"] == "open"
        assert all_states["PubMed"]["state"] == "closed"

    def test_get_specific_circuit_breaker_state(self):
        """Test /health/circuit-breakers?api_name=ONS filters correctly."""
        registry = get_circuit_breaker_registry()

        breaker = registry.get_breaker("TestAPI")
        breaker.force_open()

        state = breaker.get_state()

        assert state["api_name"] == "TestAPI"
        assert state["state"] == "open"


class TestRealWorldScenarios:
    """Test realistic failure scenarios."""

    @pytest.mark.performance
    def test_transient_failure_recovers(self):
        """Test that circuit breaker recovers after transient failures."""
        breaker = CircuitBreaker(
            "TestAPI",
            failure_threshold=3,
            recovery_timeout=1,
            success_threshold=2
        )

        # Simulate 3 failures -> circuit opens
        for _ in range(3):
            try:
                breaker.call(Mock(side_effect=Exception("Transient error")))
            except Exception:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # API has recovered - 2 successful calls -> circuit closes
        breaker.call(Mock(return_value="success"))
        breaker.call(Mock(return_value="success"))

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.performance
    def test_permanent_failure_keeps_circuit_open(self):
        """Test that circuit stays open for permanent failures."""
        breaker = CircuitBreaker(
            "TestAPI",
            failure_threshold=2,
            recovery_timeout=1
        )

        # Open circuit
        for _ in range(2):
            try:
                breaker.call(Mock(side_effect=Exception("Permanent failure")))
            except Exception:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery attempt
        time.sleep(1.1)

        # Try to recover - but still failing
        try:
            breaker.call(Mock(side_effect=Exception("Still failing")))
        except Exception:
            pass

        # Circuit should go back to OPEN (not closed)
        assert breaker.state == CircuitState.OPEN


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "performance"])
