from app.connectivity.accounting import BandwidthAccounting
from app.connectivity.metrics import ConnectivityMetrics
from app.connectivity.models import (
    ConnectivityLink,
    ConnectivityState,
    TrafficAction,
    TrafficClass,
    TrafficRequest,
)
from app.connectivity.policy import ConnectivityPolicy
from app.connectivity.scheduler import ConnectivityScheduler
from app.connectivity.service import ConnectivityService


def build_service(
    *,
    state: ConnectivityState = ConnectivityState.AVAILABLE,
    available_kbps: int = 750,
) -> ConnectivityService:
    return ConnectivityService(
        link=ConnectivityLink(
            name="satellite-link",
            state=state,
            capacity_kbps=1_000,
            available_kbps=available_kbps,
        )
    )


def test_service_starts_with_configured_link():
    service = build_service()

    assert service.link.name == "satellite-link"
    assert service.link.state == ConnectivityState.AVAILABLE
    assert service.link.capacity_kbps == 1_000
    assert service.link.available_kbps == 750


def test_service_submit_transmits_critical_traffic_when_available():
    service = build_service()

    request = TrafficRequest(
        traffic_id="critical-001",
        traffic_class=TrafficClass.CRITICAL,
        size_kb=500,
        required_kbps=100,
    )

    decision = service.submit(request)

    assert decision.traffic_id == "critical-001"
    assert decision.action == TrafficAction.TRANSMIT.value
    assert decision.allocated_kbps == 100


def test_service_submit_queues_bulk_traffic_when_degraded():
    service = build_service(
        state=ConnectivityState.DEGRADED,
        available_kbps=300,
    )

    request = TrafficRequest(
        traffic_id="bulk-001",
        traffic_class=TrafficClass.BULK,
        size_kb=2_000,
        required_kbps=200,
    )

    decision = service.submit(request)

    assert decision.action == TrafficAction.QUEUE.value
    assert decision.allocated_kbps == 0
    assert service.queued_traffic() == (request,)


def test_service_submit_queues_all_traffic_when_unavailable():
    service = build_service(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    request = TrafficRequest(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        size_kb=500,
        required_kbps=100,
    )

    decision = service.submit(request)

    assert decision.action == TrafficAction.QUEUE.value
    assert decision.allocated_kbps == 0
    assert service.queued_traffic() == (request,)


def test_service_update_link_changes_state():
    service = build_service()

    updated = service.update_link(
        state=ConnectivityState.DEGRADED,
        available_kbps=300,
    )

    assert updated.state == ConnectivityState.DEGRADED
    assert updated.available_kbps == 300
    assert service.link.state == ConnectivityState.DEGRADED


def test_service_schedule_prioritizes_higher_priority_traffic():
    service = build_service(available_kbps=150)

    requests = [
        TrafficRequest(
            traffic_id="normal-001",
            traffic_class=TrafficClass.NORMAL,
            size_kb=500,
            required_kbps=100,
        ),
        TrafficRequest(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            size_kb=500,
            required_kbps=100,
        ),
    ]

    results = service.schedule(requests)

    by_id = {
        result.traffic_id: result
        for result in results
    }

    assert by_id["critical-001"].allocated_kbps == 100
    assert by_id["critical-001"].queued is False

    assert by_id["normal-001"].allocated_kbps == 50
    assert by_id["normal-001"].queued is True


def test_service_schedule_queues_bulk_traffic_when_link_is_degraded():
    service = build_service(
        state=ConnectivityState.DEGRADED,
        available_kbps=300,
    )

    requests = [
        TrafficRequest(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            size_kb=500,
            required_kbps=300,
        ),
        TrafficRequest(
            traffic_id="bulk-001",
            traffic_class=TrafficClass.BULK,
            size_kb=1_000,
            required_kbps=200,
        ),
    ]

    results = service.schedule(requests)

    by_id = {
        result.traffic_id: result
        for result in results
    }

    assert by_id["high-001"].allocated_kbps == 240
    assert by_id["high-001"].queued is False

    assert by_id["bulk-001"].allocated_kbps == 0
    assert by_id["bulk-001"].queued is True


def test_service_retry_queue_transmits_after_recovery():
    service = build_service(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    request = TrafficRequest(
        traffic_id="recovery-001",
        traffic_class=TrafficClass.NORMAL,
        size_kb=500,
        required_kbps=100,
    )

    initial_decision = service.submit(request)

    assert initial_decision.action == TrafficAction.QUEUE.value
    assert service.queued_traffic() == (request,)

    service.update_link(
        state=ConnectivityState.AVAILABLE,
        available_kbps=750,
    )

    decisions = service.retry_queue()

    assert len(decisions) == 1
    assert decisions[0].traffic_id == "recovery-001"
    assert decisions[0].action == TrafficAction.TRANSMIT.value
    assert decisions[0].allocated_kbps == 100
    assert service.queued_traffic() == ()


def test_service_retry_queue_keeps_traffic_queued_when_unavailable():
    service = build_service(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    request = TrafficRequest(
        traffic_id="retry-001",
        traffic_class=TrafficClass.HIGH,
        size_kb=500,
        required_kbps=100,
    )

    service.submit(request)

    decisions = service.retry_queue()

    assert len(decisions) == 1
    assert decisions[0].traffic_id == "retry-001"
    assert decisions[0].action == TrafficAction.QUEUE.value
    assert service.queued_traffic() == (request,)


def test_service_snapshot_returns_current_state():
    service = build_service()

    request = TrafficRequest(
        traffic_id="snapshot-001",
        traffic_class=TrafficClass.HIGH,
        size_kb=500,
        required_kbps=100,
    )

    service.submit(request)

    snapshot = service.snapshot()

    assert snapshot.link == service.link
    assert snapshot.queued_traffic == ()
    assert snapshot.transmitted_kbps == 100


def test_service_usage_tracks_bandwidth():
    service = build_service()

    request = TrafficRequest(
        traffic_id="usage-001",
        traffic_class=TrafficClass.HIGH,
        size_kb=500,
        required_kbps=100,
    )

    service.submit(request)

    usage = service.usage()

    assert usage.requests == 1
    assert usage.transmitted_kbps == 100


def test_service_uses_injected_accounting_tracker():
    accounting = BandwidthAccounting()

    service = ConnectivityService(
        link=ConnectivityLink(
            name="satellite-link",
            state=ConnectivityState.AVAILABLE,
            capacity_kbps=1_000,
            available_kbps=750,
        ),
        accounting=accounting,
    )

    request = TrafficRequest(
        traffic_id="accounting-001",
        traffic_class=TrafficClass.HIGH,
        size_kb=500,
        required_kbps=100,
    )

    service.submit(request)

    assert service.accounting is accounting
    assert accounting.total().transmitted_kbps == 100


def test_service_transmit_updates_operational_metrics():
    service = build_service()

    request = TrafficRequest(
        traffic_id="metrics-001",
        traffic_class=TrafficClass.CRITICAL,
        size_kb=500,
        required_kbps=100,
    )

    decision = service.submit(request)

    assert decision.action == TrafficAction.TRANSMIT.value

    metrics = service.metrics_snapshot()

    assert metrics.total_requests == 1
    assert metrics.transmitted_requests == 1
    assert metrics.throttled_requests == 0
    assert metrics.queued_requests == 0
    assert metrics.transmitted_kbps == 100
    assert metrics.throttled_kbps == 0
    assert metrics.queued_kbps == 0


def test_service_queue_updates_operational_metrics():
    service = build_service(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    request = TrafficRequest(
        traffic_id="metrics-queue-001",
        traffic_class=TrafficClass.NORMAL,
        size_kb=500,
        required_kbps=100,
    )

    decision = service.submit(request)

    assert decision.action == TrafficAction.QUEUE.value

    metrics = service.metrics_snapshot()

    assert metrics.total_requests == 1
    assert metrics.transmitted_requests == 0
    assert metrics.throttled_requests == 0
    assert metrics.queued_requests == 1
    assert metrics.transmitted_kbps == 0
    assert metrics.throttled_kbps == 0
    assert metrics.queued_kbps == 100


def test_link_state_changes_update_operational_metrics():
    service = build_service()

    service.update_link(
        state=ConnectivityState.DEGRADED,
        available_kbps=500,
    )

    service.update_link(
        state=ConnectivityState.UNAVAILABLE,
        available_kbps=0,
    )

    metrics = service.metrics_snapshot()

    assert metrics.available_state_count == 0
    assert metrics.degraded_state_count == 1
    assert metrics.unavailable_state_count == 1


def test_service_uses_injected_metrics_tracker():
    metrics_tracker = ConnectivityMetrics()

    service = ConnectivityService(
        link=ConnectivityLink(
            name="satellite-link",
            state=ConnectivityState.AVAILABLE,
            capacity_kbps=1_000,
            available_kbps=750,
        ),
        metrics=metrics_tracker,
    )

    request = TrafficRequest(
        traffic_id="metrics-injected-001",
        traffic_class=TrafficClass.HIGH,
        size_kb=500,
        required_kbps=100,
    )

    service.submit(request)

    assert service.metrics is metrics_tracker
    assert metrics_tracker.snapshot().total_requests == 1


def test_reset_usage_clears_operational_metrics():
    service = build_service()

    request = TrafficRequest(
        traffic_id="metrics-reset-001",
        traffic_class=TrafficClass.HIGH,
        size_kb=500,
        required_kbps=100,
    )

    service.submit(request)

    service.reset_usage()

    metrics = service.metrics_snapshot()

    assert metrics.total_requests == 0
    assert metrics.transmitted_requests == 0
    assert metrics.throttled_requests == 0
    assert metrics.queued_requests == 0
    assert metrics.transmitted_kbps == 0
    assert metrics.throttled_kbps == 0
    assert metrics.queued_kbps == 0
    assert metrics.available_state_count == 0
    assert metrics.degraded_state_count == 0
    assert metrics.unavailable_state_count == 0