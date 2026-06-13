"""DealStore — in-memory deal object with a Redis-ready interface.

The deal object is the single source of truth for an RFP intake session.
UI components and agent nodes read/write through this store.

TODO (Redis wiring — on critical path):
  Replace the in-memory _store dict with redis-py calls:
    import redis
    _redis = redis.Redis(host=os.getenv("REDIS_URL", "localhost"), port=6379, db=0)
    Key format:  deal:{deal_id}
    Serialise:   json.dumps / json.loads
  The public API (get/set/update/delete) stays identical — only the backend changes.
"""
from __future__ import annotations

import threading
from typing import Any

_store: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def get_deal(deal_id: str) -> dict[str, Any] | None:
    with _lock:
        val = _store.get(deal_id)
        return dict(val) if val is not None else None


def set_deal(deal_id: str, deal: dict[str, Any]) -> None:
    with _lock:
        _store[deal_id] = dict(deal)


def update_deal(deal_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    """Merge patch into existing deal and return the updated deal."""
    with _lock:
        deal = dict(_store.get(deal_id, {}))
        deal.update(patch)
        _store[deal_id] = deal
        return dict(deal)


def delete_deal(deal_id: str) -> None:
    with _lock:
        _store.pop(deal_id, None)


def all_deals() -> dict[str, dict[str, Any]]:
    with _lock:
        return {k: dict(v) for k, v in _store.items()}
