import logging
from typing import Annotated

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import get_db
from models.user import User

logger = logging.getLogger(__name__)

serializer = URLSafeTimedSerializer(config.SECRET_KEY)


def create_session_cookie(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})


def verify_session_cookie(cookie_value: str) -> dict | None:
    try:
        data = serializer.loads(cookie_value, max_age=config.SESSION_MAX_AGE)
        return data
    except SignatureExpired:
        logger.warning("Session cookie has expired.")
        return None
    except BadSignature:
        logger.warning("Session cookie has invalid signature.")
        return None
    except Exception:
        logger.exception("Unexpected error verifying session cookie.")
        return None


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    cookie_value = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not cookie_value:
        return None

    session_data = verify_session_cookie(cookie_value)
    if session_data is None:
        return None

    user_id = session_data.get("user_id")
    if user_id is None:
        return None

    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            logger.warning("Session references non-existent user_id=%s", user_id)
        return user
    except Exception:
        logger.exception("Error querying user from session, user_id=%s", user_id)
        return None


async def require_auth(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    user = await get_current_user(request, db)
    if user is None:
        raise _redirect_to_login()
    return user


async def require_admin(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    user = await get_current_user(request, db)
    if user is None:
        raise _redirect_to_login()
    if user.role != "Admin":
        logger.warning(
            "User '%s' (role=%s) attempted to access admin resource.",
            user.username,
            user.role,
        )
        from main import flash

        flash(request, "You do not have permission to access that page.", "error")
        raise _redirect_to("/inventory")
    return user


def _redirect_to_login() -> Exception:
    response = RedirectResponse(url="/auth/login", status_code=303)
    raise _RedirectException(response)


def _redirect_to(url: str) -> Exception:
    response = RedirectResponse(url=url, status_code=303)
    raise _RedirectException(response)


class _RedirectException(Exception):
    def __init__(self, response: RedirectResponse) -> None:
        self.response = response


async def redirect_exception_handler(request: Request, exc: _RedirectException):
    return exc.response