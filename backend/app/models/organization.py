from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vessel import Vessel


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
    )

    vessels: Mapped[list["Vessel"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )