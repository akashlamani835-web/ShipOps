from datetime import datetime

from app.events.evaluator import evaluate_rule
from app.events.models import EventRule
from app.telemetry.models import TelemetrySample


def condition_sustained(
    rule: EventRule,
    samples: list[TelemetrySample],
) -> bool:
    """
    Return True when a rule condition remains true for the
    configured duration.

    Samples are evaluated in observation-time order. Samples that
    do not satisfy the rule break the sustained-condition window.
    """

    if not rule.active:
        return False

    if not samples:
        return False

    relevant_samples = [
        sample
        for sample in samples
        if sample.metric_definition_id == rule.metric_definition_id
    ]

    if not relevant_samples:
        return False

    relevant_samples.sort(
        key=lambda sample: sample.observed_at,
    )

    window_start: datetime | None = None

    for sample in relevant_samples:
        if not evaluate_rule(rule, sample):
            window_start = None
            continue

        if window_start is None:
            window_start = sample.observed_at

        elapsed_seconds = (
            sample.observed_at - window_start
        ).total_seconds()

        if elapsed_seconds >= rule.duration_seconds:
            return True

    return False