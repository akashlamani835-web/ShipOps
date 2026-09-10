from app.connectivity.models import (
    ConnectivityLink,
    ConnectivityState,
    TrafficClass,
    TrafficRequest,
)
from app.connectivity.service import ConnectivityService


def build_service(
    *,
    state: ConnectivityState = ConnectivityState.AVAILABLE,
    available_kbps: int = 2000,
) -> ConnectivityService:
    link = ConnectivityLink(
        name="satellite-primary",
        state=state,
        capacity_kbps=2000,
        available_kbps=available_kbps,
    )

    return ConnectivityService(link)


def test_unavailable_link_queues_traffic():
    service = build_service(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    request = TrafficRequest(
        traffic_id="critical-001",
        traffic_class=TrafficClass.CRITICAL,
        size_kb=100,
        required_kbps=100,
    )

    decision = service.submit(request)

    assert decision.action == "queue"
    assert decision.allocated_kbps == 0
    assert request in service.queued_traffic()


def test_available_link_transmits_traffic():
    service = build_service()

    request = TrafficRequest(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        size_kb=100,
        required_kbps=100,
    )

    decision = service.submit(request)

    assert decision.action == "transmit"
    assert decision.allocated_kbps == 100
    assert service.queued_traffic() == ()


def test_queued_traffic_is_retried_after_connectivity_restoration():
    service = build_service(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    request = TrafficRequest(
        traffic_id="critical-002",
        traffic_class=TrafficClass.CRITICAL,
        size_kb=100,
        required_kbps=100,
    )

    initial_decision = service.submit(request)

    assert initial_decision.action == "queue"
    assert len(service.queued_traffic()) == 1

    service.update_link(
        state=ConnectivityState.AVAILABLE,
        available_kbps=1000,
    )

    retry_decisions = service.retry_queue()

    assert len(retry_decisions) == 1
    assert retry_decisions[0].action == "transmit"
    assert retry_decisions[0].allocated_kbps == 100
    assert service.queued_traffic() == ()


def test_queued_traffic_remains_queued_when_link_is_still_unavailable():
    service = build_service(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    request = TrafficRequest(
        traffic_id="bulk-001",
        traffic_class=TrafficClass.BULK,
        size_kb=500,
        required_kbps=500,
    )

    service.submit(request)

    retry_decisions = service.retry_queue()

    assert len(retry_decisions) == 1
    assert retry_decisions[0].action == "queue"
    assert request in service.queued_traffic()


def test_snapshot_reports_current_service_state():
    service = build_service(
        state=ConnectivityState.DEGRADED,
        available_kbps=500,
    )

    request = TrafficRequest(
        traffic_id="low-001",
        traffic_class=TrafficClass.LOW,
        size_kb=200,
        required_kbps=200,
    )

    service.submit(request)

    snapshot = service.snapshot()

    assert snapshot.link.state == ConnectivityState.DEGRADED
    assert snapshot.link.available_kbps == 500
    assert isinstance(snapshot.queued_traffic, tuple)
    assert snapshot.transmitted_kbps >= 0


def test_reset_usage_clears_transmitted_bandwidth_counter():
    service = build_service()

    request = TrafficRequest(
        traffic_id="high-001",
        traffic_class=TrafficClass.HIGH,
        size_kb=100,
        required_kbps=100,
    )

    service.submit(request)

    assert service.snapshot().transmitted_kbps > 0

    service.reset_usage()

    assert service.snapshot().transmitted_kbps == 0


def test_duplicate_queued_request_is_not_added_twice():
    service = build_service(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    request = TrafficRequest(
        traffic_id="critical-003",
        traffic_class=TrafficClass.CRITICAL,
        size_kb=100,
        required_kbps=100,
    )

    service.submit(request)
    service.submit(request)

    assert service.queued_traffic() == (request,)


def test_service_schedule_prioritizes_critical_traffic():
    service = build_service(
        available_kbps=400,
    )

    requests = [
        TrafficRequest(
            traffic_id="normal-001",
            traffic_class=TrafficClass.NORMAL,
            size_kb=300,
            required_kbps=300,
        ),
        TrafficRequest(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            size_kb=300,
            required_kbps=300,
        ),
    ]

    results = service.schedule(requests)

    critical = next(
        result
        for result in results
        if result.traffic_id == "critical-001"
    )

    normal = next(
        result
        for result in results
        if result.traffic_id == "normal-001"
    )

    assert critical.allocated_kbps == 300
    assert critical.queued is False

    assert normal.allocated_kbps == 100
    assert normal.queued is True


def test_service_schedule_queues_unfunded_bulk_traffic():
    service = build_service(
        available_kbps=300,
    )

    requests = [
        TrafficRequest(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            size_kb=300,
            required_kbps=300,
        ),
        TrafficRequest(
            traffic_id="bulk-001",
            traffic_class=TrafficClass.BULK,
            size_kb=500,
            required_kbps=500,
        ),
    ]

    results = service.schedule(requests)

    high = next(
        result
        for result in results
        if result.traffic_id == "high-001"
    )

    bulk = next(
        result
        for result in results
        if result.traffic_id == "bulk-001"
    )

    assert high.allocated_kbps == 300
    assert high.queued is False

    assert bulk.allocated_kbps == 0
    assert bulk.queued is True
    assert any(
        request.traffic_id == "bulk-001"
        for request in service.queued_traffic()
    )


def test_service_schedule_updates_transmitted_usage():
    service = build_service(
        available_kbps=500,
    )

    requests = [
        TrafficRequest(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            size_kb=100,
            required_kbps=100,
        ),
        TrafficRequest(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            size_kb=150,
            required_kbps=150,
        ),
    ]

    results = service.schedule(requests)

    assert all(
        result.queued is False
        for result in results
    )

    assert service.snapshot().transmitted_kbps == 250


def test_retry_queue_uses_priority_order():
    service = build_service(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    normal = TrafficRequest(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        size_kb=300,
        required_kbps=300,
    )

    critical = TrafficRequest(
        traffic_id="critical-001",
        traffic_class=TrafficClass.CRITICAL,
        size_kb=300,
        required_kbps=300,
    )

    service.submit(normal)
    service.submit(critical)

    assert len(service.queued_traffic()) == 2

    service.update_link(
        state=ConnectivityState.AVAILABLE,
        available_kbps=300,
    )

    decisions = service.retry_queue()

    critical_decision = next(
        decision
        for decision in decisions
        if decision.traffic_id == "critical-001"
    )

    normal_decision = next(
        decision
        for decision in decisions
        if decision.traffic_id == "normal-001"
    )

    assert critical_decision.action == "transmit"
    assert critical_decision.allocated_kbps == 300

    assert normal_decision.action == "queue"
    assert normal_decision.allocated_kbps == 0