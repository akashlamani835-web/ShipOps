from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_liveness():
    response = client.get("/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
        "service": "ShipOps API",
    }


def test_readiness_when_dependencies_are_healthy(monkeypatch):
    monkeypatch.setattr("app.main.check_database_health", lambda: True)
    monkeypatch.setattr("app.main.check_redis_health", lambda: True)

    response = client.get("/ready")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ready"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["redis"] == "healthy"


def test_readiness_when_postgres_is_unhealthy(monkeypatch):
    monkeypatch.setattr("app.main.check_database_health", lambda: False)
    monkeypatch.setattr("app.main.check_redis_health", lambda: True)

    response = client.get("/ready")

    assert response.status_code == 503

    data = response.json()

    assert data["status"] == "not_ready"
    assert data["dependencies"]["postgres"] == "unhealthy"
    assert data["dependencies"]["redis"] == "healthy"


def test_readiness_when_redis_is_unhealthy(monkeypatch):
    monkeypatch.setattr("app.main.check_database_health", lambda: True)
    monkeypatch.setattr("app.main.check_redis_health", lambda: False)

    response = client.get("/ready")

    assert response.status_code == 503

    data = response.json()

    assert data["status"] == "not_ready"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["redis"] == "unhealthy"


def test_health_when_dependencies_are_healthy(monkeypatch):
    monkeypatch.setattr("app.main.check_database_health", lambda: True)
    monkeypatch.setattr("app.main.check_redis_health", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["redis"] == "healthy"


def test_health_when_postgres_is_unhealthy(monkeypatch):
    monkeypatch.setattr("app.main.check_database_health", lambda: False)
    monkeypatch.setattr("app.main.check_redis_health", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "degraded"
    assert data["dependencies"]["postgres"] == "unhealthy"
    assert data["dependencies"]["redis"] == "healthy"


def test_health_when_redis_is_unhealthy(monkeypatch):
    monkeypatch.setattr("app.main.check_database_health", lambda: True)
    monkeypatch.setattr("app.main.check_redis_health", lambda: False)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "degraded"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["redis"] == "unhealthy"