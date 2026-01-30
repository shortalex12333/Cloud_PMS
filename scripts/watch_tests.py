#!/usr/bin/env python3
"""
Watchdog Test Runner
====================

Monitors file changes and automatically reruns targeted pytest.

Watches:
- apps/api/services/
- apps/api/handlers/related_handlers.py
- apps/api/workers/

Triggers:
- File change → Run relevant test suite
- Debounced (500ms) to avoid duplicate runs

Usage:
    python3 scripts/watch_tests.py

    # Watch specific test file
    python3 scripts/watch_tests.py --test apps/api/tests/test_worker_stale_only.py

    # Run all tests on any change
    python3 scripts/watch_tests.py --all

Dependencies:
    pip install watchdog

Exit:
    Ctrl+C to stop
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

# ANSI colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

# Project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
API_DIR = PROJECT_ROOT / "apps" / "api"
TESTS_DIR = API_DIR / "tests"

# Test mapping: file pattern → test file
TEST_MAPPING = {
    "services/embedding_text_builder.py": [
        "tests/test_worker_stale_only.py"
    ],
    "handlers/related_handlers.py": [
        "tests/test_related_shadow_logger.py"
    ],
    "handlers/work_order_handlers.py": [
        "tests/test_work_order_files_list.py"
    ],
    "actions/action_registry.py": [
        "tests/test_action_registry_signed.py"
    ],
    "workers/embedding_refresh_worker.py": [
        "tests/test_worker_stale_only.py"
    ],
}

# Debounce configuration
DEBOUNCE_SECONDS = 0.5
last_run_time = {}


class TestRunner:
    """Manages test execution."""

    def __init__(self, test_files=None, run_all=False, verbose=False):
        self.test_files = test_files
        self.run_all = run_all
        self.verbose = verbose

    def run_tests(self, test_path: str = None):
        """Run pytest with specified test file."""
        # Debounce
        now = time.time()
        key = test_path or "all"
        if key in last_run_time and (now - last_run_time[key]) < DEBOUNCE_SECONDS:
            return
        last_run_time[key] = now

        # Build command
        cmd = ["pytest", "-v"]

        if self.verbose:
            cmd.append("-s")  # Show print statements

        if test_path:
            cmd.append(str(API_DIR / test_path))
        elif self.test_files:
            for tf in self.test_files:
                cmd.append(str(API_DIR / tf))
        else:
            # Run all V2 embedding tests
            cmd.extend([
                str(TESTS_DIR / "test_action_registry_signed.py"),
                str(TESTS_DIR / "test_work_order_files_list.py"),
                str(TESTS_DIR / "test_related_shadow_logger.py"),
                str(TESTS_DIR / "test_worker_stale_only.py"),
            ])

        # Print header
        timestamp = time.strftime("%H:%M:%S")
        print(f"\n{BLUE}{'=' * 60}{NC}")
        print(f"{BLUE}[{timestamp}] Running tests...{NC}")
        if test_path:
            print(f"{CYAN}Target: {test_path}{NC}")
        print(f"{BLUE}{'=' * 60}{NC}\n")

        # Run tests
        try:
            result = subprocess.run(
                cmd,
                cwd=API_DIR,
                capture_output=False,
                text=True
            )

            # Print result
            print(f"\n{BLUE}{'=' * 60}{NC}")
            if result.returncode == 0:
                print(f"{GREEN}✓ Tests passed{NC}")
            else:
                print(f"{RED}✗ Tests failed (exit code: {result.returncode}){NC}")
            print(f"{BLUE}{'=' * 60}{NC}\n")

            print(f"{YELLOW}Watching for changes...{NC}")

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"{RED}Error running tests: {e}{NC}")


class ChangeHandler(FileSystemEventHandler):
    """Handles file system events."""

    def __init__(self, test_runner: TestRunner):
        self.test_runner = test_runner
        self.ignored_patterns = {
            "__pycache__",
            ".pyc",
            ".pytest_cache",
            ".git",
            "node_modules",
        }

    def should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        return any(pattern in path for pattern in self.ignored_patterns)

    def on_modified(self, event):
        """Handle file modification event."""
        if event.is_directory:
            return

        if self.should_ignore(event.src_path):
            return

        # Only process .py files
        if not event.src_path.endswith(".py"):
            return

        # Get relative path from API directory
        try:
            rel_path = Path(event.src_path).relative_to(API_DIR)
        except ValueError:
            return

        rel_path_str = str(rel_path)

        print(f"\n{CYAN}File changed: {rel_path_str}{NC}")

        # Run all tests if configured
        if self.test_runner.run_all:
            self.test_runner.run_tests()
            return

        # Find matching test file
        test_files = []
        for pattern, tests in TEST_MAPPING.items():
            if pattern in rel_path_str:
                test_files.extend(tests)

        if test_files:
            for test_file in set(test_files):  # Remove duplicates
                self.test_runner.run_tests(test_file)
        else:
            print(f"{YELLOW}No specific test mapping found, running all V2 tests{NC}")
            self.test_runner.run_tests()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Watch files and auto-run pytest"
    )
    parser.add_argument(
        "--test",
        "-t",
        action="append",
        help="Specific test file to run (can be specified multiple times)"
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Run all tests on any change"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose test output (show print statements)"
    )

    args = parser.parse_args()

    # Validate paths
    if not API_DIR.exists():
        print(f"{RED}Error: API directory not found: {API_DIR}{NC}")
        sys.exit(1)

    # Create test runner
    test_runner = TestRunner(
        test_files=args.test,
        run_all=args.all,
        verbose=args.verbose
    )

    # Create event handler
    event_handler = ChangeHandler(test_runner)

    # Create observer
    observer = Observer()

    # Watch paths
    watch_paths = [
        API_DIR / "services",
        API_DIR / "handlers",
        API_DIR / "workers",
        API_DIR / "actions",
    ]

    print(f"{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}Watchdog Test Runner{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")

    print(f"{YELLOW}Watching paths:{NC}")
    for path in watch_paths:
        if path.exists():
            observer.schedule(event_handler, str(path), recursive=True)
            print(f"  {path.relative_to(PROJECT_ROOT)}")
        else:
            print(f"  {RED}✗ {path.relative_to(PROJECT_ROOT)} (not found){NC}")

    print(f"\n{YELLOW}Test mapping:{NC}")
    for pattern, tests in TEST_MAPPING.items():
        print(f"  {pattern} → {', '.join(tests)}")

    print(f"\n{GREEN}Starting observer...{NC}")
    print(f"{YELLOW}Press Ctrl+C to stop{NC}\n")

    # Run tests once at startup
    print(f"{CYAN}Running initial test suite...{NC}")
    test_runner.run_tests()

    # Start observer
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Stopping observer...{NC}")
        observer.stop()

    observer.join()
    print(f"{GREEN}Exited cleanly{NC}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"{RED}Fatal error: {e}{NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
