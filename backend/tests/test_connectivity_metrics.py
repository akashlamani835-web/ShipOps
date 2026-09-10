from app.connectivity.metrics import ConnectivityMetrics
from app.connectivity.models import (
    ConnectivityState,
    TrafficClass,
    TrafficDecision,
)


def build_decision(
    *,
    traffic_id: str,
    traffic_class: TrafficClass,
    action: str,
    allocated_kbps: int,
) -> TrafficDecision:
    return TrafficDecision(
        traffic_id=traffic_id,
        traffic_class=traffic_class,
        action=action,
        allocated_kbps=allocated_kbps,
        reason="test decision",
    )


def test_transmit_decision_updates_metrics():
    metrics = ConnectivityMetrics()

    decision = build_decision(
        traffic_id="critical-001",
        traffic_class=TrafficClass.CRITICAL,
        action="transmit",
        allocated_kbps=100,
    )

    metrics.record_decision(
        decision,
        requested_kbps=100,
    )

    snapshot = metrics.snapshot()

    assert snapshot.total_requests == 1
    assert snapshot.transmitted_requests == 1
    assert snapshot.throttled_requests == 0
    assert snapshot.queued_requests == 0
    assert snapshot.transmitted_kbps == 100
    assert snapshot.throttled_kbps == 0
    assert snapshot.queued_kbps == 0


def test_throttle_decision_updates_metrics():
    metrics = ConnectivityMetrics()

    decision = build_decision(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        action="throttle",
        allocated_kbps=100,
    )

    metrics.record_decision(
        decision,
        requested_kbps=300,
    )

    snapshot = metrics.snapshot()

    assert snapshot.total_requests == 1
    assert snapshot.transmitted_requests == 0
    assert snapshot.throttled_requests == 1
    assert snapshot.queued_requests == 0
    assert snapshot.throttled_kbps == 100


def test_queue_decision_updates_metrics():
    metrics = ConnectivityMetrics()

    decision = build_decision(
        traffic_id="bulk-001",
        traffic_class=TrafficClass.BULK,
        action="queue",
        allocated_kbps=0,
    )

    metrics.record_decision(
        decision,
        requested_kbps=500,
    )

    snapshot = metrics.snapshot()

    assert snapshot.total_requests == 1
    assert snapshot.transmitted_requests == 0
    assert snapshot.throttled_requests == 0
    assert snapshot.queued_requests == 1
    assert snapshot.queued_kbps == 500


def test_metrics_track_requests_by_traffic_class():
    metrics = ConnectivityMetrics()

    metrics.record_decision(
        build_decision(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            action="transmit",
            allocated_kbps=100,
        ),
        requested_kbps=100,
    )

    metrics.record_decision(
        build_decision(
            traffic_id="bulk-001",
            traffic_class=TrafficClass.BULK,
            action="queue",
            allocated_kbps=0,
        ),
        requested_kbps=500,
    )

    assert metrics.requests_by_class(
        TrafficClass.CRITICAL,
    ) == 1

    assert metrics.requests_by_class(
        TrafficClass.BULK,
    ) == 1

    assert metrics.requests_by_class(
        TrafficClass.HIGH,
    ) == 0


def test_metrics_track_connectivity_states():
    metrics = ConnectivityMetrics()

    metrics.record_state(
        ConnectivityState.AVAILABLE,
    )
    metrics.record_state(
        ConnectivityState.DEGRADED,
    )
    metrics.record_state(
        ConnectivityState.UNAVAILABLE,
    )
    metrics.record_state(
        ConnectivityState.DEGRADED,
    )

    snapshot = metrics.snapshot()

    assert snapshot.available_state_count == 1
    assert snapshot.degraded_state_count == 2
    assert snapshot.unavailable_state_count == 1


def test_metrics_aggregate_multiple_decisions():
    metrics = ConnectivityMetrics()

    metrics.record_decision(
        build_decision(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            action="transmit",
            allocated_kbps=300,
        ),
        requested_kbps=300,
    )

    metrics.record_decision(
        build_decision(
            traffic_id="normal-001",
            traffic_class=TrafficClass.NORMAL,
            action="throttle",
            allocated_kbps=100,
        ),
        requested_kbps=300,
    )

    metrics.record_decision(
        build_decision(
            traffic_id="bulk-001",
            traffic_class=TrafficClass.BULK,
            action="queue",
            allocated_kbps=0,
        ),
        requested_kbps=500,
    )

    snapshot = metrics.snapshot()

    assert snapshot.total_requests == 3
    assert snapshot.transmitted_requests == 1
    assert snapshot.throttled_requests == 1
    assert snapshot.queued_requests == 1
    assert snapshot.transmitted_kbps == 300
    assert snapshot.throttled_kbps == 100
    assert snapshot.queued_kbps == 500


def test_reset_clears_metrics():
    metrics = ConnectivityMetrics()

    metrics.record_state(
        ConnectivityState.DEGRADED,
    )

    metrics.record_decision(
        build_decision(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            action="transmit",
            allocated_kbps=200,
        ),
        requested_kbps=200,
    )

    metrics.reset()

    snapshot = metrics.snapshot()

    assert snapshot.total_requests == 0
    assert snapshot.transmitted_requests == 0
    assert snapshot.throttled_requests == 0
    assert snapshot.queued_requests == 0
    assert snapshot.transmitted_kbps == 0
    assert snapshot.throttled_kbps == 0
    assert snapshot.queued_kbps == 0
    assert snapshot.degraded_state_count == 0
    assert metrics.requests_by_class(
        TrafficClass.HIGH,
    ) == 0


def test_invalid_requested_bandwidth_is_rejected():
    metrics = ConnectivityMetrics()

    decision = build_decision(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        action="transmit",
        allocated_kbps=0,
    )

    try:
        metrics.record_decision(
            decision,
            requested_kbps=0,
        )
    except ValueError as exc:
        assert str(exc) == (
            "Requested bandwidth must be greater than zero."
        )
    else:
        raise AssertionError(
            "Expected ValueError for zero requested bandwidth.",
        )


def test_allocation_cannot_exceed_requested_bandwidth():
    metrics = ConnectivityMetrics()

    decision = build_decision(
        traffic_id="high-001",
        traffic_class=TrafficClass.HIGH,
        action="transmit",
        allocated_kbps=400,
    )

    try:
        metrics.record_decision(
            decision,
            requested_kbps=300,
        )
    except ValueError as exc:
        assert str(exc) == (
            "Allocated bandwidth cannot exceed requested bandwidth."
        )
    else:
        raise AssertionError(
            "Expected ValueError for excessive allocation.",
        )