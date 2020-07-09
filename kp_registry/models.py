"""Models for KP registry."""
from pydantic import BaseModel


class KP(BaseModel):
    """Knowledge provider."""

    source_type: str
    edge_type: str
    target_type: str

    class Config:
        extra = 'allow'
