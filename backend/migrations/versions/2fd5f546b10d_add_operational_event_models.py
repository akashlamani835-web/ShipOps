"""add operational event models

Revision ID: 2fd5f546b10d
Revises: a7baf05128a9
Create Date: 2026-09-09 17:20:35.378811

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2fd5f546b10d"
down_revision: Union[str, Sequence[str], None] = "a7baf05128a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create operational event models."""

    op.create_table(
        "event_rules",
        sa.Column(
            "code",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "metric_definition_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "operator",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "threshold",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "duration_seconds",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "INFO",
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="event_severity",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "duration_seconds > 0",
            name="event_rule_duration_positive",
        ),
        sa.ForeignKeyConstraint(
            ["metric_definition_id"],
            ["metric_definitions.id"],
            name=op.f(
                "fk_event_rules_metric_definition_id_metric_definitions"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_event_rules"),
        ),
        sa.UniqueConstraint(
            "code",
            name="uq_event_rules_code",
        ),
    )

    op.create_index(
        op.f("ix_event_rules_event_type"),
        "event_rules",
        ["event_type"],
        unique=False,
    )

    op.create_index(
        "ix_event_rules_metric_definition_id",
        "event_rules",
        ["metric_definition_id"],
        unique=False,
    )

    op.create_table(
        "operational_events",
        sa.Column(
            "asset_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "rule_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "INFO",
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="event_severity",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "ACKNOWLEDGED",
                "RESOLVED",
                name="event_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "summary",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(status = 'RESOLVED' AND resolved_at IS NOT NULL) "
            "OR (status <> 'RESOLVED' AND resolved_at IS NULL)",
            name="operational_event_resolution_consistent",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= occurred_at",
            name="operational_event_resolution_after_occurrence",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name=op.f(
                "fk_operational_events_asset_id_assets"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["event_rules.id"],
            name=op.f(
                "fk_operational_events_rule_id_event_rules"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_operational_events"),
        ),
    )

    op.create_index(
        "ix_operational_events_asset_id_occurred_at",
        "operational_events",
        ["asset_id", "occurred_at"],
        unique=False,
    )

    op.create_index(
        "ix_operational_events_event_type_occurred_at",
        "operational_events",
        ["event_type", "occurred_at"],
        unique=False,
    )

    op.create_table(
        "event_evidence",
        sa.Column(
            "event_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "telemetry_sample_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "evidence_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "explanation",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["operational_events.id"],
            name=op.f(
                "fk_event_evidence_event_id_operational_events"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["telemetry_sample_id"],
            ["telemetry_samples.id"],
            name=op.f(
                "fk_event_evidence_telemetry_sample_id_telemetry_samples"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_event_evidence"),
        ),
        sa.UniqueConstraint(
            "event_id",
            "telemetry_sample_id",
            name="uq_event_evidence_event_sample",
        ),
    )

    op.create_index(
        "ix_event_evidence_event_id",
        "event_evidence",
        ["event_id"],
        unique=False,
    )

    op.create_index(
        "ix_event_evidence_telemetry_sample_id",
        "event_evidence",
        ["telemetry_sample_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove operational event models."""

    op.drop_index(
        "ix_event_evidence_telemetry_sample_id",
        table_name="event_evidence",
    )

    op.drop_index(
        "ix_event_evidence_event_id",
        table_name="event_evidence",
    )

    op.drop_table("event_evidence")

    op.drop_index(
        "ix_operational_events_event_type_occurred_at",
        table_name="operational_events",
    )

    op.drop_index(
        "ix_operational_events_asset_id_occurred_at",
        table_name="operational_events",
    )

    op.drop_table("operational_events")

    op.drop_index(
        "ix_event_rules_metric_definition_id",
        table_name="event_rules",
    )

    op.drop_index(
        op.f("ix_event_rules_event_type"),
        table_name="event_rules",
    )

    op.drop_table("event_rules")