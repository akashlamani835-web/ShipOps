from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.redis import check_redis_health
from app.db.database import check_database_health


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict:
    """Return application and dependency health."""
    postgres_healthy = check_database_health()
    redis_healthy = check_redis_health()

    dependencies_healthy = postgres_healthy and redis_healthy
    status = "healthy" if dependencies_healthy else "degraded"

    return {
        "status": status,
        "service": settings.app_name,
        "environment": settings.app_env,
        "dependencies": {
            "postgres": "healthy" if postgres_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
        },
    }