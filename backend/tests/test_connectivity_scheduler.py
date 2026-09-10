from datetime import datetime, timedelta, timezone

import pytest

from app.connectivity.models import TrafficClass, TrafficRequest
from app.connectivity.scheduler import (
    ConnectivityScheduler,
    ScheduledTraffic,
)


def build_request(
    *,
    traffic_id: str,
    traffic_class: TrafficClass,
    required_kbps: int,
    size_kb: int = 100,
    deadline: datetime | None = None,
) -> TrafficRequest:
    return TrafficRequest(
        traffic_id=traffic_id,
        traffic_class=traffic_class,
        size_kb=size_kb,
        required_kbps=required_kbps,
        deadline=deadline,
    )


def test_critical_traffic_is_scheduled_before_high_traffic():
    scheduler = ConnectivityScheduler()

    requests = [
        build_request(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            required_kbps=200,
        ),
        build_request(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            required_kbps=200,
        ),
    ]

    results = scheduler.schedule(
        available_kbps=400,
        requests=requests,
    )

    assert [
        result.traffic_id
        for result in results
    ] == [
        "critical-001",
        "high-001",
    ]


def test_higher_priority_traffic_consumes_bandwidth_first():
    scheduler = ConnectivityScheduler()

    requests = [
        build_request(
            traffic_id="normal-001",
            traffic_class=TrafficClass.NORMAL,
            required_kbps=300,
        ),
        build_request(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            required_kbps=300,
        ),
    ]

    results = scheduler.schedule(
        available_kbps=400,
        requests=requests,
    )

    critical = results[0]
    normal = results[1]

    assert critical.traffic_id == "critical-001"
    assert critical.allocated_kbps == 300
    assert critical.queued is False

    assert normal.traffic_id == "normal-001"
    assert normal.allocated_kbps == 100
    assert normal.queued is True


def test_same_priority_uses_earliest_deadline_first():
    scheduler = ConnectivityScheduler()

    now = datetime.now(timezone.utc)

    later = build_request(
        traffic_id="high-later",
        traffic_class=TrafficClass.HIGH,
        required_kbps=100,
        deadline=now + timedelta(minutes=10),
    )

    earlier = build_request(
        traffic_id="high-earlier",
        traffic_class=TrafficClass.HIGH,
        required_kbps=100,
        deadline=now + timedelta(minutes=2),
    )

    results = scheduler.schedule(
        available_kbps=200,
        requests=[later, earlier],
    )

    assert [
        result.traffic_id
        for result in results
    ] == [
        "high-earlier",
        "high-later",
    ]


def test_requests_without_deadlines_follow_deadlined_requests():
    scheduler = ConnectivityScheduler()

    request_without_deadline = build_request(
        traffic_id="normal-no-deadline",
        traffic_class=TrafficClass.NORMAL,
        required_kbps=100,
    )

    request_with_deadline = build_request(
        traffic_id="normal-deadline",
        traffic_class=TrafficClass.NORMAL,
        required_kbps=100,
        deadline=datetime.now(timezone.utc)
        + timedelta(minutes=5),
    )

    results = scheduler.schedule(
        available_kbps=200,
        requests=[
            request_without_deadline,
            request_with_deadline,
        ],
    )

    assert [
        result.traffic_id
        for result in results
    ] == [
        "normal-deadline",
        "normal-no-deadline",
    ]


def test_request_gets_full_allocation_when_bandwidth_is_sufficient():
    scheduler = ConnectivityScheduler()

    request = build_request(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        required_kbps=100,
    )

    results = scheduler.schedule(
        available_kbps=500,
        requests=[request],
    )

    assert results == [
        ScheduledTraffic(
            traffic_id="normal-001",
            traffic_class=TrafficClass.NORMAL,
            allocated_kbps=100,
            queued=False,
            reason=(
                "Request received its full requested "
                "bandwidth allocation."
            ),
        )
    ]


def test_request_is_partially_allocated_when_bandwidth_is_insufficient():
    scheduler = ConnectivityScheduler()

    request = build_request(
        traffic_id="high-001",
        traffic_class=TrafficClass.HIGH,
        required_kbps=500,
    )

    results = scheduler.schedule(
        available_kbps=200,
        requests=[request],
    )

    result = results[0]

    assert result.traffic_id == "high-001"
    assert result.allocated_kbps == 200
    assert result.queued is True


def test_requests_are_queued_when_no_bandwidth_is_available():
    scheduler = ConnectivityScheduler()

    requests = [
        build_request(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            required_kbps=100,
        ),
        build_request(
            traffic_id="bulk-001",
            traffic_class=TrafficClass.BULK,
            required_kbps=500,
        ),
    ]

    results = scheduler.schedule(
        available_kbps=0,
        requests=requests,
    )

    assert len(results) == 2

    assert all(
        result.allocated_kbps == 0
        for result in results
    )

    assert all(
        result.queued
        for result in results
    )


def test_empty_request_list_produces_empty_schedule():
    scheduler = ConnectivityScheduler()

    assert scheduler.schedule(
        available_kbps=1000,
        requests=[],
    ) == []


def test_next_request_returns_highest_priority_request():
    scheduler = ConnectivityScheduler()

    requests = [
        build_request(
            traffic_id="bulk-001",
            traffic_class=TrafficClass.BULK,
            required_kbps=500,
        ),
        build_request(
            traffic_id="high-001",
            traffic_class=TrafficClass.HIGH,
            required_kbps=200,
        ),
        build_request(
            traffic_id="critical-001",
            traffic_class=TrafficClass.CRITICAL,
            required_kbps=100,
        ),
    ]

    next_request = scheduler.next_request(requests)

    assert next_request is not None
    assert next_request.traffic_id == "critical-001"


def test_next_request_returns_none_for_empty_list():
    scheduler = ConnectivityScheduler()

    assert scheduler.next_request([]) is None


def test_negative_bandwidth_is_rejected():
    scheduler = ConnectivityScheduler()

    request = build_request(
        traffic_id="normal-001",
        traffic_class=TrafficClass.NORMAL,
        required_kbps=100,
    )

    with pytest.raises(
        ValueError,
        match="Available bandwidth cannot be negative",
    ):
        scheduler.schedule(
            available_kbps=-1,
            requests=[request],
        )