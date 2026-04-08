import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
if SECRET_KEY == "dev-secret-key-change-in-production":
    logger.warning(
        "SECRET_KEY is using the default development value. "
        "Set a strong SECRET_KEY environment variable in production!"
    )

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./stockpilot.db")

ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")
if ADMIN_PASSWORD == "admin":
    logger.warning(
        "ADMIN_PASSWORD is using the default value 'admin'. "
        "Set a strong ADMIN_PASSWORD environment variable in production!"
    )

ADMIN_DISPLAY_NAME: str = os.getenv("ADMIN_DISPLAY_NAME", "Administrator")

SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "stockpilot_session")
SESSION_MAX_AGE: int = int(os.getenv("SESSION_MAX_AGE", "86400"))