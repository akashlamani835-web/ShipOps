from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_when_dependencies_are_healthy(monkeypatch):
    """The API should report healthy when all dependencies are healthy."""
    monkeypatch.setattr("app.main.check_database_health", lambda: True)
    monkeypatch.setattr("app.main.check_redis_health", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["redis"] == "healthy"


def test_health_when_postgres_is_unhealthy(monkeypatch):
    """The API should report degraded when PostgreSQL is unavailable."""
    monkeypatch.setattr("app.main.check_database_health", lambda: False)
    monkeypatch.setattr("app.main.check_redis_health", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "degraded"
    assert data["dependencies"]["postgres"] == "unhealthy"
    assert data["dependencies"]["redis"] == "healthy"


def test_health_when_redis_is_unhealthy(monkeypatch):
    """The API should report degraded when Redis is unavailable."""
    monkeypatch.setattr("app.main.check_database_health", lambda: True)
    monkeypatch.setattr("app.main.check_redis_health", lambda: False)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "degraded"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["redis"] == "unhealthy"


def test_health_when_all_dependencies_are_unhealthy(monkeypatch):
    """The API should report degraded when all dependencies are unavailable."""
    monkeypatch.setattr("app.main.check_database_health", lambda: False)
    monkeypatch.setattr("app.main.check_redis_health", lambda: False)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "degraded"
    assert data["dependencies"]["postgres"] == "unhealthy"
    assert data["dependencies"]["redis"] == "unhealthy"