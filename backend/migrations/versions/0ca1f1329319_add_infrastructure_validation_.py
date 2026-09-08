"""add infrastructure validation constraints

Revision ID: 0ca1f1329319
Revises: 470bd8bc7ab4
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0ca1f1329319"
down_revision: Union[str, Sequence[str], None] = "470bd8bc7ab4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add database-level validation constraints."""

    op.create_check_constraint(
        "deck_number_positive",
        "decks",
        "deck_number > 0",
    )

    op.create_check_constraint(
        "speed_mbps_positive",
        "network_interfaces",
        "speed_mbps IS NULL OR speed_mbps > 0",
    )

    op.create_check_constraint(
        "capacity_mbps_positive",
        "network_links",
        "capacity_mbps IS NULL OR capacity_mbps > 0",
    )

    op.create_check_constraint(
        "latency_ms_non_negative",
        "network_links",
        "latency_ms IS NULL OR latency_ms >= 0",
    )

    op.create_check_constraint(
        "packet_loss_percent_valid",
        "network_links",
        (
            "packet_loss_percent IS NULL "
            "OR (packet_loss_percent >= 0 "
            "AND packet_loss_percent <= 100)"
        ),
    )


def downgrade() -> None:
    """Remove database-level validation constraints."""

    op.drop_constraint(
        "packet_loss_percent_valid",
        "network_links",
        type_="check",
    )

    op.drop_constraint(
        "latency_ms_non_negative",
        "network_links",
        type_="check",
    )

    op.drop_constraint(
        "capacity_mbps_positive",
        "network_links",
        type_="check",
    )

    op.drop_constraint(
        "speed_mbps_positive",
        "network_interfaces",
        type_="check",
    )

    op.drop_constraint(
        "deck_number_positive",
        "decks",
        type_="check",
    )