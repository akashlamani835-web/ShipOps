from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.deck import Deck


class Zone(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "zones"

    __table_args__ = (
        UniqueConstraint(
            "deck_id",
            "code",
            name="uq_zones_deck_id_code",
        ),
    )

    deck_id: Mapped[UUID] = mapped_column(
        ForeignKey("decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    deck: Mapped["Deck"] = relationship(
        back_populates="zones",
    )

    assets: Mapped[list["Asset"]] = relationship(
        back_populates="zone",
        cascade="all, delete-orphan",
    )