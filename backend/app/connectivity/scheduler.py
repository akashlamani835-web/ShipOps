from dataclasses import dataclass

from app.connectivity.models import TrafficClass, TrafficRequest


@dataclass(frozen=True, slots=True)
class ScheduledTraffic:
    """Scheduling result for one traffic request."""

    traffic_id: str
    traffic_class: TrafficClass
    allocated_kbps: int
    queued: bool
    reason: str


class ConnectivityScheduler:
    """
    Deterministic scheduler for competing traffic requests.

    The scheduler is responsible only for:
    - ordering requests
    - allocating available bandwidth

    Traffic-policy decisions such as whether bulk traffic should be
    transmitted or deferred remain the responsibility of ConnectivityPolicy.
    """

    _PRIORITY_ORDER = {
        TrafficClass.CRITICAL: 0,
        TrafficClass.HIGH: 1,
        TrafficClass.NORMAL: 2,
        TrafficClass.LOW: 3,
        TrafficClass.BULK: 4,
    }

    def schedule(
        self,
        *,
        available_kbps: int,
        requests: list[TrafficRequest],
    ) -> list[ScheduledTraffic]:
        """
        Produce a deterministic resource-allocation schedule.

        The scheduler does not decide whether a traffic class is allowed
        to transmit. It only determines how much bandwidth each request
        could receive based on priority ordering and remaining capacity.
        """

        if available_kbps < 0:
            raise ValueError("Available bandwidth cannot be negative.")

        ordered_requests = sorted(
            requests,
            key=self._sort_key,
        )

        remaining_kbps = available_kbps
        results: list[ScheduledTraffic] = []

        for request in ordered_requests:
            if remaining_kbps <= 0:
                results.append(
                    ScheduledTraffic(
                        traffic_id=request.traffic_id,
                        traffic_class=request.traffic_class,
                        allocated_kbps=0,
                        queued=True,
                        reason=(
                            "No bandwidth remains after higher-priority "
                            "traffic was scheduled."
                        ),
                    )
                )
                continue

            allocation = min(
                request.required_kbps,
                remaining_kbps,
            )

            remaining_kbps -= allocation

            if allocation == request.required_kbps:
                results.append(
                    ScheduledTraffic(
                        traffic_id=request.traffic_id,
                        traffic_class=request.traffic_class,
                        allocated_kbps=allocation,
                        queued=False,
                        reason=(
                            "Request received its full requested "
                            "bandwidth allocation."
                        ),
                    )
                )
                continue

            results.append(
                ScheduledTraffic(
                    traffic_id=request.traffic_id,
                    traffic_class=request.traffic_class,
                    allocated_kbps=allocation,
                    queued=True,
                    reason=(
                        "Request received a partial allocation because "
                        "available bandwidth was insufficient."
                    ),
                )
            )

        return results

    def next_request(
        self,
        requests: list[TrafficRequest],
    ) -> TrafficRequest | None:
        """Return the request that should be considered next."""

        if not requests:
            return None

        return min(
            requests,
            key=self._sort_key,
        )

    def _sort_key(
        self,
        request: TrafficRequest,
    ) -> tuple[int, int, float, str]:
        """
        Sort by priority, then deadline, then traffic ID.

        Requests without deadlines are placed after requests with
        explicit deadlines within the same priority class.
        """

        priority = self._PRIORITY_ORDER[
            request.traffic_class
        ]

        deadline_rank = (
            0
            if request.deadline is not None
            else 1
        )

        deadline_value = (
            request.deadline.timestamp()
            if request.deadline is not None
            else float("inf")
        )

        return (
            priority,
            deadline_rank,
            deadline_value,
            request.traffic_id,
        )