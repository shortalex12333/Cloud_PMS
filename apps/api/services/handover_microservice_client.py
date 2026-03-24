"""
HTTP client for the handover_export microservice.
Delegates handover transformation to the standalone microservice.

The microservice is now stateless: items in → HTML + structured data out.
All persistence (DB writes, storage uploads) is handled by Cloud_PMS.
"""
import os
import logging
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)

HANDOVER_EXPORT_SERVICE_URL = os.environ.get(
    "HANDOVER_EXPORT_SERVICE_URL", "http://localhost:10000"
)


class HandoverMicroserviceClient:
    """HTTP client for the handover-export microservice."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or HANDOVER_EXPORT_SERVICE_URL

    async def transform_handover(
        self,
        yacht_id: str,
        user_id: str,
        user_name: str,
        items: List[Dict[str, Any]],
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        yacht_name: str = "Vessel",
        doc_number: int = 1,
        user_role: str = "",
        user_department: str = "",
    ) -> Dict[str, Any]:
        """
        Call POST /api/v1/handover/transform on the microservice.

        The microservice is stateless — it receives items and returns
        rendered HTML plus structured section data. Cloud_PMS handles
        all database writes and storage uploads.

        Args:
            yacht_id: Vessel UUID
            user_id: Requesting user UUID
            user_name: Display name for the user (used in template rendering)
            items: List of handover item dicts from handover_items table
            period_start: ISO timestamp (optional)
            period_end: ISO timestamp (optional)
            yacht_name: Vessel display name (used in template header)
            doc_number: Sequential document number for this yacht
            user_role: Role of the requesting user (e.g. "captain", "chief_engineer")
            user_department: Department of the requesting user

        Returns:
            Dict with:
                html: Full rendered HTML string
                document_hash: SHA-256 hash of the document
                sections: List of section dicts, each containing:
                    bucket, display_title, items (with domain_code,
                    is_critical, requires_action, etc.)
                metadata: Dict with total_items_input, total_items_output,
                    sections_count, critical_count, generated_at
        """
        payload = {
            "yacht_id": yacht_id,
            "user_id": user_id,
            "user_name": user_name,
            "yacht_name": yacht_name,
            "doc_number": doc_number,
            "user_role": user_role,
            "user_department": user_department,
            "items": items,
        }
        if period_start:
            payload["period_start"] = period_start
        if period_end:
            payload["period_end"] = period_end

        url = f"{self.base_url}/api/v1/handover/transform"
        logger.info(
            "Calling handover microservice: %s (yacht=%s, items=%d)",
            url, yacht_id, len(items),
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

        metadata = result.get("metadata", {})
        logger.info(
            "Microservice returned: sections=%d items_out=%d critical=%d",
            metadata.get("sections_count", 0),
            metadata.get("total_items_output", 0),
            metadata.get("critical_count", 0),
        )
        return result

    async def health_check(self) -> bool:
        """Check if the microservice is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
