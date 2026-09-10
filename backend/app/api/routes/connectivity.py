from fastapi import APIRouter

from app.connectivity.models import (
    ConnectivityLink,
    ConnectivityState,
    TrafficRequest,
)
from app.connectivity.service import ConnectivityService
from app.connectivity.simulation import ConnectivitySimulation


router = APIRouter(
    prefix="/connectivity",
    tags=["connectivity"],
)


_connectivity_service = ConnectivityService(
    link=ConnectivityLink(
        name="satellite-link",
        state=ConnectivityState.AVAILABLE,
        capacity_kbps=1_000,
        available_kbps=750,
    )
)


def get_connectivity_service() -> ConnectivityService:
    """
    Return the application-level connectivity service.

    The service is intentionally kept in memory for this simulation layer
    so state such as queued traffic and bandwidth usage persists across
    API requests.
    """

    return _connectivity_service


@router.get("/status")
def get_connectivity_status() -> dict:
    """Return the current simulated external connectivity status."""

    service = get_connectivity_service()
    snapshot = service.snapshot()
    usage = service.usage()

    return {
        "link": {
            "name": snapshot.link.name,
            "state": snapshot.link.state.value,
            "capacity_kbps": snapshot.link.capacity_kbps,
            "available_kbps": snapshot.link.available_kbps,
        },
        "queued_traffic": [
            {
                "traffic_id": request.traffic_id,
                "traffic_class": request.traffic_class.value,
                "size_kb": request.size_kb,
                "required_kbps": request.required_kbps,
                "deadline": request.deadline,
            }
            for request in snapshot.queued_traffic
        ],
        "usage": {
            "requests": usage.requests,
            "transmitted_kbps": usage.transmitted_kbps,
            "throttled_kbps": usage.throttled_kbps,
            "queued_requests": usage.queued_requests,
            "queued_kbps": usage.queued_kbps,
        },
    }


@router.post("/traffic")
def submit_traffic(request: TrafficRequest) -> dict:
    """Submit a traffic request to the connectivity service."""

    service = get_connectivity_service()
    decision = service.submit(request)

    return {
        "traffic_id": decision.traffic_id,
        "traffic_class": decision.traffic_class.value,
        "action": decision.action,
        "allocated_kbps": decision.allocated_kbps,
        "reason": decision.reason,
    }


@router.post("/link")
def update_connectivity_link(
    state: ConnectivityState,
    available_kbps: int,
) -> dict:
    """
    Update the simulated external connectivity link.

    This endpoint allows the demonstration environment to simulate
    available, degraded, and unavailable connectivity conditions.
    """

    if available_kbps < 0:
        raise ValueError(
            "Available bandwidth cannot be negative.",
        )

    service = get_connectivity_service()

    link = service.update_link(
        state=state,
        available_kbps=available_kbps,
    )

    return {
        "name": link.name,
        "state": link.state.value,
        "capacity_kbps": link.capacity_kbps,
        "available_kbps": link.available_kbps,
    }


@router.post("/retry")
def retry_connectivity_queue() -> dict:
    """
    Retry traffic currently waiting in the local connectivity queue.

    The service re-evaluates queued requests using the current link state,
    policy, and scheduler.
    """

    service = get_connectivity_service()
    decisions = service.retry_queue()

    return {
        "decisions": [
            {
                "traffic_id": decision.traffic_id,
                "traffic_class": decision.traffic_class.value,
                "action": decision.action,
                "allocated_kbps": decision.allocated_kbps,
                "reason": decision.reason,
            }
            for decision in decisions
        ],
        "queued_traffic_count": len(service.queued_traffic()),
    }


@router.post("/simulate")
def run_connectivity_simulation() -> dict:
    """
    Run the deterministic end-to-end connectivity resilience scenario.

    The simulation uses its own isolated connectivity service and therefore
    does not modify the state of the API's persistent connectivity service.
    """

    result = ConnectivitySimulation().run()

    return {
        "initial_state": result.initial_state.value,
        "degraded_state": result.degraded_state.value,
        "outage_state": result.outage_state.value,
        "recovered_state": result.recovered_state.value,
        "critical_action_during_degradation": (
            result.critical_action_during_degradation
        ),
        "bulk_action_during_degradation": (
            result.bulk_action_during_degradation
        ),
        "outage_queued_requests": result.outage_queued_requests,
        "recovered_transmitted_requests": (
            result.recovered_transmitted_requests
        ),
        "final_queued_requests": result.final_queued_requests,
        "transmitted_kbps": result.transmitted_kbps,
        "queued_kbps": result.queued_kbps,
    }