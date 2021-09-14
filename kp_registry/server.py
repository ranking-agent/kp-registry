"""REST wrapper for KP registry SQLite server."""
from fastapi import FastAPI
import asyncio

from .routers.kps import registry_router, load_from_smartapi, register_endpoints

app = FastAPI(
    title='Knowledge Provider Registry',
    description='Registry of Translator knowledge providers',
    version='2.3.1',
)

app.include_router(registry_router())

@app.on_event("startup")
async def build_registry():
    await load_from_smartapi()
