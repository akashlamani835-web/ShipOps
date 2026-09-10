from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.connectivity.models import (
    ConnectivityState,
    ConnectivityLink,
    TrafficClass,
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
    """Return the persistent connectivity service used by the API."""

    return _connectivity_service


class TrafficRequestPayload(BaseModel):
    """Validated HTTP payload for connectivity traffic submission."""

    traffic_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the traffic request.",
    )
    traffic_class: TrafficClass
    size_kb: int = Field(
        ...,
        gt=0,
        description="Traffic payload size in kilobytes.",
    )
    required_kbps: int = Field(
        ...,
        gt=0,
        description="Required bandwidth in kilobits per second.",
    )
    deadline: float | None = Field(
        default=None,
        description="Optional scheduling deadline.",
    )


@router.get("/status")
def get_connectivity_status() -> dict:
    """Return the current connectivity link, queue, and usage state."""

    service = get_connectivity_service()

    snapshot = service.snapshot()
    usage = service.usage()

    return {
        "link": asdict(snapshot.link),
        "queued_traffic": [
            asdict(request)
            for request in snapshot.queued_traffic
        ],
        "usage": asdict(usage),
    }


@router.post("/traffic")
def submit_connectivity_traffic(
    payload: TrafficRequestPayload,
) -> dict:
    """Submit one traffic request to the connectivity policy engine."""

    service = get_connectivity_service()

    request = TrafficRequest(
        traffic_id=payload.traffic_id,
        traffic_class=payload.traffic_class,
        size_kb=payload.size_kb,
        required_kbps=payload.required_kbps,
        deadline=payload.deadline,
    )

    decision = service.submit(request)

    return asdict(decision)


@router.post("/link")
def update_connectivity_link(
    state: ConnectivityState,
    available_kbps: int = Query(
        ...,
        ge=0,
        description="Currently available bandwidth in kilobits per second.",
    ),
) -> dict:
    """
    Update the simulated connectivity link.

    FastAPI validates the state enum and non-negative bandwidth before
    the request reaches the service layer.
    """

    service = get_connectivity_service()

    try:
        link = service.update_link(
            state=state,
            available_kbps=available_kbps,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return asdict(link)


@router.post("/retry")
def retry_connectivity_queue() -> dict:
    """Retry traffic currently waiting in the local connectivity queue."""

    service = get_connectivity_service()

    decisions = service.retry_queue()

    return {
        "decisions": [
            asdict(decision)
            for decision in decisions
        ],
        "queued_traffic_count": len(service.queued_traffic()),
    }


@router.post("/simulate")
def run_connectivity_simulation() -> dict:
    """
    Run an isolated connectivity degradation, outage, and recovery
    simulation.
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


@router.get("/metrics")
def get_connectivity_metrics() -> dict:
    """Return operational connectivity metrics for the current API service."""

    service = get_connectivity_service()
    metrics = service.metrics_snapshot()

    return {
        "traffic": {
            "total_requests": metrics.total_requests,
            "transmitted_requests": metrics.transmitted_requests,
            "throttled_requests": metrics.throttled_requests,
            "queued_requests": metrics.queued_requests,
        },
        "bandwidth_kbps": {
            "transmitted": metrics.transmitted_kbps,
            "throttled": metrics.throttled_kbps,
            "queued": metrics.queued_kbps,
        },
        "connectivity_states": {
            "available_observations": metrics.available_state_count,
            "degraded_observations": metrics.degraded_state_count,
            "unavailable_observations": metrics.unavailable_state_count,
        },
    }