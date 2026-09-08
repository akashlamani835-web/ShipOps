from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.zone import Zone


class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "assets"

    zone_id: Mapped[UUID] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    asset_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    identifier: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unknown",
        index=True,
    )

    zone: Mapped["Zone"] = relationship(
        back_populates="assets",
    )