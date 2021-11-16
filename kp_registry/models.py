"""Models for KP registry."""
from enum import Enum
from typing import Any, Optional

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


class Maturity(Enum):
    """Service maturity options."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Search(BaseModel):
    """Search."""

    maturity: Optional[list[Maturity]] = [Maturity.PRODUCTION]
    subject_category: list[str]
    predicate: list[str]
    object_category: list[str]

    class Config:
        extra = 'allow'
