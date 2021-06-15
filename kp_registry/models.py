"""Models for KP registry."""
from pydantic import BaseModel


class Search(BaseModel):
    """Search."""

    subject_category: list[str]
    predicate: list[str]
    object_category: list[str]

    class Config:
        extra = 'allow'
