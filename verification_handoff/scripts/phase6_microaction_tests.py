#!/usr/bin/env python3
"""
Phase 6: Microaction Execution Verification Tests
==================================================

This script tests microaction execution against a running API server.

Requirements:
- API server running at API_BASE_URL
- Valid JWT token for test yacht
- Test data in database (equipment, work orders, etc.)

Usage:
    export API_BASE_URL="https://pipeline-core.int.celeste7.ai"
    export TEST_JWT="<valid_jwt_token>"
    export TEST_YACHT_ID="<yacht_id_from_jwt>"
    export TEST_EQUIPMENT_ID="<equipment_id_belonging_to_yacht>"
    export FOREIGN_YACHT_ID="<different_yacht_id>"
    export FOREIGN_EQUIPMENT_ID="<equipment_id_from_foreign_yacht>"

    python phase6_microaction_tests.py

Author: Claude B (Security Auditor)
Date: 2026-01-21
"""

import os
import sys
import json
import time
import uuid
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime

# Try to import requests, provide instructions if not available
try:
    import requests
except ImportError:
    print("ERROR: requests library not installed")
    print("Run: pip install requests")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class TestConfig:
    """Test configuration from environment variables."""
    api_base_url: str
    jwt_token: str
    yacht_id: str
    equipment_id: str
    foreign_yacht_id: str
    foreign_equipment_id: str
    work_order_id: Optional[str] = None
    document_id: Optional[str] = None
    fault_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'TestConfig':
        """Load configuration from environment variables."""
        required_vars = [
            'API_BASE_URL',
            'TEST_JWT',
            'TEST_YACHT_ID',
            'TEST_EQUIPMENT_ID',
            'FOREIGN_YACHT_ID',
            'FOREIGN_EQUIPMENT_ID',
        ]

        missing = [v for v in required_vars if not os.getenv(v)]
        if missing:
            logger.error("Missing required environment variables:")
            for v in missing:
                logger.error(f"  - {v}")
            sys.exit(1)

        return cls(
            api_base_url=os.getenv('API_BASE_URL'),
            jwt_token=os.getenv('TEST_JWT'),
            yacht_id=os.getenv('TEST_YACHT_ID'),
            equipment_id=os.getenv('TEST_EQUIPMENT_ID'),
            foreign_yacht_id=os.getenv('FOREIGN_YACHT_ID'),
            foreign_equipment_id=os.getenv('FOREIGN_EQUIPMENT_ID'),
            work_order_id=os.getenv('TEST_WORK_ORDER_ID'),
            document_id=os.getenv('TEST_DOCUMENT_ID'),
            fault_id=os.getenv('TEST_FAULT_ID'),
        )


# ============================================================================
# TEST RESULT TRACKING
# ============================================================================

@dataclass
class TestResult:
    """Result of a single test."""
    test_name: str
    category: str  # positive, cross_yacht, ownership
    action: str
    status: str  # PASS, FAIL, SKIP, ERROR
    expected_status: int
    actual_status: int
    expected_behavior: str
    actual_behavior: str
    request_payload: Dict[str, Any]
    response_data: Optional[Dict[str, Any]]
    duration_ms: float
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_name': self.test_name,
            'category': self.category,
            'action': self.action,
            'status': self.status,
            'expected_status': self.expected_status,
            'actual_status': self.actual_status,
            'expected_behavior': self.expected_behavior,
            'actual_behavior': self.actual_behavior,
            'duration_ms': self.duration_ms,
            'error_message': self.error_message,
        }


# ============================================================================
# API CLIENT
# ============================================================================

class ActionAPIClient:
    """Client for executing actions against the API."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.endpoint = f"{config.api_base_url}/v1/actions/execute"
        self.headers = {
            'Authorization': f'Bearer {config.jwt_token}',
            'Content-Type': 'application/json',
        }

    def execute_action(
        self,
        action: str,
        context: Dict[str, Any],
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> tuple[int, Dict[str, Any], float]:
        """
        Execute an action and return (status_code, response_data, duration_ms).
        """
        request_data = {
            'action': action,
            'context': context,
            'payload': payload,
        }

        start_time = time.time()
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=request_data,
                timeout=timeout
            )
            duration_ms = (time.time() - start_time) * 1000

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {'raw': response.text}

            return response.status_code, response_data, duration_ms

        except requests.Timeout:
            duration_ms = (time.time() - start_time) * 1000
            return 504, {'error': 'Request timeout'}, duration_ms
        except requests.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            return 0, {'error': str(e)}, duration_ms


# ============================================================================
# TEST DEFINITIONS
# ============================================================================

class Phase6Tests:
    """Phase 6 microaction execution tests."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.client = ActionAPIClient(config)
        self.results: List[TestResult] = []

    def run_all_tests(self):
        """Run all Phase 6 tests."""
        logger.info("=" * 60)
        logger.info("PHASE 6: MICROACTION EXECUTION VERIFICATION")
        logger.info("=" * 60)

        # Test 1: report_fault
        self.test_report_fault_positive()
        self.test_report_fault_cross_yacht()
        self.test_report_fault_ownership()

        # Test 2: open_document (P1-001 verification)
        self.test_open_document_positive()
        self.test_open_document_cross_tenant_path()

        # Test 3: add_note (P1-002 verification)
        self.test_add_note_positive()
        self.test_add_note_ownership()

        # Test 4: add_to_handover (P1-004 verification)
        self.test_add_to_handover_positive()
        self.test_add_to_handover_ownership()

        # Test 5: update_equipment_status
        self.test_update_equipment_status_positive()

        # Print summary
        self.print_summary()

        return self.results

    # ========================================================================
    # TEST 1: report_fault
    # ========================================================================

    def test_report_fault_positive(self):
        """Test: report_fault with valid data should succeed."""
        test_name = "report_fault_positive"
        action = "report_fault"

        logger.info(f"\n[TEST] {test_name}")

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.yacht_id},
            payload={
                'equipment_id': self.config.equipment_id,
                'description': f'Phase 6 test fault - {datetime.utcnow().isoformat()}',
            }
        )

        # Expect 200 with success status
        if status == 200 and response.get('status') == 'success':
            result_status = 'PASS'
            actual_behavior = f"Fault created: {response.get('result', {}).get('fault_id', 'unknown')}"
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='positive',
            action=action,
            status=result_status,
            expected_status=200,
            actual_status=status,
            expected_behavior='Fault created successfully',
            actual_behavior=actual_behavior,
            request_payload={'yacht_id': self.config.yacht_id, 'equipment_id': self.config.equipment_id},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    def test_report_fault_cross_yacht(self):
        """Test: report_fault with mismatched yacht_id should fail."""
        test_name = "report_fault_cross_yacht"
        action = "report_fault"

        logger.info(f"\n[TEST] {test_name}")

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.foreign_yacht_id},  # Different yacht!
            payload={
                'equipment_id': self.config.equipment_id,
                'description': 'This should be rejected',
            }
        )

        # Expect 403 with yacht_mismatch error
        if status == 403 and 'yacht_mismatch' in str(response):
            result_status = 'PASS'
            actual_behavior = 'Cross-yacht access correctly rejected'
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='cross_yacht',
            action=action,
            status=result_status,
            expected_status=403,
            actual_status=status,
            expected_behavior='403 with yacht_mismatch error',
            actual_behavior=actual_behavior,
            request_payload={'yacht_id': self.config.foreign_yacht_id},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    def test_report_fault_ownership(self):
        """Test: report_fault with foreign equipment should fail (P1-003)."""
        test_name = "report_fault_ownership"
        action = "report_fault"

        logger.info(f"\n[TEST] {test_name}")

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.yacht_id},  # Correct yacht
            payload={
                'equipment_id': self.config.foreign_equipment_id,  # Foreign equipment!
                'description': 'This should be rejected - foreign equipment',
            }
        )

        # Expect 400 with "not found or access denied"
        if status == 400 and 'not found or access denied' in str(response).lower():
            result_status = 'PASS'
            actual_behavior = 'Foreign equipment correctly rejected (P1-003)'
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='ownership',
            action=action,
            status=result_status,
            expected_status=400,
            actual_status=status,
            expected_behavior='400 with "not found or access denied"',
            actual_behavior=actual_behavior,
            request_payload={'equipment_id': self.config.foreign_equipment_id},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    # ========================================================================
    # TEST 2: open_document (P1-001 verification)
    # ========================================================================

    def test_open_document_positive(self):
        """Test: open_document with valid path should succeed."""
        test_name = "open_document_positive"
        action = "open_document"

        logger.info(f"\n[TEST] {test_name}")

        # Path must start with yacht_id
        valid_path = f"{self.config.yacht_id}/test/document.pdf"

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.yacht_id},
            payload={'storage_path': valid_path}
        )

        # Could be 200 success or 404 if file doesn't exist
        # Both are valid - we're testing the yacht_id validation, not file existence
        if status == 200:
            result_status = 'PASS'
            actual_behavior = 'Signed URL generated successfully'
        elif status == 404 or (status == 500 and 'not found' in str(response).lower()):
            result_status = 'PASS'
            actual_behavior = 'File not found (expected - yacht_id validation passed)'
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='positive',
            action=action,
            status=result_status,
            expected_status=200,
            actual_status=status,
            expected_behavior='200 or 404 (yacht_id validation passed)',
            actual_behavior=actual_behavior,
            request_payload={'storage_path': valid_path},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    def test_open_document_cross_tenant_path(self):
        """Test: open_document with foreign yacht path should fail (P1-001)."""
        test_name = "open_document_cross_tenant_path"
        action = "open_document"

        logger.info(f"\n[TEST] {test_name}")

        # Path points to foreign yacht's documents
        foreign_path = f"{self.config.foreign_yacht_id}/sensitive/document.pdf"

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.yacht_id},  # Our yacht
            payload={'storage_path': foreign_path}  # Foreign yacht's path!
        )

        # Expect 400 with "Access denied: Document does not belong to your yacht"
        if status == 400 and 'does not belong to your yacht' in str(response).lower():
            result_status = 'PASS'
            actual_behavior = 'Cross-tenant path correctly rejected (P1-001)'
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='ownership',
            action=action,
            status=result_status,
            expected_status=400,
            actual_status=status,
            expected_behavior='400 with "does not belong to your yacht"',
            actual_behavior=actual_behavior,
            request_payload={'storage_path': foreign_path},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    # ========================================================================
    # TEST 3: add_note (P1-002 verification)
    # ========================================================================

    def test_add_note_positive(self):
        """Test: add_note with valid data should succeed."""
        test_name = "add_note_positive"
        action = "add_note"

        logger.info(f"\n[TEST] {test_name}")

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.yacht_id},
            payload={
                'equipment_id': self.config.equipment_id,
                'note_text': f'Phase 6 test note - {datetime.utcnow().isoformat()}',
            }
        )

        if status == 200 and response.get('status') == 'success':
            result_status = 'PASS'
            actual_behavior = f"Note created: {response.get('result', {}).get('note_id', 'unknown')}"
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='positive',
            action=action,
            status=result_status,
            expected_status=200,
            actual_status=status,
            expected_behavior='Note created successfully',
            actual_behavior=actual_behavior,
            request_payload={'equipment_id': self.config.equipment_id},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    def test_add_note_ownership(self):
        """Test: add_note with foreign equipment should fail (P1-002)."""
        test_name = "add_note_ownership"
        action = "add_note"

        logger.info(f"\n[TEST] {test_name}")

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.yacht_id},
            payload={
                'equipment_id': self.config.foreign_equipment_id,  # Foreign equipment!
                'note_text': 'This should be rejected',
            }
        )

        if status == 400 and 'not found or access denied' in str(response).lower():
            result_status = 'PASS'
            actual_behavior = 'Foreign equipment correctly rejected (P1-002)'
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='ownership',
            action=action,
            status=result_status,
            expected_status=400,
            actual_status=status,
            expected_behavior='400 with "not found or access denied"',
            actual_behavior=actual_behavior,
            request_payload={'equipment_id': self.config.foreign_equipment_id},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    # ========================================================================
    # TEST 4: add_to_handover (P1-004 verification)
    # ========================================================================

    def test_add_to_handover_positive(self):
        """Test: add_to_handover with valid data should succeed."""
        test_name = "add_to_handover_positive"
        action = "add_to_handover"

        logger.info(f"\n[TEST] {test_name}")

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.yacht_id},
            payload={
                'summary_text': f'Phase 6 test handover item - {datetime.utcnow().isoformat()}',
                'entity_type': 'equipment',
                'entity_id': self.config.equipment_id,
                'category': 'fyi',
            }
        )

        if status == 200 and response.get('status') == 'success':
            result_status = 'PASS'
            actual_behavior = f"Handover item created: {response.get('result', {}).get('handover_id', 'unknown')}"
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='positive',
            action=action,
            status=result_status,
            expected_status=200,
            actual_status=status,
            expected_behavior='Handover item created successfully',
            actual_behavior=actual_behavior,
            request_payload={'entity_id': self.config.equipment_id},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    def test_add_to_handover_ownership(self):
        """Test: add_to_handover with foreign entity should fail (P1-004)."""
        test_name = "add_to_handover_ownership"
        action = "add_to_handover"

        logger.info(f"\n[TEST] {test_name}")

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.yacht_id},
            payload={
                'summary_text': 'This should be rejected - foreign entity',
                'entity_type': 'equipment',
                'entity_id': self.config.foreign_equipment_id,  # Foreign equipment!
                'category': 'fyi',
            }
        )

        if status == 400 and 'not found or access denied' in str(response).lower():
            result_status = 'PASS'
            actual_behavior = 'Foreign entity correctly rejected (P1-004)'
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='ownership',
            action=action,
            status=result_status,
            expected_status=400,
            actual_status=status,
            expected_behavior='400 with "not found or access denied"',
            actual_behavior=actual_behavior,
            request_payload={'entity_id': self.config.foreign_equipment_id},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    # ========================================================================
    # TEST 5: update_equipment_status
    # ========================================================================

    def test_update_equipment_status_positive(self):
        """Test: update_equipment_status with valid data should succeed."""
        test_name = "update_equipment_status_positive"
        action = "update_equipment_status"

        logger.info(f"\n[TEST] {test_name}")

        status, response, duration = self.client.execute_action(
            action=action,
            context={'yacht_id': self.config.yacht_id},
            payload={
                'equipment_id': self.config.equipment_id,
                'attention_flag': True,
                'attention_reason': f'Phase 6 test - {datetime.utcnow().isoformat()}',
            }
        )

        if status == 200 and response.get('status') == 'success':
            result_status = 'PASS'
            actual_behavior = 'Equipment status updated successfully'
        else:
            result_status = 'FAIL'
            actual_behavior = f"Status {status}: {response}"

        self.results.append(TestResult(
            test_name=test_name,
            category='positive',
            action=action,
            status=result_status,
            expected_status=200,
            actual_status=status,
            expected_behavior='Equipment status updated',
            actual_behavior=actual_behavior,
            request_payload={'equipment_id': self.config.equipment_id},
            response_data=response,
            duration_ms=duration,
        ))

        logger.info(f"  Result: {result_status} ({duration:.1f}ms)")

    # ========================================================================
    # SUMMARY
    # ========================================================================

    def print_summary(self):
        """Print test summary."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == 'PASS')
        failed = sum(1 for r in self.results if r.status == 'FAIL')
        skipped = sum(1 for r in self.results if r.status == 'SKIP')

        logger.info(f"Total:   {total}")
        logger.info(f"Passed:  {passed}")
        logger.info(f"Failed:  {failed}")
        logger.info(f"Skipped: {skipped}")

        if failed > 0:
            logger.info("\nFailed Tests:")
            for r in self.results:
                if r.status == 'FAIL':
                    logger.info(f"  - {r.test_name}: {r.actual_behavior}")

        # Export results to JSON
        results_file = 'phase6_results.json'
        with open(results_file, 'w') as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)
        logger.info(f"\nResults exported to: {results_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run Phase 6 tests."""
    try:
        config = TestConfig.from_env()
    except SystemExit:
        print("\nUsage:")
        print("  export API_BASE_URL='https://pipeline-core.int.celeste7.ai'")
        print("  export TEST_JWT='<jwt_token>'")
        print("  export TEST_YACHT_ID='<yacht_id>'")
        print("  export TEST_EQUIPMENT_ID='<equipment_id>'")
        print("  export FOREIGN_YACHT_ID='<different_yacht_id>'")
        print("  export FOREIGN_EQUIPMENT_ID='<equipment_from_foreign_yacht>'")
        print("")
        print("  python phase6_microaction_tests.py")
        sys.exit(1)

    tests = Phase6Tests(config)
    results = tests.run_all_tests()

    # Exit with error code if any tests failed
    failed = sum(1 for r in results if r.status == 'FAIL')
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
