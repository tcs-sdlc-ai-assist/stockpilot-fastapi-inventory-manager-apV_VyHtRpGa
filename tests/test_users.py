import logging
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_list_users_as_admin(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
) -> None:
    response = await admin_client.get("/admin/users")
    assert response.status_code == 200
    assert b"User Management" in response.content
    assert sample_admin["username"].encode() in response.content


@pytest.mark.asyncio
async def test_list_users_as_staff_redirects(
    staff_client: httpx.AsyncClient,
    sample_staff: dict[str, Any],
) -> None:
    response = await staff_client.get("/admin/users")
    assert response.status_code == 303
    assert "/inventory" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_list_users_unauthenticated_redirects(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/admin/users")
    assert response.status_code == 303
    assert "/auth/login" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_create_user_as_admin(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    response = await admin_client.post(
        "/admin/users",
        data={
            "username": "newuser",
            "password": "newpass123",
            "display_name": "New User",
            "role": "User",
        },
    )
    assert response.status_code == 303
    assert "/admin/users" in response.headers.get("location", "")

    result = await db_session.execute(select(User).where(User.username == "newuser"))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.display_name == "New User"
    assert created_user.role == "User"


@pytest.mark.asyncio
async def test_create_admin_user(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    response = await admin_client.post(
        "/admin/users",
        data={
            "username": "newadmin",
            "password": "adminpass123",
            "display_name": "New Admin",
            "role": "Admin",
        },
    )
    assert response.status_code == 303

    result = await db_session.execute(select(User).where(User.username == "newadmin"))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.role == "Admin"


@pytest.mark.asyncio
async def test_create_user_duplicate_username(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
) -> None:
    response = await admin_client.post(
        "/admin/users",
        data={
            "username": sample_admin["username"],
            "password": "somepass123",
            "display_name": "Duplicate",
            "role": "User",
        },
    )
    assert response.status_code == 303
    assert "/admin/users" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_create_user_empty_username(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
) -> None:
    response = await admin_client.post(
        "/admin/users",
        data={
            "username": "",
            "password": "somepass123",
            "display_name": "No Username",
            "role": "User",
        },
    )
    assert response.status_code == 303
    assert "/admin/users" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_create_user_short_password(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
) -> None:
    response = await admin_client.post(
        "/admin/users",
        data={
            "username": "shortpw",
            "password": "abc",
            "display_name": "Short PW",
            "role": "User",
        },
    )
    assert response.status_code == 303
    assert "/admin/users" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_create_user_invalid_role(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
) -> None:
    response = await admin_client.post(
        "/admin/users",
        data={
            "username": "badrole",
            "password": "somepass123",
            "display_name": "Bad Role",
            "role": "SuperAdmin",
        },
    )
    assert response.status_code == 303
    assert "/admin/users" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_create_user_as_staff_denied(
    staff_client: httpx.AsyncClient,
    sample_staff: dict[str, Any],
) -> None:
    response = await staff_client.post(
        "/admin/users",
        data={
            "username": "staffcreated",
            "password": "somepass123",
            "display_name": "Staff Created",
            "role": "User",
        },
    )
    assert response.status_code == 303
    assert "/inventory" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_delete_user_as_admin(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_staff: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    staff_id = sample_staff["id"]

    response = await admin_client.post(f"/admin/users/{staff_id}/delete")
    assert response.status_code == 303
    assert "/admin/users" in response.headers.get("location", "")

    result = await db_session.execute(select(User).where(User.id == staff_id))
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is None


@pytest.mark.asyncio
async def test_delete_nonexistent_user(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
) -> None:
    response = await admin_client.post("/admin/users/99999/delete")
    assert response.status_code == 303
    assert "/admin/users" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_prevent_self_deletion(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
) -> None:
    admin_id = sample_admin["id"]

    response = await admin_client.post(f"/admin/users/{admin_id}/delete")
    assert response.status_code == 303
    assert "/admin/users" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_prevent_default_admin_deletion(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    from passlib.context import CryptContext

    import config

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    default_admin = User(
        username=config.ADMIN_USERNAME,
        display_name=config.ADMIN_DISPLAY_NAME,
        hashed_password=pwd_context.hash("defaultadminpass"),
        role="Admin",
    )
    db_session.add(default_admin)
    await db_session.commit()
    await db_session.refresh(default_admin)

    response = await admin_client.post(f"/admin/users/{default_admin.id}/delete")
    assert response.status_code == 303
    assert "/admin/users" in response.headers.get("location", "")

    result = await db_session.execute(
        select(User).where(User.id == default_admin.id)
    )
    still_exists = result.scalar_one_or_none()
    assert still_exists is not None


@pytest.mark.asyncio
async def test_delete_user_as_staff_denied(
    staff_client: httpx.AsyncClient,
    sample_staff: dict[str, Any],
    sample_admin: dict[str, Any],
) -> None:
    admin_id = sample_admin["id"]

    response = await staff_client.post(f"/admin/users/{admin_id}/delete")
    assert response.status_code == 303
    assert "/inventory" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_delete_user_unauthenticated(
    client: httpx.AsyncClient,
    sample_staff: dict[str, Any],
) -> None:
    staff_id = sample_staff["id"]

    response = await client.post(f"/admin/users/{staff_id}/delete")
    assert response.status_code == 303
    assert "/auth/login" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_list_users_shows_all_users(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_staff: dict[str, Any],
) -> None:
    response = await admin_client.get("/admin/users")
    assert response.status_code == 200
    content = response.content
    assert sample_admin["username"].encode() in content
    assert sample_staff["username"].encode() in content


@pytest.mark.asyncio
async def test_create_user_without_display_name(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    response = await admin_client.post(
        "/admin/users",
        data={
            "username": "nodisplay",
            "password": "somepass123",
            "display_name": "",
            "role": "User",
        },
    )
    assert response.status_code == 303

    result = await db_session.execute(select(User).where(User.username == "nodisplay"))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.role == "User"