import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import create_tables, get_db
from dependencies import _RedirectException, get_current_user, redirect_exception_handler
from seed import seed_database

sys.path.insert(0, str(Path(__file__).resolve().parent))

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

templates = Jinja2Templates(directory="templates")


def flash(request: Request, message: str, category: str = "info") -> None:
    if "_flash_messages" not in request.state._state:
        request.state._flash_messages = []
    request.state._flash_messages.append({"text": message, "category": category})


def get_flash_messages(request: Request) -> list[dict]:
    messages = getattr(request.state, "_flash_messages", [])
    request.state._flash_messages = []
    return messages


def get_flashed_messages(request: Request) -> list[dict]:
    return get_flash_messages(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("StockPilot starting up...")
    await create_tables()
    await seed_database()
    logger.info("StockPilot startup complete.")
    yield
    logger.info("StockPilot shutting down...")


app = FastAPI(
    title="StockPilot",
    description="Intelligent Inventory Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_exception_handler(_RedirectException, redirect_exception_handler)


@app.middleware("http")
async def flash_message_middleware(request: Request, call_next):
    request.state._flash_messages = []
    response = await call_next(request)
    return response


from routes.auth import router as auth_router
from routes.inventory import router as inventory_router
from routes.categories import router as categories_router
from routes.dashboard import router as dashboard_router
from routes.users import router as users_router

app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(categories_router)
app.include_router(dashboard_router)
app.include_router(users_router)


@app.get("/")
async def landing_page(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    current_user = await get_current_user(request, db)
    flash_messages = get_flash_messages(request)
    return templates.TemplateResponse(
        request,
        "landing.html",
        context={
            "current_user": current_user,
            "flash_messages": flash_messages,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        db_gen = get_db()
        db = await db_gen.__anext__()
        try:
            current_user = await get_current_user(request, db)
        except Exception:
            current_user = None
        finally:
            try:
                await db_gen.aclose()
            except Exception:
                pass

        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={"current_user": current_user},
            status_code=404,
        )

    return HTMLResponse(
        content=f"<h1>{exc.status_code}</h1><p>{exc.detail}</p>",
        status_code=exc.status_code,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)