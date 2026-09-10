from fastapi import APIRouter

from app.connectivity.models import (
    ConnectivityLink,
    ConnectivityState,
    TrafficRequest,
)
from app.connectivity.service import ConnectivityService


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