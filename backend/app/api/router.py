from fastapi import APIRouter

from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.topology import router as topology_router


api_router = APIRouter()

api_router.include_router(topology_router)
api_router.include_router(telemetry_router)