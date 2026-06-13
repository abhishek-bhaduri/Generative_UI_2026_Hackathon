"""DealStore — deal object storage with automatic Redis/in-memory selection.

If REDIS_URL is set, deals are stored in Redis (survives server restarts).
If not, falls back to an in-memory dict (single-session demo mode).

Key format: deal:{deal_id}  (JSON-serialised DealObject)
Public API is identical either way — callers don't need to know the backend.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any

log = logging.getLogger(__name__)

# ─── Backend selection ────────────────────────────────────────────────────────

_redis_client: Any = None
_store: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _get_redis() -> Any:
    """Return a connected redis.Redis client, or None if Redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return None

    try:
        import redis as redis_lib
        client = redis_lib.from_url(redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        log.info("[deal_store] Redis connected at %s", redis_url.split("@")[-1])
        return _redis_client
    except Exception as exc:  # noqa: BLE001
        log.warning("[deal_store] Redis unavailable (%s) — falling back to in-memory", exc)
        return None


def _key(deal_id: str) -> str:
    return f"deal:{deal_id}"


# ─── Public API ───────────────────────────────────────────────────────────────

def get_deal(deal_id: str) -> dict[str, Any] | None:
    r = _get_redis()
    if r is not None:
        raw = r.get(_key(deal_id))
        return json.loads(raw) if raw else None
    with _lock:
        val = _store.get(deal_id)
        return dict(val) if val is not None else None


def set_deal(deal_id: str, deal: dict[str, Any]) -> None:
    r = _get_redis()
    if r is not None:
        r.set(_key(deal_id), json.dumps(deal), ex=86400)  # 24h TTL
        return
    with _lock:
        _store[deal_id] = dict(deal)


def update_deal(deal_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    """Merge patch into existing deal and return the updated deal."""
    deal = get_deal(deal_id) or {}
    deal.update(patch)
    set_deal(deal_id, deal)
    return deal


def delete_deal(deal_id: str) -> None:
    r = _get_redis()
    if r is not None:
        r.delete(_key(deal_id))
        return
    with _lock:
        _store.pop(deal_id, None)


def all_deals() -> dict[str, dict[str, Any]]:
    r = _get_redis()
    if r is not None:
        keys = r.keys("deal:*")
        result = {}
        for k in keys:
            raw = r.get(k)
            if raw:
                result[k.removeprefix("deal:")] = json.loads(raw)
        return result
    with _lock:
        return {k: dict(v) for k, v in _store.items()}
