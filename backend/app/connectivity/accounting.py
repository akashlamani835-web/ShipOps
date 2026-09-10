from dataclasses import dataclass
from collections import defaultdict

from app.connectivity.models import TrafficClass, TrafficDecision


@dataclass(frozen=True, slots=True)
class TrafficUsage:
    """Aggregate traffic usage statistics."""

    requests: int
    transmitted_kbps: int
    throttled_kbps: int
    queued_requests: int
    queued_kbps: int


class BandwidthAccounting:
    """
    Track simulated bandwidth outcomes across policy decisions.

    The accounting layer records what the connectivity system decided
    to transmit, throttle, or queue. The values represent simulated
    allocation rates rather than measured physical network throughput.
    """

    def __init__(self) -> None:
        self._requests = 0
        self._transmitted_kbps = 0
        self._throttled_kbps = 0
        self._queued_requests = 0
        self._queued_kbps = 0

        self._by_class: dict[
            TrafficClass,
            TrafficUsage,
        ] = defaultdict(
            lambda: TrafficUsage(
                requests=0,
                transmitted_kbps=0,
                throttled_kbps=0,
                queued_requests=0,
                queued_kbps=0,
            )
        )

    def record(
        self,
        decision: TrafficDecision,
        *,
        requested_kbps: int,
    ) -> None:
        """Record one traffic decision."""

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

        allocated = decision.allocated_kbps

        transmitted = 0
        throttled = 0
        queued = 0
        queued_kbps = 0

        if decision.action == "transmit":
            transmitted = allocated

        elif decision.action == "throttle":
            throttled = allocated
            queued_kbps = requested_kbps - allocated

        elif decision.action == "queue":
            queued = 1
            queued_kbps = requested_kbps

        elif decision.action == "reject":
            queued_kbps = requested_kbps

        self._requests += 1
        self._transmitted_kbps += transmitted
        self._throttled_kbps += throttled
        self._queued_requests += queued
        self._queued_kbps += queued_kbps

        previous = self._by_class[
            decision.traffic_class
        ]

        self._by_class[
            decision.traffic_class
        ] = TrafficUsage(
            requests=previous.requests + 1,
            transmitted_kbps=(
                previous.transmitted_kbps
                + transmitted
            ),
            throttled_kbps=(
                previous.throttled_kbps
                + throttled
            ),
            queued_requests=(
                previous.queued_requests
                + queued
            ),
            queued_kbps=(
                previous.queued_kbps
                + queued_kbps
            ),
        )

    def total(self) -> TrafficUsage:
        """Return aggregate usage across all traffic classes."""

        return TrafficUsage(
            requests=self._requests,
            transmitted_kbps=self._transmitted_kbps,
            throttled_kbps=self._throttled_kbps,
            queued_requests=self._queued_requests,
            queued_kbps=self._queued_kbps,
        )

    def by_class(
        self,
        traffic_class: TrafficClass,
    ) -> TrafficUsage:
        """Return aggregate usage for one traffic class."""

        return self._by_class[traffic_class]

    def reset(self) -> None:
        """Reset all accounting counters."""

        self._requests = 0
        self._transmitted_kbps = 0
        self._throttled_kbps = 0
        self._queued_requests = 0
        self._queued_kbps = 0
        self._by_class.clear()