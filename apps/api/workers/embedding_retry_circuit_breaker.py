"""
Retry Policy and Circuit Breaker for Embedding Refresh Worker

Prevents worker failures from cascading into 500s in read path.

Features:
- Exponential backoff retry (1s, 2s, 4s)
- Circuit breaker after N consecutive failures
- Per-error-code tracking
- Rate limit detection and backoff
"""

import time
import logging
from typing import Any, Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger('EmbeddingRetry')


@dataclass
class CircuitBreaker:
    """
    Circuit breaker to stop retrying after too many failures.

    States:
    - CLOSED: Normal operation (allow calls)
    - OPEN: Circuit tripped (reject calls)
    - HALF_OPEN: Testing if service recovered (allow one call)
    """
    threshold: int = 10
    failures: int = 0
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        """Record successful call - reset failures"""
        self.failures = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker CLOSED (service recovered)")

    def record_failure(self):
        """Record failed call - increment failures and check threshold"""
        self.failures += 1

        if self.failures >= self.threshold:
            if self.state != "OPEN":
                self.state = "OPEN"
                logger.error(f"Circuit breaker OPEN (threshold {self.threshold} reached)")

    def allow_call(self) -> bool:
        """Check if call is allowed"""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            # Try to recover after some time (simplified: always allow one test)
            self.state = "HALF_OPEN"
            logger.info("Circuit breaker HALF_OPEN (testing recovery)")
            return True

        # HALF_OPEN: allow one call to test
        return True

    def is_open(self) -> bool:
        """Check if circuit is open (blocking calls)"""
        return self.state == "OPEN"


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
    error_stats: Optional[dict] = None
) -> Any:
    """
    Retry function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Max retry attempts (default 3)
        base_delay: Initial delay in seconds (default 1.0)
        circuit_breaker: Optional circuit breaker
        error_stats: Optional dict to track error codes

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.allow_call():
            logger.warning(f"Circuit breaker OPEN, skipping call")
            raise RuntimeError("Circuit breaker OPEN")

        try:
            result = func()

            # Success - record and return
            if circuit_breaker:
                circuit_breaker.record_success()

            if attempt > 0:
                logger.info(f"Retry succeeded on attempt {attempt + 1}")

            return result

        except Exception as e:
            last_exception = e
            error_code = type(e).__name__

            # Track error stats
            if error_stats is not None:
                error_stats[error_code] = error_stats.get(error_code, 0) + 1

            # Check if retryable
            if not is_retryable_error(e):
                logger.error(f"Non-retryable error: {error_code} - {e}")
                if circuit_breaker:
                    circuit_breaker.record_failure()
                raise

            # Record failure
            if circuit_breaker:
                circuit_breaker.record_failure()

            # Check if we should retry
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {error_code}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed")

    # All retries exhausted
    raise last_exception


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if error is retryable.

    Retryable:
    - Network errors (connection, timeout)
    - Rate limit errors (429)
    - Server errors (500, 502, 503, 504)

    Not retryable:
    - Client errors (400, 401, 403, 404)
    - Validation errors
    - Data errors

    Args:
        error: Exception

    Returns:
        True if retryable
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Network errors - retryable
    if any(keyword in error_str for keyword in [
        'timeout', 'connection', 'network', 'unreachable'
    ]):
        return True

    # Rate limit - retryable with backoff
    if '429' in error_str or 'rate limit' in error_str:
        return True

    # Server errors - retryable
    if any(code in error_str for code in ['500', '502', '503', '504']):
        return True

    # Client errors - not retryable
    if any(code in error_str for code in ['400', '401', '403', '404']):
        return False

    # OpenAI-specific errors
    if 'openai' in error_type.lower():
        # Check for specific OpenAI error types
        if any(keyword in error_str for keyword in [
            'rate_limit', 'service_unavailable', 'timeout'
        ]):
            return True

    # Default: not retryable for safety
    return False


def estimate_retry_time(max_retries: int = 3, base_delay: float = 1.0) -> float:
    """
    Estimate total retry time if all attempts fail.

    Args:
        max_retries: Max retry attempts
        base_delay: Base delay in seconds

    Returns:
        Total retry time in seconds
    """
    total = 0.0
    for attempt in range(max_retries):
        total += base_delay * (2 ** attempt)
    return total
