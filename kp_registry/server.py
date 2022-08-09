"""REST wrapper for KP registry SQLite server."""
from .trapi_openapi import TRAPI
from .config import settings
from .routers.kps import registry_router, load_from_smartapi, register_endpoints

openapi_args = dict(
    title="Knowledge Provider Registry",
    description="Registry of Translator knowledge providers",
    version="2.5.0",
    translator_teams=["Ranking Agent"],
)

APP = TRAPI(**openapi_args)

APP.include_router(registry_router())

@APP.on_event("startup")
async def build_registry():
    await load_from_smartapi()
