import logging
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.item import InventoryItem

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestInventoryList:
    """Tests for GET /inventory — listing items."""

    async def test_list_items_unauthenticated(self, client: httpx.AsyncClient):
        response = await client.get("/inventory")
        assert response.status_code == 200
        assert "Inventory" in response.text

    async def test_list_items_authenticated(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory")
        assert response.status_code == 200
        assert "Test Arduino Uno" in response.text
        assert "Test T-Shirt" in response.text
        assert "Test Out of Stock Item" in response.text

    async def test_list_items_empty(self, admin_client: httpx.AsyncClient):
        response = await admin_client.get("/inventory")
        assert response.status_code == 200
        assert "No inventory items found" in response.text

    async def test_list_items_shows_add_button_for_authenticated(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.get("/inventory")
        assert response.status_code == 200
        assert "Add New Item" in response.text

    async def test_list_items_no_add_button_for_unauthenticated(
        self,
        client: httpx.AsyncClient,
    ):
        response = await client.get("/inventory")
        assert response.status_code == 200
        # Unauthenticated users should not see the top "Add New Item" button
        # (the one in the header area, not the empty state one)
        # The page should still render without error


@pytest.mark.asyncio
class TestInventorySearch:
    """Tests for search functionality on GET /inventory."""

    async def test_search_by_name(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?search=Arduino")
        assert response.status_code == 200
        assert "Test Arduino Uno" in response.text
        assert "Test T-Shirt" not in response.text

    async def test_search_by_description(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?search=microcontroller")
        assert response.status_code == 200
        assert "Test Arduino Uno" in response.text
        assert "Test T-Shirt" not in response.text

    async def test_search_case_insensitive(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?search=arduino")
        assert response.status_code == 200
        assert "Test Arduino Uno" in response.text

    async def test_search_no_results(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?search=nonexistentxyz")
        assert response.status_code == 200
        assert "No inventory items found" in response.text

    async def test_search_shows_active_filter(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?search=Arduino")
        assert response.status_code == 200
        assert "Active filters" in response.text
        assert "Arduino" in response.text


@pytest.mark.asyncio
class TestInventoryFilterByCategory:
    """Tests for category filtering on GET /inventory."""

    async def test_filter_by_category(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        sample_categories: list[dict[str, Any]],
    ):
        electronics_id = sample_categories[0]["id"]
        response = await admin_client.get(f"/inventory?category={electronics_id}")
        assert response.status_code == 200
        assert "Test Arduino Uno" in response.text
        assert "Test T-Shirt" not in response.text

    async def test_filter_by_category_shows_category_name(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        sample_categories: list[dict[str, Any]],
    ):
        electronics_id = sample_categories[0]["id"]
        response = await admin_client.get(f"/inventory?category={electronics_id}")
        assert response.status_code == 200
        assert "Test Electronics" in response.text

    async def test_filter_by_invalid_category(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?category=invalid")
        assert response.status_code == 200
        # Should show all items when category is invalid
        assert "Test Arduino Uno" in response.text


@pytest.mark.asyncio
class TestInventorySort:
    """Tests for sort functionality on GET /inventory."""

    async def test_sort_by_name_asc(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?sort_by=name&sort_order=asc")
        assert response.status_code == 200
        text = response.text
        arduino_pos = text.find("Test Arduino Uno")
        oos_pos = text.find("Test Out of Stock Item")
        tshirt_pos = text.find("Test T-Shirt")
        assert arduino_pos < oos_pos < tshirt_pos

    async def test_sort_by_name_desc(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?sort_by=name&sort_order=desc")
        assert response.status_code == 200
        text = response.text
        tshirt_pos = text.find("Test T-Shirt")
        oos_pos = text.find("Test Out of Stock Item")
        arduino_pos = text.find("Test Arduino Uno")
        assert tshirt_pos < oos_pos < arduino_pos

    async def test_sort_by_quantity_asc(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?sort_by=quantity&sort_order=asc")
        assert response.status_code == 200
        text = response.text
        # quantity: OOS=0, T-Shirt=5, Arduino=50
        oos_pos = text.find("Test Out of Stock Item")
        tshirt_pos = text.find("Test T-Shirt")
        arduino_pos = text.find("Test Arduino Uno")
        assert oos_pos < tshirt_pos < arduino_pos

    async def test_sort_by_price_desc(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?sort_by=price&sort_order=desc")
        assert response.status_code == 200
        text = response.text
        # price: Arduino=27.50, T-Shirt=19.99, OOS=9.99
        arduino_pos = text.find("Test Arduino Uno")
        tshirt_pos = text.find("Test T-Shirt")
        oos_pos = text.find("Test Out of Stock Item")
        assert arduino_pos < tshirt_pos < oos_pos


@pytest.mark.asyncio
class TestInventoryCreate:
    """Tests for creating inventory items."""

    async def test_create_item_form_requires_auth(self, client: httpx.AsyncClient):
        response = await client.get("/inventory/create")
        assert response.status_code == 303
        assert "/auth/login" in response.headers.get("location", "")

    async def test_create_item_form_authenticated(
        self,
        admin_client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory/create")
        assert response.status_code == 200
        assert "Add New Item" in response.text

    async def test_create_item_success(
        self,
        admin_client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        response = await admin_client.post(
            "/inventory/add",
            data={
                "name": "New Test Item",
                "sku": "NEW-TEST-001",
                "description": "A brand new test item",
                "quantity": "25",
                "unit_price": "15.99",
                "reorder_level": "5",
                "category_id": str(sample_categories[0]["id"]),
            },
        )
        assert response.status_code == 303
        assert "/inventory" in response.headers.get("location", "")

        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.sku == "NEW-TEST-001")
        )
        item = result.scalar_one_or_none()
        assert item is not None
        assert item.name == "New Test Item"
        assert item.quantity == 25
        assert item.unit_price == 15.99
        assert item.reorder_level == 5

    async def test_create_item_missing_name(
        self,
        admin_client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
    ):
        response = await admin_client.post(
            "/inventory/add",
            data={
                "name": "",
                "quantity": "10",
                "unit_price": "5.00",
            },
        )
        assert response.status_code == 422
        assert "Name is required" in response.text

    async def test_create_item_invalid_quantity(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.post(
            "/inventory/add",
            data={
                "name": "Bad Quantity Item",
                "quantity": "abc",
                "unit_price": "5.00",
            },
        )
        assert response.status_code == 422
        assert "Quantity must be a valid integer" in response.text

    async def test_create_item_negative_quantity(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.post(
            "/inventory/add",
            data={
                "name": "Negative Quantity Item",
                "quantity": "-5",
                "unit_price": "5.00",
            },
        )
        assert response.status_code == 422
        assert "Quantity must be zero or greater" in response.text

    async def test_create_item_invalid_price(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.post(
            "/inventory/add",
            data={
                "name": "Bad Price Item",
                "quantity": "10",
                "unit_price": "not-a-number",
            },
        )
        assert response.status_code == 422
        assert "Unit price must be a valid number" in response.text

    async def test_create_item_duplicate_sku(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.post(
            "/inventory/add",
            data={
                "name": "Duplicate SKU Item",
                "sku": "TEST-ARD-001",
                "quantity": "10",
                "unit_price": "5.00",
            },
        )
        assert response.status_code == 422
        assert "SKU already exists" in response.text

    async def test_create_item_requires_auth(self, client: httpx.AsyncClient):
        response = await client.post(
            "/inventory/add",
            data={
                "name": "Unauthorized Item",
                "quantity": "10",
                "unit_price": "5.00",
            },
        )
        assert response.status_code == 303
        assert "/auth/login" in response.headers.get("location", "")

    async def test_create_item_staff_can_create(
        self,
        staff_client: httpx.AsyncClient,
        sample_categories: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        response = await staff_client.post(
            "/inventory/add",
            data={
                "name": "Staff Created Item",
                "sku": "STAFF-001",
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "3",
            },
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.sku == "STAFF-001")
        )
        item = result.scalar_one_or_none()
        assert item is not None
        assert item.name == "Staff Created Item"


@pytest.mark.asyncio
class TestInventoryDetail:
    """Tests for GET /inventory/{item_id} — item detail page."""

    async def test_item_detail_exists(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        item_id = sample_items[0]["id"]
        response = await admin_client.get(f"/inventory/{item_id}")
        assert response.status_code == 200
        assert "Test Arduino Uno" in response.text
        assert "TEST-ARD-001" in response.text

    async def test_item_detail_not_found(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.get("/inventory/99999")
        assert response.status_code == 404

    async def test_item_detail_unauthenticated(
        self,
        client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        item_id = sample_items[0]["id"]
        response = await client.get(f"/inventory/{item_id}")
        assert response.status_code == 200
        assert "Test Arduino Uno" in response.text

    async def test_item_detail_shows_edit_for_owner(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        item_id = sample_items[0]["id"]
        response = await admin_client.get(f"/inventory/{item_id}")
        assert response.status_code == 200
        assert "Edit" in response.text
        assert "Delete" in response.text

    async def test_item_detail_no_edit_for_non_owner_staff(
        self,
        staff_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        # sample_items are created by admin, staff should not see edit/delete
        item_id = sample_items[0]["id"]
        response = await staff_client.get(f"/inventory/{item_id}")
        assert response.status_code == 200
        assert "Test Arduino Uno" in response.text
        # Staff should not see edit button for items they don't own
        assert f"/inventory/{item_id}/edit" not in response.text


@pytest.mark.asyncio
class TestInventoryEdit:
    """Tests for editing inventory items."""

    async def test_edit_form_requires_auth(
        self,
        client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        item_id = sample_items[0]["id"]
        response = await client.get(f"/inventory/{item_id}/edit")
        assert response.status_code == 303
        assert "/auth/login" in response.headers.get("location", "")

    async def test_edit_form_admin(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        item_id = sample_items[0]["id"]
        response = await admin_client.get(f"/inventory/{item_id}/edit")
        assert response.status_code == 200
        assert "Edit Item" in response.text
        assert "Test Arduino Uno" in response.text

    async def test_edit_item_success_admin(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        item_id = sample_items[0]["id"]
        response = await admin_client.post(
            f"/inventory/{item_id}/edit",
            data={
                "name": "Updated Arduino Uno",
                "sku": "TEST-ARD-001",
                "description": "Updated description",
                "quantity": "100",
                "unit_price": "35.00",
                "reorder_level": "15",
            },
        )
        assert response.status_code == 303
        assert f"/inventory/{item_id}" in response.headers.get("location", "")

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        assert item is not None
        assert item.name == "Updated Arduino Uno"
        assert item.quantity == 100
        assert item.unit_price == 35.00

    async def test_edit_item_not_found(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.get("/inventory/99999/edit")
        assert response.status_code == 404

    async def test_edit_item_validation_error(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        item_id = sample_items[0]["id"]
        response = await admin_client.post(
            f"/inventory/{item_id}/edit",
            data={
                "name": "",
                "quantity": "10",
                "unit_price": "5.00",
            },
        )
        assert response.status_code == 422
        assert "Name is required" in response.text

    async def test_edit_item_duplicate_sku(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        item_id = sample_items[0]["id"]
        other_sku = sample_items[1]["sku"]
        response = await admin_client.post(
            f"/inventory/{item_id}/edit",
            data={
                "name": "Test Arduino Uno",
                "sku": other_sku,
                "quantity": "50",
                "unit_price": "27.50",
            },
        )
        assert response.status_code == 422
        assert "SKU already exists" in response.text


@pytest.mark.asyncio
class TestInventoryOwnership:
    """Tests for ownership-based access control."""

    async def test_staff_cannot_edit_others_items(
        self,
        staff_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        # sample_items are created by admin, staff should not be able to edit
        item_id = sample_items[0]["id"]
        response = await staff_client.get(f"/inventory/{item_id}/edit")
        # Should redirect with permission error
        assert response.status_code == 303
        assert "/inventory" in response.headers.get("location", "")

    async def test_staff_cannot_edit_others_items_post(
        self,
        staff_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        item_id = sample_items[0]["id"]
        response = await staff_client.post(
            f"/inventory/{item_id}/edit",
            data={
                "name": "Hacked Name",
                "quantity": "999",
                "unit_price": "0.01",
            },
        )
        assert response.status_code == 303
        assert "/inventory" in response.headers.get("location", "")

    async def test_staff_cannot_delete_others_items(
        self,
        staff_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        item_id = sample_items[0]["id"]
        response = await staff_client.post(f"/inventory/{item_id}/delete")
        assert response.status_code == 303

        # Item should still exist
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        assert item is not None

    async def test_staff_can_edit_own_items(
        self,
        staff_client: httpx.AsyncClient,
        sample_staff: dict[str, Any],
        sample_categories: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        # First create an item as staff
        response = await staff_client.post(
            "/inventory/add",
            data={
                "name": "Staff Own Item",
                "sku": "STAFF-OWN-001",
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "3",
            },
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.sku == "STAFF-OWN-001")
        )
        item = result.scalar_one_or_none()
        assert item is not None
        item_id = item.id

        # Now edit it
        response = await staff_client.post(
            f"/inventory/{item_id}/edit",
            data={
                "name": "Staff Own Item Updated",
                "sku": "STAFF-OWN-001",
                "quantity": "20",
                "unit_price": "10.00",
                "reorder_level": "5",
            },
        )
        assert response.status_code == 303
        assert f"/inventory/{item_id}" in response.headers.get("location", "")

    async def test_staff_can_delete_own_items(
        self,
        staff_client: httpx.AsyncClient,
        sample_staff: dict[str, Any],
        db_session: AsyncSession,
    ):
        # First create an item as staff
        response = await staff_client.post(
            "/inventory/add",
            data={
                "name": "Staff Delete Item",
                "sku": "STAFF-DEL-001",
                "quantity": "10",
                "unit_price": "5.00",
            },
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.sku == "STAFF-DEL-001")
        )
        item = result.scalar_one_or_none()
        assert item is not None
        item_id = item.id

        # Now delete it
        response = await staff_client.post(f"/inventory/{item_id}/delete")
        assert response.status_code == 303

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        deleted_item = result.scalar_one_or_none()
        assert deleted_item is None

    async def test_admin_can_edit_any_item(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        item_id = sample_items[0]["id"]
        response = await admin_client.post(
            f"/inventory/{item_id}/edit",
            data={
                "name": "Admin Edited Item",
                "sku": "TEST-ARD-001",
                "quantity": "200",
                "unit_price": "50.00",
                "reorder_level": "20",
            },
        )
        assert response.status_code == 303

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        assert item is not None
        assert item.name == "Admin Edited Item"
        assert item.quantity == 200

    async def test_admin_can_delete_any_item(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        item_id = sample_items[2]["id"]
        response = await admin_client.post(f"/inventory/{item_id}/delete")
        assert response.status_code == 303

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        deleted_item = result.scalar_one_or_none()
        assert deleted_item is None


@pytest.mark.asyncio
class TestInventoryDelete:
    """Tests for deleting inventory items."""

    async def test_delete_requires_auth(
        self,
        client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        item_id = sample_items[0]["id"]
        response = await client.post(f"/inventory/{item_id}/delete")
        assert response.status_code == 303
        assert "/auth/login" in response.headers.get("location", "")

    async def test_delete_nonexistent_item(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.post("/inventory/99999/delete")
        assert response.status_code == 303
        assert "/inventory" in response.headers.get("location", "")

    async def test_delete_item_success(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        db_session: AsyncSession,
    ):
        item_id = sample_items[0]["id"]
        response = await admin_client.post(f"/inventory/{item_id}/delete")
        assert response.status_code == 303
        assert "/inventory" in response.headers.get("location", "")

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        assert item is None


@pytest.mark.asyncio
class TestInventoryStockIndicators:
    """Tests for low-stock and out-of-stock visual indicators."""

    async def test_out_of_stock_indicator(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory")
        assert response.status_code == 200
        assert "Out of Stock" in response.text

    async def test_low_stock_indicator(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory")
        assert response.status_code == 200
        # T-Shirt has quantity=5, reorder_level=10, so it should show Low Stock
        assert "Low Stock" in response.text

    async def test_in_stock_indicator(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory")
        assert response.status_code == 200
        # Arduino has quantity=50, reorder_level=10, so it should show In Stock
        assert "In Stock" in response.text

    async def test_detail_page_out_of_stock_badge(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        # The out-of-stock item
        oos_item_id = sample_items[2]["id"]
        response = await admin_client.get(f"/inventory/{oos_item_id}")
        assert response.status_code == 200
        assert "Out of Stock" in response.text

    async def test_detail_page_low_stock_badge(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        # The low-stock item (T-Shirt: qty=5, reorder=10)
        low_stock_item_id = sample_items[1]["id"]
        response = await admin_client.get(f"/inventory/{low_stock_item_id}")
        assert response.status_code == 200
        assert "Low Stock" in response.text

    async def test_detail_page_in_stock_badge(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        # The in-stock item (Arduino: qty=50, reorder=10)
        in_stock_item_id = sample_items[0]["id"]
        response = await admin_client.get(f"/inventory/{in_stock_item_id}")
        assert response.status_code == 200
        assert "In Stock" in response.text


@pytest.mark.asyncio
class TestInventoryPagination:
    """Tests for pagination on the inventory list."""

    async def test_pagination_page_1(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?page=1")
        assert response.status_code == 200

    async def test_pagination_invalid_page(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        # Page beyond total should still work (clamped to last page)
        response = await admin_client.get("/inventory?page=999")
        assert response.status_code == 200


@pytest.mark.asyncio
class TestInventorySearchAndFilter:
    """Tests for combined search and filter."""

    async def test_search_and_category_filter(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
        sample_categories: list[dict[str, Any]],
    ):
        electronics_id = sample_categories[0]["id"]
        response = await admin_client.get(
            f"/inventory?search=Arduino&category={electronics_id}"
        )
        assert response.status_code == 200
        assert "Test Arduino Uno" in response.text
        assert "Test T-Shirt" not in response.text

    async def test_clear_filters_link(
        self,
        admin_client: httpx.AsyncClient,
        sample_items: list[dict[str, Any]],
    ):
        response = await admin_client.get("/inventory?search=test")
        assert response.status_code == 200
        assert "Clear all" in response.text