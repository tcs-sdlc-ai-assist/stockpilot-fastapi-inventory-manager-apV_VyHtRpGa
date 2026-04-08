import logging

from passlib.context import CryptContext
from sqlalchemy import select

import config
from database import async_session_maker
from models.category import Category
from models.user import User

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_CATEGORIES = [
    {"name": "Electronics", "color": "#3b82f6"},
    {"name": "Clothing", "color": "#ec4899"},
    {"name": "Food & Beverage", "color": "#f59e0b"},
    {"name": "Office Supplies", "color": "#10b981"},
    {"name": "Tools", "color": "#6366f1"},
    {"name": "Raw Materials", "color": "#8b5cf6"},
    {"name": "Packaging", "color": "#14b8a6"},
    {"name": "Other", "color": "#64748b"},
]


async def seed_database() -> None:
    logger.info("Running database seed...")

    async with async_session_maker() as session:
        async with session.begin():
            await _seed_admin_user(session)
            await _seed_default_categories(session)

    logger.info("Database seed completed.")


async def _seed_admin_user(session) -> None:
    result = await session.execute(
        select(User).where(User.username == config.ADMIN_USERNAME)
    )
    existing_admin = result.scalars().first()

    if existing_admin is not None:
        logger.info(
            "Admin user '%s' already exists — skipping creation.",
            config.ADMIN_USERNAME,
        )
        return

    hashed_password = pwd_context.hash(config.ADMIN_PASSWORD)

    admin_user = User(
        username=config.ADMIN_USERNAME,
        display_name=config.ADMIN_DISPLAY_NAME,
        hashed_password=hashed_password,
        role="Admin",
    )
    session.add(admin_user)
    logger.info("Created default admin user '%s'.", config.ADMIN_USERNAME)


async def _seed_default_categories(session) -> None:
    for cat_data in DEFAULT_CATEGORIES:
        result = await session.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing = result.scalars().first()

        if existing is not None:
            logger.debug(
                "Category '%s' already exists — skipping.", cat_data["name"]
            )
            continue

        category = Category(
            name=cat_data["name"],
            color=cat_data["color"],
        )
        session.add(category)
        logger.info(
            "Created default category '%s' (%s).",
            cat_data["name"],
            cat_data["color"],
        )