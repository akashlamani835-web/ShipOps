from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.events.evaluator import evaluate_rule
from app.events.models import EventRule, EventSeverity
from app.telemetry.models import MetricDefinition, TelemetrySample


def build_metric() -> MetricDefinition:
    return MetricDefinition(
        id=uuid4(),
        code="packet_loss",
        name="Packet Loss",
        unit="percent",
        minimum_value=0,
        maximum_value=100,
        active=True,
    )


def build_rule(
    metric_id,
    *,
    operator: str = ">",
    threshold: float = 30,
    active: bool = True,
) -> EventRule:
    return EventRule(
        id=uuid4(),
        code="packet_loss_high",
        name="High Packet Loss",
        event_type="NETWORK_DEGRADATION",
        metric_definition_id=metric_id,
        operator=operator,
        threshold=threshold,
        duration_seconds=180,
        severity=EventSeverity.HIGH,
        active=active,
    )


def build_sample(
    metric_id,
    *,
    value: float,
) -> TelemetrySample:
    observed_at = datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    received_at = datetime(
        2026,
        9,
        9,
        12,
        0,
        1,
        tzinfo=timezone.utc,
    )

    return TelemetrySample(
        id=uuid4(),
        asset_id=uuid4(),
        metric_definition_id=metric_id,
        value=value,
        observed_at=observed_at,
        received_at=received_at,
        source="simulator",
        source_sequence=1,
        quality="good",
        idempotency_key=str(uuid4()),
    )


def test_value_above_threshold_matches():
    metric = build_metric()
    rule = build_rule(metric.id, operator=">")
    sample = build_sample(metric.id, value=38)

    assert evaluate_rule(rule, sample) is True


def test_value_below_threshold_does_not_match():
    metric = build_metric()
    rule = build_rule(metric.id, operator=">")
    sample = build_sample(metric.id, value=12)

    assert evaluate_rule(rule, sample) is False


def test_greater_than_or_equal_operator():
    metric = build_metric()
    rule = build_rule(
        metric.id,
        operator=">=",
        threshold=30,
    )
    sample = build_sample(metric.id, value=30)

    assert evaluate_rule(rule, sample) is True


def test_less_than_operator():
    metric = build_metric()
    rule = build_rule(
        metric.id,
        operator="<",
        threshold=30,
    )
    sample = build_sample(metric.id, value=20)

    assert evaluate_rule(rule, sample) is True


def test_less_than_or_equal_operator():
    metric = build_metric()
    rule = build_rule(
        metric.id,
        operator="<=",
        threshold=30,
    )
    sample = build_sample(metric.id, value=30)

    assert evaluate_rule(rule, sample) is True


def test_inactive_rule_does_not_match():
    metric = build_metric()

    rule = build_rule(
        metric.id,
        active=False,
    )

    sample = build_sample(
        metric.id,
        value=90,
    )

    assert evaluate_rule(rule, sample) is False


def test_different_metric_does_not_match():
    metric = build_metric()

    rule = build_rule(metric.id)

    sample = build_sample(
        uuid4(),
        value=90,
    )

    assert evaluate_rule(rule, sample) is False


def test_unsupported_operator_raises():
    metric = build_metric()

    rule = build_rule(
        metric.id,
        operator="==",
    )

    sample = build_sample(
        metric.id,
        value=90,
    )

    with pytest.raises(
        ValueError,
        match="Unsupported event rule operator",
    ):
        evaluate_rule(rule, sample)