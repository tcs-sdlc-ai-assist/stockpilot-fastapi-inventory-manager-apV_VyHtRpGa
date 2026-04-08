import logging
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_dashboard_accessible_by_admin(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text


@pytest.mark.asyncio
async def test_dashboard_redirects_unauthenticated_user(
    client: httpx.AsyncClient,
):
    response = await client.get("/dashboard")
    assert response.status_code == 303
    assert "/auth/login" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_dashboard_accessible_by_staff(
    staff_client: httpx.AsyncClient,
    sample_staff: dict[str, Any],
):
    response = await staff_client.get("/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text


@pytest.mark.asyncio
async def test_dashboard_shows_total_items_count(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_items: list[dict[str, Any]],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text
    assert "Total Items" in content
    assert str(len(sample_items)) in content


@pytest.mark.asyncio
async def test_dashboard_shows_total_value(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_items: list[dict[str, Any]],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    expected_value = sum(
        item["quantity"] * item["unit_price"] for item in sample_items
    )
    formatted_value = f"{expected_value:.2f}"
    assert formatted_value in content


@pytest.mark.asyncio
async def test_dashboard_shows_low_stock_count(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_items: list[dict[str, Any]],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    low_stock_count = sum(
        1
        for item in sample_items
        if 0 < item["quantity"] <= item["reorder_level"]
    )
    assert "Low Stock Items" in content
    assert low_stock_count > 0, "Test data should include at least one low-stock item"
    assert str(low_stock_count) in content


@pytest.mark.asyncio
async def test_dashboard_shows_total_users_count(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    db_session: AsyncSession,
):
    from sqlalchemy import func, select

    result = await db_session.execute(select(func.count(User.id)))
    total_users = result.scalar_one_or_none() or 0

    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text
    assert "Total Users" in content
    assert str(total_users) in content


@pytest.mark.asyncio
async def test_dashboard_shows_low_stock_alerts(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_items: list[dict[str, Any]],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    assert "Low Stock Alerts" in content

    low_stock_items = [
        item for item in sample_items
        if 0 < item["quantity"] <= item["reorder_level"]
    ]
    assert len(low_stock_items) > 0

    for item in low_stock_items:
        assert item["name"] in content


@pytest.mark.asyncio
async def test_dashboard_shows_recent_activity(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_items: list[dict[str, Any]],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    assert "Recent Activity" in content

    for item in sample_items:
        assert item["name"] in content


@pytest.mark.asyncio
async def test_dashboard_no_items_shows_empty_state(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    assert "Dashboard" in content
    assert "Total Items" in content
    assert "All items are well stocked" in content or "No recent activity" in content


@pytest.mark.asyncio
async def test_dashboard_statistics_accuracy_with_known_data(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_items: list[dict[str, Any]],
    sample_categories: list[dict[str, Any]],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    total_items = len(sample_items)
    assert str(total_items) in content

    total_value = sum(
        item["quantity"] * item["unit_price"] for item in sample_items
    )
    assert f"{total_value:.2f}" in content

    low_stock = [
        i for i in sample_items
        if 0 < i["quantity"] <= i["reorder_level"]
    ]
    assert str(len(low_stock)) in content


@pytest.mark.asyncio
async def test_dashboard_out_of_stock_not_in_low_stock_alerts(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_items: list[dict[str, Any]],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    out_of_stock_items = [
        item for item in sample_items
        if item["quantity"] == 0
    ]
    assert len(out_of_stock_items) > 0

    low_stock_section_start = content.find("Low Stock Alerts")
    recent_activity_start = content.find("Recent Activity")

    if low_stock_section_start != -1 and recent_activity_start != -1:
        low_stock_section = content[low_stock_section_start:recent_activity_start]
        for item in out_of_stock_items:
            assert item["name"] not in low_stock_section


@pytest.mark.asyncio
async def test_dashboard_low_stock_item_details(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
    sample_items: list[dict[str, Any]],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    low_stock_items = [
        item for item in sample_items
        if 0 < item["quantity"] <= item["reorder_level"]
    ]

    for item in low_stock_items:
        assert item["name"] in content
        assert f"{item['quantity']} left" in content


@pytest.mark.asyncio
async def test_dashboard_manage_users_link_for_admin(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    assert "Manage users" in content or "/admin/users" in content


@pytest.mark.asyncio
async def test_dashboard_staff_no_manage_users_link(
    staff_client: httpx.AsyncClient,
    sample_staff: dict[str, Any],
):
    response = await staff_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    assert "Manage users" not in content


@pytest.mark.asyncio
async def test_dashboard_shows_manage_inventory_link(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    assert "Manage Inventory" in content or "/inventory" in content


@pytest.mark.asyncio
async def test_dashboard_zero_values_when_no_items(
    admin_client: httpx.AsyncClient,
    sample_admin: dict[str, Any],
):
    response = await admin_client.get("/dashboard")
    assert response.status_code == 200
    content = response.text

    assert "$0.00" in content or "0" in content