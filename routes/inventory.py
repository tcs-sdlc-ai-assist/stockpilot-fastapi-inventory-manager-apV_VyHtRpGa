import logging
import math
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_user, require_auth
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["inventory"])

ITEMS_PER_PAGE = 12


def _can_edit_item(user: User, item: InventoryItem) -> bool:
    if user.role == "Admin":
        return True
    return item.created_by_id == user.id


@router.get("/")
async def list_items(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    search: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "name",
    sort_order: Annotated[str, Query()] = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
):
    from main import flash, get_flashed_messages, templates

    current_user = await get_current_user(request, db)

    stmt = select(InventoryItem).options(
        selectinload(InventoryItem.category),
        selectinload(InventoryItem.owner),
    )

    count_stmt = select(func.count(InventoryItem.id))

    if search:
        search_filter = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(InventoryItem.name).like(search_filter)
            | func.lower(InventoryItem.description).like(search_filter)
        )
        count_stmt = count_stmt.where(
            func.lower(InventoryItem.name).like(search_filter)
            | func.lower(InventoryItem.description).like(search_filter)
        )

    category_id = None
    category_name = None
    if category:
        try:
            category_id = int(category)
            stmt = stmt.where(InventoryItem.category_id == category_id)
            count_stmt = count_stmt.where(InventoryItem.category_id == category_id)
            cat_result = await db.execute(
                select(Category.name).where(Category.id == category_id)
            )
            category_name = cat_result.scalar_one_or_none()
        except (ValueError, TypeError):
            pass

    sort_column_map = {
        "name": InventoryItem.name,
        "quantity": InventoryItem.quantity,
        "price": InventoryItem.unit_price,
        "created_at": InventoryItem.created_at,
    }
    sort_col = sort_column_map.get(sort_by, InventoryItem.name)
    if sort_order == "desc":
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())

    total_result = await db.execute(count_stmt)
    total_items = total_result.scalar() or 0
    total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))

    if page > total_pages:
        page = total_pages

    offset = (page - 1) * ITEMS_PER_PAGE
    stmt = stmt.offset(offset).limit(ITEMS_PER_PAGE)

    result = await db.execute(stmt)
    items = result.scalars().all()

    cat_result = await db.execute(select(Category).order_by(Category.name))
    categories = cat_result.scalars().all()

    flash_messages = get_flashed_messages(request)

    return templates.TemplateResponse(
        request,
        "inventory/list.html",
        context={
            "current_user": current_user,
            "items": items,
            "categories": categories,
            "search": search or "",
            "category_id": category_id,
            "category_name": category_name,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "current_page": page,
            "total_pages": total_pages,
            "flash_messages": flash_messages,
        },
    )


@router.get("/create")
async def add_item_form(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_auth)],
):
    from main import templates

    cat_result = await db.execute(select(Category).order_by(Category.name))
    categories = cat_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "inventory/form.html",
        context={
            "current_user": current_user,
            "item": None,
            "categories": categories,
            "form_data": None,
            "errors": None,
        },
    )


@router.post("/add")
async def add_item_submit(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_auth)],
    name: Annotated[str, Form()],
    quantity: Annotated[str, Form()],
    unit_price: Annotated[str, Form()],
    sku: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    category_id: Annotated[str | None, Form()] = None,
    reorder_level: Annotated[str | None, Form()] = None,
):
    from main import flash, templates

    cat_result = await db.execute(select(Category).order_by(Category.name))
    categories = cat_result.scalars().all()

    form_data = {
        "name": name,
        "sku": sku or "",
        "description": description or "",
        "category_id": category_id or "",
        "quantity": quantity,
        "unit_price": unit_price,
        "reorder_level": reorder_level or "10",
    }

    errors: dict[str, str] = {}

    name = name.strip()
    if not name:
        errors["name"] = "Name is required."

    try:
        qty = int(quantity)
        if qty < 0:
            errors["quantity"] = "Quantity must be zero or greater."
    except (ValueError, TypeError):
        errors["quantity"] = "Quantity must be a valid integer."
        qty = 0

    try:
        price = float(unit_price)
        if price < 0:
            errors["unit_price"] = "Unit price must be zero or greater."
    except (ValueError, TypeError):
        errors["unit_price"] = "Unit price must be a valid number."
        price = 0.0

    try:
        reorder = int(reorder_level) if reorder_level else 10
        if reorder < 0:
            errors["reorder_level"] = "Reorder level must be zero or greater."
    except (ValueError, TypeError):
        errors["reorder_level"] = "Reorder level must be a valid integer."
        reorder = 10

    cat_id = None
    if category_id:
        try:
            cat_id = int(category_id)
        except (ValueError, TypeError):
            errors["category_id"] = "Invalid category."

    if sku and sku.strip():
        sku_val = sku.strip()
        existing_sku = await db.execute(
            select(InventoryItem).where(InventoryItem.sku == sku_val)
        )
        if existing_sku.scalar_one_or_none() is not None:
            errors["sku"] = "An item with this SKU already exists."
    else:
        sku_val = None

    if errors:
        return templates.TemplateResponse(
            request,
            "inventory/form.html",
            context={
                "current_user": current_user,
                "item": None,
                "categories": categories,
                "form_data": form_data,
                "errors": errors,
            },
            status_code=422,
        )

    item = InventoryItem(
        name=name,
        sku=sku_val,
        description=description.strip() if description else None,
        quantity=qty,
        unit_price=price,
        reorder_level=reorder,
        category_id=cat_id,
        created_by_id=current_user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    logger.info(
        "User '%s' created inventory item '%s' (id=%s).",
        current_user.username,
        item.name,
        item.id,
    )
    flash(request, f"Item '{item.name}' added successfully.", "success")
    return RedirectResponse(url="/inventory", status_code=303)


@router.get("/{item_id}")
async def item_detail(
    request: Request,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from main import get_flashed_messages, templates

    current_user = await get_current_user(request, db)

    result = await db.execute(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.owner),
        )
        .where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        from main import templates as t

        return t.TemplateResponse(
            request,
            "errors/404.html",
            context={"current_user": current_user},
            status_code=404,
        )

    can_edit = False
    if current_user is not None:
        can_edit = _can_edit_item(current_user, item)

    creator = item.owner

    flash_messages = get_flashed_messages(request)

    return templates.TemplateResponse(
        request,
        "inventory/detail.html",
        context={
            "current_user": current_user,
            "item": item,
            "can_edit": can_edit,
            "creator": creator,
            "flash_messages": flash_messages,
        },
    )


@router.get("/{item_id}/edit")
async def edit_item_form(
    request: Request,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_auth)],
):
    from main import flash, templates

    result = await db.execute(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.owner),
        )
        .where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={"current_user": current_user},
            status_code=404,
        )

    if not _can_edit_item(current_user, item):
        flash(request, "You do not have permission to edit this item.", "error")
        return RedirectResponse(url="/inventory", status_code=303)

    cat_result = await db.execute(select(Category).order_by(Category.name))
    categories = cat_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "inventory/form.html",
        context={
            "current_user": current_user,
            "item": item,
            "categories": categories,
            "form_data": None,
            "errors": None,
        },
    )


@router.post("/{item_id}/edit")
async def edit_item_submit(
    request: Request,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_auth)],
    name: Annotated[str, Form()],
    quantity: Annotated[str, Form()],
    unit_price: Annotated[str, Form()],
    sku: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    category_id: Annotated[str | None, Form()] = None,
    reorder_level: Annotated[str | None, Form()] = None,
):
    from main import flash, templates

    result = await db.execute(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.owner),
        )
        .where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={"current_user": current_user},
            status_code=404,
        )

    if not _can_edit_item(current_user, item):
        flash(request, "You do not have permission to edit this item.", "error")
        return RedirectResponse(url="/inventory", status_code=303)

    cat_result = await db.execute(select(Category).order_by(Category.name))
    categories = cat_result.scalars().all()

    form_data = {
        "name": name,
        "sku": sku or "",
        "description": description or "",
        "category_id": category_id or "",
        "quantity": quantity,
        "unit_price": unit_price,
        "reorder_level": reorder_level or "10",
    }

    errors: dict[str, str] = {}

    name = name.strip()
    if not name:
        errors["name"] = "Name is required."

    try:
        qty = int(quantity)
        if qty < 0:
            errors["quantity"] = "Quantity must be zero or greater."
    except (ValueError, TypeError):
        errors["quantity"] = "Quantity must be a valid integer."
        qty = 0

    try:
        price = float(unit_price)
        if price < 0:
            errors["unit_price"] = "Unit price must be zero or greater."
    except (ValueError, TypeError):
        errors["unit_price"] = "Unit price must be a valid number."
        price = 0.0

    try:
        reorder = int(reorder_level) if reorder_level else 10
        if reorder < 0:
            errors["reorder_level"] = "Reorder level must be zero or greater."
    except (ValueError, TypeError):
        errors["reorder_level"] = "Reorder level must be a valid integer."
        reorder = 10

    cat_id = None
    if category_id:
        try:
            cat_id = int(category_id)
        except (ValueError, TypeError):
            errors["category_id"] = "Invalid category."

    if sku and sku.strip():
        sku_val = sku.strip()
        existing_sku = await db.execute(
            select(InventoryItem).where(
                InventoryItem.sku == sku_val,
                InventoryItem.id != item_id,
            )
        )
        if existing_sku.scalar_one_or_none() is not None:
            errors["sku"] = "An item with this SKU already exists."
    else:
        sku_val = None

    if errors:
        return templates.TemplateResponse(
            request,
            "inventory/form.html",
            context={
                "current_user": current_user,
                "item": item,
                "categories": categories,
                "form_data": form_data,
                "errors": errors,
            },
            status_code=422,
        )

    item.name = name
    item.sku = sku_val
    item.description = description.strip() if description else None
    item.quantity = qty
    item.unit_price = price
    item.reorder_level = reorder
    item.category_id = cat_id

    await db.commit()
    await db.refresh(item)

    logger.info(
        "User '%s' updated inventory item '%s' (id=%s).",
        current_user.username,
        item.name,
        item.id,
    )
    flash(request, f"Item '{item.name}' updated successfully.", "success")
    return RedirectResponse(url=f"/inventory/{item.id}", status_code=303)


@router.post("/{item_id}/delete")
async def delete_item(
    request: Request,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_auth)],
):
    from main import flash

    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        flash(request, "Item not found.", "error")
        return RedirectResponse(url="/inventory", status_code=303)

    if not _can_edit_item(current_user, item):
        flash(request, "You do not have permission to delete this item.", "error")
        return RedirectResponse(url="/inventory", status_code=303)

    item_name = item.name
    await db.delete(item)
    await db.commit()

    logger.info(
        "User '%s' deleted inventory item '%s' (id=%s).",
        current_user.username,
        item_name,
        item_id,
    )
    flash(request, f"Item '{item_name}' deleted successfully.", "success")
    return RedirectResponse(url="/inventory", status_code=303)