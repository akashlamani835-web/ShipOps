from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.events.duration import condition_sustained
from app.events.models import EventRule, EventSeverity
from app.telemetry.models import TelemetrySample


METRIC_ID = uuid4()
OTHER_METRIC_ID = uuid4()


def build_rule(
    *,
    duration_seconds: int = 180,
    active: bool = True,
) -> EventRule:
    return EventRule(
        id=uuid4(),
        code="packet_loss_high",
        name="High Packet Loss",
        event_type="NETWORK_DEGRADATION",
        metric_definition_id=METRIC_ID,
        operator=">",
        threshold=30,
        duration_seconds=duration_seconds,
        severity=EventSeverity.HIGH,
        active=active,
    )


def build_sample(
    *,
    value: float,
    observed_at: datetime,
    metric_definition_id=METRIC_ID,
) -> TelemetrySample:
    return TelemetrySample(
        id=uuid4(),
        asset_id=uuid4(),
        metric_definition_id=metric_definition_id,
        value=value,
        observed_at=observed_at,
        received_at=observed_at + timedelta(seconds=1),
        source="edge_gateway",
        source_sequence=1,
        quality="good",
        idempotency_key=str(uuid4()),
    )


def base_time() -> datetime:
    return datetime(
        2026,
        9,
        9,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )


def test_no_samples_returns_false():
    rule = build_rule()

    assert condition_sustained(rule, []) is False


def test_condition_never_crosses_threshold():
    start = base_time()

    samples = [
        build_sample(
            value=10,
            observed_at=start,
        ),
        build_sample(
            value=20,
            observed_at=start + timedelta(minutes=1),
        ),
        build_sample(
            value=25,
            observed_at=start + timedelta(minutes=3),
        ),
    ]

    assert condition_sustained(
        build_rule(),
        samples,
    ) is False


def test_condition_crosses_threshold_but_not_long_enough():
    start = base_time()

    samples = [
        build_sample(
            value=38,
            observed_at=start,
        ),
        build_sample(
            value=41,
            observed_at=start + timedelta(minutes=1),
        ),
        build_sample(
            value=37,
            observed_at=start + timedelta(minutes=2),
        ),
    ]

    assert condition_sustained(
        build_rule(duration_seconds=180),
        samples,
    ) is False


def test_condition_is_sustained_for_required_duration():
    start = base_time()

    samples = [
        build_sample(
            value=38,
            observed_at=start,
        ),
        build_sample(
            value=41,
            observed_at=start + timedelta(minutes=1),
        ),
        build_sample(
            value=37,
            observed_at=start + timedelta(minutes=3),
        ),
    ]

    assert condition_sustained(
        build_rule(duration_seconds=180),
        samples,
    ) is True


def test_normal_sample_breaks_sustained_window():
    start = base_time()

    samples = [
        build_sample(
            value=38,
            observed_at=start,
        ),
        build_sample(
            value=41,
            observed_at=start + timedelta(minutes=1),
        ),
        build_sample(
            value=12,
            observed_at=start + timedelta(minutes=2),
        ),
        build_sample(
            value=39,
            observed_at=start + timedelta(minutes=4),
        ),
    ]

    assert condition_sustained(
        build_rule(duration_seconds=180),
        samples,
    ) is False


def test_out_of_order_samples_are_sorted_by_observed_time():
    start = base_time()

    samples = [
        build_sample(
            value=37,
            observed_at=start + timedelta(minutes=3),
        ),
        build_sample(
            value=38,
            observed_at=start,
        ),
        build_sample(
            value=41,
            observed_at=start + timedelta(minutes=1),
        ),
    ]

    assert condition_sustained(
        build_rule(duration_seconds=180),
        samples,
    ) is True


def test_different_metric_is_ignored():
    start = base_time()

    samples = [
        build_sample(
            value=90,
            observed_at=start,
            metric_definition_id=OTHER_METRIC_ID,
        ),
        build_sample(
            value=20,
            observed_at=start + timedelta(minutes=5),
        ),
    ]

    assert condition_sustained(
        build_rule(),
        samples,
    ) is False


def test_inactive_rule_returns_false():
    start = base_time()

    samples = [
        build_sample(
            value=90,
            observed_at=start,
        ),
        build_sample(
            value=90,
            observed_at=start + timedelta(minutes=3),
        ),
    ]

    assert condition_sustained(
        build_rule(
            active=False,
        ),
        samples,
    ) is False