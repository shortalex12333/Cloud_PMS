"""
Tenant PostgreSQL Gateway
=========================

Direct SQL access to tenant databases, bypassing PostgREST.

Use Cases:
- Canonical reads from pms_part_stock view (avoids PostgREST 204)
- Post-RPC confirmation queries
- Any yacht-scoped SELECT where PostgREST behavior is uncertain

Architecture:
- Service role access (bypasses RLS, but handlers enforce yacht_id filtering)
- Connection per request (no pooling complexity for MVP)
- Explicit yacht_id filtering in all queries (doctrine compliance)
"""

import os
import logging
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class TenantPGGateway:
    """Direct PostgreSQL access to tenant databases."""

    @staticmethod
    def _get_connection_params(tenant_key_alias: str) -> Dict[str, str]:
        """
        Extract PG connection parameters from Supabase environment variables.

        Args:
            tenant_key_alias: e.g., 'yTEST_YACHT_001'

        Returns:
            Dict with host, port, database, user, password

        Raises:
            ValueError: If required env vars missing
        """
        # Supabase URL format: https://{ref}.supabase.co
        # PG connection: {ref}.supabase.co:5432
        url_key = f"{tenant_key_alias}_SUPABASE_URL"
        service_key = f"{tenant_key_alias}_SUPABASE_SERVICE_KEY"

        supabase_url = os.getenv(url_key)
        if not supabase_url:
            raise ValueError(f"Missing {url_key}")

        # Extract project ref from URL
        # https://vzsohavtuotocgrfkfyd.supabase.co → vzsohavtuotocgrfkfyd
        ref = supabase_url.replace("https://", "").replace("http://", "").split(".")[0]

        # Supabase connection strings use postgres user with service_role key as password
        # Connection format: postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
        return {
            "host": f"{ref}.supabase.co",
            "port": "5432",
            "database": "postgres",
            "user": "postgres",
            "password": os.getenv(service_key, ""),
        }

    @staticmethod
    @contextmanager
    def get_connection(tenant_key_alias: str):
        """
        Get a database connection for a tenant.

        Usage:
            with TenantPGGateway.get_connection('yTEST_YACHT_001') as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM pms_part_stock WHERE yacht_id = %s", (yacht_id,))
                    rows = cursor.fetchall()

        Args:
            tenant_key_alias: Tenant routing key

        Yields:
            psycopg2 connection
        """
        params = TenantPGGateway._get_connection_params(tenant_key_alias)
        conn = None

        try:
            conn = psycopg2.connect(
                host=params["host"],
                port=params["port"],
                database=params["database"],
                user=params["user"],
                password=params["password"],
                connect_timeout=10,
            )
            logger.info(f"[PGGateway] Connected to {tenant_key_alias} ({params['host']})")
            yield conn
        except psycopg2.Error as e:
            logger.error(f"[PGGateway] Connection failed for {tenant_key_alias}: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @staticmethod
    def query_one(
        tenant_key_alias: str,
        query: str,
        params: tuple,
        yacht_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute query and return single row as dict.

        Args:
            tenant_key_alias: Tenant routing key
            query: SQL with %s placeholders
            params: Query parameters
            yacht_id: Yacht ID for logging/validation

        Returns:
            Dict of column→value, or None if no rows
        """
        with TenantPGGateway.get_connection(tenant_key_alias) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()

                if row:
                    logger.info(f"[PGGateway] query_one returned row for yacht={yacht_id[:8]}...")
                    return dict(row)
                else:
                    logger.info(f"[PGGateway] query_one returned no rows for yacht={yacht_id[:8]}...")
                    return None

    @staticmethod
    def query_many(
        tenant_key_alias: str,
        query: str,
        params: tuple,
        yacht_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Execute query and return all rows as list of dicts.

        Args:
            tenant_key_alias: Tenant routing key
            query: SQL with %s placeholders
            params: Query parameters
            yacht_id: Yacht ID for logging/validation

        Returns:
            List of dicts (empty list if no rows)
        """
        with TenantPGGateway.get_connection(tenant_key_alias) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                logger.info(f"[PGGateway] query_many returned {len(rows)} rows for yacht={yacht_id[:8]}...")
                return [dict(row) for row in rows]


# Convenience functions for common queries

def get_part_stock(
    tenant_key_alias: str,
    yacht_id: str,
    part_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get part stock from canonical pms_part_stock view.

    Returns:
        Dict with keys: part_id, part_name, on_hand, min_level, stock_id, etc.
        None if part not found
    """
    query = """
        SELECT
            yacht_id,
            part_id,
            part_name,
            part_number,
            on_hand,
            min_level,
            reorder_multiple,
            location,
            is_critical,
            department,
            category,
            stock_id
        FROM public.pms_part_stock
        WHERE yacht_id = %s AND part_id = %s
        LIMIT 1
    """
    return TenantPGGateway.query_one(
        tenant_key_alias,
        query,
        (yacht_id, part_id),
        yacht_id,
    )
