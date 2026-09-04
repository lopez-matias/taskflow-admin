from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "OrangeFlow · Internal Request Management"
    environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg://orangeflow:orangeflow@localhost:5432/orangeflow"
    activity_limit: int = 8

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_prefix="ORANGEFLOW_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
