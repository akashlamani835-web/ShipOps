from dataclasses import dataclass

from app.connectivity.models import (
    ConnectivityLink,
    ConnectivityState,
    TrafficClass,
    TrafficRequest,
)
from app.connectivity.service import ConnectivityService


@dataclass(frozen=True, slots=True)
class ConnectivitySimulationResult:
    """Deterministic result of the connectivity recovery scenario."""

    initial_state: ConnectivityState
    degraded_state: ConnectivityState
    outage_state: ConnectivityState
    recovered_state: ConnectivityState

    critical_action_during_degradation: str
    bulk_action_during_degradation: str

    outage_queued_requests: int
    recovered_transmitted_requests: int
    final_queued_requests: int

    transmitted_kbps: int
    queued_kbps: int


class ConnectivitySimulation:
    """
    Run a deterministic end-to-end connectivity resilience scenario.

    The simulation models:
    1. normal connectivity
    2. degraded external connectivity
    3. policy-driven bulk traffic deferral
    4. complete connectivity loss
    5. local queueing during the outage
    6. connectivity recovery
    7. queued-traffic retry
    """

    def run(self) -> ConnectivitySimulationResult:
        service = ConnectivityService(
            link=ConnectivityLink(
                name="simulation-link",
                state=ConnectivityState.AVAILABLE,
                capacity_kbps=1_000,
                available_kbps=750,
            )
        )

        initial_state = service.link.state

        service.update_link(
            state=ConnectivityState.DEGRADED,
            available_kbps=300,
        )

        critical_request = TrafficRequest(
            traffic_id="sim-critical-001",
            traffic_class=TrafficClass.CRITICAL,
            size_kb=500,
            required_kbps=100,
        )

        critical_decision = service.submit(
            critical_request,
        )

        bulk_request = TrafficRequest(
            traffic_id="sim-bulk-001",
            traffic_class=TrafficClass.BULK,
            size_kb=2_000,
            required_kbps=200,
        )

        bulk_decision = service.submit(
            bulk_request,
        )

        degraded_state = service.link.state

        service.update_link(
            state=ConnectivityState.UNAVAILABLE,
            available_kbps=0,
        )

        outage_request = TrafficRequest(
            traffic_id="sim-outage-001",
            traffic_class=TrafficClass.HIGH,
            size_kb=500,
            required_kbps=100,
        )

        service.submit(outage_request)

        outage_state = service.link.state

        outage_queued_requests = sum(
            1
            for request in service.queued_traffic()
            if request.traffic_id == outage_request.traffic_id
        )

        service.update_link(
            state=ConnectivityState.AVAILABLE,
            available_kbps=750,
        )

        recovered_state = service.link.state

        retry_decisions = service.retry_queue()

        recovered_transmitted_requests = sum(
            1
            for decision in retry_decisions
            if decision.action == "transmit"
        )

        usage = service.usage()

        return ConnectivitySimulationResult(
            initial_state=initial_state,
            degraded_state=degraded_state,
            outage_state=outage_state,
            recovered_state=recovered_state,
            critical_action_during_degradation=critical_decision.action,
            bulk_action_during_degradation=bulk_decision.action,
            outage_queued_requests=outage_queued_requests,
            recovered_transmitted_requests=recovered_transmitted_requests,
            final_queued_requests=len(
                service.queued_traffic(),
            ),
            transmitted_kbps=usage.transmitted_kbps,
            queued_kbps=usage.queued_kbps,
        )