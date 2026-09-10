from operator import ge, gt, le, lt

from app.events.models import EventRule
from app.telemetry.models import TelemetrySample


OPERATORS = {
    ">": gt,
    ">=": ge,
    "<": lt,
    "<=": le,
}


def evaluate_rule(
    rule: EventRule,
    sample: TelemetrySample,
) -> bool:
    """
    Evaluate one telemetry sample against an event rule.

    Returns True when the sample satisfies the rule.
    """

    if not rule.active:
        return False

    if sample.metric_definition_id != rule.metric_definition_id:
        return False

    operator = OPERATORS.get(rule.operator)

    if operator is None:
        raise ValueError(
            f"Unsupported event rule operator: {rule.operator}",
        )

    return operator(
        sample.value,
        rule.threshold,
    )