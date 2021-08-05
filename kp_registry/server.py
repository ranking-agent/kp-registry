"""REST wrapper for KP registry SQLite server."""
from fastapi import FastAPI
import asyncio

from .routers.kps import registry_router, load_from_smartapi, register_endpoints

app = FastAPI(
    title='Knowledge Provider Registry',
    description='Registry of Translator knowledge providers',
    version='2.3.0',
)

app.include_router(registry_router())

@app.on_event("startup")
async def build_registry():
    await load_from_smartapi()
    # BTE is a KP for our purposes, but it's registered like an ARA, so load_from_smartapi misses it
    # Special casing it here is perhaps preferable to hacking around and hiding it in load_from_smartapi
    BTE = [{
        "_id": None,
        "title": "Biothings Explorer ReasonerStdAPI",
        "url": "https://api.bte.ncats.io/v1",
        "operations": None,
        "version": None,
    }]
    # At the moment this fails because the BTE meta_knowledge_graph does not validate
    # (it includes "relation: null" on all the edges)
    await register_endpoints(BTE)
