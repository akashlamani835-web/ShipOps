from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.deck import Deck
    from app.models.organization import Organization


class Vessel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vessels"

    __table_args__ = (
    UniqueConstraint(
        "organization_id",
        "code",
        name="uq_vessels_organization_id_code",
    ),
)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="vessels",
    )

    decks: Mapped[list["Deck"]] = relationship(
        back_populates="vessel",
        cascade="all, delete-orphan",
    )