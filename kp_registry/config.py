"""Configuration."""
from pydantic import BaseSettings, AnyUrl
from typing import Optional


class Settings(BaseSettings):
    """KP registry settings."""
    openapi_server_url: Optional[AnyUrl]
    openapi_server_maturity: str = "development"
    openapi_server_location: str = "RENCI"
    db_uri: str = 'file:data/kps.db'

    class Config:
        env_file = ".env"


settings = Settings()
