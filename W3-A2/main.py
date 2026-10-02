"""
Stage 0: Application startup initializes tasks.db and seeds 3 example tasks once.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Task CRUD API (SQLite)", lifespan=lifespan)
