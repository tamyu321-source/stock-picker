from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import time
from threading import Lock
from typing import Any, Callable, Hashable

from backend.providers import Article, MarketSnapshot


DEFAULT_MARKET_CACHE_TTL_SECONDS = 300
DEFAULT_NEWS_CACHE_TTL_SECONDS = 900
DEFAULT_MARKET_CACHE_SIZE = 512
DEFAULT_NEWS_CACHE_SIZE = 512


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TtlCache:
    def __init__(self, ttl_seconds: int, max_entries: int = 512, timer: Callable[[], float] | None = None):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._timer = timer or time.monotonic
        self._items: OrderedDict[Hashable, _CacheEntry] = OrderedDict()
        self._lock = Lock()

    def get(self, key: Hashable):
        now = self._timer()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return entry.value

    def set(self, key: Hashable, value: Any):
        with self._lock:
            self._items[key] = _CacheEntry(value=value, expires_at=self._timer() + self.ttl_seconds)
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

    def stats(self) -> dict:
        with self._lock:
            return {"entries": len(self._items), "ttlSeconds": self.ttl_seconds, "maxEntries": self.max_entries}


def _copy_snapshot(snapshot: MarketSnapshot) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=snapshot.symbol,
        name=snapshot.name,
        market=snapshot.market,
        sector=snapshot.sector,
        price=snapshot.price,
        change=snapshot.change,
        currency=snapshot.currency,
        closes=list(snapshot.closes),
        info=dict(snapshot.info),
    )


class CachedMarketDataProvider:
    def __init__(
        self,
        provider,
        ttl_seconds: int = DEFAULT_MARKET_CACHE_TTL_SECONDS,
        max_entries: int = DEFAULT_MARKET_CACHE_SIZE,
    ):
        self.provider = provider
        self.cache = TtlCache(ttl_seconds=ttl_seconds, max_entries=max_entries)

    def fetch(self, symbol: str, refresh: bool = False) -> MarketSnapshot:
        key = str(symbol).upper()
        cached = None if refresh else self.cache.get(key)
        if cached is not None:
            return _copy_snapshot(cached)

        snapshot = _copy_snapshot(self.provider.fetch(symbol))
        self.cache.set(key, snapshot)
        return _copy_snapshot(snapshot)

    def stats(self) -> dict:
        return self.cache.stats()


class CachedNewsCrawler:
    def __init__(
        self,
        crawler,
        ttl_seconds: int = DEFAULT_NEWS_CACHE_TTL_SECONDS,
        max_entries: int = DEFAULT_NEWS_CACHE_SIZE,
    ):
        self.crawler = crawler
        self.cache = TtlCache(ttl_seconds=ttl_seconds, max_entries=max_entries)

    def fetch(self, symbol: str, name: str, limit: int = 8, refresh: bool = False) -> list[Article]:
        key = (str(symbol).upper(), " ".join(str(name).lower().split()), int(limit))
        cached = None if refresh else self.cache.get(key)
        if cached is not None:
            return list(cached)

        articles = list(self.crawler.fetch(symbol, name, limit=limit))
        self.cache.set(key, articles)
        return list(articles)

    def stats(self) -> dict:
        return self.cache.stats()
