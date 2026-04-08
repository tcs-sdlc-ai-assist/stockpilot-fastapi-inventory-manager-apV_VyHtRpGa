import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_admin
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/")
async def list_categories(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    from main import templates, get_flash_messages

    stmt = (
        select(
            Category,
            func.count(InventoryItem.id).label("item_count"),
        )
        .outerjoin(InventoryItem, InventoryItem.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    )
    result = await db.execute(stmt)
    rows = result.all()

    categories = []
    for row in rows:
        category = row[0]
        category.item_count = row[1]
        categories.append(category)

    flash_messages = get_flash_messages(request)

    return templates.TemplateResponse(
        request,
        "categories/list.html",
        context={
            "current_user": current_user,
            "categories": categories,
            "flash_messages": flash_messages,
        },
    )


@router.post("/")
async def create_category(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str = Form(...),
    color: str = Form("#6366f1"),
) -> RedirectResponse:
    from main import flash

    name = name.strip()
    if not name:
        flash(request, "Category name is required.", "error")
        return RedirectResponse(url="/categories", status_code=303)

    if len(name) > 50:
        flash(request, "Category name must be 50 characters or fewer.", "error")
        return RedirectResponse(url="/categories", status_code=303)

    result = await db.execute(
        select(Category).where(func.lower(Category.name) == name.lower())
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        flash(request, f"A category named '{name}' already exists.", "error")
        return RedirectResponse(url="/categories", status_code=303)

    category = Category(name=name, color=color)
    db.add(category)
    await db.commit()

    logger.info(
        "User '%s' created category '%s' (color=%s).",
        current_user.username,
        name,
        color,
    )
    flash(request, f"Category '{name}' created successfully.", "success")
    return RedirectResponse(url="/categories", status_code=303)


@router.post("/{category_id}/delete")
async def delete_category(
    request: Request,
    category_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    from main import flash

    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if category is None:
        flash(request, "Category not found.", "error")
        return RedirectResponse(url="/categories", status_code=303)

    item_count_result = await db.execute(
        select(func.count(InventoryItem.id)).where(
            InventoryItem.category_id == category_id
        )
    )
    item_count = item_count_result.scalar() or 0

    if item_count > 0:
        flash(
            request,
            f"Cannot delete category '{category.name}' because it has {item_count} item{'s' if item_count != 1 else ''} assigned. "
            "Remove or reassign items first.",
            "error",
        )
        return RedirectResponse(url="/categories", status_code=303)

    category_name = category.name
    await db.delete(category)
    await db.commit()

    logger.info(
        "User '%s' deleted category '%s' (id=%s).",
        current_user.username,
        category_name,
        category_id,
    )
    flash(request, f"Category '{category_name}' deleted successfully.", "success")
    return RedirectResponse(url="/categories", status_code=303)