from secrets import compare_digest

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings


bearer_scheme = HTTPBearer(
    auto_error=False,
)


def require_api_token(
    credentials: HTTPAuthorizationCredentials | None = Security(
        bearer_scheme,
    ),
) -> str:
    """
    Require a valid bearer token for protected ShipOps API routes.

    The expected token is loaded from the environment through the
    application settings. Constant-time comparison is used to avoid
    leaking token information through comparison timing.
    """

    settings = get_settings()

    if not settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not compare_digest(credentials.credentials, settings.api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials