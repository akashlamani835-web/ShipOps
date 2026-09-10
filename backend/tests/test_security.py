from fastapi.testclient import TestClient

from app.api.routes.connectivity import get_connectivity_service
from app.core.config import get_settings
from app.core.security import require_api_token
from app.main import app


client = TestClient(app)


def reset_connectivity_service():
    service = get_connectivity_service()

    service.clear_queue()
    service.reset_usage()


def test_health_endpoint_remains_public():
    response = client.get("/health")

    assert response.status_code == 200


def test_liveness_endpoint_remains_public():
    response = client.get("/live")

    assert response.status_code == 200


def test_readiness_endpoint_remains_public():
    response = client.get("/ready")

    assert response.status_code in {200, 503}


def test_protected_api_rejects_missing_credentials():
    reset_connectivity_service()

    app.dependency_overrides.pop(
        require_api_token,
        None,
    )

    try:
        response = client.get("/connectivity/status")

        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required."
    finally:
        app.dependency_overrides[require_api_token] = (
            lambda: "test-shipops-api-token"
        )


def test_protected_api_rejects_invalid_credentials():
    reset_connectivity_service()

    app.dependency_overrides.pop(
        require_api_token,
        None,
    )

    try:
        response = client.get(
            "/connectivity/status",
            headers={
                "Authorization": "Bearer invalid-token",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == (
            "Invalid authentication credentials."
        )
    finally:
        app.dependency_overrides[require_api_token] = (
            lambda: "test-shipops-api-token"
        )


def test_protected_api_accepts_valid_environment_token():
    reset_connectivity_service()

    settings = get_settings()

    app.dependency_overrides.pop(
        require_api_token,
        None,
    )

    try:
        response = client.get(
            "/connectivity/status",
            headers={
                "Authorization": f"Bearer {settings.api_token}",
            },
        )

        assert response.status_code == 200
    finally:
        app.dependency_overrides[require_api_token] = (
            lambda: "test-shipops-api-token"
        )


def test_protected_api_rejects_non_bearer_scheme():
    reset_connectivity_service()

    app.dependency_overrides.pop(
        require_api_token,
        None,
    )

    try:
        response = client.get(
            "/connectivity/status",
            headers={
                "Authorization": "Basic test-shipops-api-token",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == (
            "Authentication required."
        )
    finally:
        app.dependency_overrides[require_api_token] = (
            lambda: "test-shipops-api-token"
        )