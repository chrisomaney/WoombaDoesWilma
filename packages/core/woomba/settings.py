from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_library() -> Path:
    return Path.home() / "Movies" / "WoombaDoesWilma"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WOOMBA_", env_file=".env", extra="ignore")

    library: Path = Field(default_factory=_default_library)
    host: str = "127.0.0.1"
    port: int = 8787
    lan: bool = False
    token: str = ""

    def resolve_library(self) -> Path:
        return self.library.expanduser().resolve()


def get_settings() -> Settings:
    return Settings()
