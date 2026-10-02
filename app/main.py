from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import create_db_and_tables
from .routers import dashboard as dashboard_router
from .routers import settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Five Good Ones", lifespan=lifespan)
app.include_router(dashboard_router.router)
app.include_router(settings_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
