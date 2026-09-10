from fastapi.testclient import TestClient

from app.api.routes.connectivity import get_connectivity_service
from app.connectivity.models import ConnectivityState
from app.main import app


client = TestClient(app)


def reset_connectivity_service():
    service = get_connectivity_service()

    service.clear_queue()
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


def test_submit_bulk_traffic_is_queued_when_connectivity_is_degraded():
    reset_connectivity_service()

    link_response = client.post(
        "/connectivity/link",
        params={
            "state": "degraded",
            "available_kbps": 300,
        },
    )

    assert link_response.status_code == 200

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

    link_response = client.post(
        "/connectivity/link",
        params={
            "state": "degraded",
            "available_kbps": 300,
        },
    )

    assert link_response.status_code == 200

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


def test_update_link_to_degraded_state():
    reset_connectivity_service()

    response = client.post(
        "/connectivity/link",
        params={
            "state": "degraded",
            "available_kbps": 300,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["name"] == "satellite-link"
    assert body["state"] == "degraded"
    assert body["capacity_kbps"] == 1_000
    assert body["available_kbps"] == 300


def test_update_link_to_unavailable_state():
    reset_connectivity_service()

    response = client.post(
        "/connectivity/link",
        params={
            "state": "unavailable",
            "available_kbps": 0,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["state"] == "unavailable"
    assert body["available_kbps"] == 0


def test_link_update_persists_across_status_requests():
    reset_connectivity_service()

    update_response = client.post(
        "/connectivity/link",
        params={
            "state": "degraded",
            "available_kbps": 250,
        },
    )

    assert update_response.status_code == 200

    status_response = client.get("/connectivity/status")

    assert status_response.status_code == 200

    body = status_response.json()

    assert body["link"]["state"] == "degraded"
    assert body["link"]["available_kbps"] == 250


def test_retry_empty_queue_returns_no_decisions():
    reset_connectivity_service()

    response = client.post("/connectivity/retry")

    assert response.status_code == 200

    body = response.json()

    assert body["decisions"] == []
    assert body["queued_traffic_count"] == 0


def test_retry_transmits_queued_traffic_after_connectivity_recovers():
    reset_connectivity_service()

    unavailable_response = client.post(
        "/connectivity/link",
        params={
            "state": "unavailable",
            "available_kbps": 0,
        },
    )

    assert unavailable_response.status_code == 200

    traffic_response = client.post(
        "/connectivity/traffic",
        json={
            "traffic_id": "recovery-001",
            "traffic_class": "normal",
            "size_kb": 500,
            "required_kbps": 100,
        },
    )

    assert traffic_response.status_code == 200
    assert traffic_response.json()["action"] == "queue"

    recovery_response = client.post(
        "/connectivity/link",
        params={
            "state": "available",
            "available_kbps": 750,
        },
    )

    assert recovery_response.status_code == 200

    retry_response = client.post("/connectivity/retry")

    assert retry_response.status_code == 200

    body = retry_response.json()

    assert len(body["decisions"]) == 1
    assert body["decisions"][0]["traffic_id"] == "recovery-001"
    assert body["decisions"][0]["action"] == "transmit"
    assert body["decisions"][0]["allocated_kbps"] == 100
    assert body["queued_traffic_count"] == 0


def test_retry_keeps_traffic_queued_when_connectivity_remains_unavailable():
    reset_connectivity_service()

    unavailable_response = client.post(
        "/connectivity/link",
        params={
            "state": "unavailable",
            "available_kbps": 0,
        },
    )

    assert unavailable_response.status_code == 200

    traffic_response = client.post(
        "/connectivity/traffic",
        json={
            "traffic_id": "recovery-002",
            "traffic_class": "high",
            "size_kb": 500,
            "required_kbps": 100,
        },
    )

    assert traffic_response.status_code == 200
    assert traffic_response.json()["action"] == "queue"

    retry_response = client.post("/connectivity/retry")

    assert retry_response.status_code == 200

    body = retry_response.json()

    assert len(body["decisions"]) == 1
    assert body["decisions"][0]["traffic_id"] == "recovery-002"
    assert body["decisions"][0]["action"] == "queue"
    assert body["decisions"][0]["allocated_kbps"] == 0
    assert body["queued_traffic_count"] == 1


def test_run_connectivity_simulation_returns_full_scenario():
    reset_connectivity_service()

    response = client.post("/connectivity/simulate")

    assert response.status_code == 200

    body = response.json()

    assert body["initial_state"] == "available"
    assert body["degraded_state"] == "degraded"
    assert body["outage_state"] == "unavailable"
    assert body["recovered_state"] == "available"


def test_run_connectivity_simulation_returns_expected_actions():
    reset_connectivity_service()

    response = client.post("/connectivity/simulate")

    assert response.status_code == 200

    body = response.json()

    assert body["critical_action_during_degradation"] == "transmit"
    assert body["bulk_action_during_degradation"] == "queue"
    assert body["outage_queued_requests"] == 1
    assert body["recovered_transmitted_requests"] == 2
    assert body["final_queued_requests"] == 0


def test_simulation_does_not_modify_persistent_api_service_state():
    reset_connectivity_service()

    response = client.post("/connectivity/simulate")

    assert response.status_code == 200

    status_response = client.get("/connectivity/status")

    assert status_response.status_code == 200

    body = status_response.json()

    assert body["link"]["state"] == "available"
    assert body["link"]["available_kbps"] == 750
    assert body["queued_traffic"] == []
    assert body["usage"] == {
        "requests": 0,
        "transmitted_kbps": 0,
        "throttled_kbps": 0,
        "queued_requests": 0,
        "queued_kbps": 0,
    }


def test_connectivity_metrics_start_empty():
    reset_connectivity_service()

    response = client.get("/connectivity/metrics")

    assert response.status_code == 200

    body = response.json()

    assert body["traffic"] == {
        "total_requests": 0,
        "transmitted_requests": 0,
        "throttled_requests": 0,
        "queued_requests": 0,
    }

    assert body["bandwidth_kbps"] == {
        "transmitted": 0,
        "throttled": 0,
        "queued": 0,
    }

    assert body["connectivity_states"] == {
        "available_observations": 1,
        "degraded_observations": 0,
        "unavailable_observations": 0,
    }


def test_connectivity_metrics_reflect_traffic_and_link_changes():
    reset_connectivity_service()

    degraded_response = client.post(
        "/connectivity/link",
        params={
            "state": "degraded",
            "available_kbps": 300,
        },
    )

    assert degraded_response.status_code == 200

    critical_response = client.post(
        "/connectivity/traffic",
        json={
            "traffic_id": "metrics-critical-001",
            "traffic_class": "critical",
            "size_kb": 500,
            "required_kbps": 100,
        },
    )

    assert critical_response.status_code == 200

    bulk_response = client.post(
        "/connectivity/traffic",
        json={
            "traffic_id": "metrics-bulk-001",
            "traffic_class": "bulk",
            "size_kb": 1_000,
            "required_kbps": 200,
        },
    )

    assert bulk_response.status_code == 200

    response = client.get("/connectivity/metrics")

    assert response.status_code == 200

    body = response.json()

    assert body["traffic"]["total_requests"] == 2
    assert body["traffic"]["transmitted_requests"] == 1
    assert body["traffic"]["throttled_requests"] == 0
    assert body["traffic"]["queued_requests"] == 1

    assert body["bandwidth_kbps"]["transmitted"] == 100
    assert body["bandwidth_kbps"]["queued"] == 200

    assert body["connectivity_states"] == {
        "available_observations": 1,
        "degraded_observations": 1,
        "unavailable_observations": 0,
    }


def test_connectivity_metrics_reset_with_service_usage_reset():
    reset_connectivity_service()

    response = client.post(
        "/connectivity/traffic",
        json={
            "traffic_id": "metrics-reset-001",
            "traffic_class": "high",
            "size_kb": 500,
            "required_kbps": 100,
        },
    )

    assert response.status_code == 200

    service = get_connectivity_service()
    service.reset_usage()

    metrics_response = client.get("/connectivity/metrics")

    assert metrics_response.status_code == 200

    body = metrics_response.json()

    assert body["traffic"]["total_requests"] == 0
    assert body["traffic"]["transmitted_requests"] == 0
    assert body["traffic"]["throttled_requests"] == 0
    assert body["traffic"]["queued_requests"] == 0

    assert body["bandwidth_kbps"]["transmitted"] == 0
    assert body["bandwidth_kbps"]["throttled"] == 0
    assert body["bandwidth_kbps"]["queued"] == 0

    assert body["connectivity_states"] == {
        "available_observations": 0,
        "degraded_observations": 0,
        "unavailable_observations": 0,
    }