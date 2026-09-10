from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import (
    EventRule,
    EventSeverity,
    EventStatus,
    OperationalEvent,
)
from app.events.service import EventService
from app.telemetry.models import TelemetrySample


def build_sample(
    *,
    asset_id,
    metric_id,
    value: float,
    observed_at: datetime,
    source_sequence: int,
) -> TelemetrySample:
    """Build telemetry data for the API integration tests."""

    return TelemetrySample(
        asset_id=asset_id,
        metric_definition_id=metric_id,
        value=value,
        observed_at=observed_at,
        received_at=observed_at + timedelta(seconds=1),
        source="edge_gateway",
        source_sequence=source_sequence,
        quality="good",
        idempotency_key=(
            f"event-api-{source_sequence}-{value}"
        ),
    )


def create_event(
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
) -> OperationalEvent:
    """Create a real operational event in the test database."""

    asset = seeded_topology["switch"]

    rule = EventRule(
        code="api_packet_loss_high",
        name="API High Packet Loss",
        event_type="NETWORK_DEGRADATION",
        metric_definition_id=packet_loss_metric.id,
        operator=">",
        threshold=30,
        duration_seconds=180,
        severity=EventSeverity.HIGH,
        active=True,
        description="Detect sustained packet loss.",
    )

    db_session.add(rule)
    db_session.flush()

    start = datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    samples = [
        build_sample(
            asset_id=asset.id,
            metric_id=packet_loss_metric.id,
            value=38,
            observed_at=start,
            source_sequence=101,
        ),
        build_sample(
            asset_id=asset.id,
            metric_id=packet_loss_metric.id,
            value=41,
            observed_at=start + timedelta(minutes=1),
            source_sequence=102,
        ),
        build_sample(
            asset_id=asset.id,
            metric_id=packet_loss_metric.id,
            value=37,
            observed_at=start + timedelta(minutes=3),
            source_sequence=103,
        ),
    ]

    db_session.add_all(samples)
    db_session.flush()

    service = EventService(db_session)

    created_events: list[OperationalEvent] = []

    for sample in samples:
        created_events.extend(
            service.process_sample(sample)
        )

    assert len(created_events) == 1

    return created_events[0]


def test_list_events_returns_empty_collection(
    api_client: TestClient,
    packet_loss_metric,
):
    """The event collection endpoint returns an empty collection initially."""

    response = api_client.get(
        "/api/v1/events",
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "items": [],
        "count": 0,
    }


def test_get_event_returns_created_event(
    api_client: TestClient,
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """A created event can be retrieved through the API."""

    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    response = api_client.get(
        f"/api/v1/events/{event.id}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(event.id)
    assert data["asset_id"] == str(event.asset_id)
    assert data["rule_id"] == str(event.rule_id)
    assert data["event_type"] == "NETWORK_DEGRADATION"
    assert data["severity"] == "high"
    assert data["status"] == "open"


def test_list_events_returns_created_event(
    api_client: TestClient,
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """The event collection endpoint returns created events."""

    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    response = api_client.get(
        "/api/v1/events",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(event.id)


def test_list_events_can_filter_by_status(
    api_client: TestClient,
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """Event status filtering works."""

    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    response = api_client.get(
        "/api/v1/events",
        params={
            "event_status": "open",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert data["items"][0]["id"] == str(event.id)
    assert data["items"][0]["status"] == "open"


def test_list_events_can_filter_by_event_type(
    api_client: TestClient,
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """Event type filtering works."""

    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    response = api_client.get(
        "/api/v1/events",
        params={
            "event_type": "NETWORK_DEGRADATION",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert data["items"][0]["id"] == str(event.id)


def test_acknowledge_event(
    api_client: TestClient,
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """An open event can be acknowledged through the API."""

    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    response = api_client.post(
        f"/api/v1/events/{event.id}/acknowledge",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(event.id)
    assert data["status"] == "acknowledged"
    assert data["resolved_at"] is None


def test_resolve_open_event(
    api_client: TestClient,
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """An open event can be resolved through the API."""

    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    resolved_at = (
        event.occurred_at
        + timedelta(minutes=5)
    )

    response = api_client.post(
        f"/api/v1/events/{event.id}/resolve",
        json={
            "resolved_at": resolved_at.isoformat(),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(event.id)
    assert data["status"] == "resolved"

    returned_resolved_at = datetime.fromisoformat(
        data["resolved_at"].replace("Z", "+00:00")
    )

    assert returned_resolved_at == resolved_at


def test_acknowledge_then_resolve_event(
    api_client: TestClient,
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """An event can move through its full API lifecycle."""

    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    acknowledge_response = api_client.post(
        f"/api/v1/events/{event.id}/acknowledge",
    )

    assert acknowledge_response.status_code == 200
    assert acknowledge_response.json()["status"] == "acknowledged"

    resolved_at = (
        event.occurred_at
        + timedelta(minutes=10)
    )

    resolve_response = api_client.post(
        f"/api/v1/events/{event.id}/resolve",
        json={
            "resolved_at": resolved_at.isoformat(),
        },
    )

    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "resolved"


def test_resolved_event_cannot_be_acknowledged_again(
    api_client: TestClient,
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """A resolved event cannot move backwards to acknowledged."""

    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    resolved_at = (
        event.occurred_at
        + timedelta(minutes=5)
    )

    resolve_response = api_client.post(
        f"/api/v1/events/{event.id}/resolve",
        json={
            "resolved_at": resolved_at.isoformat(),
        },
    )

    assert resolve_response.status_code == 200

    acknowledge_response = api_client.post(
        f"/api/v1/events/{event.id}/acknowledge",
    )

    assert acknowledge_response.status_code == 409
    assert (
        acknowledge_response.json()["detail"]
        == "Only open events can be acknowledged."
    )


def test_resolved_event_cannot_be_resolved_again(
    api_client: TestClient,
    db_session: Session,
    seeded_topology,
    packet_loss_metric,
):
    """An already resolved event cannot be resolved again."""

    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    resolved_at = (
        event.occurred_at
        + timedelta(minutes=5)
    )

    first_response = api_client.post(
        f"/api/v1/events/{event.id}/resolve",
        json={
            "resolved_at": resolved_at.isoformat(),
        },
    )

    assert first_response.status_code == 200

    second_response = api_client.post(
        f"/api/v1/events/{event.id}/resolve",
        json={
            "resolved_at": (
                resolved_at
                + timedelta(minutes=1)
            ).isoformat(),
        },
    )

    assert second_response.status_code == 409
    assert (
        second_response.json()["detail"]
        == "Event is already resolved."
    )


def test_unknown_event_returns_404(
    api_client: TestClient,
):
    """Unknown event IDs return 404."""

    missing_id = (
        "00000000-0000-0000-0000-000000000001"
    )

    response = api_client.get(
        f"/api/v1/events/{missing_id}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Operational event '{missing_id}' not found."
    )


def test_invalid_limit_returns_400(
    api_client: TestClient,
):
    """Invalid pagination limits are rejected."""

    response = api_client.get(
        "/api/v1/events",
        params={
            "limit": 0,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "limit must be between 1 and 500."
    )


def test_invalid_offset_returns_400(
    api_client: TestClient,
):
    """Negative offsets are rejected."""

    response = api_client.get(
        "/api/v1/events",
        params={
            "offset": -1,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "offset cannot be negative."
    )


def test_invalid_event_id_returns_422(
    api_client: TestClient,
):
    """Malformed UUID path parameters are rejected."""

    response = api_client.get(
        "/api/v1/events/not-a-uuid",
    )

    assert response.status_code == 422