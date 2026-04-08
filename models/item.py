import logging
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

logger = logging.getLogger(__name__)


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reorder_level: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    category: Mapped["Category"] = relationship(  # noqa: F821
        "Category", back_populates="items"
    )
    owner: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="items"
    )

    @property
    def price(self) -> float:
        return self.unit_price

    @property
    def total_value(self) -> float:
        return self.quantity * self.unit_price

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.quantity <= self.reorder_level

    @property
    def is_out_of_stock(self) -> bool:
        return self.quantity <= 0

    @property
    def low_stock_threshold(self) -> int:
        return self.reorder_level

    def __repr__(self) -> str:
        return (
            f"<InventoryItem(id={self.id}, name='{self.name}', "
            f"quantity={self.quantity}, unit_price={self.unit_price})>"
        )