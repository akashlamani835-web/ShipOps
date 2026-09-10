from datetime import datetime, timezone
from uuid import uuid4

from app.events.models import (
    EventRule,
    EventSeverity,
    EventStatus,
    OperationalEvent,
)


def create_event(
    db_session,
    seeded_topology,
    packet_loss_metric,
    *,
    asset_key: str,
    rule_code: str,
):
    """Create an operational event for API RCA tests."""

    rule = EventRule(
        code=rule_code,
        name=f"RCA API Rule {rule_code}",
        event_type="NETWORK_DEGRADATION",
        metric_definition_id=packet_loss_metric.id,
        operator=">",
        threshold=30,
        duration_seconds=180,
        severity=EventSeverity.HIGH,
        active=True,
        description="RCA API test rule.",
    )

    db_session.add(rule)
    db_session.flush()

    asset = seeded_topology[asset_key]

    event = OperationalEvent(
        asset_id=asset.id,
        rule_id=rule.id,
        event_type="NETWORK_DEGRADATION",
        severity=EventSeverity.HIGH,
        status=EventStatus.OPEN,
        occurred_at=datetime(
            2026,
            9,
            10,
            10,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        summary=(
            f"Packet loss detected on {asset.identifier}."
        ),
        details={
            "rule_code": rule.code,
            "threshold": 30,
        },
    )

    db_session.add(event)
    db_session.flush()

    return event


def test_get_event_rca(
    api_client,
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
        asset_key="pos1",
        rule_code="rca-api-single",
    )

    response = api_client.get(
        f"/api/v1/rca/events/{event.id}",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["event_id"] == str(event.id)
    assert body["affected_asset_identifier"] == "POS-07-01"
    assert body["root_cause_identifier"] == "SW-07"
    assert body["confidence"] > 0.50
    assert len(body["candidates"]) >= 3


def test_get_event_rca_unknown_event(
    api_client,
):
    response = api_client.get(
        f"/api/v1/rca/events/{uuid4()}",
    )

    assert response.status_code == 404


def test_post_cluster_rca(
    api_client,
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event_one = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
        asset_key="pos1",
        rule_code="rca-api-cluster-1",
    )

    event_two = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
        asset_key="pos2",
        rule_code="rca-api-cluster-2",
    )

    response = api_client.post(
        "/api/v1/rca/clusters",
        json={
            "event_ids": [
                str(event_one.id),
                str(event_two.id),
            ]
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["event_ids"] == [
        str(event_one.id),
        str(event_two.id),
    ]

    assert set(
        body["affected_asset_identifiers"],
    ) == {
        "POS-07-01",
        "POS-07-02",
    }

    assert body["root_cause_identifier"] == "SW-07"
    assert body["confidence"] > 0.50


def test_post_cluster_rca_requires_event_ids(
    api_client,
):
    response = api_client.post(
        "/api/v1/rca/clusters",
        json={
            "event_ids": [],
        },
    )

    assert response.status_code == 422


def test_post_cluster_rca_unknown_event(
    api_client,
):
    response = api_client.post(
        "/api/v1/rca/clusters",
        json={
            "event_ids": [
                str(uuid4()),
            ]
        },
    )

    assert response.status_code == 404