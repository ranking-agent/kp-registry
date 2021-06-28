"""Models for KP registry."""
from typing import Any

from pydantic import AnyUrl, BaseModel


class Operation(BaseModel):
    """Operation."""

    subject_category: str
    predicate: str
    object_category: str

    class Config:
        extra = 'allow'


class KP(BaseModel):
    """Knowledge provider."""

    url: AnyUrl
    operations: list[Operation]
    details: dict[str, Any] = {}

    class Config:
        extra = 'allow'


class Search(BaseModel):
    """Search."""

    subject_category: list[str]
    predicate: list[str]
    object_category: list[str]

    class Config:
        extra = 'allow'
