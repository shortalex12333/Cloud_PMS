"""
Embedding Refresh Background Worker (V2)

Nightly batch refresh of stale embeddings for Show Related re-ranking.
Runs at 2am via Render cron/scheduled job.

Features:
- Staleness detection: updated_at > embedding_updated_at (or NULL)
- Equipment joins for WO context (embedding_text includes equipment name)
- Cost caps: Max embeddings per run (default 500)
- No OpenAI calls in read path (batch only)
- Retry policy: Exponential backoff with circuit breaker
- Idempotency: Process only stale candidates
- Dry-run mode: Preview changes without writing

Usage:
    python -m workers.embedding_refresh_worker
    python -m workers.embedding_refresh_worker --dry-run

Environment Variables:
    EMBEDDING_REFRESH_ENABLED=true
    EMBEDDING_REFRESH_MAX_PER_RUN=500
    EMBEDDING_REFRESH_BATCH_SIZE=50
    EMBEDDING_REFRESH_MAX_RETRIES=3
    EMBEDDING_REFRESH_CIRCUIT_BREAKER_THRESHOLD=10
    SUPABASE_URL=...
    SUPABASE_SERVICE_KEY=...
    OPENAI_API_KEY=...

Tables refreshed:
    - pms_work_orders (with equipment join for context)
    - pms_equipment
    - pms_faults (with equipment join for context)
    - pms_parts
    - pms_attachments
    - pms_work_order_notes
"""

import os
import sys
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('EmbeddingRefresh')

# Configuration
ENABLED = os.getenv('EMBEDDING_REFRESH_ENABLED', 'false').lower() == 'true'
DRY_RUN = '--dry-run' in sys.argv
MAX_PER_RUN = int(os.getenv('EMBEDDING_REFRESH_MAX_PER_RUN', '500'))
BATCH_SIZE = int(os.getenv('EMBEDDING_REFRESH_BATCH_SIZE', '50'))
MAX_RETRIES = int(os.getenv('EMBEDDING_REFRESH_MAX_RETRIES', '3'))
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv('EMBEDDING_REFRESH_CIRCUIT_BREAKER_THRESHOLD', '10'))
MODEL = "text-embedding-3-small"
DIMENSION = 1536

# Try imports
try:
    from supabase import create_client
    from openai import OpenAI
    from services.embedding_text_builder import build_embedding_text
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    logger.error(f"Required imports not available: {e}")


@dataclass
class RefreshStats:
    """Statistics for embedding refresh run."""
    work_orders: int = 0
    equipment: int = 0
    faults: int = 0
    parts: int = 0
    attachments: int = 0
    notes: int = 0
    errors: int = 0
    api_calls: int = 0
    tokens_used: int = 0
    retries: int = 0
    skipped: int = 0
    circuit_breaker_trips: int = 0
    error_by_code: Dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return (
            self.work_orders + self.equipment + self.faults +
            self.parts + self.attachments + self.notes
        )

    @property
    def cost_estimate(self) -> float:
        """Estimate cost based on tokens used ($0.02 per 1M tokens)"""
        return (self.tokens_used / 1_000_000) * 0.02

    def to_dict(self) -> Dict[str, Any]:
        return {
            'work_orders': self.work_orders,
            'equipment': self.equipment,
            'faults': self.faults,
            'parts': self.parts,
            'attachments': self.attachments,
            'notes': self.notes,
            'total': self.total,
            'errors': self.errors,
            'error_by_code': self.error_by_code,
            'api_calls': self.api_calls,
            'tokens_used': self.tokens_used,
            'cost_estimate': f"${self.cost_estimate:.4f}",
            'retries': self.retries,
            'skipped': self.skipped,
            'circuit_breaker_trips': self.circuit_breaker_trips,
        }


class EmbeddingRefreshWorker:
    """
    Batch embedding refresh worker for V2 re-ranking.

    Refreshes stale embeddings where:
    - embedding_updated_at IS NULL (never embedded), OR
    - updated_at > embedding_updated_at (content changed since last embed)

    Uses partial indexes created by V2 migration for efficient queries.
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize the worker.

        Args:
            dry_run: If True, preview changes without writing to database
        """
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        if not openai_key:
            raise ValueError("Missing OPENAI_API_KEY")

        self.supabase = create_client(supabase_url, supabase_key)
        self.openai = OpenAI(api_key=openai_key)
        self.stats = RefreshStats()
        self.remaining = MAX_PER_RUN
        self.dry_run = dry_run

        # Initialize circuit breaker
        from workers.embedding_retry_circuit_breaker import CircuitBreaker
        self.circuit_breaker = CircuitBreaker(threshold=CIRCUIT_BREAKER_THRESHOLD)

    def run(self) -> RefreshStats:
        """
        Execute batch refresh (one-shot, not continuous).

        Returns stats for logging/monitoring.
        """
        logger.info("=" * 60)
        logger.info(f"Embedding Refresh Worker Starting {'(DRY-RUN MODE)' if self.dry_run else ''}")
        logger.info(f"Max embeddings per run: {MAX_PER_RUN}")
        logger.info(f"Batch size: {BATCH_SIZE}")
        logger.info(f"Max retries: {MAX_RETRIES}")
        logger.info(f"Circuit breaker threshold: {CIRCUIT_BREAKER_THRESHOLD}")
        if self.dry_run:
            logger.info("⚠️  DRY-RUN: No database writes will occur")
        logger.info("=" * 60)

        start_time = datetime.now(timezone.utc)

        try:
            # Refresh in priority order (work orders most important)
            if self.remaining > 0:
                self._refresh_work_orders()
            if self.remaining > 0:
                self._refresh_equipment()
            if self.remaining > 0:
                self._refresh_faults()
            if self.remaining > 0:
                self._refresh_parts()
            if self.remaining > 0:
                self._refresh_attachments()
            if self.remaining > 0:
                self._refresh_notes()

        except Exception as e:
            logger.error(f"Refresh failed: {e}", exc_info=True)
            self.stats.errors += 1

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info("=" * 60)
        logger.info(f"Embedding Refresh Complete {'(DRY-RUN)' if self.dry_run else ''}")
        logger.info(f"Total refreshed: {self.stats.total}")
        logger.info(f"Errors: {self.stats.errors}")
        if self.stats.error_by_code:
            logger.info(f"Errors by code: {self.stats.error_by_code}")
        logger.info(f"Retries: {self.stats.retries}")
        logger.info(f"Circuit breaker trips: {self.stats.circuit_breaker_trips}")
        logger.info(f"API calls: {self.stats.api_calls}")
        logger.info(f"Tokens used: {self.stats.tokens_used}")
        logger.info(f"Estimated cost: ${self.stats.cost_estimate:.4f}")
        logger.info(f"Elapsed: {elapsed:.1f}s")
        logger.info("=" * 60)

        if self.dry_run:
            logger.info("DRY-RUN Summary:")
            logger.info(f"  Would have updated {self.stats.total} embeddings")
            logger.info(f"  Estimated cost: ${self.stats.cost_estimate:.4f}")

        return self.stats

    # =========================================================================
    # Work Orders (with equipment join for context)
    # =========================================================================

    def _refresh_work_orders(self):
        """Refresh stale work order embeddings."""
        logger.info("Refreshing work order embeddings...")

        limit = min(self.remaining, BATCH_SIZE)

        # Query stale work orders with equipment join for context
        # Uses idx_pms_work_orders_embedding_stale partial index
        result = self.supabase.table("pms_work_orders").select(
            "id, yacht_id, wo_number, title, description, completion_notes, updated_at,"
            "pms_equipment(name, manufacturer, model, location)"
        ).is_(
            "deleted_at", "null"
        ).or_(
            "embedding_updated_at.is.null,updated_at.gt.embedding_updated_at"
        ).order("updated_at", desc=True).limit(limit).execute()

        if not result.data:
            logger.info("No stale work orders found")
            return

        logger.info(f"Found {len(result.data)} stale work orders")

        for row in result.data:
            if self.remaining <= 0:
                break

            try:
                # Build embedding text using embedding_text_builder
                embedding_text = build_embedding_text('work_order', row)

                if not embedding_text:
                    self.stats.skipped += 1
                    continue

                if self.dry_run:
                    # Dry-run: log what would be done, skip OpenAI call and DB write
                    logger.debug(f"[DRY-RUN] Would embed WO {row['id'][:8]}...: {embedding_text[:60]}...")
                    self.stats.work_orders += 1
                    self.remaining -= 1
                    continue

                # Generate embedding
                embedding = self._generate_embedding(embedding_text)

                if not embedding:
                    self.stats.skipped += 1
                    continue

                # Update database
                self.supabase.table("pms_work_orders").update({
                    "search_embedding": embedding,
                    "embedding_text": embedding_text,
                    "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", row["id"]).eq("yacht_id", row["yacht_id"]).execute()

                self.stats.work_orders += 1
                self.remaining -= 1

            except Exception as e:
                error_code = type(e).__name__
                logger.warning(f"Failed to refresh WO {row['id']}: {error_code} - {e}")
                self.stats.errors += 1
                self.stats.error_by_code[error_code] = self.stats.error_by_code.get(error_code, 0) + 1

        logger.info(f"Refreshed {self.stats.work_orders} work orders")

    def _build_work_order_text(self, row: Dict) -> str:
        """
        Build embedding text for work order.

        Format: WO#, title, description, completion_notes + equipment context
        """
        parts = []

        wo_number = row.get("wo_number")
        if wo_number:
            parts.append(f"WO-{wo_number}")

        title = row.get("title")
        if title:
            parts.append(title)

        description = row.get("description")
        if description:
            parts.append(description)

        completion_notes = row.get("completion_notes")
        if completion_notes:
            parts.append(f"Notes: {completion_notes}")

        # Add equipment context if available
        equipment = row.get("pms_equipment")
        if equipment:
            eq_parts = []
            if equipment.get("name"):
                eq_parts.append(equipment["name"])
            if equipment.get("manufacturer"):
                eq_parts.append(equipment["manufacturer"])
            if equipment.get("model"):
                eq_parts.append(equipment["model"])
            if equipment.get("location"):
                eq_parts.append(f"Location: {equipment['location']}")
            if eq_parts:
                parts.append(f"Equipment: {' - '.join(eq_parts)}")

        return " | ".join(parts) if parts else ""

    # =========================================================================
    # Equipment
    # =========================================================================

    def _refresh_equipment(self):
        """Refresh stale equipment embeddings."""
        logger.info("Refreshing equipment embeddings...")

        limit = min(self.remaining, BATCH_SIZE)

        result = self.supabase.table("pms_equipment").select(
            "id, yacht_id, name, manufacturer, model, serial_number, location, system_type, updated_at"
        ).is_(
            "deleted_at", "null"
        ).or_(
            "embedding_updated_at.is.null,updated_at.gt.embedding_updated_at"
        ).order("updated_at", desc=True).limit(limit).execute()

        if not result.data:
            logger.info("No stale equipment found")
            return

        logger.info(f"Found {len(result.data)} stale equipment records")

        for row in result.data:
            if self.remaining <= 0:
                break

            try:
                embedding_text = self._build_equipment_text(row)

                if not embedding_text:
                    continue

                embedding = self._generate_embedding(embedding_text)

                if not embedding:
                    continue

                self.supabase.table("pms_equipment").update({
                    "search_embedding": embedding,
                    "embedding_text": embedding_text,
                    "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", row["id"]).eq("yacht_id", row["yacht_id"]).execute()

                self.stats.equipment += 1
                self.remaining -= 1

            except Exception as e:
                logger.warning(f"Failed to refresh equipment {row['id']}: {e}")
                self.stats.errors += 1

        logger.info(f"Refreshed {self.stats.equipment} equipment records")

    def _build_equipment_text(self, row: Dict) -> str:
        """Build embedding text for equipment."""
        parts = []

        if row.get("name"):
            parts.append(row["name"])
        if row.get("manufacturer"):
            parts.append(row["manufacturer"])
        if row.get("model"):
            parts.append(f"Model: {row['model']}")
        if row.get("serial_number"):
            parts.append(f"S/N: {row['serial_number']}")
        if row.get("location"):
            parts.append(f"Location: {row['location']}")
        if row.get("system_type"):
            parts.append(f"System: {row['system_type']}")

        return " | ".join(parts) if parts else ""

    # =========================================================================
    # Faults (with equipment join)
    # =========================================================================

    def _refresh_faults(self):
        """Refresh stale fault embeddings."""
        logger.info("Refreshing fault embeddings...")

        limit = min(self.remaining, BATCH_SIZE)

        result = self.supabase.table("pms_faults").select(
            "id, yacht_id, title, description, severity, status, updated_at,"
            "pms_equipment(name, manufacturer, model)"
        ).is_(
            "deleted_at", "null"
        ).or_(
            "embedding_updated_at.is.null,updated_at.gt.embedding_updated_at"
        ).order("updated_at", desc=True).limit(limit).execute()

        if not result.data:
            logger.info("No stale faults found")
            return

        logger.info(f"Found {len(result.data)} stale faults")

        for row in result.data:
            if self.remaining <= 0:
                break

            try:
                embedding_text = self._build_fault_text(row)

                if not embedding_text:
                    continue

                embedding = self._generate_embedding(embedding_text)

                if not embedding:
                    continue

                self.supabase.table("pms_faults").update({
                    "search_embedding": embedding,
                    "embedding_text": embedding_text,
                    "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", row["id"]).eq("yacht_id", row["yacht_id"]).execute()

                self.stats.faults += 1
                self.remaining -= 1

            except Exception as e:
                logger.warning(f"Failed to refresh fault {row['id']}: {e}")
                self.stats.errors += 1

        logger.info(f"Refreshed {self.stats.faults} faults")

    def _build_fault_text(self, row: Dict) -> str:
        """Build embedding text for fault."""
        parts = []

        if row.get("title"):
            parts.append(row["title"])
        if row.get("description"):
            parts.append(row["description"])
        if row.get("severity"):
            parts.append(f"Severity: {row['severity']}")
        if row.get("status"):
            parts.append(f"Status: {row['status']}")

        # Add equipment context
        equipment = row.get("pms_equipment")
        if equipment:
            eq_parts = []
            if equipment.get("name"):
                eq_parts.append(equipment["name"])
            if equipment.get("manufacturer"):
                eq_parts.append(equipment["manufacturer"])
            if equipment.get("model"):
                eq_parts.append(equipment["model"])
            if eq_parts:
                parts.append(f"Equipment: {' - '.join(eq_parts)}")

        return " | ".join(parts) if parts else ""

    # =========================================================================
    # Parts
    # =========================================================================

    def _refresh_parts(self):
        """Refresh stale part embeddings."""
        logger.info("Refreshing part embeddings...")

        limit = min(self.remaining, BATCH_SIZE)

        result = self.supabase.table("pms_parts").select(
            "id, yacht_id, name, part_number, description, manufacturer, category, updated_at"
        ).is_(
            "deleted_at", "null"
        ).or_(
            "embedding_updated_at.is.null,updated_at.gt.embedding_updated_at"
        ).order("updated_at", desc=True).limit(limit).execute()

        if not result.data:
            logger.info("No stale parts found")
            return

        logger.info(f"Found {len(result.data)} stale parts")

        for row in result.data:
            if self.remaining <= 0:
                break

            try:
                embedding_text = self._build_part_text(row)

                if not embedding_text:
                    continue

                embedding = self._generate_embedding(embedding_text)

                if not embedding:
                    continue

                self.supabase.table("pms_parts").update({
                    "search_embedding": embedding,
                    "embedding_text": embedding_text,
                    "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", row["id"]).eq("yacht_id", row["yacht_id"]).execute()

                self.stats.parts += 1
                self.remaining -= 1

            except Exception as e:
                logger.warning(f"Failed to refresh part {row['id']}: {e}")
                self.stats.errors += 1

        logger.info(f"Refreshed {self.stats.parts} parts")

    def _build_part_text(self, row: Dict) -> str:
        """Build embedding text for part."""
        parts = []

        if row.get("name"):
            parts.append(row["name"])
        if row.get("part_number"):
            parts.append(f"P/N: {row['part_number']}")
        if row.get("manufacturer"):
            parts.append(row["manufacturer"])
        if row.get("description"):
            parts.append(row["description"])
        if row.get("category"):
            parts.append(f"Category: {row['category']}")

        return " | ".join(parts) if parts else ""

    # =========================================================================
    # Attachments
    # =========================================================================

    def _refresh_attachments(self):
        """Refresh stale attachment embeddings."""
        logger.info("Refreshing attachment embeddings...")

        limit = min(self.remaining, BATCH_SIZE)

        # Uses uploaded_at instead of updated_at for staleness
        result = self.supabase.table("pms_attachments").select(
            "id, yacht_id, filename, description, mime_type, uploaded_at"
        ).is_(
            "deleted_at", "null"
        ).or_(
            "embedding_updated_at.is.null,uploaded_at.gt.embedding_updated_at"
        ).order("uploaded_at", desc=True).limit(limit).execute()

        if not result.data:
            logger.info("No stale attachments found")
            return

        logger.info(f"Found {len(result.data)} stale attachments")

        for row in result.data:
            if self.remaining <= 0:
                break

            try:
                embedding_text = self._build_attachment_text(row)

                if not embedding_text:
                    continue

                embedding = self._generate_embedding(embedding_text)

                if not embedding:
                    continue

                self.supabase.table("pms_attachments").update({
                    "search_embedding": embedding,
                    "embedding_text": embedding_text,
                    "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", row["id"]).eq("yacht_id", row["yacht_id"]).execute()

                self.stats.attachments += 1
                self.remaining -= 1

            except Exception as e:
                logger.warning(f"Failed to refresh attachment {row['id']}: {e}")
                self.stats.errors += 1

        logger.info(f"Refreshed {self.stats.attachments} attachments")

    def _build_attachment_text(self, row: Dict) -> str:
        """Build embedding text for attachment."""
        parts = []

        if row.get("filename"):
            parts.append(row["filename"])
        if row.get("description"):
            parts.append(row["description"])
        if row.get("mime_type"):
            parts.append(f"Type: {row['mime_type']}")

        return " | ".join(parts) if parts else ""

    # =========================================================================
    # Work Order Notes
    # =========================================================================

    def _refresh_notes(self):
        """Refresh stale work order note embeddings."""
        logger.info("Refreshing work order note embeddings...")

        limit = min(self.remaining, BATCH_SIZE)

        # pms_work_order_notes uses created_at for staleness (immutable)
        result = self.supabase.table("pms_work_order_notes").select(
            "id, yacht_id, note_text, created_at"
        ).or_(
            "embedding_updated_at.is.null,created_at.gt.embedding_updated_at"
        ).order("created_at", desc=True).limit(limit).execute()

        if not result.data:
            logger.info("No stale notes found")
            return

        logger.info(f"Found {len(result.data)} stale notes")

        for row in result.data:
            if self.remaining <= 0:
                break

            try:
                note_text = row.get("note_text", "").strip()

                if not note_text:
                    continue

                embedding = self._generate_embedding(note_text)

                if not embedding:
                    continue

                self.supabase.table("pms_work_order_notes").update({
                    "search_embedding": embedding,
                    "embedding_text": note_text[:1000],  # Truncate for storage
                    "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", row["id"]).eq("yacht_id", row["yacht_id"]).execute()

                self.stats.notes += 1
                self.remaining -= 1

            except Exception as e:
                logger.warning(f"Failed to refresh note {row['id']}: {e}")
                self.stats.errors += 1

        logger.info(f"Refreshed {self.stats.notes} notes")

    # =========================================================================
    # OpenAI Integration with Retry
    # =========================================================================

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding via OpenAI API with retry logic.

        Args:
            text: Text to embed (truncated to 8000 chars)

        Returns:
            1536-dimension vector or None on error
        """
        if not text or not text.strip():
            return None

        # Truncate to model limit
        text = text[:8000]

        def _call_openai():
            """Inner function for retry wrapper"""
            response = self.openai.embeddings.create(
                model=MODEL,
                input=text,
            )
            return response

        try:
            # Use retry logic from retry_circuit_breaker module
            from workers.embedding_retry_circuit_breaker import retry_with_backoff

            response = retry_with_backoff(
                func=_call_openai,
                max_retries=MAX_RETRIES,
                base_delay=1.0,
                circuit_breaker=self.circuit_breaker,
                error_stats=self.stats.error_by_code
            )

            self.stats.api_calls += 1
            self.stats.tokens_used += response.usage.total_tokens

            return response.data[0].embedding

        except Exception as e:
            error_code = type(e).__name__
            logger.warning(f"Embedding generation failed after retries: {error_code} - {e}")
            self.stats.errors += 1
            return None


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Entry point for batch refresh."""
    if not IMPORTS_AVAILABLE:
        logger.error("Required imports not available, exiting")
        sys.exit(1)

    if not ENABLED and not DRY_RUN:
        logger.warning("Embedding refresh is disabled (EMBEDDING_REFRESH_ENABLED != true)")
        logger.warning("Set EMBEDDING_REFRESH_ENABLED=true to enable")
        logger.warning("Or run with --dry-run flag to preview")
        return

    try:
        worker = EmbeddingRefreshWorker(dry_run=DRY_RUN)
        stats = worker.run()

        # Exit with error code if too many failures (not in dry-run)
        if not DRY_RUN and stats.errors > stats.total * 0.1 and stats.errors > 5:
            logger.error(f"High error rate: {stats.errors}/{stats.total}")
            sys.exit(1)

        # Dry-run always exits 0
        if DRY_RUN:
            logger.info("✅ Dry-run complete")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
