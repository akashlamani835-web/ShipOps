from dataclasses import dataclass

from app.connectivity.models import (
    ConnectivityState,
    TrafficClass,
    TrafficDecision,
)


@dataclass(frozen=True, slots=True)
class ConnectivityMetricsSnapshot:
    """Point-in-time operational metrics for connectivity."""

    total_requests: int
    transmitted_requests: int
    throttled_requests: int
    queued_requests: int

    transmitted_kbps: int
    throttled_kbps: int
    queued_kbps: int

    available_state_count: int
    degraded_state_count: int
    unavailable_state_count: int


class ConnectivityMetrics:
    """
    Track operational connectivity metrics in memory.

    The metrics service records traffic outcomes and connectivity
    state transitions for the current application runtime.
    """

    def __init__(self) -> None:
        self._total_requests = 0
        self._transmitted_requests = 0
        self._throttled_requests = 0
        self._queued_requests = 0

        self._transmitted_kbps = 0
        self._throttled_kbps = 0
        self._queued_kbps = 0

        self._state_counts = {
            ConnectivityState.AVAILABLE: 0,
            ConnectivityState.DEGRADED: 0,
            ConnectivityState.UNAVAILABLE: 0,
        }

        self._traffic_class_requests = {
            traffic_class: 0
            for traffic_class in TrafficClass
        }

    def record_decision(
        self,
        decision: TrafficDecision,
        *,
        requested_kbps: int,
    ) -> None:
        """Record the outcome of one traffic decision."""

        if requested_kbps <= 0:
            raise ValueError(
                "Requested bandwidth must be greater than zero.",
            )

        if decision.allocated_kbps < 0:
            raise ValueError(
                "Allocated bandwidth cannot be negative.",
            )

        if decision.allocated_kbps > requested_kbps:
            raise ValueError(
                "Allocated bandwidth cannot exceed requested bandwidth.",
            )

        self._total_requests += 1

        self._traffic_class_requests[
            decision.traffic_class
        ] += 1

        if decision.action == "transmit":
            self._transmitted_requests += 1
            self._transmitted_kbps += decision.allocated_kbps

        elif decision.action == "throttle":
            self._throttled_requests += 1
            self._throttled_kbps += decision.allocated_kbps

        elif decision.action == "queue":
            self._queued_requests += 1
            self._queued_kbps += requested_kbps

        elif decision.action == "reject":
            self._queued_requests += 1
            self._queued_kbps += requested_kbps

    def record_state(
        self,
        state: ConnectivityState,
    ) -> None:
        """Record a connectivity state observation."""

        self._state_counts[state] += 1

    def requests_by_class(
        self,
        traffic_class: TrafficClass,
    ) -> int:
        """Return the number of requests recorded for a traffic class."""

        return self._traffic_class_requests[traffic_class]

    def snapshot(self) -> ConnectivityMetricsSnapshot:
        """Return all current operational metrics."""

        return ConnectivityMetricsSnapshot(
            total_requests=self._total_requests,
            transmitted_requests=self._transmitted_requests,
            throttled_requests=self._throttled_requests,
            queued_requests=self._queued_requests,
            transmitted_kbps=self._transmitted_kbps,
            throttled_kbps=self._throttled_kbps,
            queued_kbps=self._queued_kbps,
            available_state_count=self._state_counts[
                ConnectivityState.AVAILABLE
            ],
            degraded_state_count=self._state_counts[
                ConnectivityState.DEGRADED
            ],
            unavailable_state_count=self._state_counts[
                ConnectivityState.UNAVAILABLE
            ],
        )

    def reset(self) -> None:
        """Reset all recorded operational metrics."""

        self._total_requests = 0
        self._transmitted_requests = 0
        self._throttled_requests = 0
        self._queued_requests = 0

        self._transmitted_kbps = 0
        self._throttled_kbps = 0
        self._queued_kbps = 0

        for state in self._state_counts:
            self._state_counts[state] = 0

        for traffic_class in self._traffic_class_requests:
            self._traffic_class_requests[traffic_class] = 0