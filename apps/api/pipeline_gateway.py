"""
Pipeline Gateway
================

Routes pipeline requests through LOCAL, REMOTE, or REPLAY modes.

Environment:
- PIPELINE_MODE: local | remote | replay
- PIPELINE_REMOTE_URL: https://cloud-pms.onrender.com/search (or staging)
- PIPELINE_RECORD: 1 | 0 (record cassettes when calling remote)
- PIPELINE_REPLAY_DIR: proof/cassettes

Architecture:
- Frontend calls /api/pipeline/execute
- Gateway decides where to route based on PIPELINE_MODE
- All modes return same interface (PipelineResponse)
- REMOTE mode can record cassettes for later replay
"""

import os
import json
import httpx
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PipelineMode(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"
    REPLAY = "replay"


@dataclass
class PipelineMeta:
    """Metadata about pipeline execution."""
    mode: str
    latency_ms: int
    timestamp: str
    status_code: int
    source: str  # "local" | "render" | "cassette"
    cassette_id: Optional[str] = None


@dataclass
class PipelineResponse:
    """Standardized pipeline response."""
    success: bool
    query: str
    query_intent: Optional[Dict] = None
    ranked_groups: Optional[list] = None
    situation_seed: Optional[Dict] = None
    error: Optional[Dict] = None
    meta: Optional[PipelineMeta] = None

    def to_dict(self) -> Dict:
        result = {
            "success": self.success,
            "query": self.query,
            "query_intent": self.query_intent,
            "ranked_groups": self.ranked_groups,
            "situation_seed": self.situation_seed,
            "error": self.error,
            "meta": asdict(self.meta) if self.meta else None
        }
        return {k: v for k, v in result.items() if v is not None}


class CassetteRecorder:
    """
    Records and replays pipeline cassettes for deterministic testing.

    Cassette structure:
    proof/cassettes/<query_hash>/
        request.json
        response.json
        meta.json
    """

    def __init__(self, base_dir: str = "proof/cassettes"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _query_hash(self, query: str, context: Dict) -> str:
        """Generate deterministic hash for query + context."""
        content = json.dumps({"query": query, "context": context}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def record(
        self,
        query: str,
        context: Dict,
        request_payload: Dict,
        response_data: Dict,
        meta: Dict
    ) -> str:
        """Record a cassette and return cassette ID."""
        cassette_id = self._query_hash(query, context)
        cassette_dir = self.base_dir / cassette_id
        cassette_dir.mkdir(parents=True, exist_ok=True)

        # Write request
        with open(cassette_dir / "request.json", "w") as f:
            json.dump(request_payload, f, indent=2)

        # Write response
        with open(cassette_dir / "response.json", "w") as f:
            json.dump(response_data, f, indent=2)

        # Write meta
        meta["recorded_at"] = datetime.now(timezone.utc).isoformat()
        meta["cassette_id"] = cassette_id
        with open(cassette_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Recorded cassette: {cassette_id}")
        return cassette_id

    def replay(self, query: str, context: Dict) -> Optional[Dict]:
        """Replay a cassette if it exists."""
        cassette_id = self._query_hash(query, context)
        cassette_dir = self.base_dir / cassette_id

        response_file = cassette_dir / "response.json"
        if not response_file.exists():
            return None

        with open(response_file) as f:
            response_data = json.load(f)

        logger.info(f"Replaying cassette: {cassette_id}")
        return {
            "data": response_data,
            "cassette_id": cassette_id
        }


class PipelineGateway:
    """
    Gateway that routes pipeline requests based on mode.

    Modes:
    - LOCAL: Calls local Python pipeline functions
    - REMOTE: Calls Render production/staging endpoint
    - REPLAY: Returns recorded cassette data
    """

    def __init__(self):
        self.mode = PipelineMode(os.getenv("PIPELINE_MODE", "local"))
        self.remote_url = os.getenv(
            "PIPELINE_REMOTE_URL",
            "https://cloud-pms.onrender.com/search"
        )
        self.should_record = os.getenv("PIPELINE_RECORD", "0") == "1"
        self.replay_dir = os.getenv("PIPELINE_REPLAY_DIR", "proof/cassettes")
        self.recorder = CassetteRecorder(self.replay_dir)

        logger.info(f"Pipeline Gateway initialized: mode={self.mode}, remote={self.remote_url}")

    async def execute(
        self,
        query: str,
        context: Dict,
        auth_token: Optional[str] = None
    ) -> PipelineResponse:
        """
        Execute pipeline request through configured mode.

        Args:
            query: User search query
            context: Request context (yacht_id, user_id, etc.)
            auth_token: JWT token for authentication

        Returns:
            PipelineResponse with standardized structure
        """
        start_time = datetime.now(timezone.utc)

        try:
            if self.mode == PipelineMode.REPLAY:
                return await self._execute_replay(query, context, start_time)
            elif self.mode == PipelineMode.REMOTE:
                return await self._execute_remote(query, context, auth_token, start_time)
            else:  # LOCAL
                return await self._execute_local(query, context, start_time)
        except Exception as e:
            logger.exception(f"Pipeline execution failed: {e}")
            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return PipelineResponse(
                success=False,
                query=query,
                error={"code": "GATEWAY_ERROR", "message": str(e)},
                meta=PipelineMeta(
                    mode=self.mode.value,
                    latency_ms=latency_ms,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status_code=500,
                    source="gateway"
                )
            )

    async def _execute_local(
        self,
        query: str,
        context: Dict,
        start_time: datetime
    ) -> PipelineResponse:
        """Execute using local Python pipeline."""
        try:
            # Import local pipeline
            from unified_extraction_pipeline import get_pipeline

            pipeline = get_pipeline()
            result = await pipeline.process_query(query, context)

            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            return PipelineResponse(
                success=True,
                query=query,
                query_intent=result.get("intent"),
                ranked_groups=result.get("ranked_groups", []),
                situation_seed=result.get("situation_seed"),
                meta=PipelineMeta(
                    mode="local",
                    latency_ms=latency_ms,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status_code=200,
                    source="local"
                )
            )
        except ImportError as e:
            logger.warning(f"Local pipeline not available: {e}")
            raise Exception(f"Local pipeline not available: {e}")

    async def _execute_remote(
        self,
        query: str,
        context: Dict,
        auth_token: Optional[str],
        start_time: datetime
    ) -> PipelineResponse:
        """Execute using remote Render endpoint."""
        request_payload = {
            "query": query,
            "context": context
        }

        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.remote_url,
                json=request_payload,
                headers=headers
            )

        latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        response_data = response.json() if response.status_code == 200 else {}

        # Record cassette if enabled
        cassette_id = None
        if self.should_record:
            cassette_id = self.recorder.record(
                query=query,
                context=context,
                request_payload=request_payload,
                response_data=response_data,
                meta={
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "remote_url": self.remote_url,
                    "headers": dict(response.headers)
                }
            )

        if response.status_code != 200:
            return PipelineResponse(
                success=False,
                query=query,
                error={
                    "code": f"REMOTE_{response.status_code}",
                    "message": response_data.get("detail", "Remote pipeline error")
                },
                meta=PipelineMeta(
                    mode="remote",
                    latency_ms=latency_ms,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status_code=response.status_code,
                    source="render",
                    cassette_id=cassette_id
                )
            )

        return PipelineResponse(
            success=True,
            query=query,
            query_intent=response_data.get("query_intent") or response_data.get("intent"),
            ranked_groups=response_data.get("ranked_groups", []),
            situation_seed=response_data.get("situation_seed"),
            meta=PipelineMeta(
                mode="remote",
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status_code=200,
                source="render",
                cassette_id=cassette_id
            )
        )

    async def _execute_replay(
        self,
        query: str,
        context: Dict,
        start_time: datetime
    ) -> PipelineResponse:
        """Execute using recorded cassette."""
        replay_result = self.recorder.replay(query, context)

        if not replay_result:
            raise Exception(f"No cassette found for query: {query[:50]}...")

        response_data = replay_result["data"]
        cassette_id = replay_result["cassette_id"]

        latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        return PipelineResponse(
            success=response_data.get("success", True),
            query=query,
            query_intent=response_data.get("query_intent") or response_data.get("intent"),
            ranked_groups=response_data.get("ranked_groups", []),
            situation_seed=response_data.get("situation_seed"),
            meta=PipelineMeta(
                mode="replay",
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status_code=200,
                source="cassette",
                cassette_id=cassette_id
            )
        )


# Singleton gateway instance
_gateway: Optional[PipelineGateway] = None


def get_gateway() -> PipelineGateway:
    """Get or create pipeline gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = PipelineGateway()
    return _gateway
