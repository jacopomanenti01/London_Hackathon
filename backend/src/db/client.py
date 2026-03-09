from __future__ import annotations

import os
from typing import Any

from surrealdb import AsyncSurreal

from .statics import DB_URL

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PSW", "root")
DB_NAMESPACE = os.getenv("DB_NAMESPACE", "duediligence")
DB_DATABASE = os.getenv("DB_DATABASE", "main")

_client: Any = None


async def init_db() -> Any:
    global _client
    _client = AsyncSurreal(DB_URL)
    await _client.connect()
    await _client.signin({"username": DB_USER, "password": DB_PASSWORD})
    await _client.use(DB_NAMESPACE, DB_DATABASE)
    return _client


async def close_db() -> None:
    global _client
    if _client:
        await _client.close()
        _client = None


def get_db() -> Any:
    if _client is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _client
