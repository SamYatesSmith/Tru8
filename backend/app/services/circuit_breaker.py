"""
Circuit Breaker Pattern for Government API Integration
Phase 5: Week 4 - Error Handling & Resilience

Implements circuit breaker to prevent cascading failures when APIs are down.

States:
- CLOSED: Normal operation, requests flow through
- OPEN: API is failing, requests rejected immediately
- HALF_OPEN: Testing if API has recovered

Reference: Michael Nygard's "Release It!" pattern
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and request is rejected."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for API calls.

    Opens after failure_threshold consecutive failures.
    Stays open for recovery_timeout seconds.
    Allows one request in HALF_OPEN state to test recovery.
    """

    def __init__(
        self,
        api_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.

        Args:
            api_name: Name of the API being protected
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Successes needed in HALF_OPEN to close circuit
        """
        self.api_name = api_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.opened_at: Optional[float] = None

        logger.info(
            f"Circuit breaker initialized for {api_name} "
            f"(threshold={failure_threshold}, timeout={recovery_timeout}s)"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"{self.api_name} circuit breaker: OPEN -> HALF_OPEN (testing recovery)")
                self.state = CircuitState.HALF_OPEN
            else:
                # Circuit still open, reject immediately
                time_since_open = time.time() - self.opened_at
                raise CircuitBreakerError(
                    f"{self.api_name} circuit breaker is OPEN "
                    f"(opened {time_since_open:.0f}s ago, will retry in {self.recovery_timeout - time_since_open:.0f}s)"
                )

        try:
            # Execute the function
            result = func(*args, **kwargs)

            # Success - record it
            self._on_success()
            return result

        except Exception as e:
            # Failure - record it
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"{self.api_name} circuit breaker: "
                f"success in HALF_OPEN ({self.success_count}/{self.success_threshold})"
            )

            if self.success_count >= self.success_threshold:
                # Enough successes to close the circuit
                logger.info(f"{self.api_name} circuit breaker: HALF_OPEN -> CLOSED (recovered)")
                self._reset()
        else:
            # In CLOSED state, just reset failure count
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed in HALF_OPEN, go back to OPEN
            logger.warning(
                f"{self.api_name} circuit breaker: HALF_OPEN -> OPEN (recovery test failed)"
            )
            self.state = CircuitState.OPEN
            self.opened_at = time.time()
            self.success_count = 0

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                # Too many failures, open the circuit
                logger.error(
                    f"{self.api_name} circuit breaker: CLOSED -> OPEN "
                    f"({self.failure_count} consecutive failures)"
                )
                self.state = CircuitState.OPEN
                self.opened_at = time.time()

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.opened_at is None:
            return False

        time_open = time.time() - self.opened_at
        return time_open >= self.recovery_timeout

    def _reset(self):
        """Reset circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None

    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.

        Returns:
            Dictionary with state information
        """
        state_info = {
            "api_name": self.api_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count if self.state == CircuitState.HALF_OPEN else 0,
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold
        }

        if self.state == CircuitState.OPEN and self.opened_at:
            time_open = time.time() - self.opened_at
            time_until_retry = max(0, self.recovery_timeout - time_open)
            state_info["time_open_seconds"] = round(time_open, 1)
            state_info["time_until_retry_seconds"] = round(time_until_retry, 1)

        if self.last_failure_time:
            state_info["last_failure"] = datetime.fromtimestamp(
                self.last_failure_time
            ).isoformat()

        return state_info

    def force_open(self):
        """Manually open circuit (for testing or maintenance)."""
        logger.warning(f"{self.api_name} circuit breaker: manually opened")
        self.state = CircuitState.OPEN
        self.opened_at = time.time()

    def force_close(self):
        """Manually close circuit (for testing or recovery)."""
        logger.info(f"{self.api_name} circuit breaker: manually closed")
        self._reset()


class CircuitBreakerRegistry:
    """
    Registry to manage circuit breakers for all API adapters.

    Usage:
        registry = CircuitBreakerRegistry()
        breaker = registry.get_breaker("ONS")
        result = breaker.call(api_adapter.search, query)
    """

    def __init__(
        self,
        default_failure_threshold: int = 5,
        default_recovery_timeout: int = 60,
        default_success_threshold: int = 2
    ):
        """
        Initialize circuit breaker registry.

        Args:
            default_failure_threshold: Default failures before opening
            default_recovery_timeout: Default recovery wait time (seconds)
            default_success_threshold: Default successes to close circuit
        """
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.default_failure_threshold = default_failure_threshold
        self.default_recovery_timeout = default_recovery_timeout
        self.default_success_threshold = default_success_threshold

    def get_breaker(self, api_name: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for an API.

        Args:
            api_name: Name of the API

        Returns:
            Circuit breaker instance
        """
        if api_name not in self.breakers:
            self.breakers[api_name] = CircuitBreaker(
                api_name=api_name,
                failure_threshold=self.default_failure_threshold,
                recovery_timeout=self.default_recovery_timeout,
                success_threshold=self.default_success_threshold
            )
        return self.breakers[api_name]

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get state of all circuit breakers.

        Returns:
            Dictionary mapping API names to their state info
        """
        return {
            api_name: breaker.get_state()
            for api_name, breaker in self.breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers (for testing)."""
        for breaker in self.breakers.values():
            breaker.force_close()


# Global registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    return _registry
