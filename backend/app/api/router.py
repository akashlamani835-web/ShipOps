from fastapi import APIRouter, Depends

from app.api.routes.connectivity import router as connectivity_router
from app.api.routes.events import router as events_router
from app.api.routes.rca import router as rca_router
from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.topology import router as topology_router
from app.core.security import require_api_token


api_router = APIRouter(
    dependencies=[Depends(require_api_token)],
)


api_router.include_router(topology_router)
api_router.include_router(telemetry_router)
api_router.include_router(events_router)
api_router.include_router(rca_router)
api_router.include_router(connectivity_router)