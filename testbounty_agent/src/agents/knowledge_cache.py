"""
KnowledgeCache — Persistent cache for AppKnowledge objects.

Prevents re-running expensive LLM synthesis for the same URL.
Cache is keyed by normalised base URL and stored in knowledge_cache.json.

Usage:
    cache = KnowledgeCache()
    hit = cache.get("https://myapp.com")
    if hit:
        return hit
    knowledge = build_expensive_knowledge(...)
    cache.set("https://myapp.com", knowledge)
"""

from __future__ import annotations

import json
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

CACHE_FILE = Path("knowledge_cache.json")
CACHE_TTL_HOURS = 48  # Re-synthesise after 48 hours


def _normalise_url(url: str) -> str:
    """Strip query params, trailing slashes, www prefix → stable cache key."""
    url = re.sub(r"https?://", "", url.lower())
    url = re.sub(r"^www\.", "", url)
    url = url.split("?")[0].split("#")[0].rstrip("/")
    return url


def _url_key(url: str) -> str:
    return hashlib.md5(_normalise_url(url).encode()).hexdigest()[:16]


class KnowledgeCache:
    def __init__(self):
        self._data: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def _save(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"[KnowledgeCache] Save failed: {e}")

    def get(self, url: str) -> Optional[dict]:
        """Return cached AppKnowledge if fresh, else None."""
        key = _url_key(url)
        entry = self._data.get(key)
        if not entry:
            return None

        cached_at = entry.get("cached_at", "")
        if cached_at:
            try:
                age = datetime.now() - datetime.fromisoformat(cached_at)
                if age > timedelta(hours=CACHE_TTL_HOURS):
                    print(f"[KnowledgeCache] Stale cache for {_normalise_url(url)} ({age.total_seconds()/3600:.1f}h old)")
                    del self._data[key]
                    self._save()
                    return None
            except Exception:
                pass

        knowledge = entry.get("knowledge")
        if knowledge:
            print(f"[KnowledgeCache] HIT for {_normalise_url(url)} — saved LLM call")
            knowledge["_from_cache"] = True
        return knowledge

    def set(self, url: str, knowledge: dict):
        """Store AppKnowledge. Strip _from_cache flag before saving."""
        key = _url_key(url)
        clean = {k: v for k, v in knowledge.items() if k != "_from_cache"}
        self._data[key] = {
            "url": _normalise_url(url),
            "cached_at": datetime.now().isoformat(),
            "knowledge": clean,
        }
        self._save()
        print(f"[KnowledgeCache] Stored knowledge for {_normalise_url(url)}")

    def invalidate(self, url: str):
        """Force re-synthesis on next explore."""
        key = _url_key(url)
        if key in self._data:
            del self._data[key]
            self._save()

    def list_entries(self) -> list:
        return [
            {
                "url": v["url"],
                "cached_at": v.get("cached_at"),
                "domain": v.get("knowledge", {}).get("domain", "unknown"),
                "confidence": v.get("knowledge", {}).get("confidence", "unknown"),
            }
            for v in self._data.values()
        ]


# Singleton
_cache: Optional[KnowledgeCache] = None

def get_cache() -> KnowledgeCache:
    global _cache
    if _cache is None:
        _cache = KnowledgeCache()
    return _cache
