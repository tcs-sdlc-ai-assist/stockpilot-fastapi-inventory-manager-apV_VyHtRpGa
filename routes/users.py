import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import get_db
from dependencies import require_admin
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users", tags=["users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/")
async def list_users(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    from main import flash, get_flashed_messages, templates

    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    flash_messages = get_flashed_messages(request)

    return templates.TemplateResponse(
        request,
        "users/list.html",
        context={
            "current_user": current_user,
            "users": users,
            "admin_username": config.ADMIN_USERNAME,
            "flash_messages": flash_messages,
        },
    )


@router.post("/")
async def create_user(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    role: Annotated[str, Form()],
    display_name: Annotated[str | None, Form()] = None,
) -> Response:
    from main import flash

    username = username.strip()
    display_name = display_name.strip() if display_name else None
    role = role.strip()

    if not username:
        flash(request, "Username is required.", "error")
        return RedirectResponse(url="/admin/users", status_code=303)

    if not password or len(password) < 6:
        flash(request, "Password must be at least 6 characters.", "error")
        return RedirectResponse(url="/admin/users", status_code=303)

    if role not in ("User", "Admin"):
        flash(request, "Invalid role. Must be 'User' or 'Admin'.", "error")
        return RedirectResponse(url="/admin/users", status_code=303)

    result = await db.execute(select(User).where(User.username == username))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        flash(request, f"Username '{username}' is already taken.", "error")
        return RedirectResponse(url="/admin/users", status_code=303)

    hashed_password = pwd_context.hash(password)

    new_user = User(
        username=username,
        display_name=display_name,
        hashed_password=hashed_password,
        role=role,
    )
    db.add(new_user)
    await db.commit()

    logger.info(
        "Admin '%s' created new user '%s' with role '%s'.",
        current_user.username,
        username,
        role,
    )
    flash(request, f"User '{username}' created successfully.", "success")
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/{user_id}/delete")
async def delete_user(
    request: Request,
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    from main import flash

    if current_user.id == user_id:
        flash(request, "You cannot delete your own account.", "error")
        return RedirectResponse(url="/admin/users", status_code=303)

    result = await db.execute(select(User).where(User.id == user_id))
    user_to_delete = result.scalar_one_or_none()

    if user_to_delete is None:
        flash(request, "User not found.", "error")
        return RedirectResponse(url="/admin/users", status_code=303)

    if user_to_delete.username == config.ADMIN_USERNAME:
        flash(request, "Cannot delete the default admin account.", "error")
        return RedirectResponse(url="/admin/users", status_code=303)

    deleted_username = user_to_delete.username
    await db.delete(user_to_delete)
    await db.commit()

    logger.info(
        "Admin '%s' deleted user '%s' (id=%s).",
        current_user.username,
        deleted_username,
        user_id,
    )
    flash(request, f"User '{deleted_username}' has been deleted.", "success")
    return RedirectResponse(url="/admin/users", status_code=303)