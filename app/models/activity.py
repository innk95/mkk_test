from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, types
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LtreeType(types.UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw: object) -> str:
        return "ltree"


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("activities.id", ondelete="SET NULL"),
        nullable=True,
    )
    # path проставляется в триггере в файле update_activity_path.sql
    path: Mapped[str | None] = mapped_column(
        LtreeType, nullable=True, deferred=True
    )

    parent: Mapped[Activity | None] = relationship(
        "Activity", back_populates="children", remote_side="Activity.id"
    )
    children: Mapped[list[Activity]] = relationship(
        "Activity", back_populates="parent"
    )
