from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.events.models import (
    EventRule,
    EventSeverity,
    EventStatus,
    OperationalEvent,
)
from app.rca.engine import RCAEngine
from app.topology.service import TopologyService


def create_event(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    """Create an event on POS-07-01 for RCA testing."""

    rule = EventRule(
        code="rca_packet_loss_rule",
        name="RCA Packet Loss Rule",
        event_type="NETWORK_DEGRADATION",
        metric_definition_id=packet_loss_metric.id,
        operator=">",
        threshold=30,
        duration_seconds=180,
        severity=EventSeverity.HIGH,
        active=True,
        description="RCA test rule.",
    )

    db_session.add(rule)
    db_session.flush()

    pos = seeded_topology["pos1"]

    event = OperationalEvent(
        asset_id=pos.id,
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
        summary="Packet loss detected on POS-07-01.",
        details={
            "rule_code": rule.code,
            "threshold": 30,
        },
    )

    db_session.add(event)
    db_session.flush()

    return event


def test_rca_prefers_network_infrastructure_candidate(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    engine = RCAEngine(db_session)

    result = engine.analyze(event.id)

    assert result.event_id == event.id
    assert result.affected_asset_identifier == "POS-07-01"

    assert result.root_cause_identifier == "SW-07"

    assert result.confidence > 0.50

    assert len(result.candidates) >= 3

    assert result.candidates[0].identifier == "SW-07"


def test_rca_returns_ranked_candidates(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    engine = RCAEngine(db_session)

    result = engine.analyze(event.id)

    candidate_identifiers = [
        candidate.identifier
        for candidate in result.candidates
    ]

    assert "SW-07" in candidate_identifiers
    assert "AP-07-01" in candidate_identifiers

    scores = [
        candidate.score
        for candidate in result.candidates
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )


def test_rca_explanation_contains_supporting_factors(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    engine = RCAEngine(db_session)

    result = engine.analyze(event.id)

    assert "SW-07" in result.explanation
    assert "Confidence:" in result.explanation
    assert "network infrastructure role" in result.explanation
    assert "topology proximity" in result.explanation
    assert "network connectivity" in result.explanation


def test_rca_returns_no_root_cause_for_isolated_asset(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    isolated_topology = TopologyService(
        nodes=[],
        edges=[],
    )

    engine = RCAEngine(
        db_session,
        topology=isolated_topology,
    )

    result = engine.analyze(event.id)

    assert result.root_cause_asset_id is None
    assert result.root_cause_identifier is None
    assert result.confidence == 0.0
    assert result.candidates == ()


def test_rca_unknown_event_is_rejected(
    db_session,
):
    engine = RCAEngine(db_session)

    missing_event_id = uuid4()

    with pytest.raises(
        ValueError,
        match="not found",
    ):
        engine.analyze(missing_event_id)