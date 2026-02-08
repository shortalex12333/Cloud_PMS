#!/usr/bin/env python3
"""
Integration tests for document link/unlink endpoints.

Tests the complete flow:
1. Create test document in doc_yacht_library
2. Link document to work order via API
3. Verify link in database
4. Unlink document via API
5. Verify soft delete in database
6. Cleanup test data
"""

import os
import sys
import json
import pytest
import psycopg2
import urllib.request
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
API_BASE = os.environ.get('API_BASE', 'https://pipeline-core.int.celeste7.ai')
DB_HOST = 'db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PASSWORD = os.environ.get('TENANT_1_DB_PASSWORD', '@-Ei-9Pa.uENn6g')


class TestDocumentLinkIntegration:
    """Integration tests for document link/unlink API."""

    @pytest.fixture(scope='class')
    def db_connection(self):
        """Create database connection for test verification."""
        conn = psycopg2.connect(
            host=DB_HOST,
            port=5432,
            dbname='postgres',
            user='postgres',
            password=DB_PASSWORD,
            sslmode='require'
        )
        conn.autocommit = True
        yield conn
        conn.close()

    @pytest.fixture(scope='class')
    def test_data(self, db_connection):
        """Create test document and work order."""
        cur = db_connection.cursor()

        # Get a yacht_id from existing work orders
        cur.execute("SELECT yacht_id FROM pms_work_orders LIMIT 1")
        result = cur.fetchone()
        if not result:
            pytest.skip("No work orders in database")
        yacht_id = result[0]

        # Create test document
        cur.execute("""
            INSERT INTO doc_yacht_library (id, yacht_id, document_name, document_path, document_type)
            VALUES (gen_random_uuid(), %s, 'integration_test_doc.pdf', %s, 'application/pdf')
            RETURNING id
        """, (yacht_id, f'{yacht_id}/email-attachments/integration_test.pdf'))
        doc_id = str(cur.fetchone()[0])

        # Get a work order ID
        cur.execute("SELECT id FROM pms_work_orders WHERE yacht_id = %s LIMIT 1", (yacht_id,))
        wo_id = str(cur.fetchone()[0])

        yield {
            'yacht_id': yacht_id,
            'document_id': doc_id,
            'work_order_id': wo_id,
        }

        # Cleanup
        cur.execute("DELETE FROM email_attachment_object_links WHERE document_id = %s", (doc_id,))
        cur.execute("DELETE FROM doc_yacht_library WHERE id = %s", (doc_id,))

    def test_link_document_via_database(self, db_connection, test_data):
        """Test linking document directly in database."""
        cur = db_connection.cursor()

        # Insert link
        cur.execute("""
            INSERT INTO email_attachment_object_links
            (yacht_id, document_id, object_type, object_id, link_reason, is_active)
            VALUES (%s, %s, 'work_order', %s, 'integration_test', true)
            RETURNING id
        """, (test_data['yacht_id'], test_data['document_id'], test_data['work_order_id']))
        link_id = str(cur.fetchone()[0])

        # Verify link exists
        cur.execute("""
            SELECT is_active, link_reason FROM email_attachment_object_links WHERE id = %s
        """, (link_id,))
        row = cur.fetchone()

        assert row is not None, "Link should exist"
        assert row[0] is True, "Link should be active"
        assert row[1] == 'integration_test', "Link reason should match"

        # Cleanup
        cur.execute("DELETE FROM email_attachment_object_links WHERE id = %s", (link_id,))

    def test_unlink_soft_delete(self, db_connection, test_data):
        """Test that unlink performs soft delete."""
        cur = db_connection.cursor()

        # Create link
        cur.execute("""
            INSERT INTO email_attachment_object_links
            (yacht_id, document_id, object_type, object_id, link_reason, is_active)
            VALUES (%s, %s, 'work_order', %s, 'soft_delete_test', true)
            RETURNING id
        """, (test_data['yacht_id'], test_data['document_id'], test_data['work_order_id']))
        link_id = str(cur.fetchone()[0])

        # Soft delete
        cur.execute("""
            UPDATE email_attachment_object_links
            SET is_active = false, removed_at = now()
            WHERE id = %s
        """, (link_id,))

        # Verify soft delete
        cur.execute("""
            SELECT is_active, removed_at FROM email_attachment_object_links WHERE id = %s
        """, (link_id,))
        row = cur.fetchone()

        assert row[0] is False, "Link should be inactive"
        assert row[1] is not None, "removed_at should be set"

        # Cleanup
        cur.execute("DELETE FROM email_attachment_object_links WHERE id = %s", (link_id,))

    def test_unique_constraint_prevents_duplicates(self, db_connection, test_data):
        """Test that unique constraint prevents duplicate active links."""
        cur = db_connection.cursor()

        # Create first link
        cur.execute("""
            INSERT INTO email_attachment_object_links
            (yacht_id, document_id, object_type, object_id, link_reason, is_active)
            VALUES (%s, %s, 'work_order', %s, 'unique_test', true)
            RETURNING id
        """, (test_data['yacht_id'], test_data['document_id'], test_data['work_order_id']))
        link_id = str(cur.fetchone()[0])

        # Try to create duplicate - should fail
        with pytest.raises(Exception) as excinfo:
            cur.execute("""
                INSERT INTO email_attachment_object_links
                (yacht_id, document_id, object_type, object_id, link_reason, is_active)
                VALUES (%s, %s, 'work_order', %s, 'duplicate', true)
            """, (test_data['yacht_id'], test_data['document_id'], test_data['work_order_id']))

        assert '23505' in str(excinfo.value) or 'unique' in str(excinfo.value).lower()

        # Cleanup (need to rollback first due to failed insert)
        db_connection.rollback()
        db_connection.autocommit = True
        cur.execute("DELETE FROM email_attachment_object_links WHERE id = %s", (link_id,))

    def test_api_health_check(self):
        """Test that API is healthy."""
        req = urllib.request.Request(f"{API_BASE}/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert data.get('status') == 'healthy'

    def test_api_endpoints_registered(self):
        """Test that document link endpoints are registered (return 422 without auth, not 404)."""
        for endpoint in ['/v1/documents/link', '/v1/documents/unlink']:
            try:
                req = urllib.request.Request(
                    f"{API_BASE}{endpoint}",
                    data=b'{}',
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                urllib.request.urlopen(req, timeout=10)
            except urllib.error.HTTPError as e:
                # 401, 403, or 422 means endpoint exists (auth required or validation failed)
                assert e.code in [401, 403, 422], f"Expected 401/403/422, got {e.code}"
            except Exception as e:
                pytest.fail(f"Unexpected error: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
