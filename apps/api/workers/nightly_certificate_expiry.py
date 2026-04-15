#!/usr/bin/env python3
"""
Nightly Certificate Expiry Check
=================================

Runs once daily via Render cron. For every yacht in yacht_registry, calls
the `refresh_certificate_expiry(yacht_id)` DB function, which:

1. Updates `pms_vessel_certificates` and `pms_crew_certificates` rows where
   `status = 'valid'` AND `expiry_date < CURRENT_DATE` to `status = 'expired'`.
2. Writes a `ledger_events` row for each cert flipped, with
   `event_type = 'status_change'`, `source_context = 'system'`, and a
   descriptive `change_summary`.

This closes the gap where a cert expiring Tuesday night stayed `valid`
until Wednesday morning when someone next viewed the list page. With this
worker, the flip happens at 02:15 UTC every night regardless of user activity.

ENVIRONMENT
-----------
    DATABASE_URL  - PostgreSQL DSN for the tenant DB (port 5432 preferred
                    for short-lived jobs; 6543 pooler also acceptable).

SAFETY
------
- Uses SELECT … FROM yacht_registry so the script never hardcodes a yacht id
- Calls the DB function per yacht inside its own transaction so one yacht's
  failure cannot corrupt another's flip
- Exits non-zero only if every yacht failed — partial success is logged
  and the job reports success so Render's cron retry backoff does not
  thrash on a single bad row
- Never writes to pms_vessel_certificates / pms_crew_certificates directly
  from Python; all mutations go through the DB function so the ledger
  write path is identical to the lazy-eval path
"""
from __future__ import annotations

import os
import sys
import logging
from typing import List

import psycopg2

DB_DSN = os.getenv("DATABASE_URL")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("nightly_certificate_expiry")


def _list_yachts(conn) -> List[tuple]:
    """Return [(yacht_id, name), ...] for every yacht."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM yacht_registry ORDER BY id;")
        return cur.fetchall()


def _refresh_one(conn, yacht_id: str, name: str) -> tuple[int, int]:
    """
    Call refresh_certificate_expiry(yacht_id) and return the delta counts.
    Returns (vessel_flipped, crew_flipped).
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM pms_vessel_certificates "
            "WHERE yacht_id = %s AND status = 'valid' "
            "AND expiry_date IS NOT NULL AND expiry_date < CURRENT_DATE "
            "AND deleted_at IS NULL;",
            (yacht_id,),
        )
        vessel_before = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM pms_crew_certificates "
            "WHERE yacht_id = %s AND status = 'valid' "
            "AND expiry_date IS NOT NULL AND expiry_date < CURRENT_DATE "
            "AND deleted_at IS NULL;",
            (yacht_id,),
        )
        crew_before = cur.fetchone()[0]

        cur.execute("SELECT refresh_certificate_expiry(%s);", (yacht_id,))
        conn.commit()

    logger.info(
        "yacht=%s name=%r: flipped vessel=%d crew=%d",
        yacht_id, name, vessel_before, crew_before,
    )
    return vessel_before, crew_before


def main() -> int:
    if not DB_DSN:
        logger.error("DATABASE_URL is not set — cannot run")
        return 2

    logger.info("Starting nightly certificate expiry check")

    try:
        conn = psycopg2.connect(DB_DSN)
    except Exception as e:
        logger.error("Failed to connect to DB: %s", e)
        return 2

    total_yachts = 0
    total_failures = 0
    total_vessel_flipped = 0
    total_crew_flipped = 0

    try:
        yachts = _list_yachts(conn)
        total_yachts = len(yachts)
        logger.info("Found %d yacht(s) to process", total_yachts)

        for yacht_id, name in yachts:
            try:
                v, c = _refresh_one(conn, yacht_id, name)
                total_vessel_flipped += v
                total_crew_flipped += c
            except Exception as e:
                total_failures += 1
                logger.error(
                    "Yacht %s (%s) failed: %s", yacht_id, name, e
                )
                # Roll back this one and continue with the next yacht
                try:
                    conn.rollback()
                except Exception:
                    pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

    logger.info(
        "Complete. yachts=%d failures=%d vessel_expired=%d crew_expired=%d",
        total_yachts, total_failures, total_vessel_flipped, total_crew_flipped,
    )

    # Only return non-zero if EVERY yacht failed.
    if total_yachts > 0 and total_failures == total_yachts:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
