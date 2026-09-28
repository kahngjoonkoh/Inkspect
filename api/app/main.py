from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import SessionLocal
from .regions import seed
from .routers import admin, cards, inquiry, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        seed(db)
    yield


def create_app(seed_regions: bool = True) -> FastAPI:
    app = FastAPI(title="Inkspect API", lifespan=lifespan if seed_regions else None,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    for router in (cards.router, sessions.router, inquiry.router, admin.router):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
