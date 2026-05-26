from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Market = Literal["US", "CN", "HK", "SG", "TW"]
Verdict = Literal["buy", "watch", "sell"]


@dataclass(frozen=True)
class Stock:
    symbol: str
    name: str
    market: Market
    sector: str
    price: float
    change: float
    metrics: dict[str, float]


@dataclass(frozen=True)
class Signal:
    symbol: str
    source: str
    title: str
    sentiment: float
    credibility: float
    age_hours: int
