"""Configuration."""
from pydantic import BaseSettings


class Settings(BaseSettings):
    """KP registry settings."""

    db_uri: str = 'file:data/kps.db'


settings = Settings()
