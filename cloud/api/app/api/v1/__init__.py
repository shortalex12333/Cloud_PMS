"""
API v1 Router
Aggregates all v1 endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, search, work_orders, handovers, notes, documents, integrations, actions

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(search.router)
api_router.include_router(work_orders.router)
api_router.include_router(handovers.router)
api_router.include_router(notes.router)
api_router.include_router(documents.router)
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(actions.router)
