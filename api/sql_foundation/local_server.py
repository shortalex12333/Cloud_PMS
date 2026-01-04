"""
LOCAL SERVER: Host SQL Foundation for testing
==============================================
Run with: python -m api.sql_foundation.local_server

Endpoints:
  POST /prepare     - Run PREPARE stage only
  POST /generate    - PREPARE + generate SQL
  POST /search      - Full PREPARE + EXECUTE
  GET  /health      - Health check
"""
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any

from .prepare import prepare, Lane
from .sql_variants import generate_sql_for_plan, SQLVariant
from .execute import search, SearchResult

# Config
PORT = int(os.environ.get("SQL_FOUNDATION_PORT", 8765))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
DEFAULT_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


class SQLFoundationHandler(BaseHTTPRequestHandler):
    """HTTP handler for SQL Foundation endpoints."""

    def _send_json(self, data: Dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def _read_json(self) -> Dict:
        """Read JSON from request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        return json.loads(body) if body else {}

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        path = urlparse(self.path).path

        if path == "/health":
            self._send_json({"status": "ok", "service": "sql-foundation"})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        path = urlparse(self.path).path

        try:
            body = self._read_json()

            if path == "/prepare":
                self._handle_prepare(body)
            elif path == "/generate":
                self._handle_generate(body)
            elif path == "/search":
                self._handle_search(body)
            else:
                self._send_json({"error": "Not found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_prepare(self, body: Dict):
        """
        POST /prepare
        Body: {query, entities, yacht_id?, user_id?, user_role?}
        Returns: ExecutionPlan summary
        """
        query = body.get("query", "")
        entities = body.get("entities", [])
        yacht_id = body.get("yacht_id", DEFAULT_YACHT_ID)
        user_id = body.get("user_id", "api")
        user_role = body.get("user_role", "engineer")

        plan = prepare(query, entities, yacht_id, user_id, user_role)

        result = {
            "lane": plan.lane.lane.value,
            "lane_reason": plan.lane.reason,
            "intent": plan.intent.value,
            "term_count": len(plan.expanded_terms),
            "terms": [
                {
                    "type": t.entity_type,
                    "value": t.original_value,
                    "variants": len(t.variants)
                }
                for t in plan.expanded_terms
            ],
            "tables_ranked": [
                {"table": t.table, "bias": t.bias}
                for t in plan.ranked_tables[:5]
            ],
            "batches": [
                {"tier": b.tier, "tables": b.tables}
                for b in plan.batches
            ],
        }

        if plan.lane.lane == Lane.BLOCKED:
            result["blocked_message"] = plan.lane.block_message
        if plan.lane.lane == Lane.UNKNOWN:
            result["suggestions"] = plan.lane.suggestions

        self._send_json(result)

    def _handle_generate(self, body: Dict):
        """
        POST /generate
        Body: {query, entities, yacht_id?, user_id?, user_role?}
        Returns: SQL variants with params
        """
        query = body.get("query", "")
        entities = body.get("entities", [])
        yacht_id = body.get("yacht_id", DEFAULT_YACHT_ID)
        user_id = body.get("user_id", "api")
        user_role = body.get("user_role", "engineer")

        plan = prepare(query, entities, yacht_id, user_id, user_role)
        variants = generate_sql_for_plan(plan)

        result = {
            "lane": plan.lane.lane.value,
            "intent": plan.intent.value,
            "sql_count": len(variants),
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "wave": v.wave,
                    "tables": v.tables,
                    "sql": v.sql,
                    "params": v.params,
                    "description": v.description
                }
                for v in variants
            ]
        }

        self._send_json(result)

    def _handle_search(self, body: Dict):
        """
        POST /search
        Body: {query, entities, yacht_id?, user_id?, user_role?}
        Returns: Search results from database
        """
        query = body.get("query", "")
        entities = body.get("entities", [])
        yacht_id = body.get("yacht_id", DEFAULT_YACHT_ID)
        user_id = body.get("user_id", "api")
        user_role = body.get("user_role", "engineer")

        result = search(
            SUPABASE_URL,
            SUPABASE_KEY,
            query,
            entities,
            yacht_id,
            user_id,
            user_role
        )

        self._send_json({
            "total_rows": result.total_rows,
            "tables_hit": result.tables_hit,
            "waves_executed": result.waves_executed,
            "total_time_ms": result.total_time_ms,
            "early_exit": result.early_exit,
            "rows": result.rows[:50],  # Limit response size
            "trace": result.trace
        })


def run_server():
    """Run the local server."""
    server = HTTPServer(("0.0.0.0", PORT), SQLFoundationHandler)
    print(f"SQL Foundation server running on http://localhost:{PORT}")
    print()
    print("Endpoints:")
    print(f"  POST http://localhost:{PORT}/prepare  - Run PREPARE stage")
    print(f"  POST http://localhost:{PORT}/generate - Generate SQL variants")
    print(f"  POST http://localhost:{PORT}/search   - Full search")
    print(f"  GET  http://localhost:{PORT}/health   - Health check")
    print()
    print("Example:")
    print(f'  curl -X POST http://localhost:{PORT}/prepare \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"query": "Generator 1", "entities": [{"type": "EQUIPMENT_NAME", "value": "Generator 1"}]}\'')
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    run_server()
