from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ConnectivityState(str, Enum):
    """Operational state of an external connectivity link."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class TrafficClass(str, Enum):
    """Priority class used by the connectivity policy engine."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BULK = "bulk"


class TrafficAction(str, Enum):
    """Action selected by connectivity policy."""

    TRANSMIT = "transmit"
    THROTTLE = "throttle"
    QUEUE = "queue"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class ConnectivityLink:
    """
    Describe the current state and capacity of a simulated
    external connectivity link.
    """

    name: str
    state: ConnectivityState
    capacity_kbps: int
    available_kbps: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "Connectivity link name cannot be empty.",
            )

        if self.capacity_kbps <= 0:
            raise ValueError(
                "Connectivity link capacity must be greater than zero.",
            )

        if self.available_kbps < 0:
            raise ValueError(
                "Available bandwidth cannot be negative.",
            )

        if self.available_kbps > self.capacity_kbps:
            raise ValueError(
                "Available bandwidth cannot exceed link capacity.",
            )


@dataclass(frozen=True, slots=True)
class TrafficRequest:
    """
    Represent traffic that wants to use the connectivity link.

    size_kb represents the total data volume.

    required_kbps represents the desired transfer rate for the
    simulated scheduling period.
    """

    traffic_id: str
    traffic_class: TrafficClass
    size_kb: int
    required_kbps: int = 1
    deadline: datetime | None = None

    def __post_init__(self) -> None:
        if not self.traffic_id.strip():
            raise ValueError(
                "Traffic ID cannot be empty.",
            )

        if self.size_kb <= 0:
            raise ValueError(
                "Traffic size must be greater than zero.",
            )

        if self.required_kbps <= 0:
            raise ValueError(
                "Required bandwidth must be greater than zero.",
            )


@dataclass(frozen=True, slots=True)
class TrafficDecision:
    """
    Result of the connectivity policy decision.

    The policy engine determines whether traffic can be transmitted,
    throttled, queued, or rejected.
    """

    traffic_id: str
    traffic_class: TrafficClass
    action: str
    allocated_kbps: int
    reason: str

    def __post_init__(self) -> None:
        if not self.traffic_id.strip():
            raise ValueError(
                "Traffic ID cannot be empty.",
            )

        if self.allocated_kbps < 0:
            raise ValueError(
                "Allocated bandwidth cannot be negative.",
            )

        valid_actions = {
            TrafficAction.TRANSMIT.value,
            TrafficAction.THROTTLE.value,
            TrafficAction.QUEUE.value,
            TrafficAction.REJECT.value,
        }

        if self.action not in valid_actions:
            raise ValueError(
                f"Unsupported traffic action '{self.action}'.",
            )


@dataclass(frozen=True, slots=True)
class BandwidthAllocation:
    """
    Describe bandwidth allocated to a traffic request.
    """

    traffic_class: TrafficClass
    requested_kbps: int
    allocated_kbps: int

    def __post_init__(self) -> None:
        if self.requested_kbps < 0:
            raise ValueError(
                "Requested bandwidth cannot be negative.",
            )

        if self.allocated_kbps < 0:
            raise ValueError(
                "Allocated bandwidth cannot be negative.",
            )

        if self.allocated_kbps > self.requested_kbps:
            raise ValueError(
                "Allocated bandwidth cannot exceed requested bandwidth.",
            )