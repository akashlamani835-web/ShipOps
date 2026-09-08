from fastapi import APIRouter

from app.api.routes.topology import router as topology_router


api_router = APIRouter()

api_router.include_router(topology_router)