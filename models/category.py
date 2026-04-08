import logging

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

logger = logging.getLogger(__name__)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")

    items: Mapped[list["InventoryItem"]] = relationship(  # noqa: F821
        "InventoryItem",
        back_populates="category",
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', color='{self.color}')>"