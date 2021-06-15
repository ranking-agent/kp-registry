"""Test KP registry."""
"""Test the server."""
from contextlib import asynccontextmanager, AsyncExitStack
from functools import partial, wraps
import os
from typing import Callable

from asgiar import ASGIAR
from fastapi import FastAPI, Request
import httpx
import pytest

from kp_registry.server import app as APP

os.environ["DB_URI"] = ":memory:"


def with_context(context, *args_, **kwargs_):
    """Turn context manager into decorator."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with context(*args_, **kwargs_):
                await func(*args, **kwargs)
        return wrapper
    return decorator


@asynccontextmanager
async def function_overlay(host: str, fcn: Callable):
    """Apply an ASGIAR overlay that runs `fcn` for all routes."""
    async with AsyncExitStack() as stack:
        app = FastAPI()

        # pylint: disable=unused-variable disable=unused-argument
        @app.api_route(
            "/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE"],
        )
        async def all_paths(path: str, request: Request):
            return fcn(request)

        await stack.enter_async_context(
            ASGIAR(app, host=host)
        )
        yield


with_function_overlay = partial(with_context, function_overlay)


@pytest.fixture
async def client():
    """Create and teardown async httpx client."""
    async with httpx.AsyncClient(app=APP, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
@with_function_overlay(
    "smart-api.info",
    lambda request: {
        "hits": [
            {
                "_id": "123abc",
                "servers": [{"url": "http://test-kp"}],
                "info": {
                    "title": "Test KP",
                    "x-translator": {
                        "component": "KP"
                    },
                    "x-trapi": {
                        "version": "1.1.0",
                        "operations": [
                            "lookup"
                        ]
                    }
                },
                "paths": {
                    "/meta_knowledge_graph": {}
                }
            }
        ]
    },
)
@with_function_overlay(
    "test-kp",
    lambda request: {
        "nodes": {
            "biolink:ChemicalSubstance": {"id_prefixes": ["CHEBI", "PUBCHEM.COMPOUND"]}
        },
        "edges": [
            {
                "subject": "biolink:ChemicalSubstance",
                "predicate": "biolink:treats",
                "object": "biolink:Disease"
            }
        ]
    },
)
async def test_main(client):
    """Test KP registry."""
    # refresh KPs
    response = await client.post(f'/refresh')
    assert response.status_code == 202

    # get all KPs (there is one)
    response = await client.get('/kps')
    assert response.status_code == 200
    assert len(response.json()) == 1
    print(response.json())

    # get KP
    response = await client.get(f'/kps/Test%20KP')
    assert response.status_code == 200

    # search for KPs (find one)
    response = await client.post('/search', json=dict(
        source_type=['biolink:ChemicalSubstance'],
        edge_type=['-biolink:treats->'],
        target_type=['biolink:Disease'],
    ))
    assert response.status_code == 200
    assert len(response.json()) == 1
