from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

organization_activity = Table(
    "organization_activity",
    Base.metadata,
    Column(
        "organization_id",
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "activity_id",
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    building_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("buildings.id", ondelete="RESTRICT"),
        nullable=False,
    )

    building: Mapped["Building"] = relationship(
        back_populates="organizations"
    )
    phones: Mapped[list["OrganizationPhone"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    activities: Mapped[list["Activity"]] = relationship(
        secondary=organization_activity
    )


class OrganizationPhone(Base):
    __tablename__ = "organization_phones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    phone: Mapped[str] = mapped_column(String(50), nullable=False)

    organization: Mapped["Organization"] = relationship(
        back_populates="phones"
    )
