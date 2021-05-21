"""Models for KP registry."""
from pydantic import BaseModel


class Search(BaseModel):
    """Search."""

    source_type: list[str]
    edge_type: list[str]
    target_type: list[str]

    class Config:
        extra = 'allow'
