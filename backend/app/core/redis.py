import logging

from redis import Redis

from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


def check_redis_health() -> bool:
    """Return True when Redis responds to PING."""
    try:
        return bool(redis_client.ping())
    except Exception:
        logger.exception("Redis health check failed")
        return False