from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Five Good Ones", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}
