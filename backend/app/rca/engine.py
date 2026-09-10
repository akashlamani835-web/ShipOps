from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.evaluator import evaluate_rule
from app.events.models import EventRule, OperationalEvent
from app.models.asset import Asset
from app.rca.schemas import (
    RCACandidate,
    RCAClusterResult,
    RCAResult,
)
from app.telemetry.models import TelemetrySample
from app.topology.service import TopologyService


class RCAEngine:
    """
    Deterministic root-cause analysis for network-related events.

    Single-event ranking uses:
    - asset role
    - topology proximity
    - physical network connectivity
    - corroborating telemetry

    Cluster analysis additionally uses:
    - number of affected events sharing a candidate
    - common topology relationship across affected assets

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

    TELEMETRY_LOOKBACK_SECONDS = 300

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

        rule = self._db.get(
            EventRule,
            event.rule_id,
        )

        if rule is None:
            raise ValueError(
                f"Event rule '{event.rule_id}' not found.",
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

        candidates = self._build_candidates(
            event=event,
            rule=rule,
            distances_by_affected_asset={
                str(event.asset_id): distances,
            },
            shared_event_counts={},
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

    def analyze_cluster(
        self,
        event_ids: list[UUID] | tuple[UUID, ...],
    ) -> RCAClusterResult:
        """
        Analyze multiple operational events together.

        A candidate receives a shared-impact bonus when it is connected
        to multiple affected assets in the supplied event cluster.
        """

        normalized_event_ids = tuple(event_ids)

        if not normalized_event_ids:
            raise ValueError(
                "At least one event ID is required for cluster RCA.",
            )

        events = self._load_events(normalized_event_ids)

        affected_assets = list(
            self._db.scalars(
                select(Asset).where(
                    Asset.id.in_(
                        {
                            event.asset_id
                            for event in events
                        }
                    ),
                )
            )
        )

        asset_by_id = {
            asset.id: asset
            for asset in affected_assets
        }

        affected_asset_identifiers = tuple(
            asset_by_id[event.asset_id].identifier
            for event in events
        )

        severity = self._highest_severity(
            event.severity
            for event in events
        )

        distances_by_affected_asset: dict[
            str,
            dict[str, int],
        ] = {}

        for event in events:
            distances_by_affected_asset[
                str(event.asset_id)
            ] = self._topology.asset_distances(
                str(event.asset_id),
            )

        shared_event_counts = self._calculate_shared_event_counts(
            distances_by_affected_asset,
        )

        representative_event = events[0]

        rule_cache: dict[UUID, EventRule] = {}

        for event in events:
            rule = self._db.get(
                EventRule,
                event.rule_id,
            )

            if rule is None:
                raise ValueError(
                    f"Event rule '{event.rule_id}' not found.",
                )

            rule_cache[event.id] = rule

        candidates = self._build_cluster_candidates(
            events=events,
            rule_cache=rule_cache,
            distances_by_affected_asset=distances_by_affected_asset,
            shared_event_counts=shared_event_counts,
        )

        ranked_candidates = tuple(candidates)

        if not ranked_candidates:
            return RCAClusterResult(
                event_ids=normalized_event_ids,
                affected_asset_ids=tuple(
                    event.asset_id
                    for event in events
                ),
                affected_asset_identifiers=affected_asset_identifiers,
                root_cause_asset_id=None,
                root_cause_identifier=None,
                confidence=0.0,
                severity=severity,
                explanation=(
                    "No common topology candidates were found across "
                    "the supplied operational events."
                ),
                candidates=(),
            )

        winner = ranked_candidates[0]

        confidence = self._calculate_confidence(
            ranked_candidates,
        )

        explanation = self._build_cluster_explanation(
            affected_asset_identifiers=affected_asset_identifiers,
            winner=winner,
            confidence=confidence,
        )

        return RCAClusterResult(
            event_ids=normalized_event_ids,
            affected_asset_ids=tuple(
                event.asset_id
                for event in events
            ),
            affected_asset_identifiers=affected_asset_identifiers,
            root_cause_asset_id=winner.asset_id,
            root_cause_identifier=winner.identifier,
            confidence=confidence,
            severity=severity,
            explanation=explanation,
            candidates=ranked_candidates,
        )

    def _load_events(
        self,
        event_ids: tuple[UUID, ...],
    ) -> list[OperationalEvent]:
        """Load events and preserve the caller's event ordering."""

        events_by_id = {
            event.id: event
            for event in self._db.scalars(
                select(OperationalEvent).where(
                    OperationalEvent.id.in_(event_ids),
                )
            )
        }

        missing_event_ids = [
            event_id
            for event_id in event_ids
            if event_id not in events_by_id
        ]

        if missing_event_ids:
            raise ValueError(
                "Operational event(s) not found: "
                + ", ".join(
                    str(event_id)
                    for event_id in missing_event_ids
                ),
            )

        return [
            events_by_id[event_id]
            for event_id in event_ids
        ]

    def _build_candidates(
        self,
        *,
        event: OperationalEvent,
        rule: EventRule,
        distances_by_affected_asset: dict[str, dict[str, int]],
        shared_event_counts: dict[str, int],
    ) -> list[RCACandidate]:
        """Build candidates for single-event RCA."""

        distances = distances_by_affected_asset[
            str(event.asset_id)
        ]

        return self._build_candidates_from_distances(
            event=event,
            rule=rule,
            distances=distances,
            shared_event_counts=shared_event_counts,
        )

    def _build_cluster_candidates(
        self,
        *,
        events: list[OperationalEvent],
        rule_cache: dict[UUID, EventRule],
        distances_by_affected_asset: dict[str, dict[str, int]],
        shared_event_counts: dict[str, int],
    ) -> list[RCACandidate]:
        """Build and aggregate candidates for a multi-event cluster."""

        candidate_data: dict[str, dict] = {}

        for event in events:
            rule = rule_cache[event.id]

            distances = distances_by_affected_asset[
                str(event.asset_id)
            ]

            single_event_candidates = (
                self._build_candidates_from_distances(
                    event=event,
                    rule=rule,
                    distances=distances,
                    shared_event_counts=shared_event_counts,
                )
            )

            for candidate in single_event_candidates:
                existing = candidate_data.get(
                    str(candidate.asset_id),
                )

                if existing is None:
                    candidate_data[
                        str(candidate.asset_id)
                    ] = {
                        "candidate": candidate,
                        "total_score": candidate.score,
                        "max_distance": candidate.distance,
                        "telemetry_support": (
                            candidate.telemetry_support
                        ),
                        "shared_event_support": (
                            candidate.shared_event_support
                        ),
                        "reasons": list(candidate.reasons),
                    }
                    continue

                existing["total_score"] += candidate.score
                existing["max_distance"] = min(
                    existing["max_distance"],
                    candidate.distance,
                )
                existing["telemetry_support"] += (
                    candidate.telemetry_support
                )
                existing["shared_event_support"] = max(
                    existing["shared_event_support"],
                    candidate.shared_event_support,
                )
                existing["reasons"].extend(
                    candidate.reasons,
                )

        candidates: list[RCACandidate] = []

        assets = list(
            self._db.scalars(
                select(Asset).where(
                    Asset.id.in_(
                        {
                            UUID(asset_id)
                            for asset_id in candidate_data
                        }
                    ),
                )
            )
        )

        asset_by_id = {
            str(asset.id): asset
            for asset in assets
        }

        for asset_id, data in candidate_data.items():
            asset = asset_by_id.get(asset_id)

            if asset is None:
                continue

            score = data["total_score"]

            candidates.append(
                RCACandidate(
                    asset_id=asset.id,
                    identifier=asset.identifier,
                    asset_type=asset.asset_type,
                    distance=data["max_distance"],
                    score=score,
                    telemetry_support=data["telemetry_support"],
                    shared_event_support=data[
                        "shared_event_support"
                    ],
                    reasons=tuple(
                        dict.fromkeys(
                            data["reasons"],
                        )
                    ),
                )
            )

        candidates.sort(
            key=lambda candidate: (
                -candidate.score,
                -candidate.shared_event_support,
                -candidate.telemetry_support,
                candidate.distance,
                candidate.identifier,
            )
        )

        return candidates

    def _build_candidates_from_distances(
        self,
        *,
        event: OperationalEvent,
        rule: EventRule,
        distances: dict[str, int],
        shared_event_counts: dict[str, int],
    ) -> list[RCACandidate]:
        """Build candidate records from one event's topology distances."""

        if not distances:
            return []

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

            telemetry_support = (
                self._count_correlating_telemetry(
                    asset_id=asset.id,
                    metric_definition_id=rule.metric_definition_id,
                    event=event,
                    rule=rule,
                )
            )

            shared_event_support = shared_event_counts.get(
                asset_id,
                1,
            )

            score, reasons = self._score_candidate(
                asset=asset,
                distance=distance,
                connectivity_degree=connectivity_degree,
                telemetry_support=telemetry_support,
                shared_event_support=shared_event_support,
            )

            candidates.append(
                RCACandidate(
                    asset_id=asset.id,
                    identifier=asset.identifier,
                    asset_type=asset.asset_type,
                    distance=distance,
                    score=score,
                    telemetry_support=telemetry_support,
                    shared_event_support=shared_event_support,
                    reasons=tuple(reasons),
                )
            )

        candidates.sort(
            key=lambda candidate: (
                -candidate.score,
                -candidate.shared_event_support,
                -candidate.telemetry_support,
                candidate.distance,
                candidate.identifier,
            )
        )

        return candidates

    @staticmethod
    def _calculate_shared_event_counts(
        distances_by_affected_asset: dict[
            str,
            dict[str, int],
        ],
    ) -> dict[str, int]:
        """
        Count how many distinct affected assets can reach each
        candidate through physical topology.
        """

        shared_event_counts: dict[str, int] = {}

        for distances in distances_by_affected_asset.values():
            for candidate_asset_id in distances:
                shared_event_counts[candidate_asset_id] = (
                    shared_event_counts.get(
                        candidate_asset_id,
                        0,
                    )
                    + 1
                )

        return shared_event_counts

    def _score_candidate(
        self,
        *,
        asset: Asset,
        distance: int,
        connectivity_degree: int,
        telemetry_support: int,
        shared_event_support: int,
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
            f"({connectivity_degree} links, "
            f"+{connectivity_bonus:.0f})"
        )

        telemetry_bonus = min(
            30.0,
            telemetry_support * 10.0,
        )

        score += telemetry_bonus

        if telemetry_support > 0:
            reasons.append(
                f"corroborating telemetry "
                f"({telemetry_support} matching samples, "
                f"+{telemetry_bonus:.0f})"
            )
        else:
            reasons.append(
                "no corroborating candidate telemetry"
            )

        shared_event_bonus = max(
            0.0,
            (shared_event_support - 1) * 20.0,
        )

        score += shared_event_bonus

        if shared_event_support > 1:
            reasons.append(
                f"shared impact across "
                f"{shared_event_support} affected assets "
                f"(+{shared_event_bonus:.0f})"
            )
        else:
            reasons.append(
                "single affected-asset path"
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
    def _highest_severity(
        severities,
    ):
        """Return the highest severity present in an event cluster."""

        severity_order = {
            "info": 0,
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }

        return max(
            severities,
            key=lambda severity: severity_order[
                severity.value
            ],
        )

    @staticmethod
    def _build_explanation(
        *,
        affected_asset: Asset,
        winner: RCACandidate,
        confidence: float,
    ) -> str:
        """Build a human-readable single-event RCA explanation."""

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

    @staticmethod
    def _build_cluster_explanation(
        *,
        affected_asset_identifiers: tuple[str, ...],
        winner: RCACandidate,
        confidence: float,
    ) -> str:
        """Build a human-readable cluster RCA explanation."""

        affected = ", ".join(
            affected_asset_identifiers,
        )

        reasons = "; ".join(
            winner.reasons,
        )

        return (
            f"Probable common root cause for affected assets "
            f"{affected} is {winner.identifier}. "
            f"Confidence: {confidence:.1%}. "
            f"Supporting factors: {reasons}."
        )

    def _count_correlating_telemetry(
        self,
        *,
        asset_id: UUID,
        metric_definition_id: UUID,
        event: OperationalEvent,
        rule: EventRule,
    ) -> int:
        """
        Count recent candidate telemetry samples that also satisfy
        the event rule.

        This is bounded to a short window immediately preceding the
        event occurrence.
        """

        start_at = (
            event.occurred_at
            - timedelta(
                seconds=self.TELEMETRY_LOOKBACK_SECONDS,
            )
        )

        samples = list(
            self._db.scalars(
                select(TelemetrySample)
                .where(
                    TelemetrySample.asset_id == asset_id,
                    TelemetrySample.metric_definition_id
                    == metric_definition_id,
                    TelemetrySample.observed_at >= start_at,
                    TelemetrySample.observed_at
                    <= event.occurred_at,
                )
                .order_by(
                    TelemetrySample.observed_at,
                )
            )
        )

        return sum(
            1
            for sample in samples
            if evaluate_rule(rule, sample)
        )