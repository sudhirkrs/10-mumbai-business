"""Tiny SQLite JSON store: one table per collection."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from typing import Iterable

DB_PATH = os.environ.get("PROPAI_DB", os.path.join(os.path.dirname(__file__), "..", "data", "propai.db"))
COLLECTIONS = ("listings", "transactions", "rera", "market", "research")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    for name in COLLECTIONS:
        c.execute(f"CREATE TABLE IF NOT EXISTS {name} (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    return c


def put(coll: str, obj: dict, key: str | None = None) -> str:
    key = key or obj.get("id") or uuid.uuid4().hex[:10]
    obj = {**obj, "id": key} if coll not in ("rera", "market", "research") else obj
    with _conn() as c:
        c.execute(f"INSERT OR REPLACE INTO {coll} (id, data) VALUES (?, ?)", (key, json.dumps(obj)))
    return key


def put_many(coll: str, objs: Iterable[tuple[str | None, dict]]) -> int:
    n = 0
    for key, o in objs:
        put(coll, o, key)
        n += 1
    return n


def get(coll: str, key: str) -> dict | None:
    with _conn() as c:
        row = c.execute(f"SELECT data FROM {coll} WHERE id=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def all_(coll: str) -> list[dict]:
    with _conn() as c:
        return [json.loads(r[0]) for r in c.execute(f"SELECT data FROM {coll}")]


def clear(coll: str) -> None:
    with _conn() as c:
        c.execute(f"DELETE FROM {coll}")
