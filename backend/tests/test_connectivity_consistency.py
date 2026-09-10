import pytest

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


def build_link(
    *,
    state=ConnectivityState.AVAILABLE,
    available_kbps=1_000,
):
    return ConnectivityLink(
        name="satellite-link",
        state=state,
        capacity_kbps=1_000,
        available_kbps=available_kbps,
    )


def build_request(
    *,
    traffic_id="traffic-1",
    traffic_class=TrafficClass.NORMAL,
    required_kbps=100,
):
    return TrafficRequest(
        traffic_id=traffic_id,
        traffic_class=traffic_class,
        size_kb=100,
        required_kbps=required_kbps,
    )


def test_critical_traffic_is_transmitted_when_bandwidth_is_available():
    policy = ConnectivityPolicy()
    request = build_request(
        traffic_class=TrafficClass.CRITICAL,
        required_kbps=100,
    )

    decision = policy.decide(
        link=build_link(available_kbps=500),
        request=request,
    )

    assert decision.action == TrafficAction.TRANSMIT.value
    assert decision.allocated_kbps == 100


def test_critical_traffic_is_throttled_when_bandwidth_is_insufficient():
    policy = ConnectivityPolicy()
    request = build_request(
        traffic_class=TrafficClass.CRITICAL,
        required_kbps=500,
    )

    decision = policy.decide(
        link=build_link(available_kbps=200),
        request=request,
    )

    assert decision.action == TrafficAction.THROTTLE.value
    assert decision.allocated_kbps == 200


def test_bulk_traffic_is_queued_when_connectivity_is_degraded():
    policy = ConnectivityPolicy()
    request = build_request(
        traffic_class=TrafficClass.BULK,
        required_kbps=100,
    )

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.DEGRADED,
            available_kbps=500,
        ),
        request=request,
    )

    assert decision.action == TrafficAction.QUEUE.value
    assert decision.allocated_kbps == 0


def test_bulk_traffic_is_transmitted_when_connectivity_is_healthy():
    policy = ConnectivityPolicy()
    request = build_request(
        traffic_class=TrafficClass.BULK,
        required_kbps=100,
    )

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.AVAILABLE,
            available_kbps=500,
        ),
        request=request,
    )

    assert decision.action == TrafficAction.TRANSMIT.value
    assert decision.allocated_kbps == 100


def test_unavailable_connectivity_queues_traffic():
    policy = ConnectivityPolicy()
    request = build_request(required_kbps=100)

    decision = policy.decide(
        link=build_link(
            state=ConnectivityState.UNAVAILABLE,
            available_kbps=0,
        ),
        request=request,
    )

    assert decision.action == TrafficAction.QUEUE.value
    assert decision.allocated_kbps == 0


def test_scheduler_preserves_operational_priority_order():
    scheduler = ConnectivityScheduler()

    requests = [
        build_request(
            traffic_id="normal",
            traffic_class=TrafficClass.NORMAL,
            required_kbps=100,
        ),
        build_request(
            traffic_id="critical",
            traffic_class=TrafficClass.CRITICAL,
            required_kbps=100,
        ),
        build_request(
            traffic_id="high",
            traffic_class=TrafficClass.HIGH,
            required_kbps=100,
        ),
    ]

    results = scheduler.schedule(
        available_kbps=200,
        requests=requests,
    )

    assert [result.traffic_id for result in results] == [
        "critical",
        "high",
        "normal",
    ]


def test_scheduler_does_not_override_policy_bulk_decision():
    policy = ConnectivityPolicy()
    scheduler = ConnectivityScheduler()

    request = build_request(
        traffic_id="bulk-1",
        traffic_class=TrafficClass.BULK,
        required_kbps=100,
    )

    policy_decision = policy.decide(
        link=build_link(
            state=ConnectivityState.DEGRADED,
            available_kbps=500,
        ),
        request=request,
    )

    scheduler_result = scheduler.schedule(
        available_kbps=500,
        requests=[request],
    )[0]

    assert policy_decision.action == TrafficAction.QUEUE.value
    assert scheduler_result.allocated_kbps == 100


def test_service_submit_uses_policy_for_single_request():
    service = ConnectivityService(
        link=build_link(
            state=ConnectivityState.DEGRADED,
            available_kbps=500,
        ),
    )

    request = build_request(
        traffic_id="bulk-1",
        traffic_class=TrafficClass.BULK,
        required_kbps=100,
    )

    decision = service.submit(request)

    assert decision.action == TrafficAction.QUEUE.value
    assert decision.allocated_kbps == 0
    assert request in service.queued_traffic()


@pytest.mark.parametrize(
    ("traffic_class", "expected_action"),
    [
        (TrafficClass.CRITICAL, TrafficAction.TRANSMIT.value),
        (TrafficClass.HIGH, TrafficAction.TRANSMIT.value),
        (TrafficClass.NORMAL, TrafficAction.TRANSMIT.value),
        (TrafficClass.LOW, TrafficAction.TRANSMIT.value),
        (TrafficClass.BULK, TrafficAction.TRANSMIT.value),
    ],
)
def test_policy_has_deterministic_action_by_traffic_class(
    traffic_class,
    expected_action,
):
    policy = ConnectivityPolicy()
    request = build_request(
        traffic_class=traffic_class,
        required_kbps=50,
    )

    decision = policy.decide(
        link=build_link(available_kbps=500),
        request=request,
    )

    assert decision.action == expected_action