"""
Supabase Database Connection

Handles connection to Supabase Postgres database with pgvector support.
Provides query methods for predictive maintenance operations.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import logging

from supabase import create_client, Client
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)


class SupabaseDB:
    """Supabase database client for predictive maintenance"""

    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        self.client: Client = create_client(self.url, self.key)
        logger.info("Supabase client initialized")

    # ===== EQUIPMENT QUERIES =====

    async def get_equipment_by_yacht(self, yacht_id: UUID) -> List[Dict[str, Any]]:
        """Get all equipment for a yacht"""
        try:
            response = self.client.table("equipment").select("*").eq("yacht_id", str(yacht_id)).execute()
            return response.data
        except APIError as e:
            logger.error(f"Error fetching equipment: {e}")
            return []

    async def get_equipment_by_id(self, equipment_id: UUID) -> Optional[Dict[str, Any]]:
        """Get specific equipment by ID"""
        try:
            response = self.client.table("equipment").select("*").eq("id", str(equipment_id)).single().execute()
            return response.data
        except APIError as e:
            logger.error(f"Error fetching equipment {equipment_id}: {e}")
            return None

    # ===== FAULT QUERIES =====

    async def get_faults_by_equipment(
        self,
        equipment_id: UUID,
        days_back: int = 365
    ) -> List[Dict[str, Any]]:
        """Get faults for equipment within time period"""
        try:
            cutoff = datetime.now() - timedelta(days=days_back)
            response = (
                self.client.table("faults")
                .select("*")
                .eq("equipment_id", str(equipment_id))
                .gte("detected_at", cutoff.isoformat())
                .order("detected_at", desc=True)
                .execute()
            )
            return response.data
        except APIError as e:
            logger.error(f"Error fetching faults: {e}")
            return []

    async def get_faults_by_yacht(
        self,
        yacht_id: UUID,
        days_back: int = 365
    ) -> List[Dict[str, Any]]:
        """Get all faults for a yacht within time period"""
        try:
            cutoff = datetime.now() - timedelta(days=days_back)
            response = (
                self.client.table("faults")
                .select("*")
                .eq("yacht_id", str(yacht_id))
                .gte("detected_at", cutoff.isoformat())
                .execute()
            )
            return response.data
        except APIError as e:
            logger.error(f"Error fetching yacht faults: {e}")
            return []

    # ===== WORK ORDER QUERIES =====

    async def get_work_orders_by_equipment(
        self,
        equipment_id: UUID,
        days_back: int = 365
    ) -> List[Dict[str, Any]]:
        """Get work orders for equipment"""
        try:
            cutoff = datetime.now() - timedelta(days=days_back)
            response = (
                self.client.table("work_orders")
                .select("*")
                .eq("equipment_id", str(equipment_id))
                .gte("created_at", cutoff.isoformat())
                .execute()
            )
            return response.data
        except APIError as e:
            logger.error(f"Error fetching work orders: {e}")
            return []

    async def get_work_order_history(
        self,
        equipment_id: UUID,
        days_back: int = 365
    ) -> List[Dict[str, Any]]:
        """Get work order history for equipment"""
        try:
            cutoff = datetime.now() - timedelta(days=days_back)
            response = (
                self.client.table("work_order_history")
                .select("*")
                .eq("equipment_id", str(equipment_id))
                .gte("completed_at", cutoff.isoformat())
                .order("completed_at", desc=True)
                .execute()
            )
            return response.data
        except APIError as e:
            logger.error(f"Error fetching work order history: {e}")
            return []

    # ===== PARTS & INVENTORY QUERIES =====

    async def get_part_usage_by_equipment(
        self,
        equipment_id: UUID,
        days_back: int = 365
    ) -> List[Dict[str, Any]]:
        """Get parts used on equipment from work order history"""
        try:
            history = await self.get_work_order_history(equipment_id, days_back)
            part_usage = []
            for record in history:
                if record.get("parts_used"):
                    part_usage.append({
                        "completed_at": record["completed_at"],
                        "parts": record["parts_used"]
                    })
            return part_usage
        except Exception as e:
            logger.error(f"Error fetching part usage: {e}")
            return []

    async def get_stock_levels_by_yacht(self, yacht_id: UUID) -> List[Dict[str, Any]]:
        """Get current stock levels for yacht"""
        try:
            response = self.client.table("stock_levels").select("*").eq("yacht_id", str(yacht_id)).execute()
            return response.data
        except APIError as e:
            logger.error(f"Error fetching stock levels: {e}")
            return []

    # ===== SEARCH QUERY ANALYSIS (Crew Pain Index) =====

    async def get_search_queries_by_equipment(
        self,
        yacht_id: UUID,
        equipment_id: Optional[UUID] = None,
        days_back: int = 90
    ) -> List[Dict[str, Any]]:
        """Get search queries related to equipment"""
        try:
            cutoff = datetime.now() - timedelta(days=days_back)
            query = (
                self.client.table("search_queries")
                .select("*")
                .eq("yacht_id", str(yacht_id))
                .gte("created_at", cutoff.isoformat())
            )

            # Note: Filtering by equipment_id in entities is complex
            # This simplified version gets all queries, filtering happens in signal processor
            response = query.execute()
            return response.data
        except APIError as e:
            logger.error(f"Error fetching search queries: {e}")
            return []

    # ===== NOTES QUERIES =====

    async def get_notes_by_equipment(
        self,
        equipment_id: UUID,
        days_back: int = 365
    ) -> List[Dict[str, Any]]:
        """Get notes related to equipment"""
        try:
            cutoff = datetime.now() - timedelta(days=days_back)
            # Assuming notes table has equipment_id field
            response = (
                self.client.table("notes")
                .select("*")
                .eq("equipment_id", str(equipment_id))
                .gte("created_at", cutoff.isoformat())
                .execute()
            )
            return response.data
        except APIError as e:
            logger.error(f"Error fetching notes: {e}")
            return []

    # ===== GRAPH QUERIES =====

    async def get_graph_edges_for_equipment(
        self,
        equipment_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get graph edges related to equipment"""
        try:
            # Get edges where equipment is source or target
            response = self.client.rpc(
                "get_equipment_graph_edges",
                {"p_equipment_id": str(equipment_id)}
            ).execute()
            return response.data if response.data else []
        except APIError as e:
            logger.warning(f"Graph RPC not available or error: {e}")
            return []

    # ===== PREDICTIVE STATE OPERATIONS =====

    async def save_risk_state(self, risk_data: Dict[str, Any]) -> bool:
        """Save or update risk state for equipment"""
        try:
            # Upsert (insert or update)
            response = (
                self.client.table("predictive_state")
                .upsert(risk_data, on_conflict="yacht_id,equipment_id")
                .execute()
            )
            return True
        except APIError as e:
            logger.error(f"Error saving risk state: {e}")
            return False

    async def get_risk_state_by_yacht(self, yacht_id: UUID) -> List[Dict[str, Any]]:
        """Get all risk states for a yacht"""
        try:
            response = (
                self.client.table("predictive_state")
                .select("*")
                .eq("yacht_id", str(yacht_id))
                .order("risk_score", desc=True)
                .execute()
            )
            return response.data
        except APIError as e:
            logger.error(f"Error fetching risk state: {e}")
            return []

    async def get_risk_state_by_equipment(
        self,
        equipment_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get risk state for specific equipment"""
        try:
            response = (
                self.client.table("predictive_state")
                .select("*")
                .eq("equipment_id", str(equipment_id))
                .single()
                .execute()
            )
            return response.data
        except APIError as e:
            logger.error(f"Error fetching equipment risk state: {e}")
            return None

    # ===== PREDICTIVE INSIGHTS OPERATIONS =====

    async def save_insight(self, insight_data: Dict[str, Any]) -> bool:
        """Save predictive insight"""
        try:
            response = self.client.table("predictive_insights").insert(insight_data).execute()
            return True
        except APIError as e:
            logger.error(f"Error saving insight: {e}")
            return False

    async def get_insights_by_yacht(
        self,
        yacht_id: UUID,
        min_severity: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get predictive insights for yacht"""
        try:
            query = (
                self.client.table("predictive_insights")
                .select("*")
                .eq("yacht_id", str(yacht_id))
                .order("created_at", desc=True)
                .limit(limit)
            )

            if min_severity:
                severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
                min_val = severity_order.get(min_severity, 1)
                # Note: This would require a custom RPC or post-processing
                # For now, we fetch all and filter client-side

            response = query.execute()
            return response.data
        except APIError as e:
            logger.error(f"Error fetching insights: {e}")
            return []

    # ===== FLEET-LEVEL QUERIES (Global/Anonymized) =====

    async def get_fleet_statistics(
        self,
        equipment_class: str,
        manufacturer: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get anonymized fleet statistics for equipment class"""
        try:
            # This would use a custom RPC function to compute fleet averages
            # while maintaining yacht privacy
            response = self.client.rpc(
                "get_fleet_stats",
                {
                    "p_equipment_class": equipment_class,
                    "p_manufacturer": manufacturer
                }
            ).execute()
            return response.data if response.data else None
        except APIError as e:
            logger.warning(f"Fleet stats RPC not available: {e}")
            return None


# Global instance
db = SupabaseDB()
