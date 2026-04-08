import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_auth
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    request: Request,
    current_user: Annotated[User, Depends(require_auth)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    from main import templates

    # Total items count
    result = await db.execute(select(func.count(InventoryItem.id)))
    total_items: int = result.scalar_one_or_none() or 0

    # Total inventory value
    result = await db.execute(
        select(func.coalesce(func.sum(InventoryItem.quantity * InventoryItem.unit_price), 0.0))
    )
    total_value: float = float(result.scalar_one_or_none() or 0.0)

    # Low stock count (quantity > 0 and quantity <= reorder_level)
    result = await db.execute(
        select(func.count(InventoryItem.id)).where(
            InventoryItem.quantity > 0,
            InventoryItem.quantity <= InventoryItem.reorder_level,
        )
    )
    low_stock_count: int = result.scalar_one_or_none() or 0

    # Total users count
    result = await db.execute(select(func.count(User.id)))
    total_users: int = result.scalar_one_or_none() or 0

    # Low stock items list
    result = await db.execute(
        select(InventoryItem)
        .where(
            InventoryItem.quantity > 0,
            InventoryItem.quantity <= InventoryItem.reorder_level,
        )
        .order_by(InventoryItem.quantity.asc())
    )
    low_stock_items = list(result.scalars().all())

    # 5 most recently updated items
    result = await db.execute(
        select(InventoryItem)
        .options()
        .order_by(InventoryItem.updated_at.desc().nullslast(), InventoryItem.created_at.desc())
        .limit(5)
    )
    recent_items_raw = list(result.scalars().all())

    # Eagerly load category names for recent items
    recent_items = []
    for item in recent_items_raw:
        category_name = None
        if item.category_id:
            cat_result = await db.execute(
                select(Category.name).where(Category.id == item.category_id)
            )
            category_name = cat_result.scalar_one_or_none()
        item.category_name = category_name  # type: ignore[attr-defined]
        recent_items.append(item)

    logger.info(
        "Dashboard loaded: total_items=%d, total_value=%.2f, low_stock=%d, users=%d",
        total_items,
        total_value,
        low_stock_count,
        total_users,
    )

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        context={
            "current_user": current_user,
            "total_items": total_items,
            "total_value": total_value,
            "low_stock_count": low_stock_count,
            "total_users": total_users,
            "low_stock_items": low_stock_items,
            "recent_items": recent_items,
        },
    )