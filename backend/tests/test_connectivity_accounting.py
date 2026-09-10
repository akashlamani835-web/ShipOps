from app.connectivity.accounting import BandwidthAccounting
from app.connectivity.models import TrafficClass, TrafficDecision


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


def test_transmit_decision_is_recorded():
    accounting = BandwidthAccounting()

    decision = build_decision(
        traffic_id="critical-001",
        traffic_class=TrafficClass.CRITICAL,
        action="transmit",
        allocated_kbps=300,
    )

    accounting.record(
        decision,
        requested_kbps=300,
    )

    usage = accounting.total()

    assert usage.requests == 1
    assert usage.transmitted_kbps == 300
    assert usage.throttled_kbps == 0
    assert usage.queued_requests == 0
    assert usage.queued_kbps == 0


def test_throttle_records_transmitted_and_deferred_bandwidth():
    accounting = BandwidthAccounting()

    decision = build_decision(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        action="throttle",
        allocated_kbps=100,
    )

    accounting.record(
        decision,
        requested_kbps=300,
    )

    usage = accounting.total()

    assert usage.requests == 1
    assert usage.transmitted_kbps == 0
    assert usage.throttled_kbps == 100
    assert usage.queued_requests == 0
    assert usage.queued_kbps == 200


def test_queue_records_entire_request_as_deferred():
    accounting = BandwidthAccounting()

    decision = build_decision(
        traffic_id="bulk-001",
        traffic_class=TrafficClass.BULK,
        action="queue",
        allocated_kbps=0,
    )

    accounting.record(
        decision,
        requested_kbps=500,
    )

    usage = accounting.total()

    assert usage.requests == 1
    assert usage.transmitted_kbps == 0
    assert usage.throttled_kbps == 0
    assert usage.queued_requests == 1
    assert usage.queued_kbps == 500


def test_usage_is_tracked_independently_by_traffic_class():
    accounting = BandwidthAccounting()

    accounting.record(
        build_decision(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            action="transmit",
            allocated_kbps=300,
        ),
        requested_kbps=300,
    )

    accounting.record(
        build_decision(
            traffic_id="low-001",
            traffic_class=TrafficClass.LOW,
            action="throttle",
            allocated_kbps=50,
        ),
        requested_kbps=200,
    )

    critical = accounting.by_class(
        TrafficClass.CRITICAL,
    )

    low = accounting.by_class(
        TrafficClass.LOW,
    )

    assert critical.requests == 1
    assert critical.transmitted_kbps == 300

    assert low.requests == 1
    assert low.throttled_kbps == 50
    assert low.queued_kbps == 150


def test_multiple_decisions_are_aggregated():
    accounting = BandwidthAccounting()

    accounting.record(
        build_decision(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            action="transmit",
            allocated_kbps=200,
        ),
        requested_kbps=200,
    )

    accounting.record(
        build_decision(
            traffic_id="normal-001",
            traffic_class=TrafficClass.NORMAL,
            action="transmit",
            allocated_kbps=100,
        ),
        requested_kbps=100,
    )

    accounting.record(
        build_decision(
            traffic_id="bulk-001",
            traffic_class=TrafficClass.BULK,
            action="queue",
            allocated_kbps=0,
        ),
        requested_kbps=500,
    )

    usage = accounting.total()

    assert usage.requests == 3
    assert usage.transmitted_kbps == 300
    assert usage.queued_requests == 1
    assert usage.queued_kbps == 500


def test_reset_clears_all_accounting():
    accounting = BandwidthAccounting()

    accounting.record(
        build_decision(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            action="transmit",
            allocated_kbps=200,
        ),
        requested_kbps=200,
    )

    accounting.reset()

    usage = accounting.total()

    assert usage.requests == 0
    assert usage.transmitted_kbps == 0
    assert usage.throttled_kbps == 0
    assert usage.queued_requests == 0
    assert usage.queued_kbps == 0

    assert (
        accounting.by_class(
            TrafficClass.HIGH,
        ).requests
        == 0
    )


def test_invalid_requested_bandwidth_is_rejected():
    accounting = BandwidthAccounting()

    decision = build_decision(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        action="transmit",
        allocated_kbps=0,
    )

    try:
        accounting.record(
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
    accounting = BandwidthAccounting()

    decision = build_decision(
        traffic_id="high-001",
        traffic_class=TrafficClass.HIGH,
        action="transmit",
        allocated_kbps=400,
    )

    try:
        accounting.record(
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