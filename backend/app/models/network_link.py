from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.network_interface import NetworkInterface


class NetworkLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "network_links"

    source_interface_id: Mapped[UUID] = mapped_column(
        ForeignKey("network_interfaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    destination_interface_id: Mapped[UUID] = mapped_column(
        ForeignKey("network_interfaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    link_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    capacity_mbps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    packet_loss_percent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    operational_up: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    source_interface: Mapped["NetworkInterface"] = relationship(
        foreign_keys=[source_interface_id],
        back_populates="outgoing_links",
    )

    destination_interface: Mapped["NetworkInterface"] = relationship(
        foreign_keys=[destination_interface_id],
        back_populates="incoming_links",
    )