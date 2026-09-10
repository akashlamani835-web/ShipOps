from app.connectivity.models import (
    BandwidthAllocation,
    ConnectivityLink,
    ConnectivityState,
    TrafficAction,
    TrafficClass,
    TrafficDecision,
    TrafficRequest,
)


class ConnectivityPolicy:
    """
    Deterministic bandwidth-allocation policy for constrained links.

    Higher-priority traffic receives bandwidth before lower-priority
    traffic. Bulk traffic is queued when the link is constrained.
    """

    _PRIORITY_ORDER = (
        TrafficClass.CRITICAL,
        TrafficClass.HIGH,
        TrafficClass.NORMAL,
        TrafficClass.LOW,
        TrafficClass.BULK,
    )

    _CLASS_WEIGHTS = {
        TrafficClass.CRITICAL: 1.00,
        TrafficClass.HIGH: 0.80,
        TrafficClass.NORMAL: 0.60,
        TrafficClass.LOW: 0.25,
        TrafficClass.BULK: 0.00,
    }

    def decide(
        self,
        *,
        link: ConnectivityLink,
        request: TrafficRequest,
    ) -> TrafficDecision:
        """Decide how a single traffic request should be handled."""

        if link.state == ConnectivityState.UNAVAILABLE:
            return TrafficDecision(
                traffic_id=request.traffic_id,
                traffic_class=request.traffic_class,
                action=TrafficAction.QUEUE.value,
                allocated_kbps=0,
                reason=(
                    "External connectivity is unavailable; "
                    "traffic is queued locally."
                ),
            )

        if request.traffic_class == TrafficClass.CRITICAL:
            return self._decide_critical(
                link=link,
                request=request,
            )

        if request.traffic_class == TrafficClass.BULK:
            return self._decide_bulk(
                link=link,
                request=request,
            )

        return self._decide_priority_class(
            link=link,
            request=request,
        )

    def allocate(
        self,
        *,
        available_kbps: int,
        requests: list[TrafficRequest],
    ) -> list[BandwidthAllocation]:
        """
        Allocate available bandwidth across a batch of requests.

        Requests are processed in operational priority order.
        Each request receives no more than its required bandwidth.
        """

        if available_kbps < 0:
            raise ValueError(
                "Available bandwidth cannot be negative.",
            )

        allocations: list[BandwidthAllocation] = []
        remaining_kbps = available_kbps

        ordered_requests = sorted(
            requests,
            key=lambda request: self._priority_index(
                request.traffic_class,
            ),
        )

        for request in ordered_requests:
            requested_kbps = request.required_kbps

            if remaining_kbps <= 0:
                allocations.append(
                    BandwidthAllocation(
                        traffic_class=request.traffic_class,
                        requested_kbps=requested_kbps,
                        allocated_kbps=0,
                    )
                )
                continue

            allocation = min(
                requested_kbps,
                remaining_kbps,
            )

            allocations.append(
                BandwidthAllocation(
                    traffic_class=request.traffic_class,
                    requested_kbps=requested_kbps,
                    allocated_kbps=allocation,
                )
            )

            remaining_kbps -= allocation

        return allocations

    def _decide_critical(
        self,
        *,
        link: ConnectivityLink,
        request: TrafficRequest,
    ) -> TrafficDecision:
        if link.available_kbps <= 0:
            return TrafficDecision(
                traffic_id=request.traffic_id,
                traffic_class=request.traffic_class,
                action=TrafficAction.QUEUE.value,
                allocated_kbps=0,
                reason=(
                    "No bandwidth is currently available; "
                    "critical traffic is queued rather than discarded."
                ),
            )

        allocation = min(
            request.required_kbps,
            link.available_kbps,
        )

        if allocation < request.required_kbps:
            return TrafficDecision(
                traffic_id=request.traffic_id,
                traffic_class=request.traffic_class,
                action=TrafficAction.THROTTLE.value,
                allocated_kbps=allocation,
                reason=(
                    "Critical traffic is protected but the available "
                    "bandwidth is below its requested transfer rate."
                ),
            )

        return TrafficDecision(
            traffic_id=request.traffic_id,
            traffic_class=request.traffic_class,
            action=TrafficAction.TRANSMIT.value,
            allocated_kbps=allocation,
            reason=(
                "Critical traffic receives first priority on "
                "available connectivity."
            ),
        )

    def _decide_bulk(
        self,
        *,
        link: ConnectivityLink,
        request: TrafficRequest,
    ) -> TrafficDecision:
        return TrafficDecision(
            traffic_id=request.traffic_id,
            traffic_class=request.traffic_class,
            action=TrafficAction.QUEUE.value,
            allocated_kbps=0,
            reason=(
                "Bulk traffic is deferred to preserve bandwidth "
                "for operational traffic."
            ),
        )

    def _decide_priority_class(
        self,
        *,
        link: ConnectivityLink,
        request: TrafficRequest,
    ) -> TrafficDecision:
        if link.state == ConnectivityState.DEGRADED:
            weight = self._CLASS_WEIGHTS[
                request.traffic_class
            ]

            allocated = min(
                request.required_kbps,
                max(
                    1,
                    int(link.available_kbps * weight),
                ),
            )

            if request.traffic_class == TrafficClass.LOW:
                return TrafficDecision(
                    traffic_id=request.traffic_id,
                    traffic_class=request.traffic_class,
                    action=TrafficAction.THROTTLE.value,
                    allocated_kbps=allocated,
                    reason=(
                        "Low-priority traffic is throttled while "
                        "the link is degraded."
                    ),
                )

            if allocated < request.required_kbps:
                return TrafficDecision(
                    traffic_id=request.traffic_id,
                    traffic_class=request.traffic_class,
                    action=TrafficAction.THROTTLE.value,
                    allocated_kbps=allocated,
                    reason=(
                        "Traffic is partially allocated because "
                        "the link is degraded."
                    ),
                )

            return TrafficDecision(
                traffic_id=request.traffic_id,
                traffic_class=request.traffic_class,
                action=TrafficAction.TRANSMIT.value,
                allocated_kbps=allocated,
                reason=(
                    "Traffic is transmitted using its requested "
                    "bandwidth while the link is degraded."
                ),
            )

        allocation = min(
            request.required_kbps,
            link.available_kbps,
        )

        if allocation < request.required_kbps:
            return TrafficDecision(
                traffic_id=request.traffic_id,
                traffic_class=request.traffic_class,
                action=TrafficAction.THROTTLE.value,
                allocated_kbps=allocation,
                reason=(
                    "Available bandwidth is below the requested "
                    "transfer rate."
                ),
            )

        return TrafficDecision(
            traffic_id=request.traffic_id,
            traffic_class=request.traffic_class,
            action=TrafficAction.TRANSMIT.value,
            allocated_kbps=allocation,
            reason=(
                "Connectivity is available and sufficient "
                "bandwidth exists."
            ),
        )

    @staticmethod
    def _priority_index(
        traffic_class: TrafficClass,
    ) -> int:
        return ConnectivityPolicy._PRIORITY_ORDER.index(
            traffic_class,
        )