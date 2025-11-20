"""
Secure SQL Migration Endpoint for Supabase
WARNING: Still risky - prefer manual migrations or Supabase CLI
"""
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os
import psycopg2
from psycopg2 import sql
import re

app = FastAPI()

# Configuration
EXEC_SQL_TOKEN = os.getenv("EXEC_SQL_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # Direct postgres connection

class SQLRequest(BaseModel):
    sql: str
    dry_run: bool = True  # Default to dry run!

class MigrationRequest(BaseModel):
    """Safer: Only allow predefined migration files"""
    migration_file: str  # e.g., "setup_part1_cleanup.sql"

# Whitelist of allowed operations
ALLOWED_OPERATIONS = {
    "CREATE TABLE",
    "ALTER TABLE",
    "CREATE INDEX",
    "CREATE FUNCTION",
    "CREATE POLICY",
    "INSERT INTO",
    "UPDATE",
    "COMMENT ON"
}

# Blacklist of forbidden operations
FORBIDDEN_OPERATIONS = {
    "DROP DATABASE",
    "DROP SCHEMA",
    "DROP TABLE",  # Unless explicitly allowed
    "TRUNCATE",
    "DELETE FROM",  # Unless explicitly allowed
    "GRANT",
    "REVOKE"
}

def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validates SQL for safety.
    Returns (is_valid, error_message)
    """
    sql_upper = sql.upper()

    # Check for forbidden operations
    for forbidden in FORBIDDEN_OPERATIONS:
        if forbidden in sql_upper:
            return False, f"Forbidden operation: {forbidden}"

    # Check that at least one allowed operation is present
    has_allowed = any(allowed in sql_upper for allowed in ALLOWED_OPERATIONS)
    if not has_allowed:
        return False, "No allowed operations found"

    # Check for common SQL injection patterns
    injection_patterns = [
        r";\s*DROP",
        r";\s*DELETE",
        r"--.*DROP",
        r"/\*.*DROP.*\*/"
    ]
    for pattern in injection_patterns:
        if re.search(pattern, sql_upper):
            return False, "Potential SQL injection detected"

    return True, ""

@app.post("/exec-sql")
def exec_sql(payload: SQLRequest, authorization: str = Header(None)):
    """
    Execute SQL with safety checks.

    Default is DRY RUN - set dry_run=false to actually execute.
    """
    # 1. Authentication
    if authorization != f"Bearer {EXEC_SQL_TOKEN}":
        raise HTTPException(status_code=403, detail="Unauthorized")

    sql_text = payload.sql.strip()

    # 2. Validation
    is_valid, error = validate_sql(sql_text)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # 3. Execute (or dry run)
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        if payload.dry_run:
            # Parse only, don't execute
            cursor.execute("EXPLAIN " + sql_text)
            result = {"status": "dry_run_ok", "message": "SQL is valid"}
        else:
            # Actually execute
            cursor.execute(sql_text)
            conn.commit()
            result = {
                "status": "executed",
                "rows_affected": cursor.rowcount
            }

        cursor.close()
        conn.close()

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SQL execution failed: {str(e)}"
        )

@app.post("/exec-migration")
def exec_migration(payload: MigrationRequest, authorization: str = Header(None)):
    """
    Safer: Execute a pre-vetted migration file by name.

    Migration files must exist in ./migrations/ directory.
    """
    # 1. Authentication
    if authorization != f"Bearer {EXEC_SQL_TOKEN}":
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 2. Whitelist check
    allowed_migrations = {
        "setup_part1_cleanup.sql",
        "setup_part2_tables.sql",
        "setup_part3_functions_rls.sql",
        "setup_part4_demo_data.sql"
    }

    if payload.migration_file not in allowed_migrations:
        raise HTTPException(
            status_code=400,
            detail=f"Migration file not whitelisted: {payload.migration_file}"
        )

    # 3. Read migration file
    migration_path = f"./migrations/{payload.migration_file}"
    try:
        with open(migration_path, 'r') as f:
            sql_text = f.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Migration file not found: {migration_path}"
        )

    # 4. Execute
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(sql_text)
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "executed",
            "migration": payload.migration_file
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}

# NO "execute_sql" RPC function needed - this uses direct psycopg2
