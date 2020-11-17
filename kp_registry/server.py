"""REST wrapper for KP registry SQLite server."""
from fastapi import FastAPI

from .routers.kps import registry_router

app = FastAPI(
    title='Knowledge Provider Registry',
    description='Registry of Translator knowledge providers',
    version='1.0.0',
)

app.include_router(registry_router())
