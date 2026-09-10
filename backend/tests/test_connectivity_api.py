from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_get_connectivity_status_returns_link_state():
    response = client.get("/connectivity/status")

    assert response.status_code == 200

    body = response.json()

    assert body["link"]["name"] == "satellite-link"
    assert body["link"]["state"] == "available"
    assert body["link"]["capacity_kbps"] == 1_000
    assert body["link"]["available_kbps"] == 750


def test_get_connectivity_status_returns_empty_queue_initially():
    response = client.get("/connectivity/status")

    assert response.status_code == 200

    body = response.json()

    assert body["queued_traffic"] == []


def test_get_connectivity_status_returns_usage_structure():
    response = client.get("/connectivity/status")

    assert response.status_code == 200

    body = response.json()

    assert body["usage"] == {
        "requests": 0,
        "transmitted_kbps": 0,
        "throttled_kbps": 0,
        "queued_requests": 0,
        "queued_kbps": 0,
    }