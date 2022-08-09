"""REST wrapper for KP registry SQLite server."""
import asyncio
import json
from kp_registry.models import Search
import logging
import traceback
import re

from fastapi import Body, Depends, APIRouter, status, BackgroundTasks
import httpx
import pydantic
from reasoner_pydantic import MetaKnowledgeGraph

from ..config import settings
from ..models import KP
from ..registry import Registry

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
LOGGER.addHandler(handler)

example = {
    "my_kp": {
        "url": "http://my_kp_url",
        "operations": [{
            "subject_category": "biolink:Disease",
            "predicate": "biolink:related_to",
            "object_category": "biolink:Gene",
        }],
    }
}

async def load_from_smartapi():
    """Load KP definitions from SmartAPI."""
    endpoints = await retrieve_kp_endpoints_from_smartapi()
    await register_endpoints(endpoints)

async def register_endpoints(endpoints):
    """Takes list of KP endpoints defined with a dict like
    {
            "_id": _id,
            "title": title,
            "infores": infores,
            "url": url,
            "maturity": maturity,
            "operations": operations,
            "version": version,
    }
    and registers them.  "url" is used to access meta_knowledge_graph, the others are used for logging
    """
    LOGGER.info('register')
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
        LOGGER.info(endpoint)
        if isinstance(response, Exception):
            LOGGER.warning(
                "Error accessing /meta_knowledge_graph for %s (https://smart-api.info/registry?q=%s): %s",
                endpoint["title"],
                endpoint["_id"],
                response,
            )
            continue
        if response.status_code >= 300:
            LOGGER.warning(
                "Bad response from /meta_knowledge_graph for %s (%s) (https://smart-api.info/registry?q=%s): %s",
                endpoint["title"],
                endpoint["url"],
                endpoint["_id"],
                f"<HTTP {response.status_code}> {response.text}",
            )
            continue
        try:
            meta_kg = response.json()
        except json.decoder.JSONDecodeError as err:
            LOGGER.warning(
                "Error decoding /meta_knowledge_graph response for %s (https://smart-api.info/registry?q=%s): %s",
                endpoint["title"],
                endpoint["_id"],
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
                endpoint["_id"],
                err,
            )
            # There are currently issues with reasoner pydantic: https://github.com/TranslatorSRI/reasoner-pydantic/issues/35
            # we want to keep even invalid meta_knowledge_graphs
            # continue
        meta_kgs.append((endpoint, response.json()))
    kps = dict()
    for endpoint, meta_kg in meta_kgs:
        try:
            kps[endpoint["title"]] = {
                "url": endpoint["url"] + "/query",
                "infores": endpoint["infores"],
                "maturity": endpoint["maturity"],
                "operations": [
                    {
                        "subject_category": edge["subject"],
                        "predicate": edge["predicate"],
                        "object_category": edge["object"],
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
                endpoint["_id"],
                tb,
            )
    async with Registry(settings.db_uri) as registry:
        await registry.delete_all()
        await registry.add(**kps)
    LOGGER.debug("Reloaded registry.")


async def retrieve_kp_endpoints_from_smartapi():
    """Returns a list of KP endpoints defined with a dict like
    {
            "_id": _id,
            "title": title,
            "url": url,
            "operations": operations,
            "version": version,
    }
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://smart-api.info/api/query?limit=1000&q=TRAPI%20KP")
            response.raise_for_status()
        except httpx.HTTPError as e:
            LOGGER.warning(f"Failed to get smart api services. Error: {e}")
            try:
                LOGGER.info("Trying fallback smart api query.")
                response = await client.get("https://smart-api.info/api/query?limit=1000&q=TRAPI")
                response.raise_for_status()
            except httpx.HTTPError as e:
                LOGGER.error("Failed to query smart api. Exiting...")
                raise e

    registrations = response.json()
    endpoints = []
    for hit in registrations["hits"]:
        try:
            title = hit["info"]["title"]
        except KeyError:
            LOGGER.warning(
                "No title for service. Cannot use."
            )
            continue
        # _id currently is missing on each "hit" (5/2/2022)
        # https://github.com/SmartAPI/smartapi_registry/issues/7#issuecomment-1115007211
        try:
            _id = hit["_id"]
        except KeyError:
            _id = title
        try:
            infores = hit["info"]["x-translator"]["infores"]
        except KeyError:
            LOGGER.warning(
                "No x-translator.infores for %s (https://smart-api.info/registry?q=%s)",
                title,
                _id,
            )
            infores = f'infores:{_id}'
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
        regex = re.compile("[0-9]\.[0-9]")
        trapi_version = regex.match(settings.trapi_version)
        if not version.startswith(trapi_version.group() + "."):
            LOGGER.info(
                f"TRAPI version != {trapi_version.group()}.x for %s (https://smart-api.info/registry?q=%s)",
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
            for server in hit["servers"]:
                try:
                    url = server["url"]
                    url += prefix
                    if url.endswith('/'):
                        url = url[:-1]
                except KeyError:
                    LOGGER.warning(
                        "No servers[0].url for %s (https://smart-api.info/registry?q=%s)",
                        title,
                        _id,
                    )
                    continue
                try:
                    maturity = server["x-maturity"]
                except KeyError:
                    maturity = "production"
                
                endpoint_title = title
                # If multiple servers, need to disambiguate the service titles
                if len(hit["servers"]) > 1:
                    endpoint_title = f"{title}_{maturity}"

                endpoints.append({
                    "_id": _id,
                    "title": endpoint_title,
                    "infores": infores,
                    "url": url,
                    "maturity": maturity,
                    "operations": operations,
                    "version": version,
                })
        except (KeyError):
            LOGGER.warning(
                "No servers for %s (https://smart-api.info/registry?q=%s)",
                title,
                _id,
            )
            continue
        
    return endpoints


def registry_router(db_uri=settings.db_uri):
    """Generate registry router."""
    router = APIRouter()

    async def get_registry() -> Registry:
        """Get KP registry."""
        async with Registry(db_uri) as registry:
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

    @router.post('/kps', status_code=status.HTTP_201_CREATED)
    async def add_knowledge_provider(
            kps: dict[str, KP] = Body(..., example=example),
            registry: Registry = Depends(get_registry),
    ):
        """Add a knowledge provider."""
        kps = {key: value.dict() for key, value in kps.items()}
        await registry.add(**kps)

    @router.post('/search')
    async def search_for_knowledge_providers(
            operation: Search = Body(..., example={
                "subject_category": ["biolink:ChemicalSubstance"],
                "predicate": ["biolink:treats"],
                "object_category": ["biolink:Disease"],
                "maturity": ["development"],
            }),
            registry: Registry = Depends(get_registry),
    ):
        """Search for knowledge providers matching a specification."""
        return await registry.search(
            operation.subject_category,
            operation.predicate,
            operation.object_category,
            operation.maturity,
        )

    @router.post('/refresh', status_code=status.HTTP_202_ACCEPTED)
    async def refresh_kps(background_tasks: BackgroundTasks):
        """Refresh registered KPs by consulting SmartAPI registry."""
        background_tasks.add_task(load_from_smartapi)
        return "Queued refresh. It will take a few seconds."

    @router.post('/clear', status_code=status.HTTP_204_NO_CONTENT)
    async def clear_kps(
            registry: Registry = Depends(get_registry),
    ):
        """Clear all registered KPs."""
        await registry.delete_all()

    return router

