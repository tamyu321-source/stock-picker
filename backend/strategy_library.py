from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.request import Request, urlopen


DETAILED_WEIGHT_KEYS = [
    "todayBuy",
    "futureRise",
    "profitableExit",
    "newsHeat",
    "trendContinuation",
    "maStructure",
    "momentum",
    "volumeConfirmation",
    "rsiHealth",
    "macdConfirmation",
    "supportResistance",
    "fundFlow",
    "valuation",
    "quality",
    "riskControl",
    "tTrade",
]


DETAILED_WEIGHT_LABELS = {
    "todayBuy": "Worth buying today",
    "futureRise": "Future rise potential",
    "profitableExit": "Profitable exit later",
    "newsHeat": "News heat",
    "trendContinuation": "Trend continuation",
    "maStructure": "Moving-average structure",
    "momentum": "Momentum",
    "volumeConfirmation": "Volume confirmation",
    "rsiHealth": "RSI health",
    "macdConfirmation": "MACD confirmation",
    "supportResistance": "Support / resistance",
    "fundFlow": "Fund flow",
    "valuation": "Valuation",
    "quality": "Fundamental quality",
    "riskControl": "Risk control",
    "tTrade": "T / exit tradability",
}


ONLINE_STRATEGY_SOURCES = [
    {
        "id": "fidelity-indicator-guide",
        "title": "Fidelity Technical Indicator Guide",
        "url": "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/overview",
        "families": ["trend", "momentum", "volume", "supportResistance", "risk"],
        "keywords": ["moving average", "rsi", "macd", "volume", "support", "resistance"],
    },
    {
        "id": "fidelity-rsi",
        "title": "Fidelity RSI guide",
        "url": "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI",
        "families": ["rsi", "momentum", "reversal"],
        "keywords": ["relative strength index", "overbought", "oversold", "divergence"],
    },
    {
        "id": "fidelity-macd",
        "title": "Fidelity MACD guide",
        "url": "https://www.fidelity.com/viewpoints/active-investor/how-to-use-macd",
        "families": ["macd", "momentum", "trend"],
        "keywords": ["macd", "signal line", "momentum", "buy-and-sell signals"],
    },
    {
        "id": "schwab-momentum-strength",
        "title": "Schwab momentum strength indicators",
        "url": "https://www.schwab.com/learn/story/3-strength-indicators-assessing-stock-momentum",
        "families": ["momentum", "trend", "rsi", "macd"],
        "keywords": ["adx", "rsi", "macd", "momentum", "trend"],
    },
    {
        "id": "schwab-moving-averages",
        "title": "Schwab moving averages",
        "url": "https://www.schwab.com/learn/story/simple-vs-exponential-moving-averages",
        "families": ["ma", "trend", "supportResistance"],
        "keywords": ["moving average", "support", "resistance", "trend"],
    },
    {
        "id": "schwab-vwap-volume",
        "title": "Schwab VWAP and volume-weighted indicators",
        "url": "https://www.schwab.com/learn/story/how-to-use-volume-weighted-indicators-trading",
        "families": ["volume", "intraday", "exit"],
        "keywords": ["vwap", "volume", "intraday", "average price"],
    },
    {
        "id": "schwab-bollinger-bands",
        "title": "Schwab Bollinger Bands",
        "url": "https://www.schwab.com/learn/story/bollinger-bands-what-they-are-and-how-to-use-them",
        "families": ["volatility", "meanReversion", "entryExit"],
        "keywords": ["bollinger", "volatility", "entry", "exit"],
    },
    {
        "id": "investopedia-moving-average",
        "title": "Investopedia moving averages",
        "url": "https://www.investopedia.com/articles/active-trading/052014/how-use-moving-average-buy-stocks.asp",
        "families": ["ma", "trend", "supportResistance"],
        "keywords": ["moving average", "crossover", "support", "resistance"],
    },
    {
        "id": "investopedia-golden-cross",
        "title": "Investopedia golden cross",
        "url": "https://www.investopedia.com/terms/g/goldencross.asp",
        "families": ["ma", "breakout", "trend"],
        "keywords": ["golden cross", "breakout", "moving average", "support"],
    },
    {
        "id": "investopedia-macd",
        "title": "Investopedia MACD strategies",
        "url": "https://www.investopedia.com/articles/forex/05/macddiverge.asp",
        "families": ["macd", "momentum", "divergence"],
        "keywords": ["macd", "histogram", "divergence", "crossover"],
    },
    {
        "id": "investopedia-rsi-signals",
        "title": "Investopedia RSI buy and sell signals",
        "url": "https://www.investopedia.com/articles/active-trading/042114/overbought-or-oversold-use-relative-strength-index-find-out.asp",
        "families": ["rsi", "meanReversion", "macd"],
        "keywords": ["rsi", "overbought", "oversold", "macd"],
    },
    {
        "id": "fidelity-trading-central-methodology",
        "title": "Trading Central technical views on Fidelity",
        "url": "https://research2.fidelity.com/fidelity/research/reports/release2/Research/TradingCentral.asp",
        "families": ["intraday", "shortTerm", "mediumTerm", "supportResistance"],
        "keywords": ["intraday", "short term", "medium term", "technical analysis"],
    },
]


REFINED_STRATEGIES = [
    {
        "id": "ai_smart_blend",
        "name": "AI Smart Blend",
        "description": "Auto-blends the refreshed online strategy library across buy-today quality, future rise, profitable exit, news heat, trend, and risk.",
        "sourceStrategyIds": [source["id"] for source in ONLINE_STRATEGY_SOURCES],
        "detailedWeights": {
            "todayBuy": 12,
            "futureRise": 13,
            "profitableExit": 10,
            "newsHeat": 8,
            "trendContinuation": 10,
            "maStructure": 7,
            "momentum": 8,
            "volumeConfirmation": 7,
            "rsiHealth": 5,
            "macdConfirmation": 6,
            "supportResistance": 5,
            "fundFlow": 4,
            "valuation": 3,
            "quality": 4,
            "riskControl": 7,
            "tTrade": 5,
        },
    },
    {
        "id": "today_breakout_volume",
        "name": "Today Breakout + Volume",
        "description": "Focuses on whether the current price break has volume and enough same-day entry quality.",
        "sourceStrategyIds": ["investopedia-golden-cross", "schwab-vwap-volume", "fidelity-indicator-guide"],
        "detailedWeights": {
            "todayBuy": 18,
            "futureRise": 10,
            "profitableExit": 8,
            "newsHeat": 6,
            "trendContinuation": 8,
            "maStructure": 7,
            "momentum": 10,
            "volumeConfirmation": 16,
            "rsiHealth": 3,
            "macdConfirmation": 5,
            "supportResistance": 9,
            "fundFlow": 5,
            "valuation": 2,
            "quality": 2,
            "riskControl": 6,
            "tTrade": 5,
        },
    },
    {
        "id": "next_session_continuation",
        "name": "Next-Session Continuation",
        "description": "Prioritizes whether today's edge can continue tomorrow without immediate reversal risk.",
        "sourceStrategyIds": ["schwab-momentum-strength", "fidelity-macd", "fidelity-rsi"],
        "detailedWeights": {
            "todayBuy": 8,
            "futureRise": 20,
            "profitableExit": 11,
            "newsHeat": 6,
            "trendContinuation": 17,
            "maStructure": 10,
            "momentum": 12,
            "volumeConfirmation": 7,
            "rsiHealth": 8,
            "macdConfirmation": 10,
            "supportResistance": 5,
            "fundFlow": 4,
            "valuation": 2,
            "quality": 4,
            "riskControl": 8,
            "tTrade": 4,
        },
    },
    {
        "id": "profitable_exit_t_trade",
        "name": "Profitable Exit / T Trade",
        "description": "Optimizes for tradable range, liquidity, and whether a later high-sell window is realistic.",
        "sourceStrategyIds": ["schwab-vwap-volume", "schwab-bollinger-bands", "fidelity-trading-central-methodology"],
        "detailedWeights": {
            "todayBuy": 8,
            "futureRise": 8,
            "profitableExit": 22,
            "newsHeat": 5,
            "trendContinuation": 8,
            "maStructure": 5,
            "momentum": 7,
            "volumeConfirmation": 12,
            "rsiHealth": 7,
            "macdConfirmation": 5,
            "supportResistance": 10,
            "fundFlow": 4,
            "valuation": 2,
            "quality": 2,
            "riskControl": 10,
            "tTrade": 18,
        },
    },
    {
        "id": "news_heat_catalyst",
        "name": "News Heat Catalyst",
        "description": "Looks for strong, fresh, broad news attention that still aligns with trend and exit quality.",
        "sourceStrategyIds": ["fidelity-indicator-guide", "schwab-momentum-strength"],
        "detailedWeights": {
            "todayBuy": 10,
            "futureRise": 12,
            "profitableExit": 7,
            "newsHeat": 22,
            "trendContinuation": 8,
            "maStructure": 5,
            "momentum": 8,
            "volumeConfirmation": 7,
            "rsiHealth": 4,
            "macdConfirmation": 5,
            "supportResistance": 4,
            "fundFlow": 8,
            "valuation": 2,
            "quality": 3,
            "riskControl": 7,
            "tTrade": 4,
        },
    },
    {
        "id": "pullback_to_rising_average",
        "name": "Pullback to Rising Average",
        "description": "Prefers controlled pullbacks near rising moving averages instead of chasing extended candles.",
        "sourceStrategyIds": ["fidelity-indicator-guide", "schwab-moving-averages", "investopedia-moving-average"],
        "detailedWeights": {
            "todayBuy": 14,
            "futureRise": 12,
            "profitableExit": 9,
            "newsHeat": 4,
            "trendContinuation": 10,
            "maStructure": 15,
            "momentum": 7,
            "volumeConfirmation": 5,
            "rsiHealth": 10,
            "macdConfirmation": 5,
            "supportResistance": 10,
            "fundFlow": 3,
            "valuation": 5,
            "quality": 5,
            "riskControl": 12,
            "tTrade": 4,
        },
    },
    {
        "id": "rsi_macd_reversal",
        "name": "RSI + MACD Reversal",
        "description": "Waits for RSI exhaustion to align with MACD confirmation before treating a turn as buyable.",
        "sourceStrategyIds": ["fidelity-rsi", "investopedia-rsi-signals", "investopedia-macd"],
        "detailedWeights": {
            "todayBuy": 10,
            "futureRise": 13,
            "profitableExit": 8,
            "newsHeat": 4,
            "trendContinuation": 9,
            "maStructure": 6,
            "momentum": 8,
            "volumeConfirmation": 5,
            "rsiHealth": 17,
            "macdConfirmation": 17,
            "supportResistance": 7,
            "fundFlow": 3,
            "valuation": 4,
            "quality": 3,
            "riskControl": 11,
            "tTrade": 4,
        },
    },
    {
        "id": "defensive_quality_value",
        "name": "Defensive Quality + Value",
        "description": "Uses online technical confirmation only after valuation, quality, and risk are acceptable.",
        "sourceStrategyIds": ["fidelity-indicator-guide", "schwab-moving-averages"],
        "detailedWeights": {
            "todayBuy": 9,
            "futureRise": 9,
            "profitableExit": 7,
            "newsHeat": 4,
            "trendContinuation": 6,
            "maStructure": 6,
            "momentum": 4,
            "volumeConfirmation": 4,
            "rsiHealth": 4,
            "macdConfirmation": 4,
            "supportResistance": 5,
            "fundFlow": 4,
            "valuation": 18,
            "quality": 18,
            "riskControl": 18,
            "tTrade": 3,
        },
    },
]


_cached_catalog: dict | None = None


def _fetch_source_status(source: dict) -> dict:
    request = Request(source["url"], headers={"User-Agent": "Mozilla/5.0 Codex Stock Picker"})
    try:
        with urlopen(request, timeout=7) as response:
            raw = response.read(180_000)
            text = raw.decode("utf-8", errors="ignore").lower()
    except Exception as exc:
        return {**source, "available": False, "matchedKeywords": [], "error": str(exc)[:160]}
    matched = [keyword for keyword in source["keywords"] if re.search(re.escape(keyword.lower()), text)]
    return {**source, "available": True, "matchedKeywords": matched, "error": ""}


def _normalize_detailed(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(weights.get(key) or 0)) for key in DETAILED_WEIGHT_KEYS) or 1.0
    return {key: round(max(0.0, float(weights.get(key) or 0)) / total * 100, 2) for key in DETAILED_WEIGHT_KEYS}


def _core_weights_from_detailed(detailed: dict[str, float]) -> dict[str, float]:
    normalized = _normalize_detailed(detailed)
    return {
        "momentum": round(
            normalized["futureRise"] * 0.18
            + normalized["trendContinuation"] * 0.22
            + normalized["maStructure"] * 0.12
            + normalized["momentum"] * 0.18
            + normalized["volumeConfirmation"] * 0.10
            + normalized["rsiHealth"] * 0.08
            + normalized["macdConfirmation"] * 0.12,
            2,
        ),
        "value": round(normalized["valuation"] * 0.72 + normalized["supportResistance"] * 0.18 + normalized["todayBuy"] * 0.10, 2),
        "sentiment": round(normalized["newsHeat"] * 0.68 + normalized["fundFlow"] * 0.18 + normalized["todayBuy"] * 0.14, 2),
        "risk": round(normalized["riskControl"] * 0.55 + normalized["profitableExit"] * 0.20 + normalized["tTrade"] * 0.15 + normalized["rsiHealth"] * 0.10, 2),
        "quality": round(normalized["quality"] * 0.74 + normalized["valuation"] * 0.12 + normalized["riskControl"] * 0.14, 2),
    }


def _source_family_scores(sources: list[dict]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for source in sources:
        if not source.get("available"):
            continue
        multiplier = 1 + min(4, len(source.get("matchedKeywords") or [])) * 0.12
        for family in source["families"]:
            scores[family] = scores.get(family, 0.0) + multiplier
    return scores


def _refreshed_ai_weights(base_weights: dict[str, float], sources: list[dict]) -> dict[str, float]:
    scores = _source_family_scores(sources)
    weights = dict(base_weights)
    adjustments = {
        "trend": ["trendContinuation", "maStructure", "momentum"],
        "momentum": ["momentum", "macdConfirmation", "rsiHealth"],
        "volume": ["volumeConfirmation", "profitableExit"],
        "supportResistance": ["supportResistance", "todayBuy"],
        "rsi": ["rsiHealth", "riskControl"],
        "macd": ["macdConfirmation", "futureRise"],
        "intraday": ["tTrade", "profitableExit"],
        "entryExit": ["todayBuy", "profitableExit", "supportResistance"],
        "volatility": ["riskControl", "profitableExit"],
        "meanReversion": ["rsiHealth", "supportResistance"],
        "breakout": ["todayBuy", "volumeConfirmation", "futureRise"],
    }
    for family, keys in adjustments.items():
        bump = min(4.0, scores.get(family, 0.0) * 0.45)
        for key in keys:
            weights[key] = weights.get(key, 0.0) + bump
    return _normalize_detailed(weights)


def get_strategy_catalog(refresh: bool = False) -> dict:
    global _cached_catalog
    if _cached_catalog is not None and not refresh:
        return _cached_catalog

    sources = [_fetch_source_status(source) for source in ONLINE_STRATEGY_SOURCES] if refresh else [{**source, "available": None, "matchedKeywords": [], "error": ""} for source in ONLINE_STRATEGY_SOURCES]
    strategies = []
    for strategy in REFINED_STRATEGIES:
        detailed = _normalize_detailed(strategy["detailedWeights"])
        if strategy["id"] == "ai_smart_blend":
            detailed = _refreshed_ai_weights(detailed, sources)
        strategies.append(
            {
                **strategy,
                "detailedWeights": detailed,
                "weights": _core_weights_from_detailed(detailed),
                "riskTolerance": 55 if strategy["id"] != "defensive_quality_value" else 38,
            }
        )
    _cached_catalog = {
        "refreshedAt": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "strategies": strategies,
        "detailedWeightKeys": DETAILED_WEIGHT_KEYS,
        "detailedWeightLabels": DETAILED_WEIGHT_LABELS,
    }
    return _cached_catalog


def all_runtime_strategies(base_strategies: list[dict] | None = None, refresh: bool = False, include_base: bool = False) -> list[dict]:
    catalog = get_strategy_catalog(refresh=refresh)
    base_strategies = base_strategies or []
    if not include_base:
        return list(catalog["strategies"])
    existing = {strategy["id"] for strategy in base_strategies}
    return [*base_strategies, *[strategy for strategy in catalog["strategies"] if strategy["id"] not in existing]]
