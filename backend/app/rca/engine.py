from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import OperationalEvent
from app.models.asset import Asset
from app.rca.schemas import (
    RCACandidate,
    RCAResult,
)
from app.topology.service import TopologyService


class RCAEngine:
    """
    Deterministic root-cause analysis for network-related events.

    Candidate ranking uses:
    - asset role
    - topology proximity
    - physical network connectivity

    The engine does not use an LLM.
    """

    INFRASTRUCTURE_WEIGHTS = {
        "router": 60.0,
        "switch": 55.0,
        "access_point": 45.0,
        "gateway": 50.0,
    }

    ENDPOINT_WEIGHTS = {
        "pos_terminal": 15.0,
        "workstation": 10.0,
        "printer": 8.0,
        "service": 20.0,
    }

    def __init__(
        self,
        db: Session,
        topology: TopologyService | None = None,
    ) -> None:
        self._db = db
        self._topology = (
            topology
            if topology is not None
            else TopologyService.from_database(db)
        )

    def analyze(
        self,
        event_id: UUID,
    ) -> RCAResult:
        """Analyze one operational event and rank candidate root causes."""

        event = self._db.get(
            OperationalEvent,
            event_id,
        )

        if event is None:
            raise ValueError(
                f"Operational event '{event_id}' not found.",
            )

        affected_asset = self._db.get(
            Asset,
            event.asset_id,
        )

        if affected_asset is None:
            raise ValueError(
                f"Affected asset '{event.asset_id}' not found.",
            )

        distances = self._topology.asset_distances(
            str(event.asset_id),
        )

        if not distances:
            return RCAResult(
                event_id=event.id,
                affected_asset_id=affected_asset.id,
                affected_asset_identifier=affected_asset.identifier,
                root_cause_asset_id=None,
                root_cause_identifier=None,
                confidence=0.0,
                severity=event.severity,
                explanation=(
                    "No connected topology candidates were found for "
                    f"affected asset {affected_asset.identifier}."
                ),
                candidates=(),
            )

        candidate_ids = [
            UUID(asset_id)
            for asset_id in distances
        ]

        assets = list(
            self._db.scalars(
                select(Asset).where(
                    Asset.id.in_(candidate_ids),
                )
            )
        )

        asset_by_id = {
            str(asset.id): asset
            for asset in assets
        }

        candidates: list[RCACandidate] = []

        for asset_id, distance in distances.items():
            asset = asset_by_id.get(asset_id)

            if asset is None:
                continue

            connectivity_degree = (
                self._topology.asset_connectivity_degree(
                    asset_id,
                )
            )

            score, reasons = self._score_candidate(
                asset=asset,
                distance=distance,
                connectivity_degree=connectivity_degree,
            )

            candidates.append(
                RCACandidate(
                    asset_id=asset.id,
                    identifier=asset.identifier,
                    asset_type=asset.asset_type,
                    distance=distance,
                    score=score,
                    reasons=tuple(reasons),
                )
            )

        candidates.sort(
            key=lambda candidate: (
                -candidate.score,
                candidate.distance,
                candidate.identifier,
            )
        )

        ranked_candidates = tuple(candidates)

        if not ranked_candidates:
            return RCAResult(
                event_id=event.id,
                affected_asset_id=affected_asset.id,
                affected_asset_identifier=affected_asset.identifier,
                root_cause_asset_id=None,
                root_cause_identifier=None,
                confidence=0.0,
                severity=event.severity,
                explanation=(
                    "Topology candidates existed, but none could be "
                    "resolved to current assets."
                ),
                candidates=(),
            )

        winner = ranked_candidates[0]

        confidence = self._calculate_confidence(
            ranked_candidates,
        )

        explanation = self._build_explanation(
            affected_asset=affected_asset,
            winner=winner,
            confidence=confidence,
        )

        return RCAResult(
            event_id=event.id,
            affected_asset_id=affected_asset.id,
            affected_asset_identifier=affected_asset.identifier,
            root_cause_asset_id=winner.asset_id,
            root_cause_identifier=winner.identifier,
            confidence=confidence,
            severity=event.severity,
            explanation=explanation,
            candidates=ranked_candidates,
        )

    def _score_candidate(
        self,
        *,
        asset: Asset,
        distance: int,
        connectivity_degree: int,
    ) -> tuple[float, list[str]]:
        """Calculate a transparent deterministic candidate score."""

        score = 0.0
        reasons: list[str] = []

        infrastructure_weight = self.INFRASTRUCTURE_WEIGHTS.get(
            asset.asset_type,
        )

        endpoint_weight = self.ENDPOINT_WEIGHTS.get(
            asset.asset_type,
        )

        if infrastructure_weight is not None:
            score += infrastructure_weight
            reasons.append(
                f"network infrastructure role "
                f"(+{infrastructure_weight:.0f})"
            )
        elif endpoint_weight is not None:
            score += endpoint_weight
            reasons.append(
                f"endpoint/service role (+{endpoint_weight:.0f})"
            )
        else:
            score += 5.0
            reasons.append("unknown asset role (+5)")

        distance_bonus = max(
            0.0,
            10.0 - ((distance - 1) * 3.0),
        )

        score += distance_bonus

        reasons.append(
            f"topology proximity (+{distance_bonus:.0f})"
        )

        connectivity_bonus = min(
            20.0,
            connectivity_degree * 5.0,
        )

        score += connectivity_bonus

        reasons.append(
            f"network connectivity "
            f"({connectivity_degree} links, +{connectivity_bonus:.0f})"
        )

        if asset.status.lower() in {
            "offline",
            "degraded",
            "failed",
            "unknown",
        }:
            score += 20.0
            reasons.append(
                f"asset status '{asset.status}' (+20)"
            )
        else:
            reasons.append(
                f"asset status '{asset.status}'"
            )

        return score, reasons

    @staticmethod
    def _calculate_confidence(
        candidates: tuple[RCACandidate, ...],
    ) -> float:
        """
        Convert the winner's separation from the runner-up into
        a bounded confidence score.
        """

        if not candidates:
            return 0.0

        winner_score = candidates[0].score

        if len(candidates) == 1:
            return 0.95

        runner_up_score = candidates[1].score

        if winner_score <= 0:
            return 0.0

        separation = (
            winner_score - runner_up_score
        ) / winner_score

        confidence = 0.50 + (
            separation * 0.50
        )

        return round(
            min(
                max(confidence, 0.0),
                0.99,
            ),
            3,
        )

    @staticmethod
    def _build_explanation(
        *,
        affected_asset: Asset,
        winner: RCACandidate,
        confidence: float,
    ) -> str:
        """Build a human-readable deterministic RCA explanation."""

        reasons = "; ".join(
            winner.reasons,
        )

        return (
            f"Probable root cause for event on "
            f"{affected_asset.identifier} is "
            f"{winner.identifier}. "
            f"Confidence: {confidence:.1%}. "
            f"Supporting factors: {reasons}."
        )