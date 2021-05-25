"""REST wrapper for KP registry SQLite server."""
import asyncio
import json
from kp_registry.models import Search
import logging
import traceback

from fastapi import Body, Depends, APIRouter, status, BackgroundTasks
import httpx
import pydantic
from reasoner_pydantic import MetaKnowledgeGraph

from ..config import settings
from ..registry import Registry

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
LOGGER.addHandler(handler)

def registry_router(db_uri=settings.db_uri):
    """Generate registry router."""
    router = APIRouter()

    async def get_registry():
        """Get KP registry."""
        async with Registry(settings.db_uri) as registry:
            yield registry

    @router.get('/kps')
    async def get_all_knowledge_providers(
            registry: Registry = Depends(get_registry),
    ):
        """Get all knowledge providers."""
        return await registry.get_all()

    @router.get('/kps/{uid}')
    async def get_knowledge_provider(
            uid: str,
            registry: Registry = Depends(get_registry),
    ):
        """Get a knowledge provider by url."""
        return await registry.get_one(uid)

    @router.post('/search')
    async def search_for_knowledge_providers(
            operation: Search = Body(..., example={
                "source_type": ["biolink:ChemicalSubstance"],
                "edge_type": ["-biolink:treats->"],
                "target_type": ["biolink:Disease"],
            }),
            registry=Depends(get_registry),
    ):
        """Search for knowledge providers matching a specification."""
        return await registry.search(
            operation.source_type,
            operation.edge_type,
            operation.target_type,
        )

    async def load_from_smartapi():
        """Load KP definitions from SmartAPI."""
        async with httpx.AsyncClient() as client:
            response = await client.get("https://smart-api.info/api/query?limit=1000&q=TRAPI%20KP")
        response.raise_for_status()
        registrations = response.json()
        endpoints = []
        for hit in registrations["hits"]:
            _id = hit["_id"]
            try:
                title = hit["info"]["title"]
            except KeyError:
                title = _id
            try:
                component = hit["info"]["x-translator"]["component"]
            except KeyError:
                LOGGER.warning(
                    "No x-translator.component for %s (https://smart-api.info/registry?q=%s)",
                    title,
                    _id,
                )
                continue
            if component != "KP":
                LOGGER.info(
                    "component != KP for %s (https://smart-api.info/registry?q=%s)",
                    title,
                    _id,
                )
                continue
            try:
                version = hit["info"]["x-trapi"]["version"]
            except KeyError:
                LOGGER.warning(
                    "No x-trapi.version for %s (https://smart-api.info/registry?q=%s)",
                    title,
                    _id,
                )
                continue
            if not version.startswith("1.1."):
                LOGGER.info(
                    "TRAPI version != 1.1.x for %s (https://smart-api.info/registry?q=%s)",
                    title,
                    _id,
                )
                continue
            try:
                operations = hit["info"]["x-trapi"]["operations"]
            except KeyError:
                operations = None
            paths = list(hit["paths"].keys())
            try:
                prefix = next(path for path in paths if path.endswith("/meta_knowledge_graph"))[:-21]
            except StopIteration:
                LOGGER.warning(
                    "No /meta_knowledge_graph for %s (https://smart-api.info/registry?q=%s)",
                    title,
                    _id,
                )
                continue
            try:
                url = hit["servers"][0]["url"]
            except (KeyError, IndexError):
                LOGGER.warning(
                    "No servers[0].url for %s (https://smart-api.info/registry?q=%s)",
                    title,
                    _id,
                )
                continue
            url += prefix
            endpoints.append({
                "_id": _id,
                "title": title,
                "url": url,
                "operations": operations,
                "version": version,
            })
        async with httpx.AsyncClient() as client:
            responses = await asyncio.gather(
                *[
                    client.get(endpoint["url"] + "/meta_knowledge_graph")
                    for endpoint in endpoints
                ],
                return_exceptions=True,
            )
        meta_kgs = []
        for endpoint, response in zip(endpoints, responses):
            if isinstance(response, Exception):
                LOGGER.warning(
                    "Error accessing /meta_knowledge_graph for %s (https://smart-api.info/registry?q=%s): %s",
                    endpoint["title"],
                    _id,
                    response,
                )
                continue
            if response.status_code >= 300:
                LOGGER.warning(
                    "Bad response from /meta_knowledge_graph for %s (https://smart-api.info/registry?q=%s): %s",
                    endpoint["title"],
                    _id,
                    f"<HTTP {response.status_code}> {response.text}",
                )
                continue
            try:
                meta_kg = response.json()
            except json.decoder.JSONDecodeError as err:
                LOGGER.warning(
                    "Error decoding /meta_knowledge_graph response for %s (https://smart-api.info/registry?q=%s): %s",
                    endpoint["title"],
                    _id,
                    response.text,
                )
                continue
            try:
                # validate /meta_knowledge_graph response.
                MetaKnowledgeGraph.parse_obj(meta_kg)
            except pydantic.ValidationError as err:
                LOGGER.warning(
                    "Failed to validate /meta_knowledge_graph response for %s (https://smart-api.info/registry?q=%s): %s",
                    endpoint["title"],
                    _id,
                    err,
                )
                continue
            meta_kgs.append((endpoint, response.json()))

        kps = dict()
        for endpoint, meta_kg in meta_kgs:
            try:
                kps[endpoint["title"]] = {
                    "url": endpoint["url"] + "/query",
                    "operations": [
                        {
                            "source_type": edge["subject"],
                            "edge_type": "-{}->".format(edge["predicate"]),
                            "target_type": edge["object"],
                        }
                        for edge in meta_kg["edges"]
                    ] + [
                        {
                            "source_type": edge["object"],
                            "edge_type": "<-{}-".format(edge["predicate"]),
                            "target_type": edge["subject"],
                        }
                        for edge in meta_kg["edges"]
                    ],
                    "details": {"preferred_prefixes": {
                        category: value["id_prefixes"]
                        for category, value in meta_kg["nodes"].items()
                    }},
                }
            except Exception as err:
                tb = traceback.format_exc()
                LOGGER.warning(
                    "Error parsing KP details for %s (https://smart-api.info/registry?q=%s): %s",
                    endpoint["title"],
                    _id,
                    tb,
                )
        async with Registry(settings.db_uri) as registry:
            await registry.delete_all()
            await registry.add(**kps)
        LOGGER.debug("Reloaded registry.")

    @router.post('/refresh', status_code=status.HTTP_202_ACCEPTED)
    async def refresh_kps(background_tasks: BackgroundTasks):
        """Refresh registered KPs by consulting SmartAPI registry."""
        background_tasks.add_task(load_from_smartapi)
        return "Queued refresh. It will take a few seconds."

    return router
