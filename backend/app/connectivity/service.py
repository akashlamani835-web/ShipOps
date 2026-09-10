from dataclasses import dataclass

from app.connectivity.models import (
    ConnectivityLink,
    ConnectivityState,
    TrafficDecision,
    TrafficRequest,
)
from app.connectivity.policy import ConnectivityPolicy
from app.connectivity.scheduler import (
    ConnectivityScheduler,
    ScheduledTraffic,
)


@dataclass(frozen=True, slots=True)
class ConnectivitySnapshot:
    """Current simulated connectivity-service state."""

    link: ConnectivityLink
    queued_traffic: tuple[TrafficRequest, ...]
    transmitted_kbps: int


class ConnectivityService:
    """
    Manage a simulated external connectivity link.

    This service coordinates policy decisions, scheduling, local
    queuing, and bandwidth accounting.
    """

    def __init__(
        self,
        link: ConnectivityLink,
        policy: ConnectivityPolicy | None = None,
        scheduler: ConnectivityScheduler | None = None,
    ) -> None:
        self._link = link
        self._policy = policy or ConnectivityPolicy()
        self._scheduler = scheduler or ConnectivityScheduler()
        self._queue: list[TrafficRequest] = []
        self._transmitted_kbps = 0

    @property
    def link(self) -> ConnectivityLink:
        """Return the current simulated connectivity link."""

        return self._link

    def update_link(
        self,
        *,
        state: ConnectivityState,
        available_kbps: int,
    ) -> ConnectivityLink:
        """Update the simulated connectivity state."""

        self._link = ConnectivityLink(
            name=self._link.name,
            state=state,
            capacity_kbps=self._link.capacity_kbps,
            available_kbps=available_kbps,
        )

        return self._link

    def submit(
        self,
        request: TrafficRequest,
    ) -> TrafficDecision:
        """
        Process a single traffic request through the connectivity policy.

        Traffic that is queued is retained locally for later retry.
        """

        decision = self._policy.decide(
            link=self._link,
            request=request,
        )

        if decision.action == "queue":
            self._enqueue(request)

        elif decision.action in {"transmit", "throttle"}:
            self._transmitted_kbps += decision.allocated_kbps

        return decision

    def schedule(
        self,
        requests: list[TrafficRequest],
    ) -> list[ScheduledTraffic]:
        """
        Schedule multiple competing traffic requests.

        The scheduler determines priority and allocates the link's
        currently available bandwidth.
        """

        results = self._scheduler.schedule(
            available_kbps=self._link.available_kbps,
            requests=requests,
        )

        for request, result in zip(
            self._ordered_requests(requests),
            results,
        ):
            if result.queued:
                self._enqueue(request)
            else:
                self._transmitted_kbps += result.allocated_kbps

        return results

    def retry_queue(self) -> list[TrafficDecision]:
        """
        Retry queued traffic using the current link conditions.

        Queued requests are scheduled together so higher-priority traffic
        is considered before lower-priority traffic.
        """

        pending = list(self._queue)
        self._queue.clear()

        if not pending:
            return []

        scheduled = self.schedule(pending)

        decisions: list[TrafficDecision] = []

        for result in scheduled:
            if result.queued:
                action = "queue"

                reason = result.reason

                if result.allocated_kbps > 0:
                    action = "throttle"
            else:
                action = "transmit"
                reason = result.reason

            decisions.append(
                TrafficDecision(
                    traffic_id=result.traffic_id,
                    traffic_class=result.traffic_class,
                    action=action,
                    allocated_kbps=result.allocated_kbps,
                    reason=reason,
                )
            )

        return decisions

    def queued_traffic(self) -> tuple[TrafficRequest, ...]:
        """Return traffic currently waiting in the local queue."""

        return tuple(self._queue)

    def snapshot(self) -> ConnectivitySnapshot:
        """Return a point-in-time service snapshot."""

        return ConnectivitySnapshot(
            link=self._link,
            queued_traffic=tuple(self._queue),
            transmitted_kbps=self._transmitted_kbps,
        )

    def reset_usage(self) -> None:
        """Reset the simulated bandwidth counter."""

        self._transmitted_kbps = 0

    def _ordered_requests(
        self,
        requests: list[TrafficRequest],
    ) -> list[TrafficRequest]:
        """Return requests in exactly the scheduler's order."""

        pending = list(requests)
        ordered: list[TrafficRequest] = []

        while pending:
            request = self._scheduler.next_request(
                pending,
            )

            if request is None:
                break

            ordered.append(request)
            pending.remove(request)

        return ordered

    def _enqueue(
        self,
        request: TrafficRequest,
    ) -> None:
        """Add traffic to the local queue once."""

        if request not in self._queue:
            self._queue.append(request)