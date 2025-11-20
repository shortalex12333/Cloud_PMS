"""
Predictive Maintenance Worker

Background worker that runs predictive maintenance computations:
- 6-hour scheduled runs (cron mode)
- On-demand triggers (manual mode)
- Post-indexing triggers

This worker:
1. Computes risk scores for all equipment
2. Detects anomalies
3. Generates insights
4. Saves results to database

Can be run as:
- Standalone cron job
- Triggered by n8n workflow
- Kubernetes CronJob
- Docker container with scheduler
"""

import logging
import asyncio
import os
from datetime import datetime
from typing import List
from uuid import UUID

from services.scoring import RiskScorer
from services.insights import InsightGenerator
from db.supabase import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PredictiveWorker:
    """Background worker for predictive maintenance computations"""

    def __init__(self):
        self.scorer = RiskScorer()
        self.insight_generator = InsightGenerator()
        self.db = db

    async def get_all_yachts(self) -> List[dict]:
        """Get all active yachts from database"""
        try:
            response = self.db.client.table("yachts").select("*").eq("status", "active").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching yachts: {e}")
            return []

    async def process_yacht(self, yacht_id: UUID, force_recalculate: bool = False):
        """
        Process a single yacht: compute risks and generate insights.

        Args:
            yacht_id: Yacht UUID
            force_recalculate: Force recalculation even if recently updated
        """
        logger.info(f"Processing yacht {yacht_id}")

        try:
            # Step 1: Compute risk scores for all equipment
            logger.info(f"Computing risk scores for yacht {yacht_id}")
            risk_result = await self.scorer.compute_risk_for_yacht(
                yacht_id,
                force_recalculate
            )

            logger.info(
                f"Risk computation complete: {risk_result['total_equipment']} equipment, "
                f"{risk_result['high_risk_count']} high risk"
            )

            # Step 2: Generate insights
            logger.info(f"Generating insights for yacht {yacht_id}")
            insights_result = await self.insight_generator.generate_insights_for_yacht(
                yacht_id,
                min_severity="low"
            )

            logger.info(
                f"Insights generation complete: {insights_result['total_insights']} insights, "
                f"{insights_result['critical_count']} critical"
            )

            return {
                "yacht_id": str(yacht_id),
                "success": True,
                "risk_summary": {
                    "total_equipment": risk_result["total_equipment"],
                    "high_risk_count": risk_result["high_risk_count"],
                    "emerging_risk_count": risk_result["emerging_risk_count"]
                },
                "insights_summary": {
                    "total_insights": insights_result["total_insights"],
                    "critical_count": insights_result["critical_count"],
                    "high_count": insights_result["high_count"]
                }
            }

        except Exception as e:
            logger.error(f"Error processing yacht {yacht_id}: {e}", exc_info=True)
            return {
                "yacht_id": str(yacht_id),
                "success": False,
                "error": str(e)
            }

    async def run_for_all_yachts(self, force_recalculate: bool = False):
        """
        Run predictive maintenance for all active yachts.

        This is the main cron job entry point.
        """
        logger.info("Starting predictive maintenance worker for all yachts")
        start_time = datetime.now()

        # Get all active yachts
        yachts = await self.get_all_yachts()
        logger.info(f"Found {len(yachts)} active yachts to process")

        if not yachts:
            logger.warning("No active yachts found")
            return

        # Process each yacht
        results = []
        for yacht in yachts:
            yacht_id = UUID(yacht["id"])
            result = await self.process_yacht(yacht_id, force_recalculate)
            results.append(result)

            # Add small delay between yachts to avoid overload
            await asyncio.sleep(2)

        # Summary
        successful = len([r for r in results if r["success"]])
        failed = len([r for r in results if not r["success"]])

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Predictive maintenance worker complete: "
            f"{successful} successful, {failed} failed, "
            f"duration: {duration:.1f}s"
        )

        return {
            "total_yachts": len(yachts),
            "successful": successful,
            "failed": failed,
            "duration_seconds": duration,
            "results": results
        }

    async def run_for_yacht(self, yacht_id: str, force_recalculate: bool = False):
        """
        Run predictive maintenance for a specific yacht.

        Args:
            yacht_id: Yacht ID (string)
            force_recalculate: Force recalculation
        """
        yacht_uuid = UUID(yacht_id)
        return await self.process_yacht(yacht_uuid, force_recalculate)


async def main():
    """Main entry point for worker"""
    import sys

    worker = PredictiveWorker()

    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "run-all":
            # Run for all yachts
            force = "--force" in sys.argv
            await worker.run_for_all_yachts(force_recalculate=force)

        elif command == "run-yacht":
            # Run for specific yacht
            if len(sys.argv) < 3:
                logger.error("Usage: python worker.py run-yacht <yacht_id> [--force]")
                sys.exit(1)

            yacht_id = sys.argv[2]
            force = "--force" in sys.argv
            await worker.run_for_yacht(yacht_id, force_recalculate=force)

        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Available commands: run-all, run-yacht")
            sys.exit(1)
    else:
        # Default: run for all yachts
        await worker.run_for_all_yachts()


if __name__ == "__main__":
    asyncio.run(main())
