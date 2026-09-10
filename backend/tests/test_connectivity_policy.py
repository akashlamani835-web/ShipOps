from app.connectivity.models import (
    ConnectivityLink,
    ConnectivityState,
    TrafficClass,
    TrafficRequest,
)
from app.connectivity.policy import ConnectivityPolicy


def build_link(
    *,
    state: ConnectivityState,
    available_kbps: int,
    capacity_kbps: int = 2000,
) -> ConnectivityLink:
    return ConnectivityLink(
        name="satellite-primary",
        state=state,
        capacity_kbps=capacity_kbps,
        available_kbps=available_kbps,
    )


def test_critical_traffic_transmits_when_bandwidth_is_available():
    policy = ConnectivityPolicy()

    request = TrafficRequest(
        traffic_id="critical-001",
        traffic_class=TrafficClass.CRITICAL,
        size_kb=100,
        required_kbps=100,
    )

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.DEGRADED,
            available_kbps=500,
        ),
        request=request,
    )

    assert decision.action == "transmit"
    assert decision.allocated_kbps == 100
    assert decision.traffic_class == TrafficClass.CRITICAL


def test_critical_traffic_is_queued_when_link_is_unavailable():
    policy = ConnectivityPolicy()

    request = TrafficRequest(
        traffic_id="critical-002",
        traffic_class=TrafficClass.CRITICAL,
        size_kb=100,
        required_kbps=100,
    )

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.UNAVAILABLE,
            available_kbps=0,
        ),
        request=request,
    )

    assert decision.action == "queue"
    assert decision.allocated_kbps == 0


def test_bulk_traffic_is_queued_during_connectivity_management():
    policy = ConnectivityPolicy()

    request = TrafficRequest(
        traffic_id="bulk-001",
        traffic_class=TrafficClass.BULK,
        size_kb=500,
        required_kbps=500,
    )

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.DEGRADED,
            available_kbps=2000,
        ),
        request=request,
    )

    assert decision.action == "queue"
    assert decision.allocated_kbps == 0


def test_bulk_traffic_transmits_when_healthy_connectivity_is_available():
    policy = ConnectivityPolicy()

    request = TrafficRequest(
        traffic_id="bulk-002",
        traffic_class=TrafficClass.BULK,
        size_kb=500,
        required_kbps=500,
    )

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.AVAILABLE,
            available_kbps=2000,
        ),
        request=request,
    )

    assert decision.action == "transmit"
    assert decision.allocated_kbps == 500


def test_low_priority_traffic_is_throttled_when_link_is_degraded():
    policy = ConnectivityPolicy()

    request = TrafficRequest(
        traffic_id="low-001",
        traffic_class=TrafficClass.LOW,
        size_kb=500,
        required_kbps=500,
    )

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.DEGRADED,
            available_kbps=400,
        ),
        request=request,
    )

    assert decision.action == "throttle"
    assert decision.allocated_kbps > 0
    assert decision.allocated_kbps < request.required_kbps


def test_normal_traffic_transmits_on_available_link():
    policy = ConnectivityPolicy()

    request = TrafficRequest(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        size_kb=100,
        required_kbps=100,
    )

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.AVAILABLE,
            available_kbps=1000,
        ),
        request=request,
    )

    assert decision.action == "transmit"
    assert decision.allocated_kbps == 100


def test_high_priority_traffic_preempts_lower_priority_allocation():
    policy = ConnectivityPolicy()

    requests = [
        TrafficRequest(
            traffic_id="low-001",
            traffic_class=TrafficClass.LOW,
            size_kb=500,
            required_kbps=500,
        ),
        TrafficRequest(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            size_kb=500,
            required_kbps=500,
        ),
    ]

    allocations = policy.allocate(
        available_kbps=500,
        requests=requests,
    )

    high_allocation = next(
        item
        for item in allocations
        if item.traffic_class == TrafficClass.HIGH
    )

    low_allocation = next(
        item
        for item in allocations
        if item.traffic_class == TrafficClass.LOW
    )

    assert high_allocation.requested_kbps == 500
    assert high_allocation.allocated_kbps == 500

    assert low_allocation.requested_kbps == 500
    assert low_allocation.allocated_kbps == 0

    assert (
        high_allocation.allocated_kbps
        > low_allocation.allocated_kbps
    )


def test_priority_order_is_preserved_when_bandwidth_is_constrained():
    policy = ConnectivityPolicy()

    requests = [
        TrafficRequest(
            traffic_id="bulk-001",
            traffic_class=TrafficClass.BULK,
            size_kb=500,
            required_kbps=500,
        ),
        TrafficRequest(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            size_kb=500,
            required_kbps=500,
        ),
        TrafficRequest(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            size_kb=500,
            required_kbps=500,
        ),
    ]

    allocations = policy.allocate(
        available_kbps=700,
        requests=requests,
    )

    critical = next(
        item
        for item in allocations
        if item.traffic_class == TrafficClass.CRITICAL
    )

    high = next(
        item
        for item in allocations
        if item.traffic_class == TrafficClass.HIGH
    )

    bulk = next(
        item
        for item in allocations
        if item.traffic_class == TrafficClass.BULK
    )

    assert critical.allocated_kbps == 500
    assert high.allocated_kbps == 200
    assert bulk.allocated_kbps == 0

    assert critical.allocated_kbps >= high.allocated_kbps


def test_zero_bandwidth_queues_critical_traffic():
    policy = ConnectivityPolicy()

    request = TrafficRequest(
        traffic_id="critical-003",
        traffic_class=TrafficClass.CRITICAL,
        size_kb=100,
        required_kbps=100,
    )

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.DEGRADED,
            available_kbps=0,
        ),
        request=request,
    )

    assert decision.action == "queue"
    assert decision.allocated_kbps == 0