"""
Tests for circuit breaker pattern implementation.

Covers:
- State machine transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- get_state() reporting
- CircuitBreakerRegistry (creation, caching, bulk operations)
"""

import time
from unittest.mock import patch

import pytest

from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _succeed():
    """A trivial function that succeeds."""
    return "ok"


def _fail():
    """A trivial function that always raises."""
    raise RuntimeError("boom")


def _trip_breaker(cb: CircuitBreaker):
    """Drive a breaker from CLOSED to OPEN by hitting the failure threshold."""
    for _ in range(cb.failure_threshold):
        with pytest.raises(RuntimeError):
            cb.call(_fail)


# ---------------------------------------------------------------------------
# TestCircuitBreakerStateMachine
# ---------------------------------------------------------------------------


class TestCircuitBreakerStateMachine:
    """State machine transitions for CircuitBreaker."""

    def test_starts_closed(self):
        cb = CircuitBreaker("test-api")
        assert cb.state == CircuitState.CLOSED

    def test_stays_closed_on_success(self):
        cb = CircuitBreaker("test-api")
        cb.call(_succeed)
        cb.call(_succeed)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker("test-api", failure_threshold=3)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(_fail)
        assert cb.state == CircuitState.OPEN

    def test_does_not_open_before_threshold(self):
        cb = CircuitBreaker("test-api", failure_threshold=5)
        for _ in range(4):
            with pytest.raises(RuntimeError):
                cb.call(_fail)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 4

    def test_open_rejects_calls(self):
        cb = CircuitBreaker("test-api", failure_threshold=2, recovery_timeout=300)
        _trip_breaker(cb)
        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(_succeed)
        assert "OPEN" in str(exc_info.value)

    def test_transitions_to_half_open(self):
        cb = CircuitBreaker("test-api", failure_threshold=2, recovery_timeout=0.05)
        _trip_breaker(cb)
        assert cb.state == CircuitState.OPEN

        time.sleep(0.06)

        # The next call should trigger the OPEN -> HALF_OPEN transition and
        # then execute the function.
        result = cb.call(_succeed)
        assert result == "ok"
        # After one success the breaker is in HALF_OPEN (needs success_threshold=2).
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_closes_on_success_threshold(self):
        cb = CircuitBreaker(
            "test-api", failure_threshold=2, recovery_timeout=0.05, success_threshold=2
        )
        _trip_breaker(cb)
        time.sleep(0.06)

        # First success — still HALF_OPEN
        cb.call(_succeed)
        assert cb.state == CircuitState.HALF_OPEN

        # Second success — should close
        cb.call(_succeed)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_half_open_reopens_on_failure(self):
        cb = CircuitBreaker("test-api", failure_threshold=2, recovery_timeout=0.05)
        _trip_breaker(cb)
        time.sleep(0.06)

        # One success to enter HALF_OPEN
        cb.call(_succeed)
        assert cb.state == CircuitState.HALF_OPEN

        # Failure should send it back to OPEN
        with pytest.raises(RuntimeError):
            cb.call(_fail)
        assert cb.state == CircuitState.OPEN
        assert cb.success_count == 0

    def test_force_open(self):
        cb = CircuitBreaker("test-api")
        assert cb.state == CircuitState.CLOSED
        cb.force_open()
        assert cb.state == CircuitState.OPEN
        assert cb.opened_at is not None

    def test_force_close(self):
        cb = CircuitBreaker("test-api", failure_threshold=2)
        _trip_breaker(cb)
        assert cb.state == CircuitState.OPEN

        cb.force_close()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.opened_at is None

    def test_force_close_from_half_open(self):
        cb = CircuitBreaker("test-api", failure_threshold=2, recovery_timeout=0.05)
        _trip_breaker(cb)
        time.sleep(0.06)
        cb.call(_succeed)
        assert cb.state == CircuitState.HALF_OPEN

        cb.force_close()
        assert cb.state == CircuitState.CLOSED

    def test_success_resets_failure_count_in_closed(self):
        """A success in CLOSED state should reset the failure count to 0."""
        cb = CircuitBreaker("test-api", failure_threshold=5)
        # Accumulate some failures (but not enough to open)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(_fail)
        assert cb.failure_count == 3

        cb.call(_succeed)
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_call_returns_function_result(self):
        cb = CircuitBreaker("test-api")

        def add(a, b):
            return a + b

        result = cb.call(add, 3, 7)
        assert result == 10

    def test_call_passes_kwargs(self):
        cb = CircuitBreaker("test-api")

        def greet(name="world"):
            return f"hello {name}"

        result = cb.call(greet, name="tru8")
        assert result == "hello tru8"

    def test_call_propagates_original_exception(self):
        cb = CircuitBreaker("test-api")

        def bad():
            raise ValueError("specific error")

        with pytest.raises(ValueError, match="specific error"):
            cb.call(bad)


# ---------------------------------------------------------------------------
# TestCircuitBreakerGetState
# ---------------------------------------------------------------------------


class TestCircuitBreakerGetState:
    """Tests for get_state() reporting."""

    def test_state_includes_all_fields(self):
        cb = CircuitBreaker("test-api", failure_threshold=5, success_threshold=2)
        state = cb.get_state()

        assert state["api_name"] == "test-api"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["success_count"] == 0
        assert state["failure_threshold"] == 5
        assert state["success_threshold"] == 2
        # No timing fields when CLOSED with no failures
        assert "time_open_seconds" not in state
        assert "last_failure" not in state

    def test_state_after_failures(self):
        cb = CircuitBreaker("test-api", failure_threshold=5)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(_fail)

        state = cb.get_state()
        assert state["failure_count"] == 3
        assert state["state"] == "closed"
        assert "last_failure" in state

    def test_state_when_open_includes_timing(self):
        cb = CircuitBreaker("test-api", failure_threshold=2, recovery_timeout=120)
        _trip_breaker(cb)

        state = cb.get_state()
        assert state["state"] == "open"
        assert "time_open_seconds" in state
        assert "time_until_retry_seconds" in state
        assert state["time_until_retry_seconds"] > 0

    def test_state_success_count_only_in_half_open(self):
        """success_count should be 0 in CLOSED state even if internally non-zero."""
        cb = CircuitBreaker(
            "test-api", failure_threshold=2, recovery_timeout=0.05, success_threshold=3
        )
        _trip_breaker(cb)
        time.sleep(0.06)

        # Enter HALF_OPEN with one success
        cb.call(_succeed)
        assert cb.state == CircuitState.HALF_OPEN

        state = cb.get_state()
        assert state["success_count"] == 1

        # After force_close the success_count in state should be 0
        cb.force_close()
        state = cb.get_state()
        assert state["success_count"] == 0


# ---------------------------------------------------------------------------
# TestCircuitBreakerRegistry
# ---------------------------------------------------------------------------


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    def test_creates_breaker_on_first_access(self):
        registry = CircuitBreakerRegistry()
        breaker = registry.get_breaker("ONS")
        assert isinstance(breaker, CircuitBreaker)
        assert breaker.api_name == "ONS"

    def test_returns_same_breaker(self):
        registry = CircuitBreakerRegistry()
        b1 = registry.get_breaker("ONS")
        b2 = registry.get_breaker("ONS")
        assert b1 is b2

    def test_different_names_different_breakers(self):
        registry = CircuitBreakerRegistry()
        b1 = registry.get_breaker("ONS")
        b2 = registry.get_breaker("FRED")
        assert b1 is not b2

    def test_get_all_states(self):
        registry = CircuitBreakerRegistry()
        registry.get_breaker("ONS")
        registry.get_breaker("FRED")
        registry.get_breaker("Hansard")

        states = registry.get_all_states()
        assert set(states.keys()) == {"ONS", "FRED", "Hansard"}
        for name, state in states.items():
            assert state["api_name"] == name
            assert state["state"] == "closed"

    def test_reset_all(self):
        registry = CircuitBreakerRegistry(default_failure_threshold=2)
        b_ons = registry.get_breaker("ONS")
        b_fred = registry.get_breaker("FRED")

        # Trip both breakers
        _trip_breaker(b_ons)
        _trip_breaker(b_fred)
        assert b_ons.state == CircuitState.OPEN
        assert b_fred.state == CircuitState.OPEN

        registry.reset_all()
        assert b_ons.state == CircuitState.CLOSED
        assert b_fred.state == CircuitState.CLOSED
        assert b_ons.failure_count == 0
        assert b_fred.failure_count == 0

    def test_registry_uses_default_thresholds(self):
        registry = CircuitBreakerRegistry(
            default_failure_threshold=10,
            default_recovery_timeout=120,
            default_success_threshold=3,
        )
        breaker = registry.get_breaker("custom")
        assert breaker.failure_threshold == 10
        assert breaker.recovery_timeout == 120
        assert breaker.success_threshold == 3

    def test_get_all_states_empty_registry(self):
        registry = CircuitBreakerRegistry()
        assert registry.get_all_states() == {}
