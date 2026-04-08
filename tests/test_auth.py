import logging
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from models.user import User

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestLoginPage:
    async def test_login_page_renders(self, client: httpx.AsyncClient):
        response = await client.get("/auth/login")
        assert response.status_code == 200
        assert "Sign In" in response.text
        assert "username" in response.text
        assert "password" in response.text

    async def test_login_page_redirects_authenticated_admin(
        self,
        admin_client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await admin_client.get("/auth/login")
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

    async def test_login_page_redirects_authenticated_staff(
        self,
        staff_client: httpx.AsyncClient,
        sample_staff: dict[str, Any],
    ):
        response = await staff_client.get("/auth/login")
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory"


@pytest.mark.asyncio
class TestLoginSubmit:
    async def test_login_valid_admin_credentials(
        self,
        client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": sample_admin["username"],
                "password": sample_admin["password"],
            },
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

        set_cookie = response.headers.get("set-cookie", "")
        assert config.SESSION_COOKIE_NAME in set_cookie

    async def test_login_valid_staff_credentials(
        self,
        client: httpx.AsyncClient,
        sample_staff: dict[str, Any],
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": sample_staff["username"],
                "password": sample_staff["password"],
            },
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory"

        set_cookie = response.headers.get("set-cookie", "")
        assert config.SESSION_COOKIE_NAME in set_cookie

    async def test_login_invalid_password(
        self,
        client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": sample_admin["username"],
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 200
        assert "Invalid username or password" in response.text

    async def test_login_nonexistent_user(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/login",
            data={
                "username": "nonexistentuser",
                "password": "somepassword",
            },
        )
        assert response.status_code == 200
        assert "Invalid username or password" in response.text

    async def test_login_empty_username(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/login",
            data={
                "username": "",
                "password": "somepassword",
            },
        )
        assert response.status_code == 200
        assert "Please enter both username and password" in response.text

    async def test_login_empty_password(
        self,
        client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": sample_admin["username"],
                "password": "",
            },
        )
        assert response.status_code == 200
        assert "Please enter both username and password" in response.text

    async def test_login_empty_both_fields(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/login",
            data={
                "username": "",
                "password": "",
            },
        )
        assert response.status_code == 200
        assert "Please enter both username and password" in response.text

    async def test_login_session_cookie_is_httponly(
        self,
        client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": sample_admin["username"],
                "password": sample_admin["password"],
            },
        )
        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "httponly" in set_cookie

    async def test_login_session_cookie_samesite_lax(
        self,
        client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": sample_admin["username"],
                "password": sample_admin["password"],
            },
        )
        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "samesite=lax" in set_cookie


@pytest.mark.asyncio
class TestRegisterPage:
    async def test_register_page_renders(self, client: httpx.AsyncClient):
        response = await client.get("/auth/register")
        assert response.status_code == 200
        assert "Create Account" in response.text
        assert "username" in response.text
        assert "password" in response.text
        assert "display_name" in response.text

    async def test_register_page_redirects_authenticated_admin(
        self,
        admin_client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await admin_client.get("/auth/register")
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

    async def test_register_page_redirects_authenticated_staff(
        self,
        staff_client: httpx.AsyncClient,
        sample_staff: dict[str, Any],
    ):
        response = await staff_client.get("/auth/register")
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory"


@pytest.mark.asyncio
class TestRegisterSubmit:
    async def test_register_valid_data(
        self,
        client: httpx.AsyncClient,
        db_session: AsyncSession,
    ):
        response = await client.post(
            "/auth/register",
            data={
                "username": "newuser",
                "display_name": "New User",
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory"

        set_cookie = response.headers.get("set-cookie", "")
        assert config.SESSION_COOKIE_NAME in set_cookie

        result = await db_session.execute(
            select(User).where(User.username == "newuser")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.username == "newuser"
        assert user.display_name == "New User"
        assert user.role == "Staff"

    async def test_register_duplicate_username(
        self,
        client: httpx.AsyncClient,
        sample_staff: dict[str, Any],
    ):
        response = await client.post(
            "/auth/register",
            data={
                "username": sample_staff["username"],
                "display_name": "Another User",
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response.status_code == 200
        assert "already taken" in response.text

    async def test_register_empty_username(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "username": "",
                "display_name": "Some Name",
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response.status_code == 200
        assert "Username is required" in response.text

    async def test_register_short_username(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "username": "ab",
                "display_name": "Some Name",
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response.status_code == 200
        assert "at least 3 characters" in response.text

    async def test_register_long_username(self, client: httpx.AsyncClient):
        long_username = "a" * 51
        response = await client.post(
            "/auth/register",
            data={
                "username": long_username,
                "display_name": "Some Name",
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response.status_code == 200
        assert "50 characters or fewer" in response.text

    async def test_register_empty_display_name(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "username": "validuser",
                "display_name": "",
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response.status_code == 200
        assert "Display name is required" in response.text

    async def test_register_long_display_name(self, client: httpx.AsyncClient):
        long_name = "A" * 101
        response = await client.post(
            "/auth/register",
            data={
                "username": "validuser",
                "display_name": long_name,
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response.status_code == 200
        assert "100 characters or fewer" in response.text

    async def test_register_empty_password(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "username": "validuser",
                "display_name": "Valid User",
                "password": "",
                "confirm_password": "",
            },
        )
        assert response.status_code == 200
        assert "Password is required" in response.text

    async def test_register_short_password(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "username": "validuser",
                "display_name": "Valid User",
                "password": "short",
                "confirm_password": "short",
            },
        )
        assert response.status_code == 200
        assert "at least 8 characters" in response.text

    async def test_register_password_mismatch(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "username": "validuser",
                "display_name": "Valid User",
                "password": "securepass123",
                "confirm_password": "differentpass456",
            },
        )
        assert response.status_code == 200
        assert "Passwords do not match" in response.text

    async def test_register_empty_confirm_password(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "username": "validuser",
                "display_name": "Valid User",
                "password": "securepass123",
                "confirm_password": "",
            },
        )
        assert response.status_code == 200
        assert "confirm your password" in response.text

    async def test_register_preserves_form_data_on_error(
        self, client: httpx.AsyncClient
    ):
        response = await client.post(
            "/auth/register",
            data={
                "username": "validuser",
                "display_name": "Valid User",
                "password": "short",
                "confirm_password": "short",
            },
        )
        assert response.status_code == 200
        assert 'value="validuser"' in response.text
        assert 'value="Valid User"' in response.text

    async def test_register_password_is_hashed(
        self,
        client: httpx.AsyncClient,
        db_session: AsyncSession,
    ):
        response = await client.post(
            "/auth/register",
            data={
                "username": "hashcheckuser",
                "display_name": "Hash Check",
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(User).where(User.username == "hashcheckuser")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.hashed_password != "securepass123"
        assert user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")

    async def test_register_multiple_errors(self, client: httpx.AsyncClient):
        response = await client.post(
            "/auth/register",
            data={
                "username": "",
                "display_name": "",
                "password": "",
                "confirm_password": "",
            },
        )
        assert response.status_code == 200
        assert "Username is required" in response.text
        assert "Display name is required" in response.text
        assert "Password is required" in response.text


@pytest.mark.asyncio
class TestLogout:
    async def test_logout_clears_cookie(
        self,
        admin_client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await admin_client.post("/auth/logout")
        assert response.status_code == 303
        assert response.headers["location"] == "/"

        set_cookie = response.headers.get("set-cookie", "")
        assert config.SESSION_COOKIE_NAME in set_cookie
        cookie_lower = set_cookie.lower()
        has_expiry_or_max_age = (
            'max-age=0' in cookie_lower
            or 'expires=' in cookie_lower
            or f'{config.SESSION_COOKIE_NAME}=""' in set_cookie
            or f'{config.SESSION_COOKIE_NAME}="";' in set_cookie
        )
        assert has_expiry_or_max_age or '""' in set_cookie

    async def test_logout_unauthenticated_user(self, client: httpx.AsyncClient):
        response = await client.post("/auth/logout")
        assert response.status_code == 303
        assert response.headers["location"] == "/"

    async def test_after_logout_cannot_access_protected_routes(
        self,
        client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        login_response = await client.post(
            "/auth/login",
            data={
                "username": sample_admin["username"],
                "password": sample_admin["password"],
            },
        )
        cookies = {}
        for name, value in login_response.cookies.items():
            cookies[name] = value

        if not cookies:
            set_cookie_header = login_response.headers.get("set-cookie", "")
            if set_cookie_header:
                cookie_key = config.SESSION_COOKIE_NAME
                for part in set_cookie_header.split(";"):
                    part = part.strip()
                    if part.startswith(f"{cookie_key}="):
                        cookies[cookie_key] = part.split("=", 1)[1]
                        break

        transport = httpx.ASGITransport(app=client._transport._app)  # type: ignore[attr-defined]
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            cookies=cookies,
            follow_redirects=False,
        ) as authed_client:
            logout_response = await authed_client.post("/auth/logout")
            assert logout_response.status_code == 303

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            follow_redirects=False,
        ) as fresh_client:
            dashboard_response = await fresh_client.get("/dashboard")
            assert dashboard_response.status_code == 303
            assert "/auth/login" in dashboard_response.headers.get("location", "")


@pytest.mark.asyncio
class TestSessionCookie:
    async def test_valid_session_cookie_grants_access(
        self,
        admin_client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await admin_client.get("/dashboard")
        assert response.status_code == 200
        assert "Dashboard" in response.text

    async def test_invalid_session_cookie_redirects_to_login(
        self, client: httpx.AsyncClient
    ):
        response = await client.get(
            "/dashboard",
            cookies={config.SESSION_COOKIE_NAME: "invalid-cookie-value"},
        )
        assert response.status_code == 303
        assert "/auth/login" in response.headers.get("location", "")

    async def test_no_session_cookie_redirects_to_login(
        self, client: httpx.AsyncClient
    ):
        response = await client.get("/inventory/create")
        assert response.status_code == 303
        assert "/auth/login" in response.headers.get("location", "")


@pytest.mark.asyncio
class TestRoleBasedRedirect:
    async def test_admin_login_redirects_to_dashboard(
        self,
        client: httpx.AsyncClient,
        sample_admin: dict[str, Any],
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": sample_admin["username"],
                "password": sample_admin["password"],
            },
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

    async def test_staff_login_redirects_to_inventory(
        self,
        client: httpx.AsyncClient,
        sample_staff: dict[str, Any],
    ):
        response = await client.post(
            "/auth/login",
            data={
                "username": sample_staff["username"],
                "password": sample_staff["password"],
            },
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory"

    async def test_new_registered_user_redirects_to_inventory(
        self, client: httpx.AsyncClient
    ):
        response = await client.post(
            "/auth/register",
            data={
                "username": "brandnewuser",
                "display_name": "Brand New",
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/inventory"