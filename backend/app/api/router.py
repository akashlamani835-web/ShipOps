from fastapi import APIRouter

from app.api.routes.events import router as events_router
from app.api.routes.rca import router as rca_router
from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.topology import router as topology_router


api_router = APIRouter()

for route in topology_router.routes:
    api_router.routes.append(route)

for route in telemetry_router.routes:
    api_router.routes.append(route)

for route in events_router.routes:
    api_router.routes.append(route)

for route in rca_router.routes:
    api_router.routes.append(route)