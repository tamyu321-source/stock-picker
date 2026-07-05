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
        "families": ["trend", "momentum", "volume", "supportResistance", "risk", "shortTerm"],
        "timeHorizon": "short",
        "keywords": ["moving average", "rsi", "macd", "volume", "support", "resistance"],
    },
    {
        "id": "fidelity-rsi",
        "title": "Fidelity RSI guide",
        "url": "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI",
        "families": ["rsi", "momentum", "reversal", "shortTerm"],
        "timeHorizon": "short",
        "keywords": ["relative strength index", "overbought", "oversold", "divergence"],
    },
    {
        "id": "fidelity-macd",
        "title": "Fidelity MACD guide",
        "url": "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/macd",
        "urls": ["https://www.fidelity.com/viewpoints/active-investor/how-to-use-macd"],
        "families": ["macd", "momentum", "trend", "shortTerm"],
        "timeHorizon": "short",
        "keywords": ["macd", "signal line", "momentum", "buy-and-sell signals"],
    },
    {
        "id": "fidelity-moving-averages",
        "title": "Fidelity moving average signals",
        "url": "https://www.fidelity.com/viewpoints/active-investor/moving-averages",
        "families": ["ma", "trend", "supportResistance", "mediumTerm"],
        "timeHorizon": "medium",
        "keywords": ["moving averages", "buy and sell signals", "crossovers", "trend"],
    },
    {
        "id": "schwab-momentum-strength",
        "title": "Schwab momentum strength indicators",
        "url": "https://www.schwab.com/learn/story/3-strength-indicators-assessing-stock-momentum",
        "families": ["momentum", "trend", "rsi", "macd", "shortTerm"],
        "timeHorizon": "short",
        "keywords": ["adx", "rsi", "macd", "momentum", "trend"],
    },
    {
        "id": "schwab-moving-averages",
        "title": "Schwab moving averages",
        "url": "https://www.schwab.com/learn/story/how-to-use-moving-averages-stock-trading",
        "urls": ["https://www.schwab.com/learn/story/how-to-trade-simple-moving-averages"],
        "families": ["ma", "trend", "supportResistance", "mediumTerm"],
        "timeHorizon": "medium",
        "keywords": ["moving average", "support", "resistance", "trend"],
    },
    {
        "id": "schwab-macd",
        "title": "Schwab MACD trading guide",
        "url": "https://www.schwab.com/learn/story/trading-stocks-with-macd",
        "families": ["macd", "momentum", "trend", "shortTerm"],
        "timeHorizon": "short",
        "keywords": ["macd", "momentum", "buy", "sell", "signal"],
    },
    {
        "id": "schwab-vwap-volume",
        "title": "Schwab VWAP and volume-weighted indicators",
        "url": "https://www.schwab.com/learn/story/how-to-use-volume-weighted-indicators-trading",
        "families": ["volume", "intraday", "exit", "shortTerm"],
        "timeHorizon": "short",
        "keywords": ["vwap", "volume", "intraday", "average price"],
    },
    {
        "id": "schwab-bollinger-bands",
        "title": "Schwab Bollinger Bands",
        "url": "https://www.schwab.com/learn/story/bollinger-bands-what-they-are-and-how-to-use-them",
        "families": ["volatility", "meanReversion", "entryExit", "shortTerm"],
        "timeHorizon": "short",
        "keywords": ["bollinger", "volatility", "entry", "exit"],
    },
    {
        "id": "investopedia-moving-average",
        "title": "Investopedia moving averages",
        "url": "https://www.investopedia.com/articles/active-trading/052014/how-use-moving-average-buy-stocks.asp",
        "families": ["ma", "trend", "supportResistance", "mediumTerm"],
        "timeHorizon": "medium",
        "keywords": ["moving average", "crossover", "support", "resistance"],
    },
    {
        "id": "investopedia-golden-cross",
        "title": "Investopedia golden cross",
        "url": "https://www.investopedia.com/terms/g/goldencross.asp",
        "families": ["ma", "breakout", "trend", "mediumTerm"],
        "timeHorizon": "medium",
        "keywords": ["golden cross", "breakout", "moving average", "support"],
    },
    {
        "id": "investopedia-macd",
        "title": "Investopedia MACD",
        "url": "https://www.investopedia.com/terms/m/macd.asp",
        "urls": ["https://www.investopedia.com/articles/forex/05/macddiverge.asp"],
        "families": ["macd", "momentum", "divergence", "shortTerm"],
        "timeHorizon": "short",
        "keywords": ["macd", "histogram", "divergence", "crossover"],
    },
    {
        "id": "investopedia-rsi-signals",
        "title": "Investopedia RSI buy and sell signals",
        "url": "https://www.investopedia.com/articles/active-trading/042114/overbought-or-oversold-use-relative-strength-index-find-out.asp",
        "families": ["rsi", "meanReversion", "macd", "shortTerm"],
        "timeHorizon": "short",
        "keywords": ["rsi", "overbought", "oversold", "macd"],
    },
    {
        "id": "fidelity-trading-central-methodology",
        "title": "Trading Central technical views on Fidelity",
        "url": "https://research2.fidelity.com/fidelity/research/reports/release2/Research/TradingCentral.asp",
        "families": ["intraday", "shortTerm", "mediumTerm", "supportResistance"],
        "timeHorizon": "short",
        "keywords": ["intraday", "short term", "medium term", "technical analysis"],
    },
    {
        "id": "fidelity-fundamental-analysis",
        "title": "Fidelity fundamental analysis",
        "url": "https://www.fidelity.com/learning-center/trading-investing/fundamental-analysis/analyzing-stock-fundamentals",
        "urls": ["https://www.fidelity.com/learning-center/trading-investing/fundamental-analysis/introduction-to-fundamental-analysis-video"],
        "families": ["fundamental", "quality", "valuation", "longTerm"],
        "timeHorizon": "long",
        "keywords": ["fundamental analysis", "earnings", "intrinsic value", "financial metrics"],
    },
    {
        "id": "fidelity-quality-stocks",
        "title": "Fidelity quality stocks",
        "url": "https://www.fidelity.com/learning-center/trading-investing/investing-in-quality",
        "families": ["quality", "risk", "longTerm"],
        "timeHorizon": "long",
        "keywords": ["quality stocks", "volatility", "discounted prices", "long term"],
    },
    {
        "id": "fidelity-quality-value",
        "title": "Fidelity quality and valuation research",
        "url": "https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/Intersection_of_High_Quality_and_Cheap_Valuation_Fidelity.pdf",
        "families": ["quality", "valuation", "longTerm"],
        "timeHorizon": "long",
        "keywords": ["quality", "valuation", "return on assets", "long term"],
    },
    {
        "id": "investor-gov-asset-allocation",
        "title": "Investor.gov asset allocation and diversification",
        "url": "https://www.investor.gov/introduction-investing/getting-started/asset-allocation",
        "urls": ["https://www.sec.gov/about/reports-publications/investorpubsassetallocationhtm"],
        "families": ["risk", "portfolio", "longTerm"],
        "timeHorizon": "long",
        "keywords": ["asset allocation", "diversification", "risk", "time horizon"],
    },
    {
        "id": "investor-gov-diversification",
        "title": "Investor.gov diversification",
        "url": "https://www.investor.gov/introduction-investing/investing-basics/glossary/diversification",
        "families": ["risk", "portfolio", "longTerm"],
        "timeHorizon": "long",
        "keywords": ["diversification", "risk", "investments"],
    },
    {
        "id": "finra-diversification",
        "title": "FINRA asset allocation and diversification",
        "url": "https://www.finra.org/investors/investing/investing-basics/asset-allocation-diversification",
        "families": ["risk", "portfolio", "longTerm"],
        "timeHorizon": "long",
        "keywords": ["asset allocation", "diversification", "risk", "portfolio"],
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
        "id": "short_term_adaptive_trade",
        "name": "Short-Term Adaptive Trade",
        "description": "Separates short-term tradability from long-term quality, prioritizing same-day entry, tomorrow continuation, liquidity, fund flow, and exit windows.",
        "sourceStrategyIds": [
            "fidelity-indicator-guide",
            "fidelity-rsi",
            "fidelity-macd",
            "schwab-momentum-strength",
            "schwab-macd",
            "schwab-vwap-volume",
            "schwab-bollinger-bands",
            "fidelity-trading-central-methodology",
        ],
        "detailedWeights": {
            "todayBuy": 17,
            "futureRise": 16,
            "profitableExit": 14,
            "newsHeat": 9,
            "trendContinuation": 13,
            "maStructure": 7,
            "momentum": 10,
            "volumeConfirmation": 12,
            "rsiHealth": 6,
            "macdConfirmation": 8,
            "supportResistance": 8,
            "fundFlow": 8,
            "valuation": 2,
            "quality": 2,
            "riskControl": 8,
            "tTrade": 10,
        },
    },
    {
        "id": "mid_long_quality_compounder",
        "name": "Mid/Long Quality Compounder",
        "description": "Ranks durable quality candidates by fundamentals, valuation, risk control, trend support, and score stability instead of one-day heat.",
        "sourceStrategyIds": [
            "fidelity-fundamental-analysis",
            "fidelity-quality-stocks",
            "fidelity-quality-value",
            "investor-gov-asset-allocation",
            "investor-gov-diversification",
            "finra-diversification",
            "fidelity-moving-averages",
            "schwab-moving-averages",
        ],
        "detailedWeights": {
            "todayBuy": 5,
            "futureRise": 12,
            "profitableExit": 6,
            "newsHeat": 3,
            "trendContinuation": 10,
            "maStructure": 10,
            "momentum": 4,
            "volumeConfirmation": 3,
            "rsiHealth": 4,
            "macdConfirmation": 4,
            "supportResistance": 7,
            "fundFlow": 3,
            "valuation": 20,
            "quality": 22,
            "riskControl": 20,
            "tTrade": 1,
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


DEFAULT_STRATEGY_BEHAVIOR = {
    "mode": "balanced",
    "horizon": "balanced",
    "buyFloor": 68,
    "watchFloor": 54,
    "entryGates": [
        {"key": "strategyGateTodayBuy", "metric": "todayBuyScore", "min": 56},
        {"key": "strategyGateFutureRise", "metric": "futureRiseScore", "min": 54},
        {"key": "strategyGateDownside", "metric": "downsideRiskScore", "max": 66, "cap": 58},
    ],
    "vetoRules": [
        {"key": "strategyVetoSevereDrop", "metric": "priceChange", "max": -7.0, "cap": 38, "direction": "min"},
        {"key": "strategyVetoDownside", "metric": "downsideRiskScore", "max": 78, "cap": 42},
        {"key": "strategyVetoReversal", "metric": "nextSessionReversalRiskScore", "max": 78, "cap": 52},
    ],
    "fitWeights": {
        "qualityCompositeScore": 0.22,
        "shortTermScore": 0.18,
        "midLongTermScore": 0.18,
        "overallTotal": 0.14,
        "todayBuyScore": 0.10,
        "futureRiseScore": 0.08,
        "risk": 0.06,
        "fundFlowScore": 0.04,
    },
    "sortWeights": {
        "strategyFitScore": 0.34,
        "overallTotal": 0.25,
        "futureRiseScore": 0.14,
        "todayBuyScore": 0.12,
        "profitableExitScore": 0.08,
        "risk": 0.07,
    },
    "focusKeys": ["strategyFocusTodayEntry", "strategyFocusFutureExit", "strategyFocusRiskControl"],
}


STRATEGY_BEHAVIOR_PROFILES = {
    "ai_smart_blend": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "adaptive_blend",
        "horizon": "balancedQuality",
        "entryGates": [
            {"key": "strategyGateTodayBuy", "metric": "todayBuyScore", "min": 56},
            {"key": "strategyGateFutureRise", "metric": "futureRiseScore", "min": 55},
            {"key": "strategyGateProfitableExit", "metric": "profitableExitScore", "min": 52},
            {"key": "strategyGateMidLongQuality", "metric": "midLongTermScore", "min": 52},
            {"key": "strategyGateDownside", "metric": "downsideRiskScore", "max": 66, "cap": 58},
        ],
        "fitWeights": {
            "qualityCompositeScore": 0.30,
            "shortTermScore": 0.22,
            "midLongTermScore": 0.22,
            "todayBuyScore": 0.08,
            "futureRiseScore": 0.08,
            "profitableExitScore": 0.05,
            "fundFlowScore": 0.03,
            "newsHeatImpactScore": 0.02,
        },
        "sortWeights": {
            "qualityCompositeScore": 0.34,
            "strategyFitScore": 0.26,
            "midLongTermScore": 0.16,
            "shortTermScore": 0.14,
            "overallTotal": 0.10,
        },
        "focusKeys": ["strategyFocusShortTerm", "strategyFocusMidLongTerm", "strategyFocusTodayEntry", "strategyFocusFutureExit", "strategyFocusRiskControl"],
    },
    "short_term_adaptive_trade": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "short_term_adaptive_trade",
        "horizon": "shortTerm",
        "buyFloor": 70,
        "watchFloor": 56,
        "entryGates": [
            {"key": "strategyGateShortTerm", "metric": "shortTermScore", "min": 66},
            {"key": "strategyGateTodayBuy", "metric": "todayBuyScore", "min": 60},
            {"key": "strategyGateContinuation", "metric": "nextSessionContinuationScore", "min": 58},
            {"key": "strategyGateProfitableExit", "metric": "profitableExitScore", "min": 56},
            {"key": "strategyGateDownside", "metric": "downsideRiskScore", "max": 66, "cap": 58},
        ],
        "vetoRules": [
            *DEFAULT_STRATEGY_BEHAVIOR["vetoRules"],
            {"key": "strategyVetoShortTermFail", "metric": "shortTermScore", "min": 46, "cap": 46, "direction": "max"},
            {"key": "strategyVetoOverheated", "metric": "pullbackRiskScore", "max": 76, "cap": 48},
        ],
        "fitWeights": {
            "shortTermScore": 0.34,
            "todayBuyScore": 0.16,
            "futureRiseScore": 0.13,
            "profitableExitScore": 0.12,
            "nextSessionContinuationScore": 0.09,
            "breakoutSetupScore": 0.07,
            "fundFlowScore": 0.05,
            "midLongTermScore": 0.04,
        },
        "sortWeights": {
            "strategyFitScore": 0.36,
            "shortTermScore": 0.28,
            "todayBuyScore": 0.12,
            "profitableExitScore": 0.10,
            "nextSessionContinuationScore": 0.08,
            "fundFlowScore": 0.06,
        },
        "focusKeys": ["strategyFocusShortTerm", "strategyFocusTodayEntry", "strategyFocusFutureExit", "strategyFocusNextSession", "strategyFocusNoChase"],
    },
    "mid_long_quality_compounder": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "mid_long_quality_compounder",
        "horizon": "midLongTerm",
        "buyFloor": 68,
        "watchFloor": 54,
        "entryGates": [
            {"key": "strategyGateMidLongQuality", "metric": "midLongTermScore", "min": 64},
            {"key": "strategyGateStableQuality", "metric": "qualityCompositeScore", "min": 62},
            {"key": "strategyGateQuality", "metric": "quality", "min": 56},
            {"key": "strategyGateValue", "metric": "value", "min": 52},
            {"key": "strategyGateRisk", "metric": "risk", "min": 56},
            {"key": "strategyGateDownside", "metric": "downsideRiskScore", "max": 58, "cap": 54},
        ],
        "vetoRules": [
            *DEFAULT_STRATEGY_BEHAVIOR["vetoRules"],
            {"key": "strategyVetoQuality", "metric": "quality", "min": 44, "cap": 42, "direction": "max"},
            {"key": "strategyVetoRisk", "metric": "risk", "min": 44, "cap": 42, "direction": "max"},
            {"key": "strategyVetoMidLongWeak", "metric": "midLongTermScore", "min": 46, "cap": 44, "direction": "max"},
        ],
        "fitWeights": {
            "midLongTermScore": 0.34,
            "qualityCompositeScore": 0.22,
            "quality": 0.14,
            "value": 0.12,
            "risk": 0.10,
            "maStructureScore": 0.04,
            "shortTermScore": 0.04,
        },
        "sortWeights": {
            "qualityCompositeScore": 0.34,
            "midLongTermScore": 0.28,
            "strategyFitScore": 0.18,
            "quality": 0.08,
            "risk": 0.07,
            "value": 0.05,
        },
        "focusKeys": ["strategyFocusMidLongTerm", "strategyFocusStableQuality", "strategyFocusQualityValue", "strategyFocusRiskControl", "strategyFocusFinancialRepair"],
    },
    "today_breakout_volume": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "breakout_volume",
        "buyFloor": 70,
        "watchFloor": 56,
        "entryGates": [
            {"key": "strategyGateBreakout", "metric": "breakoutSetupScore", "min": 68},
            {"key": "strategyGateVolume", "metric": "volumeConfirmationScore", "min": 58},
            {"key": "strategyGateTodayBuy", "metric": "todayBuyScore", "min": 60},
            {"key": "strategyGatePullback", "metric": "pullbackRiskScore", "max": 66, "cap": 60},
            {"key": "strategyGateReversal", "metric": "nextSessionReversalRiskScore", "max": 70, "cap": 58},
        ],
        "vetoRules": [
            *DEFAULT_STRATEGY_BEHAVIOR["vetoRules"],
            {"key": "strategyVetoNoVolume", "metric": "volumeConfirmationScore", "min": 42, "cap": 50, "direction": "max"},
            {"key": "strategyVetoOverheated", "metric": "pullbackRiskScore", "max": 76, "cap": 48},
        ],
        "fitWeights": {
            "breakoutSetupScore": 0.24,
            "volumeConfirmationScore": 0.18,
            "todayBuyScore": 0.18,
            "momentum": 0.12,
            "futureRiseScore": 0.10,
            "nextSessionContinuationScore": 0.08,
            "risk": 0.06,
            "fundFlowScore": 0.04,
        },
        "sortWeights": {
            "strategyFitScore": 0.40,
            "breakoutSetupScore": 0.22,
            "volumeConfirmationScore": 0.12,
            "todayBuyScore": 0.10,
            "nextSessionContinuationScore": 0.08,
            "overallTotal": 0.08,
        },
        "focusKeys": ["strategyFocusBreakoutVolume", "strategyFocusNoChase", "strategyFocusNextSession"],
    },
    "next_session_continuation": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "next_session_continuation",
        "entryGates": [
            {"key": "strategyGateContinuation", "metric": "nextSessionContinuationScore", "min": 62},
            {"key": "strategyGateReversal", "metric": "nextSessionReversalRiskScore", "max": 60, "cap": 58},
            {"key": "strategyGateFutureRise", "metric": "futureRiseScore", "min": 60},
            {"key": "strategyGateMacd", "metric": "macdScore", "min": 54},
        ],
        "vetoRules": [
            *DEFAULT_STRATEGY_BEHAVIOR["vetoRules"],
            {"key": "strategyVetoContinuationBreak", "metric": "nextSessionContinuationScore", "min": 46, "cap": 46, "direction": "max"},
        ],
        "fitWeights": {
            "nextSessionContinuationScore": 0.24,
            "futureRiseScore": 0.20,
            "nextSessionReversalRiskInverse": 0.16,
            "macdScore": 0.12,
            "maStructureScore": 0.10,
            "momentum": 0.08,
            "profitableExitScore": 0.06,
            "fundFlowScore": 0.04,
        },
        "sortWeights": {
            "strategyFitScore": 0.42,
            "nextSessionContinuationScore": 0.22,
            "futureRiseScore": 0.16,
            "nextSessionReversalRiskInverse": 0.12,
            "overallTotal": 0.08,
        },
        "focusKeys": ["strategyFocusNextSession", "strategyFocusReversalRisk", "strategyFocusTrendStructure"],
    },
    "profitable_exit_t_trade": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "profitable_exit_t_trade",
        "entryGates": [
            {"key": "strategyGateTScore", "metric": "tScore", "min": 62},
            {"key": "strategyGateLiquidity", "metric": "liquidityScore", "min": 55},
            {"key": "strategyGateVolatility", "metric": "volatilityScore", "min": 54},
            {"key": "strategyGateProfitableExit", "metric": "profitableExitScore", "min": 58},
            {"key": "strategyGateDownside", "metric": "downsideRiskScore", "max": 62, "cap": 56},
        ],
        "vetoRules": [
            *DEFAULT_STRATEGY_BEHAVIOR["vetoRules"],
            {"key": "strategyVetoLiquidity", "metric": "liquidityScore", "min": 38, "cap": 42, "direction": "max"},
        ],
        "fitWeights": {
            "tScore": 0.24,
            "profitableExitScore": 0.22,
            "liquidityScore": 0.14,
            "volatilityScore": 0.12,
            "pullbackRiskInverse": 0.10,
            "downsideRiskInverse": 0.08,
            "breakoutSetupScore": 0.06,
            "fundFlowScore": 0.04,
        },
        "sortWeights": {
            "strategyFitScore": 0.42,
            "tScore": 0.22,
            "profitableExitScore": 0.16,
            "liquidityScore": 0.10,
            "volatilityScore": 0.10,
        },
        "focusKeys": ["strategyFocusTExit", "strategyFocusLiquidity", "strategyFocusRiskControl"],
    },
    "news_heat_catalyst": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "news_heat_catalyst",
        "entryGates": [
            {"key": "strategyGateNewsHeat", "metric": "newsHeatImpactScore", "min": 60},
            {"key": "strategyGateSentiment", "metric": "sentiment", "min": 54},
            {"key": "strategyGateFundFlow", "metric": "fundFlowScore", "min": 48},
            {"key": "strategyGateFutureRise", "metric": "futureRiseScore", "min": 56},
        ],
        "vetoRules": [
            *DEFAULT_STRATEGY_BEHAVIOR["vetoRules"],
            {"key": "strategyVetoNewsCold", "metric": "newsHeatImpactScore", "min": 38, "cap": 48, "direction": "max"},
        ],
        "fitWeights": {
            "newsHeatImpactScore": 0.26,
            "sentiment": 0.18,
            "fundFlowScore": 0.14,
            "futureRiseScore": 0.14,
            "todayBuyScore": 0.10,
            "nextSessionContinuationScore": 0.08,
            "risk": 0.06,
            "volumeConfirmationScore": 0.04,
        },
        "sortWeights": {
            "strategyFitScore": 0.40,
            "newsHeatImpactScore": 0.22,
            "fundFlowScore": 0.14,
            "sentiment": 0.12,
            "futureRiseScore": 0.12,
        },
        "focusKeys": ["strategyFocusNewsFlow", "strategyFocusFundFlow", "strategyFocusNextSession"],
    },
    "pullback_to_rising_average": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "pullback_to_rising_average",
        "entryGates": [
            {"key": "strategyGateMaStructure", "metric": "maStructureScore", "min": 58},
            {"key": "strategyGateRsi", "metric": "rsiScore", "min": 54},
            {"key": "strategyGatePullback", "metric": "pullbackRiskScore", "max": 62, "cap": 58},
            {"key": "strategyGateTodayBuy", "metric": "todayBuyScore", "min": 56},
        ],
        "vetoRules": [
            *DEFAULT_STRATEGY_BEHAVIOR["vetoRules"],
            {"key": "strategyVetoOverheated", "metric": "pullbackRiskScore", "max": 72, "cap": 48},
        ],
        "fitWeights": {
            "maStructureScore": 0.20,
            "pullbackRiskInverse": 0.18,
            "rsiScore": 0.14,
            "todayBuyScore": 0.14,
            "supportScore": 0.12,
            "futureRiseScore": 0.10,
            "risk": 0.08,
            "value": 0.04,
        },
        "sortWeights": {
            "strategyFitScore": 0.42,
            "maStructureScore": 0.18,
            "pullbackRiskInverse": 0.16,
            "todayBuyScore": 0.12,
            "supportScore": 0.12,
        },
        "focusKeys": ["strategyFocusPullbackSupport", "strategyFocusTrendStructure", "strategyFocusNoChase"],
    },
    "rsi_macd_reversal": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "rsi_macd_reversal",
        "entryGates": [
            {"key": "strategyGateRsi", "metric": "rsiScore", "min": 52},
            {"key": "strategyGateMacd", "metric": "macdScore", "min": 56},
            {"key": "strategyGateReversal", "metric": "nextSessionReversalRiskScore", "max": 64, "cap": 56},
            {"key": "strategyGateFutureRise", "metric": "futureRiseScore", "min": 55},
        ],
        "vetoRules": [
            *DEFAULT_STRATEGY_BEHAVIOR["vetoRules"],
            {"key": "strategyVetoNoReversalConfirm", "metric": "macdScore", "min": 40, "cap": 44, "direction": "max"},
        ],
        "fitWeights": {
            "rsiScore": 0.20,
            "macdScore": 0.20,
            "nextSessionReversalRiskInverse": 0.14,
            "futureRiseScore": 0.14,
            "maStructureScore": 0.10,
            "todayBuyScore": 0.08,
            "risk": 0.08,
            "fundFlowScore": 0.06,
        },
        "sortWeights": {
            "strategyFitScore": 0.42,
            "rsiScore": 0.18,
            "macdScore": 0.18,
            "nextSessionReversalRiskInverse": 0.12,
            "futureRiseScore": 0.10,
        },
        "focusKeys": ["strategyFocusRsiMacd", "strategyFocusReversalRisk", "strategyFocusConfirmBeforeBuy"],
    },
    "defensive_quality_value": {
        **DEFAULT_STRATEGY_BEHAVIOR,
        "mode": "defensive_quality_value",
        "buyFloor": 66,
        "watchFloor": 52,
        "entryGates": [
            {"key": "strategyGateQuality", "metric": "quality", "min": 58},
            {"key": "strategyGateValue", "metric": "value", "min": 56},
            {"key": "strategyGateRisk", "metric": "risk", "min": 58},
            {"key": "strategyGateDownside", "metric": "downsideRiskScore", "max": 54, "cap": 54},
        ],
        "vetoRules": [
            *DEFAULT_STRATEGY_BEHAVIOR["vetoRules"],
            {"key": "strategyVetoQuality", "metric": "quality", "min": 44, "cap": 42, "direction": "max"},
            {"key": "strategyVetoRisk", "metric": "risk", "min": 44, "cap": 42, "direction": "max"},
        ],
        "fitWeights": {
            "quality": 0.24,
            "value": 0.22,
            "risk": 0.20,
            "downsideRiskInverse": 0.12,
            "futureRiseScore": 0.08,
            "profitableExitScore": 0.06,
            "maStructureScore": 0.05,
            "newsHeatImpactScore": 0.03,
        },
        "sortWeights": {
            "strategyFitScore": 0.40,
            "quality": 0.20,
            "value": 0.18,
            "risk": 0.14,
            "downsideRiskInverse": 0.08,
        },
        "focusKeys": ["strategyFocusQualityValue", "strategyFocusRiskControl", "strategyFocusFinancialRepair"],
    },
}


def _strategy_behavior(strategy_id: str) -> dict:
    profile = STRATEGY_BEHAVIOR_PROFILES.get(strategy_id, DEFAULT_STRATEGY_BEHAVIOR)
    return {
        **profile,
        "entryGates": list(profile.get("entryGates") or []),
        "vetoRules": list(profile.get("vetoRules") or []),
        "fitWeights": dict(profile.get("fitWeights") or {}),
        "sortWeights": dict(profile.get("sortWeights") or {}),
        "focusKeys": list(profile.get("focusKeys") or []),
    }


_cached_catalog: dict | None = None


def _source_urls(source: dict) -> list[str]:
    urls = [source.get("url"), *(source.get("urls") or [])]
    return [str(url) for url in urls if url]


def _source_fallback_status(source: dict, status: str, error: str = "") -> dict:
    keywords = list(source.get("fallbackKeywords") or source.get("keywords") or [])
    return {
        **source,
        "available": False,
        "usable": True,
        "fallback": True,
        "status": status,
        "matchedKeywords": keywords[: min(5, len(keywords))],
        "error": error[:160],
    }


def _fetch_source_status(source: dict) -> dict:
    last_error = ""
    for url in _source_urls(source):
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urlopen(request, timeout=7) as response:
                raw = response.read(240_000)
                text = raw.decode("utf-8", errors="ignore").lower()
        except Exception as exc:
            last_error = str(exc)
            continue
        matched = [keyword for keyword in source["keywords"] if re.search(re.escape(keyword.lower()), text)]
        if matched:
            return {
                **source,
                "url": url,
                "available": True,
                "usable": True,
                "fallback": False,
                "status": "live",
                "matchedKeywords": matched,
                "error": "",
            }
        last_error = "Fetched page but no strategy keywords matched."
    return _source_fallback_status(source, "fallback", last_error)


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
        if not (source.get("available") or source.get("usable")):
            continue
        live_factor = 1.0 if source.get("available") else 0.72
        multiplier = live_factor * (1 + min(4, len(source.get("matchedKeywords") or [])) * 0.12)
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
        "fundamental": ["quality", "valuation", "riskControl"],
        "quality": ["quality", "riskControl"],
        "valuation": ["valuation", "quality"],
        "longTerm": ["quality", "valuation", "riskControl", "futureRise"],
        "mediumTerm": ["futureRise", "trendContinuation", "maStructure"],
        "shortTerm": ["todayBuy", "profitableExit", "volumeConfirmation", "fundFlow"],
        "portfolio": ["riskControl", "quality"],
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

    sources = [_fetch_source_status(source) for source in ONLINE_STRATEGY_SOURCES] if refresh else [_source_fallback_status(source, "not_refreshed") for source in ONLINE_STRATEGY_SOURCES]
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
                "behavior": _strategy_behavior(strategy["id"]),
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
