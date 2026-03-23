from __future__ import annotations

import importlib.metadata as importlib_metadata
from contextlib import asynccontextmanager


def _patch_email_validator_version() -> None:
    original_version = importlib_metadata.version

    def patched_version(name: str) -> str:
        value = original_version(name)
        if name == 'email-validator' and value is None:
            return '2.3.0'
        return value

    importlib_metadata.version = patched_version  # type: ignore[assignment]


_patch_email_validator_version()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.scheduler import scheduler_manager

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler_manager.start()
    try:
        yield
    finally:
        scheduler_manager.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
allowed_origins = [
    settings.frontend_origin,
    'http://localhost:4173',
    'http://127.0.0.1:4173',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allowed_origins)),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(api_router, prefix='/api/v1')


