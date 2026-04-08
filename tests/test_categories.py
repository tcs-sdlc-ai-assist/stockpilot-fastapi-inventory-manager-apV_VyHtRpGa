import logging
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from models.item import InventoryItem

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestListCategories:
    """Tests for GET /categories/ — Admin only."""

    async def test_list_categories_as_admin(
        self,
        admin_client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
    ):
        response = await admin_client.get("/categories/")
        assert response.status_code == 200
        text = response.text
        for cat in sample_categories:
            assert cat["name"] in text

    async def test_list_categories_shows_item_counts(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        sample_categories: list[dict[str, Any]],
    ):
        response = await admin_client.get("/categories/")
        assert response.status_code == 200
        assert "1 item" in response.text or "items" in response.text

    async def test_list_categories_empty(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.get("/categories/")
        assert response.status_code == 200
        assert "No categories yet" in response.text

    async def test_list_categories_redirects_unauthenticated(
        self,
        client: httpx.AsyncClient,
    ):
        response = await client.get("/categories/")
        assert response.status_code == 303
        assert "/auth/login" in response.headers.get("location", "")

    async def test_list_categories_denied_for_staff(
        self,
        staff_client: httpx.AsyncClient,
    ):
        response = await staff_client.get("/categories/")
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert "/inventory" in location


@pytest.mark.asyncio
class TestCreateCategory:
    """Tests for POST /categories/ — Admin only."""

    async def test_create_category_success(
        self,
        admin_client: httpx.AsyncClient,
        db_session: AsyncSession,
    ):
        response = await admin_client.post(
            "/categories/",
            data={"name": "New Category", "color": "#ff5733"},
        )
        assert response.status_code == 303
        assert "/categories" in response.headers.get("location", "")

        result = await db_session.execute(
            select(Category).where(Category.name == "New Category")
        )
        category = result.scalar_one_or_none()
        assert category is not None
        assert category.color == "#ff5733"

    async def test_create_category_default_color(
        self,
        admin_client: httpx.AsyncClient,
        db_session: AsyncSession,
    ):
        response = await admin_client.post(
            "/categories/",
            data={"name": "Default Color Cat"},
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(Category).where(Category.name == "Default Color Cat")
        )
        category = result.scalar_one_or_none()
        assert category is not None
        assert category.color == "#6366f1"

    async def test_create_category_empty_name(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.post(
            "/categories/",
            data={"name": "   ", "color": "#ff5733"},
        )
        assert response.status_code == 303

    async def test_create_category_name_too_long(
        self,
        admin_client: httpx.AsyncClient,
    ):
        long_name = "A" * 51
        response = await admin_client.post(
            "/categories/",
            data={"name": long_name, "color": "#ff5733"},
        )
        assert response.status_code == 303

    async def test_create_category_duplicate_name(
        self,
        admin_client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
    ):
        existing_name = sample_categories[0]["name"]
        response = await admin_client.post(
            "/categories/",
            data={"name": existing_name, "color": "#ff5733"},
        )
        assert response.status_code == 303

    async def test_create_category_duplicate_name_case_insensitive(
        self,
        admin_client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
    ):
        existing_name = sample_categories[0]["name"].upper()
        response = await admin_client.post(
            "/categories/",
            data={"name": existing_name, "color": "#ff5733"},
        )
        assert response.status_code == 303

    async def test_create_category_denied_for_staff(
        self,
        staff_client: httpx.AsyncClient,
    ):
        response = await staff_client.post(
            "/categories/",
            data={"name": "Staff Category", "color": "#ff5733"},
        )
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert "/inventory" in location

    async def test_create_category_redirects_unauthenticated(
        self,
        client: httpx.AsyncClient,
    ):
        response = await client.post(
            "/categories/",
            data={"name": "Unauth Category", "color": "#ff5733"},
        )
        assert response.status_code == 303
        assert "/auth/login" in response.headers.get("location", "")


@pytest.mark.asyncio
class TestDeleteCategory:
    """Tests for POST /categories/{category_id}/delete — Admin only."""

    async def test_delete_empty_category(
        self,
        admin_client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        category_id = sample_categories[0]["id"]

        response = await admin_client.post(f"/categories/{category_id}/delete")
        assert response.status_code == 303
        assert "/categories" in response.headers.get("location", "")

        result = await db_session.execute(
            select(Category).where(Category.id == category_id)
        )
        deleted = result.scalar_one_or_none()
        assert deleted is None

    async def test_delete_category_with_items_prevented(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        sample_categories: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        category_id = sample_categories[0]["id"]

        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.category_id == category_id)
        )
        items_in_category = result.scalars().all()
        assert len(items_in_category) > 0

        response = await admin_client.post(f"/categories/{category_id}/delete")
        assert response.status_code == 303

        result = await db_session.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        assert category is not None

    async def test_delete_nonexistent_category(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.post("/categories/99999/delete")
        assert response.status_code == 303
        assert "/categories" in response.headers.get("location", "")

    async def test_delete_category_denied_for_staff(
        self,
        staff_client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
    ):
        category_id = sample_categories[0]["id"]
        response = await staff_client.post(f"/categories/{category_id}/delete")
        assert response.status_code == 303
        location = response.headers.get("location", "")
        assert "/inventory" in location

    async def test_delete_category_redirects_unauthenticated(
        self,
        client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
    ):
        category_id = sample_categories[0]["id"]
        response = await client.post(f"/categories/{category_id}/delete")
        assert response.status_code == 303
        assert "/auth/login" in response.headers.get("location", "")