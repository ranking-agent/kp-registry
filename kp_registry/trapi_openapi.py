"""TRAPI FastAPI wrapper."""
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from .config import settings


class TRAPI(FastAPI):
    """Translator Reasoner API - wrapper for FastAPI."""

    required_tags = [
        {"name": "translator"},
        {"name": "trapi"},
    ]

    def __init__(
        self,
        *args,
        translator_teams: Optional[List[str]] = None,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )
        self.translator_teams = translator_teams

    def openapi(self) -> Dict[str, Any]:
        """Build custom OpenAPI schema."""
        if self.openapi_schema:
            return self.openapi_schema

        tags = self.required_tags
        if self.openapi_tags:
            tags += self.openapi_tags

        openapi_schema = get_openapi(
            title=self.title,
            version=self.version,
            openapi_version=self.openapi_version,
            description=self.description,
            routes=self.routes,
            tags=tags,
        )

        if settings.openapi_server_url:
            openapi_schema["servers"] = [
                {
                    "url": settings.openapi_server_url,
                    "x-maturity": settings.openapi_server_maturity,
                    "x-location": settings.openapi_server_location,
                },
            ]

        openapi_schema["info"]["x-translator"] = {
            "team": self.translator_teams,
            "externalDocs": {
                "description": "The values for component and team are restricted according to this external JSON schema. See schema and examples at url",
                "url": "https://github.com/NCATSTranslator/translator_extensions/blob/production/x-translator/",
            },
            "infores": "infores:kpregistry",
        }
        openapi_schema["info"]["x-trapi"] = {
            "version": "1.2.0",
            "externalDocs": {
                "description": "The values for version are restricted according to the regex in this external JSON schema. See schema and examples at url",
                "url": "https://github.com/NCATSTranslator/translator_extensions/blob/production/x-trapi/",
            },
        }

        self.openapi_schema = openapi_schema
        return self.openapi_schema
