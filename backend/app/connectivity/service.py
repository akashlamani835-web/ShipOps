from dataclasses import dataclass, replace

from app.connectivity.accounting import BandwidthAccounting, TrafficUsage
from app.connectivity.models import (
    ConnectivityLink,
    ConnectivityState,
    TrafficAction,
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

    This service coordinates:
    - policy decisions
    - scheduling
    - local queuing
    - bandwidth accounting

    ConnectivityPolicy is authoritative for whether traffic is permitted
    to transmit and establishes the maximum bandwidth allocation allowed
    for each request.

    ConnectivityScheduler determines ordering and allocation among traffic
    requests permitted by policy.
    """

    def __init__(
        self,
        link: ConnectivityLink,
        policy: ConnectivityPolicy | None = None,
        scheduler: ConnectivityScheduler | None = None,
        accounting: BandwidthAccounting | None = None,
    ) -> None:
        self._link = link
        self._policy = policy or ConnectivityPolicy()
        self._scheduler = scheduler or ConnectivityScheduler()
        self._accounting = accounting or BandwidthAccounting()
        self._queue: list[TrafficRequest] = []

    @property
    def link(self) -> ConnectivityLink:
        """Return the current simulated connectivity link."""

        return self._link

    @property
    def accounting(self) -> BandwidthAccounting:
        """Return the bandwidth accounting tracker."""

        return self._accounting

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

        self._apply_decision(
            request=request,
            decision=decision,
        )

        return decision

    def schedule(
        self,
        requests: list[TrafficRequest],
    ) -> list[ScheduledTraffic]:
        """
        Schedule multiple competing traffic requests.

        Policy is evaluated first.

        Requests explicitly queued by policy never enter the scheduler.
        For requests permitted by policy, the scheduler receives a
        policy-constrained copy whose required bandwidth cannot exceed
        the policy-approved allocation.

        The returned results are kept in the same order as the original
        input list.
        """

        policy_allowed: list[TrafficRequest] = []
        policy_deferred: dict[str, ScheduledTraffic] = {}

        for request in requests:
            policy_decision = self._policy.decide(
                link=self._link,
                request=request,
            )

            if policy_decision.action == TrafficAction.QUEUE.value:
                policy_deferred[request.traffic_id] = ScheduledTraffic(
                    traffic_id=request.traffic_id,
                    traffic_class=request.traffic_class,
                    allocated_kbps=0,
                    queued=True,
                    reason=policy_decision.reason,
                )

                self._enqueue(request)

                self._accounting.record(
                    policy_decision,
                    requested_kbps=request.required_kbps,
                )

                continue

            policy_allowed.append(
                replace(
                    request,
                    required_kbps=policy_decision.allocated_kbps,
                )
            )

        scheduled = self._scheduler.schedule(
            available_kbps=self._link.available_kbps,
            requests=policy_allowed,
        )

        scheduled_by_id = {
            result.traffic_id: result
            for result in scheduled
        }

        results: list[ScheduledTraffic] = []

        for request in requests:
            deferred = policy_deferred.get(request.traffic_id)

            if deferred is not None:
                results.append(deferred)
                continue

            result = scheduled_by_id[request.traffic_id]

            decision = self._scheduled_to_decision(
                request=request,
                result=result,
            )

            self._apply_decision(
                request=request,
                decision=decision,
            )

            results.append(result)

        return results

    def retry_queue(self) -> list[TrafficDecision]:
        """
        Retry queued traffic using the current link conditions.

        Queued requests are evaluated again against the current policy
        and then scheduled according to priority.
        """

        pending = list(self._queue)
        self._queue.clear()

        if not pending:
            return []

        scheduled = self.schedule(pending)

        decisions: list[TrafficDecision] = []

        request_by_id = {
            request.traffic_id: request
            for request in pending
        }

        for result in scheduled:
            request = request_by_id[result.traffic_id]

            decision = self._scheduled_to_decision(
                request=request,
                result=result,
            )

            decisions.append(decision)

        return decisions

    def queued_traffic(self) -> tuple[TrafficRequest, ...]:
        """Return traffic currently waiting in the local queue."""

        return tuple(self._queue)

    def snapshot(self) -> ConnectivitySnapshot:
        """Return a point-in-time service snapshot."""

        return ConnectivitySnapshot(
            link=self._link,
            queued_traffic=tuple(self._queue),
            transmitted_kbps=self._accounting.total().transmitted_kbps,
        )

    def usage(self) -> TrafficUsage:
        """Return aggregate bandwidth usage statistics."""

        return self._accounting.total()

    def reset_usage(self) -> None:
        """Reset all simulated bandwidth accounting."""

        self._accounting.reset()

    def _apply_decision(
        self,
        *,
        request: TrafficRequest,
        decision: TrafficDecision,
    ) -> None:
        """Apply a traffic decision to service state and accounting."""

        if decision.action == TrafficAction.QUEUE.value:
            self._enqueue(request)

        self._accounting.record(
            decision,
            requested_kbps=request.required_kbps,
        )

    def _scheduled_to_decision(
        self,
        *,
        request: TrafficRequest,
        result: ScheduledTraffic,
    ) -> TrafficDecision:
        """Convert a scheduler result into the service decision model."""

        if result.queued:
            action = (
                TrafficAction.THROTTLE.value
                if result.allocated_kbps > 0
                else TrafficAction.QUEUE.value
            )
        else:
            action = TrafficAction.TRANSMIT.value

        return TrafficDecision(
            traffic_id=result.traffic_id,
            traffic_class=result.traffic_class,
            action=action,
            allocated_kbps=result.allocated_kbps,
            reason=result.reason,
        )

    def _enqueue(
        self,
        request: TrafficRequest,
    ) -> None:
        """Add traffic to the local queue once."""

        if request not in self._queue:
            self._queue.append(request)