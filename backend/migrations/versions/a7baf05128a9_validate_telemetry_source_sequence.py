"""validate telemetry source sequence

Revision ID: a7baf05128a9
Revises: 6cc0f9aabcb7
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a7baf05128a9"
down_revision: Union[str, Sequence[str], None] = "6cc0f9aabcb7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enforce non-negative telemetry source sequences."""

    op.create_check_constraint(
        "telemetry_source_sequence_non_negative",
        "telemetry_samples",
        "source_sequence >= 0",
    )


def downgrade() -> None:
    """Remove telemetry source sequence validation."""

    op.drop_constraint(
        "telemetry_source_sequence_non_negative",
        "telemetry_samples",
        type_="check",
    )