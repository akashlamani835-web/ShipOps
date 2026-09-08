from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.network_link import NetworkLink


class NetworkInterface(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "network_interfaces"

    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "name",
            name="uq_network_interfaces_asset_id_name",
        ),
        CheckConstraint(
            "speed_mbps IS NULL OR speed_mbps > 0",
            name="speed_mbps_positive",
        ),
    )

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    interface_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    mac_address: Mapped[str | None] = mapped_column(
        String(17),
        nullable=True,
    )

    ipv4_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    speed_mbps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    administrative_up: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    operational_up: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    asset: Mapped["Asset"] = relationship()

    outgoing_links: Mapped[list["NetworkLink"]] = relationship(
        foreign_keys="NetworkLink.source_interface_id",
        back_populates="source_interface",
        cascade="all, delete-orphan",
    )

    incoming_links: Mapped[list["NetworkLink"]] = relationship(
        foreign_keys="NetworkLink.destination_interface_id",
        back_populates="destination_interface",
        cascade="all, delete-orphan",
    )