from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

from woomba.db import connect
from woomba.paths import db_path, ensure_library_layout
from woomba.settings import Settings, get_settings


@lru_cache(maxsize=1)
def _conn_for(library: str) -> sqlite3.Connection:
    return connect(db_path(Path(library)))


def settings_dep() -> Settings:
    return get_settings()


def library_root() -> Path:
    settings = get_settings()
    return ensure_library_layout(settings.resolve_library())


def get_conn() -> sqlite3.Connection:
    return _conn_for(str(library_root()))
