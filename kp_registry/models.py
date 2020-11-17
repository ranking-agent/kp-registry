"""Models for KP registry."""
from typing import Any, Dict, List

from pydantic import AnyUrl, BaseModel


class Operation(BaseModel):
    """Operation."""

    source_type: str
    edge_type: str
    target_type: str

    class Config:
        extra = 'allow'


class KP(BaseModel):
    """Knowledge provider."""

    url: AnyUrl
    operations: List[Operation]
    details: Dict[str, Any] = {}

    class Config:
        extra = 'allow'
