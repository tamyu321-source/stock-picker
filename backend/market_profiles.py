from __future__ import annotations

from copy import deepcopy
from typing import Any


def _source(id: str, label: str, kind: str, role: str, official: bool = False, licensed: bool = False) -> dict[str, Any]:
    return {
        "id": id,
        "label": label,
        "kind": kind,
        "role": role,
        "official": official,
        "licensed": licensed,
    }


MARKET_PROFILES: dict[str, dict[str, Any]] = {
    "TW": {
        "market": "TW",
        "coverageTier": "local-deep",
        "sourceReliabilityScore": 91,
        "localPriority": True,
        "preferred": True,
        "focusRank": 1,
        "primarySources": [
            _source("twse-openapi", "TWSE OpenAPI", "exchange-openapi", "listed prices, valuations, halt and margin data", True),
            _source("taipei-exchange", "Taipei Exchange", "exchange-site", "OTC market, ETF, institutional and margin context", True),
            _source("yahoo-finance", "Yahoo Finance", "market-data", "fallback fundamentals and history"),
            _source("local-news", "MoneyDJ / Cnyes", "local-news", "local market news and company catalysts"),
        ],
        "capabilities": {
            "priceHistory": True,
            "officialExchange": True,
            "localNews": True,
            "fundamentals": True,
            "valuation": True,
            "institutionFlow": True,
            "fundFlow": True,
            "marginShort": True,
            "haltWatch": True,
            "etfCoverage": True,
        },
        "limitations": [
            "TWSE-listed equities have the deepest open coverage; TPEX and full intraday depth still need dedicated adapters.",
            "Some fund and ownership fields can lag official publication schedules.",
        ],
        "professionalAnchors": ["source-transparency", "factor-attribution", "portfolio-risk", "local-market-microstructure"],
    },
    "CN": {
        "market": "CN",
        "coverageTier": "local-deep",
        "sourceReliabilityScore": 88,
        "localPriority": True,
        "preferred": True,
        "focusRank": 2,
        "primarySources": [
            _source("eastmoney", "Eastmoney", "market-data", "A-share quote, turnover, flow and news context"),
            _source("sina-finance", "Sina Finance", "market-data", "A-share real-time quote fallback"),
            _source("sse-market-data", "SSE market data products", "exchange-licensed", "official Shanghai exchange data path", True, True),
            _source("szse-market-data", "SZSE / SZSI market data", "exchange-licensed", "official Shenzhen market data path", True, True),
        ],
        "capabilities": {
            "priceHistory": True,
            "officialExchange": True,
            "localNews": True,
            "fundamentals": True,
            "valuation": True,
            "institutionFlow": True,
            "fundFlow": True,
            "marginShort": True,
            "haltWatch": True,
            "etfCoverage": True,
        },
        "limitations": [
            "Official real-time SSE/SZSE redistribution is licensed; public providers are used with conservative confidence.",
            "Northbound and exchange-level flow data should be added before treating short-term signals as institutional grade.",
        ],
        "professionalAnchors": ["source-transparency", "factor-attribution", "market-regime", "liquidity-risk"],
    },
    "HK": {
        "market": "HK",
        "coverageTier": "regional",
        "sourceReliabilityScore": 78,
        "localPriority": True,
        "preferred": False,
        "focusRank": 3,
        "primarySources": [
            _source("yahoo-finance", "Yahoo Finance", "market-data", "price, fundamentals and history"),
            _source("google-news", "Google News", "news", "English and Chinese catalyst discovery"),
            _source("local-news", "HK regional finance news", "local-news", "regional context"),
        ],
        "capabilities": {
            "priceHistory": True,
            "officialExchange": False,
            "localNews": True,
            "fundamentals": True,
            "valuation": True,
            "institutionFlow": False,
            "fundFlow": False,
            "marginShort": False,
            "haltWatch": False,
            "etfCoverage": True,
        },
        "limitations": [
            "HKEX official feeds and northbound/southbound flow adapters are not wired yet.",
        ],
        "professionalAnchors": ["source-transparency", "portfolio-risk", "regional-flow"],
    },
    "US": {
        "market": "US",
        "coverageTier": "global",
        "sourceReliabilityScore": 76,
        "localPriority": False,
        "preferred": False,
        "focusRank": 4,
        "primarySources": [
            _source("yahoo-finance", "Yahoo Finance", "market-data", "price, fundamentals and ETF profile"),
            _source("google-news", "Google News", "news", "company catalyst discovery"),
            _source("sec-filings", "SEC filings", "future-official", "future official filings adapter", True),
        ],
        "capabilities": {
            "priceHistory": True,
            "officialExchange": False,
            "localNews": True,
            "fundamentals": True,
            "valuation": True,
            "institutionFlow": False,
            "fundFlow": False,
            "marginShort": False,
            "haltWatch": False,
            "etfCoverage": True,
        },
        "limitations": [
            "Current open stack is broad but not a paid institutional consolidated feed.",
        ],
        "professionalAnchors": ["economic-moat", "factor-attribution", "portfolio-risk", "gics-industry"],
    },
    "JP": {
        "market": "JP",
        "coverageTier": "basic",
        "sourceReliabilityScore": 70,
        "localPriority": False,
        "preferred": False,
        "focusRank": 5,
        "primarySources": [
            _source("yahoo-finance", "Yahoo Finance", "market-data", "price, fundamentals and history"),
            _source("google-news", "Google News", "news", "Japanese and English news fallback"),
        ],
        "capabilities": {
            "priceHistory": True,
            "officialExchange": False,
            "localNews": True,
            "fundamentals": True,
            "valuation": True,
            "institutionFlow": False,
            "fundFlow": False,
            "marginShort": False,
            "haltWatch": False,
            "etfCoverage": True,
        },
        "limitations": [
            "TSE official, margin and shareholder-flow adapters are not yet integrated.",
        ],
        "professionalAnchors": ["source-transparency", "gics-industry", "portfolio-risk"],
    },
    "KR": {
        "market": "KR",
        "coverageTier": "basic",
        "sourceReliabilityScore": 68,
        "localPriority": False,
        "preferred": False,
        "focusRank": 6,
        "primarySources": [
            _source("yahoo-finance", "Yahoo Finance", "market-data", "price, fundamentals and history"),
            _source("google-news", "Google News", "news", "Korean and English news fallback"),
        ],
        "capabilities": {
            "priceHistory": True,
            "officialExchange": False,
            "localNews": True,
            "fundamentals": True,
            "valuation": True,
            "institutionFlow": False,
            "fundFlow": False,
            "marginShort": False,
            "haltWatch": False,
            "etfCoverage": True,
        },
        "limitations": [
            "KRX official and investor-flow adapters are not yet integrated.",
        ],
        "professionalAnchors": ["source-transparency", "gics-industry", "portfolio-risk"],
    },
    "SG": {
        "market": "SG",
        "coverageTier": "basic",
        "sourceReliabilityScore": 66,
        "localPriority": False,
        "preferred": False,
        "focusRank": 7,
        "primarySources": [
            _source("yahoo-finance", "Yahoo Finance", "market-data", "price, fundamentals and history"),
            _source("google-news", "Google News", "news", "English news fallback"),
        ],
        "capabilities": {
            "priceHistory": True,
            "officialExchange": False,
            "localNews": True,
            "fundamentals": True,
            "valuation": True,
            "institutionFlow": False,
            "fundFlow": False,
            "marginShort": False,
            "haltWatch": False,
            "etfCoverage": True,
        },
        "limitations": [
            "SGX official and REIT-specific adapters are not yet integrated.",
        ],
        "professionalAnchors": ["source-transparency", "portfolio-risk", "income-quality"],
    },
}


DEFAULT_MARKET_PROFILE = {
    "market": "UNKNOWN",
    "coverageTier": "basic",
    "sourceReliabilityScore": 58,
    "localPriority": False,
    "preferred": False,
    "focusRank": 99,
    "primarySources": [
        _source("yahoo-finance", "Yahoo Finance", "market-data", "generic market data fallback"),
        _source("google-news", "Google News", "news", "generic news fallback"),
    ],
    "capabilities": {
        "priceHistory": True,
        "officialExchange": False,
        "localNews": False,
        "fundamentals": False,
        "valuation": False,
        "institutionFlow": False,
        "fundFlow": False,
        "marginShort": False,
        "haltWatch": False,
        "etfCoverage": False,
    },
    "limitations": ["Market-specific adapter is not configured."],
    "professionalAnchors": ["source-transparency"],
}


SOURCE_SHARE_BASE = {
    "local-news": 0.28,
    "google-news": 0.20,
    "market-universe": 0.34,
    "etf-universe": 0.12,
    "fallback-search": 0.10,
}

SOURCE_SHARE_BY_MARKET = {
    "TW": {
        "local-news": 0.30,
        "google-news": 0.14,
        "market-universe": 0.42,
        "etf-universe": 0.12,
        "fallback-search": 0.06,
    },
    "CN": {
        "local-news": 0.32,
        "google-news": 0.10,
        "market-universe": 0.42,
        "etf-universe": 0.12,
        "fallback-search": 0.06,
    },
}


def market_profile(market: str | None) -> dict[str, Any]:
    key = (market or "").upper()
    profile = MARKET_PROFILES.get(key, {**DEFAULT_MARKET_PROFILE, "market": key or "UNKNOWN"})
    return deepcopy(profile)


def market_profiles() -> dict[str, dict[str, Any]]:
    return {market: market_profile(market) for market in MARKET_PROFILES}


def market_source_reliability(market: str | None) -> float:
    return float(market_profile(market).get("sourceReliabilityScore", DEFAULT_MARKET_PROFILE["sourceReliabilityScore"]))


def market_preferred_source_shares(market: str | None) -> dict[str, float]:
    key = (market or "").upper()
    return {**SOURCE_SHARE_BASE, **SOURCE_SHARE_BY_MARKET.get(key, {})}

