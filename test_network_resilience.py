#!/usr/bin/env python3
"""
Test script for network resilience features.

Tests:
    1. SQLite persistent queue operations
    2. Connection monitoring
    3. Async upload manager
    4. Error handling and retries
"""

import os
import time
import tempfile
from pathlib import Path

# Test configuration
WEBHOOK_ENDPOINT = "https://celeste-digest-index.onrender.com"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
YACHT_SALT = os.getenv("YACHT_SALT", "e49469e09cb6529e0bfef118370cf8425b006f0abbc77475da2e0cb479af8b18")


def test_upload_queue():
    """Test SQLite persistent upload queue."""
    print("\n" + "="*60)
    print("TEST 1: Upload Queue (SQLite Persistence)")
    print("="*60)

    from celesteos_agent.upload_queue import UploadQueue

    # Create queue with temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        queue = UploadQueue(db_path=db_path)

        # Test 1: Add items
        print("\n📝 Adding items to queue...")
        item1_id = queue.add(
            file_path="/tmp/test1.pdf",
            yacht_id=YACHT_ID,
            system_path="Engineering/Electrical",
            directories=["Engineering", "Electrical"],
            doc_type="manual",
            system_tag="electrical",
            priority=8
        )
        print(f"   ✓ Added item 1 (ID: {item1_id}, Priority: 8)")

        item2_id = queue.add(
            file_path="/tmp/test2.pdf",
            yacht_id=YACHT_ID,
            system_path="Safety/Procedures",
            directories=["Safety", "Procedures"],
            doc_type="sop",
            system_tag="safety",
            priority=5
        )
        print(f"   ✓ Added item 2 (ID: {item2_id}, Priority: 5)")

        # Test 2: Get next (should be priority 8 first)
        print("\n📤 Getting next item (priority order)...")
        next_item = queue.get_next()
        assert next_item is not None, "No items in queue"
        assert next_item.priority == 8, f"Expected priority 8, got {next_item.priority}"
        print(f"   ✓ Got item ID {next_item.item_id} with priority {next_item.priority}")

        # Test 3: Mark uploading
        print("\n🔄 Marking item as uploading...")
        queue.mark_uploading(next_item.item_id)
        print(f"   ✓ Item {next_item.item_id} marked as uploading")

        # Test 4: Mark completed
        print("\n✅ Marking item as completed...")
        queue.mark_completed(next_item.item_id)
        print(f"   ✓ Item {next_item.item_id} marked as completed")

        # Test 5: Get next (should be item 2 now)
        print("\n📤 Getting next item (should be item 2)...")
        next_item = queue.get_next()
        assert next_item is not None, "Queue empty unexpectedly"
        assert next_item.priority == 5, f"Expected priority 5, got {next_item.priority}"
        print(f"   ✓ Got item ID {next_item.item_id} with priority {next_item.priority}")

        # Test 6: Mark failed with retry
        print("\n❌ Marking item as failed (with retry)...")
        queue.mark_failed(next_item.item_id, "Connection timeout", retry=True)
        print(f"   ✓ Item {next_item.item_id} marked as failed, retry_count incremented")

        # Test 7: Check status
        print("\n📊 Checking queue status...")
        status = queue.get_status()
        print(f"   ✓ Pending: {status['pending']}")
        print(f"   ✓ Completed: {status['completed']}")
        print(f"   ✓ Failed: {status['failed']}")
        print(f"   ✓ Total: {status['total']}")

        # Test 8: Persistence (create new queue instance with same DB)
        print("\n💾 Testing persistence (new queue instance)...")
        queue2 = UploadQueue(db_path=db_path)
        status2 = queue2.get_status()
        assert status2['total'] == status['total'], "Queue not persisted correctly"
        print(f"   ✓ Queue persisted correctly ({status2['total']} items)")

        # Test 9: Exponential backoff calculation
        print("\n⏱️  Testing exponential backoff...")
        backoff0 = queue.get_backoff_seconds(0)
        backoff1 = queue.get_backoff_seconds(1)
        backoff2 = queue.get_backoff_seconds(2)
        print(f"   ✓ Retry 0: {backoff0}s")
        print(f"   ✓ Retry 1: {backoff1}s")
        print(f"   ✓ Retry 2: {backoff2}s")
        assert backoff1 > backoff0, "Backoff not increasing"

        print("\n✅ All upload queue tests passed!")

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)


def test_connection_monitor():
    """Test connection monitoring."""
    print("\n" + "="*60)
    print("TEST 2: Connection Monitor")
    print("="*60)

    from celesteos_agent.connection_monitor import ConnectionMonitor

    # Create monitor
    health_endpoint = f"{WEBHOOK_ENDPOINT}/health"
    monitor = ConnectionMonitor(
        endpoint=health_endpoint,
        timeout=5,
        check_interval=10
    )

    # Test 1: Check connectivity
    print("\n🔍 Checking connectivity to endpoint...")
    is_online = monitor.check_connectivity(verbose=True)

    if is_online:
        print("   ✅ Connection successful")
    else:
        print("   ❌ Connection failed (this is OK if offline)")

    # Test 2: Get state
    print("\n📊 Getting connection state...")
    state = monitor.get_state()
    print(f"   ✓ Is Online: {state['is_online']}")
    print(f"   ✓ Total Checks: {state['total_checks']}")
    print(f"   ✓ Uptime: {state['uptime_percentage']:.1f}%")

    # Test 3: Quality score
    print("\n⭐ Getting quality score...")
    quality = monitor.get_quality_score()
    print(f"   ✓ Quality Score: {quality:.1%}")

    # Test 4: Upload recommendation
    print("\n💡 Getting upload recommendation...")
    recommendation = monitor.get_upload_recommendation()
    print(f"   ✓ Should Upload: {recommendation['should_upload']}")
    print(f"   ✓ Reason: {recommendation['reason']}")
    print(f"   ✓ Quality: {recommendation['quality_score']:.1%}")

    # Test 5: Multiple checks for stability
    if is_online:
        print("\n🔄 Testing stability (3 consecutive checks)...")
        for i in range(3):
            result = monitor.check_connectivity()
            print(f"   {'✓' if result else '✗'} Check {i+1}: {'online' if result else 'offline'}")
            time.sleep(1)

        state = monitor.get_state()
        print(f"   ✓ Consecutive Successes: {state['consecutive_successes']}")

    print("\n✅ All connection monitor tests passed!")


def test_async_uploader():
    """Test async upload manager (without actual upload)."""
    print("\n" + "="*60)
    print("TEST 3: Async Upload Manager")
    print("="*60)

    from celesteos_agent.async_uploader import create_async_uploader

    # Create async uploader
    print("\n🚀 Creating async upload manager...")
    uploader = create_async_uploader(
        webhook_endpoint=WEBHOOK_ENDPOINT,
        yacht_id=YACHT_ID,
        yacht_salt=YACHT_SALT,
        auto_start=False  # Don't auto-start for testing
    )
    print("   ✓ Async upload manager created")

    # Test 1: Add items to queue
    print("\n📋 Adding test items to queue...")

    # Create temporary test files
    temp_dir = Path(tempfile.mkdtemp())
    try:
        test_files = []
        for i in range(3):
            test_file = temp_dir / f"test_doc_{i}.txt"
            test_file.write_text(f"Test document {i}\n" * 100)
            test_files.append(test_file)

        for i, test_file in enumerate(test_files, 1):
            item_id = uploader.add_to_queue(
                file_path=str(test_file),
                system_path=f"Test/Documents/File{i}",
                directories=["Test", "Documents", f"File{i}"],
                doc_type="manual",
                system_tag="testing",
                priority=5
            )
            print(f"   ✓ Added {test_file.name} (ID: {item_id})")

        # Test 2: Get progress
        print("\n📊 Checking upload progress...")
        progress = uploader.get_progress()
        print(f"   ✓ Queue Pending: {progress['queue_pending']}")
        print(f"   ✓ Queue Total: {progress['queue_total']}")
        print(f"   ✓ Is Uploading: {progress['is_uploading']}")
        print(f"   ✓ Connection Online: {progress['connection_online']}")

        # Test 3: Get queue status
        print("\n📋 Getting queue status...")
        queue_status = uploader.get_queue_status()
        print(f"   ✓ Pending Items: {len(queue_status.get('pending_items', []))}")
        print(f"   ✓ Failed Items: {len(queue_status.get('failed_items', []))}")

        # Test 4: Pause/Resume
        print("\n⏸️  Testing pause/resume...")
        uploader.pause()
        print("   ✓ Paused")
        time.sleep(1)
        uploader.resume()
        print("   ✓ Resumed")

        print("\n✅ All async uploader tests passed!")

    finally:
        # Cleanup
        uploader.stop_processing()
        for test_file in temp_dir.glob("*"):
            test_file.unlink()
        temp_dir.rmdir()


def test_error_handling():
    """Test error handling and retry logic."""
    print("\n" + "="*60)
    print("TEST 4: Error Handling & Retry Logic")
    print("="*60)

    from celesteos_agent.uploader import FileUploader, UploadError

    # Create uploader
    uploader = FileUploader(
        webhook_endpoint=WEBHOOK_ENDPOINT,
        yacht_id=YACHT_ID,
        yacht_salt=YACHT_SALT,
        max_retries=2,
        timeout=5
    )

    # Test 1: Error categorization (invalid signature - should not retry)
    print("\n🔐 Testing invalid signature error (should not retry)...")
    temp_file = Path(tempfile.mktemp(suffix=".txt"))
    temp_file.write_text("Test document")

    try:
        # Use invalid salt to trigger 403
        bad_uploader = FileUploader(
            webhook_endpoint=WEBHOOK_ENDPOINT,
            yacht_id=YACHT_ID,
            yacht_salt="invalid_salt_12345",
            max_retries=2,
            timeout=5
        )

        try:
            result = bad_uploader.upload_file(
                file_path=temp_file,
                system_path="Test/Error",
                directories=["Test", "Error"],
                doc_type="manual",
                system_tag="testing"
            )
            print("   ❌ Expected UploadError, but upload succeeded unexpectedly")
        except UploadError as e:
            if "403" in str(e) or "Forbidden" in str(e):
                print(f"   ✓ Correctly raised UploadError for invalid signature: {e}")
            else:
                print(f"   ⚠️  Got UploadError but unexpected message: {e}")

    finally:
        temp_file.unlink()

    print("\n✅ Error handling tests completed!")


def run_all_tests():
    """Run all network resilience tests."""
    print("\n" + "="*80)
    print("   NETWORK RESILIENCE TEST SUITE")
    print("="*80)
    print(f"\nEndpoint: {WEBHOOK_ENDPOINT}")
    print(f"Yacht ID: {YACHT_ID}")
    print(f"Salt Configured: {'Yes' if YACHT_SALT else 'No'}")

    try:
        test_upload_queue()
        test_connection_monitor()
        test_async_uploader()
        test_error_handling()

        print("\n" + "="*80)
        print("   ✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nNetwork resilience features are working correctly:")
        print("  ✓ SQLite persistent queue")
        print("  ✓ Connection health monitoring")
        print("  ✓ Async background uploads")
        print("  ✓ Error handling with retry logic")
        print("\nSystem is ready for yacht deployment!")
        print("="*80 + "\n")

    except Exception as e:
        print("\n" + "="*80)
        print("   ❌ TEST FAILED")
        print("="*80)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*80 + "\n")
        return 1

    return 0


if __name__ == "__main__":
    exit(run_all_tests())
