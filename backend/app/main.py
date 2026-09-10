import logging

from fastapi import FastAPI, Response, status

from app.api.router import api_router
from app.core.config import get_settings
from app.core.redis import check_redis_health
from app.db.database import check_database_health


def configure_logging() -> None:
    """Configure application-wide logging for ShipOps."""

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


configure_logging()

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

    logger.info("Liveness check requested")

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

        logger.warning(
            "Readiness check failed: postgres=%s redis=%s",
            postgres_healthy,
            redis_healthy,
        )
    else:
        logger.info("Readiness check passed")

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
    overall_status = (
        "healthy"
        if dependencies_healthy
        else "degraded"
    )

    logger.info(
        "Health check completed: status=%s postgres=%s redis=%s",
        overall_status,
        postgres_healthy,
        redis_healthy,
    )

    return {
        "status": overall_status,
        "service": settings.app_name,
        "environment": settings.app_env,
        "dependencies": {
            "postgres": "healthy"
            if postgres_healthy
            else "unhealthy",
            "redis": "healthy"
            if redis_healthy
            else "unhealthy",
        },
    }