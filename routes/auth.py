import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import create_session_cookie, get_current_user
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/login")
async def login_page(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from main import flash, get_flash_messages, templates

    user = await get_current_user(request, db)
    if user is not None:
        if user.role == "Admin":
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/inventory", status_code=303)

    flash_messages = get_flash_messages(request)
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        context={
            "current_user": None,
            "error": None,
            "username": "",
            "flash_messages": flash_messages,
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from main import flash, get_flash_messages, templates

    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")

    if not username or not password:
        flash_messages = get_flash_messages(request)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "current_user": None,
                "error": "Please enter both username and password.",
                "username": username,
                "flash_messages": flash_messages,
            },
        )

    try:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
    except Exception:
        logger.exception("Database error during login for username='%s'", username)
        flash_messages = get_flash_messages(request)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "current_user": None,
                "error": "An unexpected error occurred. Please try again.",
                "username": username,
                "flash_messages": flash_messages,
            },
        )

    if user is None or not pwd_context.verify(password, user.hashed_password):
        logger.warning("Failed login attempt for username='%s'", username)
        flash_messages = get_flash_messages(request)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "current_user": None,
                "error": "Invalid username or password.",
                "username": username,
                "flash_messages": flash_messages,
            },
        )

    logger.info("User '%s' logged in successfully.", user.username)

    cookie_value = create_session_cookie(user.id)

    if user.role == "Admin":
        redirect_url = "/dashboard"
    else:
        redirect_url = "/inventory"

    response = RedirectResponse(url=redirect_url, status_code=303)

    import config

    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=cookie_value,
        max_age=config.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )

    flash(request, "Welcome back, {}!".format(user.display_name or user.username), "success")

    return response


@router.get("/register")
async def register_page(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from main import get_flash_messages, templates

    user = await get_current_user(request, db)
    if user is not None:
        if user.role == "Admin":
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/inventory", status_code=303)

    flash_messages = get_flash_messages(request)
    return templates.TemplateResponse(
        request,
        "auth/register.html",
        context={
            "current_user": None,
            "errors": None,
            "field_errors": None,
            "form_data": None,
            "flash_messages": flash_messages,
        },
    )


@router.post("/register")
async def register_submit(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from main import flash, get_flash_messages, templates

    form = await request.form()
    username = form.get("username", "").strip()
    display_name = form.get("display_name", "").strip()
    password = form.get("password", "")
    confirm_password = form.get("confirm_password", "")

    form_data = {
        "username": username,
        "display_name": display_name,
    }

    errors = []
    field_errors = {}

    if not username:
        errors.append("Username is required.")
        field_errors["username"] = "Username is required."
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters long.")
        field_errors["username"] = "Username must be at least 3 characters long."
    elif len(username) > 50:
        errors.append("Username must be 50 characters or fewer.")
        field_errors["username"] = "Username must be 50 characters or fewer."

    if not display_name:
        errors.append("Display name is required.")
        field_errors["display_name"] = "Display name is required."
    elif len(display_name) > 100:
        errors.append("Display name must be 100 characters or fewer.")
        field_errors["display_name"] = "Display name must be 100 characters or fewer."

    if not password:
        errors.append("Password is required.")
        field_errors["password"] = "Password is required."
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
        field_errors["password"] = "Password must be at least 8 characters long."

    if not confirm_password:
        errors.append("Please confirm your password.")
        field_errors["confirm_password"] = "Please confirm your password."
    elif password and confirm_password != password:
        errors.append("Passwords do not match.")
        field_errors["confirm_password"] = "Passwords do not match."

    if not field_errors.get("username") and username:
        try:
            result = await db.execute(select(User).where(User.username == username))
            existing_user = result.scalar_one_or_none()
            if existing_user is not None:
                errors.append("Username '{}' is already taken.".format(username))
                field_errors["username"] = "This username is already taken."
        except Exception:
            logger.exception("Database error checking username uniqueness for '%s'", username)
            errors.append("An unexpected error occurred. Please try again.")

    if errors:
        flash_messages = get_flash_messages(request)
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "current_user": None,
                "errors": errors,
                "field_errors": field_errors,
                "form_data": form_data,
                "flash_messages": flash_messages,
            },
        )

    try:
        hashed_password = pwd_context.hash(password)

        new_user = User(
            username=username,
            display_name=display_name,
            hashed_password=hashed_password,
            role="Staff",
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info("New user registered: '%s' (id=%s)", new_user.username, new_user.id)
    except Exception:
        await db.rollback()
        logger.exception("Error creating user '%s'", username)
        flash_messages = get_flash_messages(request)
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "current_user": None,
                "errors": ["An unexpected error occurred. Please try again."],
                "field_errors": None,
                "form_data": form_data,
                "flash_messages": flash_messages,
            },
        )

    cookie_value = create_session_cookie(new_user.id)

    response = RedirectResponse(url="/inventory", status_code=303)

    import config

    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=cookie_value,
        max_age=config.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )

    flash(request, "Account created successfully! Welcome to StockPilot.", "success")

    return response


@router.post("/logout")
async def logout(request: Request):
    from main import flash

    import config

    flash(request, "You have been signed out.", "info")

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(
        key=config.SESSION_COOKIE_NAME,
        path="/",
    )

    logger.info("User logged out.")

    return response