import logging

from fastapi import FastAPI, Response, status

from app.api.router import api_router
from app.core.config import get_settings
from app.core.redis import check_redis_health
from app.db.database import check_database_health


logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.include_router(api_router)


@app.get("/live")
def liveness() -> dict[str, str]:
    """Confirm that the application process is alive."""
    return {
        "status": "alive",
        "service": settings.app_name,
    }


@app.get("/ready")
def readiness(response: Response) -> dict:
    """
    Confirm that the application is ready to serve normal traffic.

    Returns HTTP 503 when a required dependency is unavailable.
    """
    postgres_healthy = check_database_health()
    redis_healthy = check_redis_health()

    ready = postgres_healthy and redis_healthy

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "not_ready",
        "service": settings.app_name,
        "environment": settings.app_env,
        "dependencies": {
            "postgres": "healthy" if postgres_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
        },
    }


@app.get("/health")
def health() -> dict:
    """Return detailed application and dependency health."""
    postgres_healthy = check_database_health()
    redis_healthy = check_redis_health()

    dependencies_healthy = postgres_healthy and redis_healthy
    overall_status = "healthy" if dependencies_healthy else "degraded"

    return {
        "status": overall_status,
        "service": settings.app_name,
        "environment": settings.app_env,
        "dependencies": {
            "postgres": "healthy" if postgres_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
        },
    }