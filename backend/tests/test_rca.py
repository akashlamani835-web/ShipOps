from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.events.models import (
    EventRule,
    EventSeverity,
    EventStatus,
    OperationalEvent,
)
from app.rca.engine import RCAEngine
from app.telemetry.models import TelemetrySample
from app.topology.service import TopologyService


def create_event(
    db_session,
    seeded_topology,
    packet_loss_metric,
    *,
    asset_key: str = "pos1",
    rule_code: str = "rca_packet_loss_rule",
    observed_at: datetime | None = None,
):
    """Create an event for RCA testing."""

    rule = EventRule(
        code=rule_code,
        name=f"RCA Rule {rule_code}",
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

    asset = seeded_topology[asset_key]

    if observed_at is None:
        observed_at = datetime(
            2026,
            9,
            10,
            10,
            0,
            0,
            tzinfo=timezone.utc,
        )

    event = OperationalEvent(
        asset_id=asset.id,
        rule_id=rule.id,
        event_type="NETWORK_DEGRADATION",
        severity=EventSeverity.HIGH,
        status=EventStatus.OPEN,
        occurred_at=observed_at,
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


def add_candidate_telemetry(
    db_session,
    *,
    asset,
    metric,
    values: list[float],
    event_time: datetime | None = None,
    key_prefix: str = "rca-candidate",
):
    """Add candidate telemetry immediately before the event."""

    if event_time is None:
        event_time = datetime(
            2026,
            9,
            10,
            10,
            0,
            0,
            tzinfo=timezone.utc,
        )

    samples = []

    for index, value in enumerate(values):
        observed_at = (
            event_time
            - timedelta(
                minutes=4 - index,
            )
        )

        samples.append(
            TelemetrySample(
                asset_id=asset.id,
                metric_definition_id=metric.id,
                value=value,
                observed_at=observed_at,
                received_at=observed_at + timedelta(seconds=1),
                source="edge_gateway",
                source_sequence=100 + index,
                quality="good",
                idempotency_key=(
                    f"{key_prefix}-{asset.identifier}-{index}"
                ),
            )
        )

    db_session.add_all(samples)
    db_session.flush()

    return samples


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
    assert "no corroborating candidate telemetry" in result.explanation


def test_rca_uses_candidate_telemetry_as_evidence(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    switch = seeded_topology["switch"]

    samples = add_candidate_telemetry(
        db_session,
        asset=switch,
        metric=packet_loss_metric,
        values=[35, 42, 38],
    )

    engine = RCAEngine(db_session)

    result = engine.analyze(event.id)

    winner = result.candidates[0]

    assert winner.identifier == "SW-07"
    assert winner.telemetry_support == 3
    assert any(
        "corroborating telemetry" in reason
        for reason in winner.reasons
    )

    assert all(
        sample.value > 30
        for sample in samples
    )


def test_rca_ignores_candidate_telemetry_outside_lookback_window(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
    )

    switch = seeded_topology["switch"]

    old_observed_at = (
        event.occurred_at
        - timedelta(minutes=10)
    )

    old_sample = TelemetrySample(
        asset_id=switch.id,
        metric_definition_id=packet_loss_metric.id,
        value=50,
        observed_at=old_observed_at,
        received_at=old_observed_at + timedelta(seconds=1),
        source="edge_gateway",
        source_sequence=500,
        quality="good",
        idempotency_key="rca-old-candidate-sample",
    )

    db_session.add(old_sample)
    db_session.flush()

    engine = RCAEngine(db_session)

    result = engine.analyze(event.id)

    switch_candidate = next(
        candidate
        for candidate in result.candidates
        if candidate.identifier == "SW-07"
    )

    assert switch_candidate.telemetry_support == 0


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


def test_cluster_rca_identifies_common_upstream_switch(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event_time = datetime(
        2026,
        9,
        10,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    event_one = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
        asset_key="pos1",
        rule_code="cluster_rule_pos1",
        observed_at=event_time,
    )

    event_two = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
        asset_key="pos2",
        rule_code="cluster_rule_pos2",
        observed_at=event_time,
    )

    engine = RCAEngine(db_session)

    result = engine.analyze_cluster(
        [
            event_one.id,
            event_two.id,
        ]
    )

    assert result.root_cause_identifier == "SW-07"
    assert result.confidence > 0.50

    switch_candidate = result.candidates[0]

    assert switch_candidate.identifier == "SW-07"
    assert switch_candidate.shared_event_support == 2

    assert any(
        "shared impact across 2 affected assets"
        in reason
        for reason in switch_candidate.reasons
    )


def test_cluster_rca_increases_support_for_shared_candidate(
    db_session,
    seeded_topology,
    packet_loss_metric,
):
    event_time = datetime(
        2026,
        9,
        10,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    event_one = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
        asset_key="pos1",
        rule_code="cluster_compare_rule_1",
        observed_at=event_time,
    )

    event_two = create_event(
        db_session,
        seeded_topology,
        packet_loss_metric,
        asset_key="pos2",
        rule_code="cluster_compare_rule_2",
        observed_at=event_time,
    )

    engine = RCAEngine(db_session)

    single_result = engine.analyze(event_one.id)

    cluster_result = engine.analyze_cluster(
        [
            event_one.id,
            event_two.id,
        ]
    )

    single_switch = next(
        candidate
        for candidate in single_result.candidates
        if candidate.identifier == "SW-07"
    )

    cluster_switch = next(
        candidate
        for candidate in cluster_result.candidates
        if candidate.identifier == "SW-07"
    )

    assert cluster_switch.shared_event_support == 2
    assert (
        cluster_switch.score
        > single_switch.score
    )


def test_cluster_rca_requires_at_least_one_event(
    db_session,
):
    engine = RCAEngine(db_session)

    with pytest.raises(
        ValueError,
        match="At least one event ID",
    ):
        engine.analyze_cluster([])


def test_cluster_rca_rejects_unknown_event(
    db_session,
):
    engine = RCAEngine(db_session)

    missing_event_id = uuid4()

    with pytest.raises(
        ValueError,
        match="not found",
    ):
        engine.analyze_cluster(
            [missing_event_id]
        )