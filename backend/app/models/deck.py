from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vessel import Vessel
    from app.models.zone import Zone


class Deck(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "decks"

    __table_args__ = (
        UniqueConstraint(
            "vessel_id",
            "deck_number",
            name="uq_decks_vessel_id_deck_number",
        ),
    )

    vessel_id: Mapped[UUID] = mapped_column(
        ForeignKey("vessels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    deck_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    vessel: Mapped["Vessel"] = relationship(
        back_populates="decks",
    )

    zones: Mapped[list["Zone"]] = relationship(
        back_populates="deck",
        cascade="all, delete-orphan",
    )