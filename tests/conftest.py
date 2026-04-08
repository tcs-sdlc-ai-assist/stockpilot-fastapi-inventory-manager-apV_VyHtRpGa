import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database import Base, get_db
from main import app

logger = logging.getLogger(__name__)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

test_async_session_maker = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.DefaultEventLoopPolicy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_admin(db_session: AsyncSession) -> dict[str, Any]:
    from passlib.context import CryptContext

    from models.user import User

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    admin = User(
        username="testadmin",
        display_name="Test Admin",
        hashed_password=pwd_context.hash("adminpass123"),
        role="Admin",
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    return {
        "id": admin.id,
        "username": "testadmin",
        "password": "adminpass123",
        "display_name": "Test Admin",
        "role": "Admin",
        "user": admin,
    }


@pytest_asyncio.fixture
async def sample_staff(db_session: AsyncSession) -> dict[str, Any]:
    from passlib.context import CryptContext

    from models.user import User

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    staff = User(
        username="teststaff",
        display_name="Test Staff",
        hashed_password=pwd_context.hash("staffpass123"),
        role="Staff",
    )
    db_session.add(staff)
    await db_session.commit()
    await db_session.refresh(staff)

    return {
        "id": staff.id,
        "username": "teststaff",
        "password": "staffpass123",
        "display_name": "Test Staff",
        "role": "Staff",
        "user": staff,
    }


@pytest_asyncio.fixture
async def sample_categories(db_session: AsyncSession) -> list[dict[str, Any]]:
    from models.category import Category

    categories_data = [
        {"name": "Test Electronics", "color": "#3b82f6"},
        {"name": "Test Clothing", "color": "#ec4899"},
        {"name": "Test Food", "color": "#f59e0b"},
    ]

    created = []
    for cat_data in categories_data:
        category = Category(name=cat_data["name"], color=cat_data["color"])
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        created.append({
            "id": category.id,
            "name": category.name,
            "color": category.color,
            "category": category,
        })

    return created


@pytest_asyncio.fixture
async def sample_items(
    db_session: AsyncSession,
    sample_admin: dict[str, Any],
    sample_categories: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    from models.item import InventoryItem

    items_data = [
        {
            "name": "Test Arduino Uno",
            "sku": "TEST-ARD-001",
            "description": "A test microcontroller board",
            "quantity": 50,
            "unit_price": 27.50,
            "reorder_level": 10,
            "category_id": sample_categories[0]["id"],
            "created_by_id": sample_admin["id"],
        },
        {
            "name": "Test T-Shirt",
            "sku": "TEST-TSH-001",
            "description": "A test clothing item",
            "quantity": 5,
            "unit_price": 19.99,
            "reorder_level": 10,
            "category_id": sample_categories[1]["id"],
            "created_by_id": sample_admin["id"],
        },
        {
            "name": "Test Out of Stock Item",
            "sku": "TEST-OOS-001",
            "description": "An item with zero quantity",
            "quantity": 0,
            "unit_price": 9.99,
            "reorder_level": 5,
            "category_id": sample_categories[2]["id"],
            "created_by_id": sample_admin["id"],
        },
    ]

    created = []
    for item_data in items_data:
        item = InventoryItem(**item_data)
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        created.append({
            "id": item.id,
            "name": item.name,
            "sku": item.sku,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "reorder_level": item.reorder_level,
            "category_id": item.category_id,
            "created_by_id": item.created_by_id,
            "item": item,
        })

    return created


async def _login_user(
    client: httpx.AsyncClient,
    username: str,
    password: str,
) -> dict[str, str]:
    response = await client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    cookies = {}
    for cookie_name, cookie_value in response.cookies.items():
        cookies[cookie_name] = cookie_value

    if not cookies and response.status_code == 303:
        set_cookie_header = response.headers.get("set-cookie", "")
        if set_cookie_header:
            import config
            cookie_key = config.SESSION_COOKIE_NAME
            for part in set_cookie_header.split(";"):
                part = part.strip()
                if part.startswith(f"{cookie_key}="):
                    cookies[cookie_key] = part.split("=", 1)[1]
                    break

    return cookies


@pytest_asyncio.fixture
async def admin_cookies(
    client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
) -> dict[str, str]:
    cookies = await _login_user(client, sample_admin["username"], sample_admin["password"])
    return cookies


@pytest_asyncio.fixture
async def staff_cookies(
    client: httpx.AsyncClient,
    sample_staff: dict[str, Any],
) -> dict[str, str]:
    cookies = await _login_user(client, sample_staff["username"], sample_staff["password"])
    return cookies


@pytest_asyncio.fixture
async def admin_client(
    admin_cookies: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies=admin_cookies,
        follow_redirects=False,
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def staff_client(
    staff_cookies: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies=staff_cookies,
        follow_redirects=False,
    ) as ac:
        yield ac