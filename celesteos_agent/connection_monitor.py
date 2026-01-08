"""
Connection health monitoring for network resilience.

Purpose:
    - Test connectivity before uploads (don't waste time trying when offline)
    - Monitor connection quality
    - Track connection state changes
    - Log connectivity events

Flow:
    1. Check connectivity to endpoint
    2. If online → Allow uploads
    3. If offline → Queue uploads for later
    4. Notify on state change (online → offline, offline → online)
"""

import time
import requests
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import threading


class ConnectionState:
    """Connection state tracking."""

    def __init__(self):
        self.is_online = False
        self.last_check_time: Optional[float] = None
        self.last_online_time: Optional[float] = None
        self.last_offline_time: Optional[float] = None
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.total_checks = 0
        self.total_online = 0
        self.total_offline = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'is_online': self.is_online,
            'last_check_time': self.last_check_time,
            'last_online_time': self.last_online_time,
            'last_offline_time': self.last_offline_time,
            'consecutive_failures': self.consecutive_failures,
            'consecutive_successes': self.consecutive_successes,
            'total_checks': self.total_checks,
            'uptime_percentage': (self.total_online / self.total_checks * 100) if self.total_checks > 0 else 0
        }


class ConnectionMonitor:
    """
    Monitor network connectivity to cloud endpoint.

    Features:
        - Fast connectivity checks (< 5s)
        - State change notifications
        - Connection quality metrics
        - Thread-safe operations
    """

    def __init__(
        self,
        endpoint: str,
        timeout: int = 5,
        check_interval: int = 30,
        on_state_change: Optional[Callable[[bool, bool], None]] = None
    ):
        """
        Initialize connection monitor.

        Args:
            endpoint: URL to test connectivity (e.g., https://api.celeste7.ai/health)
            timeout: Request timeout in seconds (default 5s)
            check_interval: Seconds between automatic checks (default 30s)
            on_state_change: Callback(was_online, is_online) on state change
        """
        self.endpoint = endpoint
        self.timeout = timeout
        self.check_interval = check_interval
        self.on_state_change = on_state_change

        self.state = ConnectionState()
        self._lock = threading.Lock()
        self._stop_monitoring = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

    def check_connectivity(self, verbose: bool = False) -> bool:
        """
        Test if internet connection is available.

        Args:
            verbose: Print detailed info

        Returns:
            True if online, False if offline
        """
        try:
            # Try to reach health endpoint
            response = requests.get(
                self.endpoint,
                timeout=self.timeout,
                headers={'User-Agent': 'CelesteOS-Agent/1.0'}
            )

            # Consider online if we get ANY response (even 404)
            # This means we have internet, even if endpoint is down
            is_online = True

            if verbose:
                print(f"✅ Connection OK (status {response.status_code})")

        except requests.Timeout:
            is_online = False
            if verbose:
                print(f"❌ Connection timeout (>{self.timeout}s)")

        except requests.ConnectionError as e:
            is_online = False
            if verbose:
                print(f"❌ Connection error: {e}")

        except Exception as e:
            is_online = False
            if verbose:
                print(f"❌ Unexpected error: {e}")

        # Update state
        self._update_state(is_online)

        return is_online

    def _update_state(self, is_online: bool):
        """Update connection state and trigger callbacks."""
        with self._lock:
            was_online = self.state.is_online
            now = time.time()

            # Update state
            self.state.is_online = is_online
            self.state.last_check_time = now
            self.state.total_checks += 1

            if is_online:
                self.state.last_online_time = now
                self.state.total_online += 1
                self.state.consecutive_successes += 1
                self.state.consecutive_failures = 0
            else:
                self.state.last_offline_time = now
                self.state.total_offline += 1
                self.state.consecutive_failures += 1
                self.state.consecutive_successes = 0

            # Trigger callback on state change
            if was_online != is_online and self.on_state_change:
                try:
                    self.on_state_change(was_online, is_online)
                except Exception as e:
                    print(f"⚠️  Error in state change callback: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get current connection state."""
        with self._lock:
            return self.state.to_dict()

    def wait_for_connection(self, max_wait: int = 300, check_interval: int = 10) -> bool:
        """
        Wait for connection to become available.

        Args:
            max_wait: Maximum seconds to wait (default 5 minutes)
            check_interval: Seconds between checks (default 10s)

        Returns:
            True if connected, False if timeout
        """
        start_time = time.time()
        print(f"⏳ Waiting for connection (max {max_wait}s)...")

        while time.time() - start_time < max_wait:
            if self.check_connectivity():
                print(f"✅ Connection restored!")
                return True

            # Wait before next check
            time.sleep(check_interval)
            elapsed = int(time.time() - start_time)
            print(f"   Still waiting... ({elapsed}/{max_wait}s)")

        print(f"❌ Connection timeout ({max_wait}s)")
        return False

    def start_monitoring(self):
        """Start background monitoring thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            print("⚠️  Monitoring already running")
            return

        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ConnectionMonitor"
        )
        self._monitor_thread.start()
        print(f"🔍 Started connection monitoring (interval: {self.check_interval}s)")

    def stop_monitoring(self):
        """Stop background monitoring thread."""
        if not self._monitor_thread or not self._monitor_thread.is_alive():
            return

        print("⏹  Stopping connection monitoring...")
        self._stop_monitoring.set()
        self._monitor_thread.join(timeout=10)
        print("✅ Connection monitoring stopped")

    def _monitor_loop(self):
        """Background monitoring loop."""
        while not self._stop_monitoring.is_set():
            # Check connectivity
            self.check_connectivity()

            # Wait for next check (or stop signal)
            self._stop_monitoring.wait(self.check_interval)

    def get_quality_score(self) -> float:
        """
        Get connection quality score (0.0 - 1.0).

        Based on:
            - Uptime percentage
            - Consecutive successes
            - Recent stability

        Returns:
            Quality score (1.0 = excellent, 0.0 = terrible)
        """
        with self._lock:
            if self.state.total_checks == 0:
                return 0.0

            # Base score: uptime percentage
            uptime_pct = self.state.total_online / self.state.total_checks

            # Bonus for stability (consecutive successes)
            stability_bonus = min(self.state.consecutive_successes / 10, 0.2)

            # Penalty for current offline state
            online_bonus = 0.1 if self.state.is_online else 0.0

            score = uptime_pct + stability_bonus + online_bonus
            return min(score, 1.0)

    def should_attempt_upload(self, require_quality: float = 0.5) -> bool:
        """
        Determine if upload should be attempted based on connection quality.

        Args:
            require_quality: Minimum quality score required (0.0 - 1.0)

        Returns:
            True if upload should be attempted
        """
        # Always check current connectivity first
        if not self.check_connectivity():
            return False

        # Check quality score
        quality = self.get_quality_score()
        return quality >= require_quality

    def get_upload_recommendation(self) -> Dict[str, Any]:
        """
        Get recommendation for upload timing.

        Returns:
            {
                'should_upload': bool,
                'reason': str,
                'quality_score': float,
                'wait_seconds': int (if should wait)
            }
        """
        quality = self.get_quality_score()

        if not self.state.is_online:
            return {
                'should_upload': False,
                'reason': 'Offline - connection not available',
                'quality_score': quality,
                'wait_seconds': self.check_interval
            }

        if self.state.consecutive_successes < 2:
            return {
                'should_upload': False,
                'reason': 'Connection unstable - waiting for stability',
                'quality_score': quality,
                'wait_seconds': self.check_interval * 2
            }

        if quality < 0.5:
            return {
                'should_upload': False,
                'reason': f'Connection quality too low ({quality:.1%})',
                'quality_score': quality,
                'wait_seconds': self.check_interval * 3
            }

        return {
            'should_upload': True,
            'reason': f'Connection quality good ({quality:.1%})',
            'quality_score': quality,
            'wait_seconds': 0
        }


def create_monitor(endpoint: str, auto_start: bool = True) -> ConnectionMonitor:
    """
    Convenience function to create and optionally start connection monitor.

    Args:
        endpoint: URL to monitor
        auto_start: Start monitoring automatically

    Returns:
        ConnectionMonitor instance
    """
    def on_state_change(was_online: bool, is_online: bool):
        """Log state changes."""
        if is_online and not was_online:
            print(f"🟢 Connection restored ({datetime.now().strftime('%H:%M:%S')})")
        elif not is_online and was_online:
            print(f"🔴 Connection lost ({datetime.now().strftime('%H:%M:%S')})")

    monitor = ConnectionMonitor(
        endpoint=endpoint,
        timeout=5,
        check_interval=30,
        on_state_change=on_state_change
    )

    if auto_start:
        monitor.start_monitoring()

    return monitor
