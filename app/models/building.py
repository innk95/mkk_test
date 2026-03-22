from sqlalchemy import Double, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)

    organizations: Mapped[list["Organization"]] = relationship(
        back_populates="building"
    )
