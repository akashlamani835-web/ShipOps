from fastapi.testclient import TestClient

from app.api.routes.connectivity import get_connectivity_service
from app.connectivity.models import ConnectivityState
from app.main import app


client = TestClient(app)


def reset_connectivity_service():
    service = get_connectivity_service()

    service._queue.clear()
    service.reset_usage()
    service.update_link(
        state=ConnectivityState.AVAILABLE,
        available_kbps=750,
    )


def test_get_connectivity_status_returns_link_state():
    reset_connectivity_service()

    response = client.get("/connectivity/status")

    assert response.status_code == 200

    body = response.json()

    assert body["link"]["name"] == "satellite-link"
    assert body["link"]["state"] == "available"
    assert body["link"]["capacity_kbps"] == 1_000
    assert body["link"]["available_kbps"] == 750


def test_get_connectivity_status_returns_empty_queue_initially():
    reset_connectivity_service()

    response = client.get("/connectivity/status")

    assert response.status_code == 200

    body = response.json()

    assert body["queued_traffic"] == []


def test_get_connectivity_status_returns_usage_structure():
    reset_connectivity_service()

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


def test_submit_critical_traffic_returns_transmit_decision():
    reset_connectivity_service()

    response = client.post(
        "/connectivity/traffic",
        json={
            "traffic_id": "pos-sync-001",
            "traffic_class": "critical",
            "size_kb": 500,
            "required_kbps": 100,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["traffic_id"] == "pos-sync-001"
    assert body["traffic_class"] == "critical"
    assert body["action"] == "transmit"
    assert body["allocated_kbps"] == 100


def test_submit_bulk_traffic_is_queued():
    reset_connectivity_service()

    response = client.post(
        "/connectivity/traffic",
        json={
            "traffic_id": "backup-001",
            "traffic_class": "bulk",
            "size_kb": 2_000,
            "required_kbps": 200,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["traffic_id"] == "backup-001"
    assert body["traffic_class"] == "bulk"
    assert body["action"] == "queue"
    assert body["allocated_kbps"] == 0


def test_submitted_bulk_traffic_appears_in_status_queue():
    reset_connectivity_service()

    response = client.post(
        "/connectivity/traffic",
        json={
            "traffic_id": "backup-002",
            "traffic_class": "bulk",
            "size_kb": 1_000,
            "required_kbps": 150,
        },
    )

    assert response.status_code == 200

    status_response = client.get("/connectivity/status")

    assert status_response.status_code == 200

    body = status_response.json()

    assert len(body["queued_traffic"]) == 1
    assert body["queued_traffic"][0]["traffic_id"] == "backup-002"