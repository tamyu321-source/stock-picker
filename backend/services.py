from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from math import exp, log10
from statistics import mean

from backend.data import DEFAULT_SYMBOLS, MARKETS, STRATEGIES
from backend.providers import Article, MarketSnapshot, RssNewsCrawler, YFinanceMarketDataProvider, infer_market, local_company_name, volatility_score
from backend.strategy_library import DETAILED_WEIGHT_KEYS, all_runtime_strategies, get_strategy_catalog
from backend.universe import DiscoveredSymbol, MarketUniverseProvider


FACTOR_ORDER = ["sentiment", "momentum", "value", "risk", "quality"]
AUTO_SCAN_DISCOVERY_LIMIT_PER_MARKET = 96
AUTO_SCAN_SINGLE_MARKET_DISCOVERY_LIMIT = 160
AUTO_SCAN_EXPANSION_LIMITS_PER_MARKET = (96, 160, 240)
AUTO_SCAN_TARGET_QUALITY_BUYS = 4
AUTO_SCAN_TARGET_ACTIONABLE_CANDIDATES = 10
AUTO_SCAN_RESULT_LIMIT = 48
AUTO_SCAN_SINGLE_MARKET_RESULT_LIMIT = 120
AUTO_SCAN_BUY_LIMIT = 14
AUTO_SCAN_TRADE_LIMIT = 14
AUTO_SCAN_SELL_LIMIT = 8
AUTO_SCAN_WATCH_LIMIT = 16
SEVERE_PRICE_DROP_PCT = -8.5
LARGE_PRICE_DROP_PCT = -5.0
STRICT_BUY_SCORE_FLOOR = 68
STRICT_BUY_PRIORITY_FLOOR = 68
STRICT_BUY_RISK_FLOOR = 50
STRICT_BUY_QUALITY_FLOOR = 62
STRICT_BUY_SENTIMENT_FLOOR = 52
OPPORTUNITY_BUY_FLOOR = 70
BREAKOUT_SETUP_BUY_FLOOR = 74
BREAKOUT_SETUP_PRIORITY_FLOOR = 72
BREAKOUT_SETUP_DOWNSIDE_CEILING = 56
OVERHEATED_PRICE_JUMP_PCT = 12.0
EXTREME_PRICE_JUMP_PCT = 18.0
PULLBACK_RISK_BLOCK_BUY_FLOOR = 62
DOWNSIDE_EXIT_FLOOR = 62
DOWNSIDE_URGENT_EXIT_FLOOR = 72
T_TRADE_CANDIDATE_FLOOR = 68
T_TRADE_WATCH_FLOOR = 54
NEXT_SESSION_CONTINUATION_BUY_FLOOR = 52
NEXT_SESSION_REVERSAL_BLOCK_BUY_FLOOR = 68


def get_config() -> dict:
    strategy_catalog = get_strategy_catalog(refresh=False)
    return {
        "markets": MARKETS,
        "strategies": all_runtime_strategies(STRATEGIES, refresh=False),
        "strategyLibrary": strategy_catalog,
        "defaultSymbols": DEFAULT_SYMBOLS,
        "scanUniverseSize": {market["id"]: "dynamic" for market in MARKETS},
    }


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(value, 0) for value in weights.values()) or 1
    return {key: max(value, 0) / total for key, value in weights.items()}


def _clamp_score(value: float) -> float:
    return max(0, min(100, value))


def _metric_number(value) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_severe_price_drop(value) -> bool:
    change = _metric_number(value)
    return change is not None and change <= SEVERE_PRICE_DROP_PCT


def _is_large_price_drop(value) -> bool:
    change = _metric_number(value)
    return change is not None and change <= LARGE_PRICE_DROP_PCT


def _is_overheated_price_jump(value) -> bool:
    change = _metric_number(value)
    return change is not None and change >= OVERHEATED_PRICE_JUMP_PCT


def _is_extreme_price_jump(value) -> bool:
    change = _metric_number(value)
    return change is not None and change >= EXTREME_PRICE_JUMP_PCT


def _strategy_from_payload(payload: dict) -> dict:
    custom_weights = payload.get("customWeights")
    if custom_weights:
        custom_detailed = payload.get("customDetailedWeights")
        return {
            "id": "custom",
            "name": "Custom AI Strategy",
            "description": "User-defined scoring weights from the web interface.",
            "weights": custom_weights,
            "detailedWeights": custom_detailed if isinstance(custom_detailed, dict) else None,
            "riskTolerance": 55,
        }

    strategy_id = payload.get("strategyId", "ai_smart_blend")
    strategies = all_runtime_strategies(STRATEGIES, refresh=bool(payload.get("refreshStrategies")))
    return next((strategy for strategy in strategies if strategy["id"] == strategy_id), strategies[0])


def _age_hours(published_at: datetime | None, now: datetime) -> int:
    if published_at is None:
        return 999
    return max(0, round((now - published_at.astimezone(timezone.utc)).total_seconds() / 3600))


def _signals_for(articles: list[Article]) -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "source": article.source,
            "title": article.title,
            "summary": article.summary,
            "link": article.link,
            "sentiment": article.sentiment,
            "credibility": article.credibility,
            "relevance": article.relevance,
            "ageHours": _age_hours(article.published_at, now),
        }
        for article in articles
    ]


def _article_weight(article: Article, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    return article.credibility * article.relevance * max(0.2, 1 - _age_hours(article.published_at, now) / 168)


def _sentiment_score(articles: list[Article]) -> float:
    if not articles:
        return 50
    now = datetime.now(timezone.utc)
    weighted_values = []
    weights = []
    for article in articles:
        weight = _article_weight(article, now)
        weighted_values.append(article.sentiment * weight)
        weights.append(weight)
    lexical_score = sum(weighted_values) / (sum(weights) or 1)
    return _clamp_score(50 + lexical_score * 32 + _news_event_adjustment(articles))


def _news_event_adjustment(articles: list[Article]) -> float:
    profile = _news_sentiment_profile(articles)
    return max(-24, min(24, profile["netScore"] * 0.28))


def _sentiment_boost(articles: list[Article]) -> float:
    if not articles:
        return 0
    return (_sentiment_score(articles) - 50) / 50 * 10


NEWS_EVENT_RULES = [
    ("earningsPositive", "positive", ["earnings beat", "beats expectations", "profit rises", "record revenue", "revenue growth", "showstopping earnings", "record $", "业绩增长", "業績增長", "营收增长", "營收成長", "获利成长", "獲利成長", "利润增长", "盈喜"]),
    ("earningsNegative", "negative", ["misses expectations", "profit warning", "revenue falls", "业绩下滑", "業績下滑", "业绩持续承压", "業績持續承壓", "营收下滑", "營收下滑", "获利衰退", "獲利衰退", "利润下降", "盈警", "亏损", "虧損", "承压", "承壓"]),
    ("guidancePositive", "positive", ["raises guidance", "上调指引", "上修財測", "财测上修", "展望樂觀", "展望乐观", "高端化升级", "高端化升級", "产能升级", "產能升級"]),
    ("guidanceNegative", "negative", ["cuts guidance", "下调指引", "財測下修", "财测下修", "展望保守", "需求放缓", "需求放緩"]),
    ("analystPositive", "positive", ["upgrade", "outperform", "buy rating", "target price raised", "上调评级", "调高至买入", "评级被调高", "评级调高", "買入評級", "目标价上调", "目标价涨幅", "目標價上調", "強推", "强推"]),
    ("analystNegative", "negative", ["downgrade", "underperform", "sell rating", "target price cut", "下调评级", "评级调低", "賣出評級", "目标价下调", "目標價下調"]),
    ("capitalReturn", "positive", ["buyback", "repurchase", "dividend", "回购", "回購", "分红", "派息", "股息"]),
    ("shareholderSale", "negative", ["insider selling", "stake sale", "减持", "減持", "套现", "沽售"]),
    ("legalRegulatoryRisk", "negative", ["lawsuit", "probe", "investigation", "regulatory", "sanction", "诉讼", "調查", "调查", "监管", "罰款", "罚款"]),
    ("demandPositive", "positive", ["strong demand", "long-term demand", "order growth", "contract win", "新订单", "大单", "需求強勁", "需求强劲", "接單", "接单", "产业链提价", "提价"]),
    ("demandNegative", "negative", ["weak demand", "china problem", "not enough", "isn't enough", "wobbly", "inventory correction", "order cut", "库存调整", "庫存調整", "砍单", "訂單下滑", "订单下滑"]),
    ("fundFlowPositive", "positive", ["net inflow", "institutional buying", "资金流入", "主力资金净流入", "净流入资金", "净流入", "資金流入", "機構買入", "机构买入", "抢筹", "搶籌"]),
    ("fundFlowNegative", "negative", ["net outflow", "institutional selling", "资金流出", "主力资金净流出", "净流出", "資金流出", "機構賣出", "机构卖出"]),
    ("marketMomentumPositive", "positive", ["创上市以来新高", "創上市以來新高", "成交额创", "成交額創", "涨停", "漲停", "封板", "放量上涨", "批量涨停"]),
    ("marketMomentumNegative", "negative", ["跌停", "放量下跌", "大幅下跌", "创阶段新低", "創階段新低", "破位"]),
]

NEWS_EVENT_STRENGTH = {
    "earningsPositive": 0.95,
    "earningsNegative": 0.98,
    "guidancePositive": 0.78,
    "guidanceNegative": 0.86,
    "analystPositive": 0.66,
    "analystNegative": 0.72,
    "capitalReturn": 0.55,
    "shareholderSale": 0.82,
    "legalRegulatoryRisk": 0.95,
    "demandPositive": 0.72,
    "demandNegative": 0.78,
    "fundFlowPositive": 0.58,
    "fundFlowNegative": 0.62,
    "marketMomentumPositive": 0.50,
    "marketMomentumNegative": 0.58,
    "generalPositiveNews": 0.45,
    "generalNegativeNews": 0.45,
}


def _news_events_for(article: Article) -> list[dict]:
    text = f"{article.title} {article.summary}".lower()
    article_weight = _article_weight(article)
    events = []
    for key, impact, needles in NEWS_EVENT_RULES:
        matched = [needle for needle in needles if needle.lower() in text]
        if matched:
            strength = NEWS_EVENT_STRENGTH.get(key, 0.5)
            polarity = 1 if impact == "positive" else -1 if impact == "negative" else 0
            events.append(
                {
                    "key": key,
                    "impact": impact,
                    "title": article.title,
                    "source": article.source,
                    "ageHours": _age_hours(article.published_at, datetime.now(timezone.utc)),
                    "weight": round(article_weight * strength, 3),
                    "strength": round(strength, 2),
                    "score": round(polarity * strength * 100, 1),
                    "evidence": matched[0],
                }
            )
    if not events and abs(article.sentiment) >= 0.45:
        key = "generalPositiveNews" if article.sentiment > 0 else "generalNegativeNews"
        impact = "positive" if article.sentiment > 0 else "negative"
        strength = NEWS_EVENT_STRENGTH[key]
        polarity = 1 if article.sentiment > 0 else -1
        events.append(
            {
                "key": key,
                "impact": impact,
                "title": article.title,
                "source": article.source,
                "ageHours": _age_hours(article.published_at, datetime.now(timezone.utc)),
                "weight": round(article_weight * strength, 3),
                "strength": round(strength, 2),
                "score": round(polarity * strength * 100, 1),
                "evidence": "sentiment",
            }
        )
    return events


def _news_sentiment_profile(articles: list[Article]) -> dict:
    events = [event for article in articles for event in _news_events_for(article)]
    positive_raw = sum(event["weight"] * abs(event["score"]) for event in events if event["impact"] == "positive")
    negative_raw = sum(event["weight"] * abs(event["score"]) for event in events if event["impact"] == "negative")
    positive_score = round(min(100, 100 * (1 - exp(-positive_raw / 85))), 1)
    negative_score = round(min(100, 100 * (1 - exp(-negative_raw / 85))), 1)
    return {
        "events": events,
        "positiveScore": positive_score,
        "negativeScore": negative_score,
        "netScore": round(positive_score - negative_score, 1),
    }


def _news_analysis(articles: list[Article]) -> dict:
    profile = _news_sentiment_profile(articles)
    events = profile["events"]
    positive_count = sum(1 for event in events if event["impact"] == "positive")
    negative_count = sum(1 for event in events if event["impact"] == "negative")
    if not articles:
        summary_key = "newsNoEvidence"
    elif profile["netScore"] >= 12:
        summary_key = "newsBullishSummary"
    elif profile["netScore"] <= -12:
        summary_key = "newsBearishSummary"
    else:
        summary_key = "newsMixedSummary"
    return {
        "summary": {
            "key": summary_key,
            "params": {
                "positive": positive_count,
                "negative": negative_count,
                "total": len(articles),
                "positiveScore": profile["positiveScore"],
                "negativeScore": profile["negativeScore"],
                "netScore": profile["netScore"],
            },
        },
        "positiveCount": positive_count,
        "negativeCount": negative_count,
        "positiveScore": profile["positiveScore"],
        "negativeScore": profile["negativeScore"],
        "netScore": profile["netScore"],
        "events": sorted(events, key=lambda event: (abs(event["score"]) * event["weight"], -event["ageHours"]), reverse=True)[:8],
    }


def _freshness_score(articles: list[Article]) -> float:
    if not articles:
        return 0.0
    now = datetime.now(timezone.utc)
    scores = []
    for article in articles:
        age = _age_hours(article.published_at, now)
        scores.append(_clamp_score(100 - age * 2.4) * article.credibility * article.relevance)
    return round(_clamp_score(mean(scores)), 1)


def _news_heat_analysis(articles: list[Article], news_analysis: dict) -> dict:
    events = news_analysis.get("events") or []
    total = len(articles)
    source_count = len({article.source for article in articles if article.source})
    freshness = _freshness_score(articles)
    count_score = _clamp_score(100 * (1 - exp(-total / 3))) if total else 0.0
    source_score = _clamp_score(source_count * 24)
    event_raw = sum(abs(float(event.get("score") or 0)) * float(event.get("weight") or 0) for event in events)
    event_intensity = _clamp_score(100 * (1 - exp(-event_raw / 115))) if event_raw else 0.0
    heat_score = round(
        _clamp_score(
            count_score * 0.28
            + freshness * 0.25
            + source_score * 0.18
            + event_intensity * 0.29
        ),
        1,
    )
    net_score = float(news_analysis.get("netScore") or 0)
    if total == 0:
        impact_score = 45.0
        summary_key = "newsHeatColdSummary"
    elif net_score >= 12 and heat_score >= 52:
        impact_score = _clamp_score(50 + heat_score * 0.24 + net_score * 0.32)
        summary_key = "newsHeatHotPositiveSummary"
    elif net_score <= -12 and heat_score >= 52:
        impact_score = _clamp_score(50 - heat_score * 0.24 + net_score * 0.32)
        summary_key = "newsHeatHotNegativeSummary"
    elif heat_score >= 52:
        impact_score = _clamp_score(50 + net_score * 0.22 - abs(net_score) * 0.04)
        summary_key = "newsHeatHotMixedSummary"
    else:
        impact_score = _clamp_score(47 + net_score * 0.18)
        summary_key = "newsHeatColdSummary"

    params = {
        "heat": round(heat_score, 1),
        "impact": round(impact_score, 1),
        "netScore": round(net_score, 1),
        "count": total,
        "sources": source_count,
    }
    positives = []
    negatives = []
    watch_items = []
    if impact_score >= 62:
        positives.append({"key": "newsHeatSupport", "params": params})
    elif impact_score <= 42:
        negatives.append({"key": "newsHeatRisk", "params": params})
    else:
        watch_items.append({"key": "newsHeatWatch", "params": params})
    if freshness >= 70:
        positives.append({"key": "newsHeatFresh", "params": {"score": freshness}})
    elif total and freshness <= 35:
        watch_items.append({"key": "newsHeatStale", "params": {"score": freshness}})

    return {
        "summary": {"key": summary_key, "params": params},
        "heatScore": heat_score,
        "impactScore": round(impact_score, 1),
        "freshnessScore": freshness,
        "sourceCount": source_count,
        "eventIntensityScore": round(event_intensity, 1),
        "metrics": [
            {"key": "newsHeat", "value": f"{heat_score:.1f}/100", "score": heat_score},
            {"key": "newsHeatImpact", "value": f"{impact_score:.1f}/100", "score": round(impact_score, 1)},
            {"key": "newsFreshness", "value": f"{freshness:.1f}/100", "score": freshness},
            {"key": "newsSourceBreadth", "value": str(source_count), "score": round(source_score, 1)},
            {"key": "newsEventIntensity", "value": f"{event_intensity:.1f}/100", "score": round(event_intensity, 1)},
        ],
        "positives": positives[:4],
        "negatives": negatives[:4],
        "watchItems": watch_items[:4],
    }


def _effective_weights(weights: dict[str, float], availability: dict[str, bool] | None = None) -> dict[str, float]:
    if not availability:
        return weights
    active_weight = sum(weights.get(factor, 0) for factor in FACTOR_ORDER if availability.get(factor))
    if active_weight <= 0:
        return weights
    return {
        factor: (weights.get(factor, 0) / active_weight if availability.get(factor) else 0)
        for factor in FACTOR_ORDER
    }


def _score_stock(metrics: dict[str, float], weights: dict[str, float], availability: dict[str, bool] | None = None) -> float:
    effective_weights = _effective_weights(weights, availability)
    weighted_score = sum(metrics[key] * effective_weights.get(key, 0) for key in metrics)
    return max(0, min(100, weighted_score))


def _score_breakdown(metrics: dict[str, float], weights: dict[str, float], availability: dict[str, bool] | None = None) -> list[dict]:
    effective_weights = _effective_weights(weights, availability)
    return [
        {
            "factor": factor,
            "score": round(metrics[factor], 1),
            "weight": round(effective_weights.get(factor, 0) * 100, 1),
            "baseWeight": round(weights.get(factor, 0) * 100, 1),
            "available": bool(availability.get(factor, True)) if availability is not None else True,
            "contribution": round(metrics[factor] * effective_weights.get(factor, 0), 1),
        }
        for factor in FACTOR_ORDER
    ]


def _verdict(
    score: float,
    risk_metric: float,
    quality_metric: float | None = None,
    sentiment_metric: float | None = None,
    price_change: float | None = None,
) -> str:
    if _is_severe_price_drop(price_change):
        return "sell"
    if score < 52 or (risk_metric < 35 and score < 58):
        return "sell"
    if _is_large_price_drop(price_change):
        return "watch"
    if (
        score >= 72
        and risk_metric >= STRICT_BUY_RISK_FLOOR
        and (quality_metric is None or quality_metric >= 58)
        and (sentiment_metric is None or sentiment_metric >= STRICT_BUY_SENTIMENT_FLOOR)
    ):
        return "buy"
    return "watch"


def _relative_verdicts(picks: list[dict]) -> None:
    if not picks:
        return
    for pick in picks:
        pick["reasonCodes"] = [reason for reason in pick["reasonCodes"] if reason["key"] != "rankedTopOpportunity"]
        if _is_buy_candidate(pick):
            pick["verdict"] = "buy"
            pick["reasonCodes"] = [reason for reason in pick["reasonCodes"] if reason["key"] not in {"notHighConviction", "clearsBuyThreshold"}]
        elif _is_exit_candidate(pick):
            pick["verdict"] = "sell"
        else:
            pick["verdict"] = "watch"
        pick["decision"] = _decision_details(pick["verdict"], pick["score"], pick["metrics"], pick["signals"], pick["newsAnalysis"], pick.get("change"), pick.get("breakoutSetupScore"), pick.get("pullbackRiskScore"), pick.get("fundFlow"))
        pick["actionPlan"] = _action_plan(pick["verdict"], pick["score"], pick["metrics"], pick["newsAnalysis"], pick["financialAnalysis"], pick.get("change"), pick.get("pullbackRiskScore"))

    for index, pick in enumerate(sorted([item for item in picks if item["verdict"] == "buy"], key=_investment_priority, reverse=True), start=1):
        pick["reasonCodes"].append({"key": "rankedTopOpportunity", "params": {"rank": index}})


def _investment_priority(pick: dict) -> float:
    metrics = pick["metrics"]
    setup_score = float(pick.get("breakoutSetupScore") or 0)
    overall = pick.get("overallAssessment") or {}
    if overall:
        return round(
            float(overall.get("totalScore") or 0) * 0.58
            + float(pick.get("opportunityScore") or 0) * 0.24
            + setup_score * 0.10
            + float((pick.get("trendAnalysis") or {}).get("continuationScore") or 0) * 0.08,
            3,
        )
    if "opportunityScore" in pick:
        return round(float(pick["opportunityScore"]) * 0.82 + setup_score * 0.18, 3)
    return round(
        pick["score"] * 0.44
        + metrics["quality"] * 0.16
        + metrics["momentum"] * 0.14
        + setup_score * 0.14
        + metrics["value"] * 0.10
        + metrics["risk"] * 0.06
        + metrics["sentiment"] * 0.06,
        3,
    )


def _sell_priority(pick: dict) -> float:
    metrics = pick["metrics"]
    if "downsideRiskScore" in pick:
        return float(pick["downsideRiskScore"])
    price_penalty = 14 if _is_severe_price_drop(pick.get("change")) else 7 if _is_large_price_drop(pick.get("change")) else 0
    return round(
        (100 - pick["score"]) * 0.45
        + (100 - metrics["risk"]) * 0.25
        + (100 - metrics["sentiment"]) * 0.15
        + (100 - metrics["momentum"]) * 0.10
        + (100 - metrics["quality"]) * 0.05
        + price_penalty,
        3,
    )


def _is_exit_candidate(pick: dict) -> bool:
    metrics = pick["metrics"]
    return (
        _is_severe_price_drop(pick.get("change"))
        or float(pick.get("downsideRiskScore") or 0) >= DOWNSIDE_EXIT_FLOOR
        or pick["score"] < 52
        or (metrics["risk"] < 35 and pick["score"] < 58)
    )


def _is_urgent_exit_candidate(pick: dict) -> bool:
    metrics = pick["metrics"]
    return (
        _is_severe_price_drop(pick.get("change"))
        or float(pick.get("downsideRiskScore") or 0) >= DOWNSIDE_URGENT_EXIT_FLOOR
        or pick["score"] <= 48
        or metrics["sentiment"] <= 35
        or metrics["momentum"] <= 35
        or (metrics["risk"] < 35 and pick["score"] < 58)
        or (metrics["quality"] <= 35 and pick["score"] < 58)
    )


def _investable_factor_count(metrics: dict[str, float]) -> int:
    return sum(
        [
            metrics["quality"] >= 58,
            metrics["risk"] >= 48,
            metrics["sentiment"] >= 54,
            metrics["momentum"] >= 56,
            metrics["value"] >= 50,
        ]
    )


def _news_strengths(news: dict) -> tuple[float, float, float]:
    positive_news = float(news.get("positiveScore") or 0)
    negative_news = float(news.get("negativeScore") or 0)
    net_news = float(news.get("netScore", positive_news - negative_news) or 0)
    return positive_news, negative_news, net_news


def _price_action_bonus(change) -> float:
    value = _metric_number(change)
    if value is None:
        return 0
    if value <= SEVERE_PRICE_DROP_PCT:
        return -30
    if value <= LARGE_PRICE_DROP_PCT:
        return -18
    if value < 0:
        return max(-8, value * 1.2)
    if value >= EXTREME_PRICE_JUMP_PCT:
        return -20
    if value >= OVERHEATED_PRICE_JUMP_PCT:
        return -10
    return min(6, value * 0.8)


def _price_action_risk(change) -> float:
    value = _metric_number(change)
    if value is None:
        return 0
    if value <= SEVERE_PRICE_DROP_PCT:
        return 45
    if value <= LARGE_PRICE_DROP_PCT:
        return 25
    if value < 0:
        return min(12, abs(value) * 1.8)
    if value >= EXTREME_PRICE_JUMP_PCT:
        return 34
    if value >= OVERHEATED_PRICE_JUMP_PCT:
        return 22
    return max(-8, -value * 0.8)


def _recent_abs_return_percent(closes: list[float], window: int = 20) -> float:
    values = closes[-(window + 1) :] if len(closes) > window else closes
    if len(values) < 2:
        return 0.0
    returns = []
    for previous, current in zip(values, values[1:]):
        if previous:
            returns.append(abs(current / previous - 1) * 100)
    return mean(returns) if returns else 0.0


def _t_trade_volatility_percent(snapshot: MarketSnapshot) -> float:
    change = abs(_metric_number(snapshot.change) or 0)
    recent_move = _recent_abs_return_percent(snapshot.closes, 20) * 1.55
    five_day_move = abs(_price_return(snapshot.closes, 5) * 100) / 2.5 if len(snapshot.closes) > 6 else 0.0
    return round(max(recent_move, change * 0.62, five_day_move), 2)


def _t_trade_volatility_score(volatility_percent: float) -> float:
    if volatility_percent <= 0:
        return 20.0
    if volatility_percent < 2.0:
        return _clamp_score(18 + volatility_percent * 18)
    if volatility_percent < 3.2:
        return _clamp_score(54 + (volatility_percent - 2.0) * 22)
    if volatility_percent <= 8.5:
        return _clamp_score(82 + min(12, (volatility_percent - 3.2) * 2.2))
    if volatility_percent <= 12:
        return _clamp_score(88 - (volatility_percent - 8.5) * 7)
    return _clamp_score(58 - (volatility_percent - 12) * 9)


def _latest_turnover_percent(info: dict) -> float | None:
    value = _metric_number(info.get("latestTurnoverRate"))
    if value is None:
        value = _metric_number(info.get("turnoverRate"))
    if value is None:
        return None
    return value * 100 if value <= 1 else value


def _turnover_trade_score(turnover_percent: float | None) -> float:
    if turnover_percent is None:
        return 48.0
    if turnover_percent < 0.6:
        return _clamp_score(22 + turnover_percent * 24)
    if turnover_percent < 2.0:
        return _clamp_score(42 + (turnover_percent - 0.6) * 14)
    if turnover_percent <= 12.0:
        return _clamp_score(72 + min(18, (turnover_percent - 2.0) * 1.8))
    if turnover_percent <= 22.0:
        return _clamp_score(86 - (turnover_percent - 12.0) * 2.2)
    return _clamp_score(64 - (turnover_percent - 22.0) * 3.4)


def _pullback_risk_score(snapshot: MarketSnapshot, news: dict) -> float:
    closes = snapshot.closes
    change = _metric_number(snapshot.change)
    volume_surge = max(
        _metric_number(snapshot.info.get("volumeSurge20")) or 0,
        _metric_number(snapshot.info.get("amountSurge20")) or 0,
    )
    turnover_percent = _latest_turnover_percent(snapshot.info)
    positive_news, negative_news, net_news = _news_strengths(news)
    fund_flow = _fund_flow_profile(snapshot.info)

    risk = 6.0
    if change is not None:
        if change >= EXTREME_PRICE_JUMP_PCT:
            risk += 42
        elif change >= OVERHEATED_PRICE_JUMP_PCT:
            risk += 30
        elif change >= 8:
            risk += 16
        elif change >= 5:
            risk += 8
        elif change <= LARGE_PRICE_DROP_PCT:
            risk += 18

    if len(closes) >= 22:
        current = closes[-1]
        ma20 = _moving_average(closes, 20)
        return_5 = _price_return(closes, 5) * 100
        return_20 = _price_return(closes, 20) * 100
        if return_5 >= 28:
            risk += 22
        elif return_5 >= 18:
            risk += 14
        elif return_5 >= 12:
            risk += 8
        if return_20 >= 60:
            risk += 16
        elif return_20 >= 40:
            risk += 10
        if ma20 and ma20 > 0:
            distance = (current / ma20 - 1) * 100
            if distance >= 28:
                risk += 18
            elif distance >= 18:
                risk += 12
            elif distance >= 12:
                risk += 6
        range_position = _range_position(snapshot)
        if range_position is not None and range_position >= 96:
            risk += 8

    if volume_surge >= 4:
        risk += 10
    elif volume_surge >= 2.5:
        risk += 6
    if turnover_percent is not None:
        if turnover_percent >= 25:
            risk += 10
        elif turnover_percent >= 16:
            risk += 6

    if negative_news > positive_news + 8 or net_news <= -8:
        risk += 14
    elif positive_news >= 24 and net_news >= 12:
        risk -= 6
    if fund_flow.get("available"):
        risk += float(fund_flow.get("negativeScore") or 0) * 0.20
        risk -= float(fund_flow.get("positiveScore") or 0) * 0.12

    return round(_clamp_score(risk), 1)


def _breakout_setup_score(snapshot: MarketSnapshot, news: dict) -> float:
    closes = snapshot.closes
    if len(closes) < 22:
        return 0.0

    current = closes[-1]
    prior_window = closes[-21:-1]
    prior_high = max(prior_window) if prior_window else current
    return_5 = _price_return(closes, 5) * 100
    return_20 = _price_return(closes, 20) * 100
    change = _metric_number(snapshot.change)
    volume_surge = max(
        _metric_number(snapshot.info.get("volumeSurge20")) or 0,
        _metric_number(snapshot.info.get("amountSurge20")) or 0,
    )
    turnover_percent = _latest_turnover_percent(snapshot.info)
    positive_news, negative_news, net_news = _news_strengths(news)
    fund_flow = _fund_flow_profile(snapshot.info)

    setup = 12.0
    has_fresh_impulse = volume_surge >= 1.25 or (change is not None and change >= 2.0) or return_5 >= 3.0
    if has_fresh_impulse and prior_high > 0:
        breakout_ratio = current / prior_high
        if breakout_ratio >= 1.0:
            setup += 22
        elif breakout_ratio >= 0.97:
            setup += 12

    if change is not None:
        if 2.0 <= change <= 8.0:
            setup += 18
        elif 8.0 < change < OVERHEATED_PRICE_JUMP_PCT:
            setup += 6
        elif 0.5 <= change < 2.0:
            setup += 6
        elif change >= EXTREME_PRICE_JUMP_PCT:
            setup -= min(46, 24 + (change - EXTREME_PRICE_JUMP_PCT) * 5)
        elif change >= OVERHEATED_PRICE_JUMP_PCT:
            setup -= min(28, 12 + (change - OVERHEATED_PRICE_JUMP_PCT) * 4)
        elif change < 0:
            setup += max(-18, change * 2)

    if 3.0 <= return_5 <= 22.0:
        setup += 14
    elif return_5 > 28.0:
        setup -= 16
    elif return_5 > 22.0:
        setup -= 8
    elif return_5 <= -4.0:
        setup -= 10

    if 5.0 <= return_20 <= 38.0:
        setup += 10
    elif return_20 > 55.0:
        setup -= 14

    if volume_surge >= 2.0:
        setup += 18
    elif volume_surge >= 1.35:
        setup += 10

    if turnover_percent is not None:
        if 2.0 <= turnover_percent <= 18.0:
            setup += 8
        elif turnover_percent < 0.6:
            setup -= 4
        elif turnover_percent > 28.0:
            setup -= 4

    if positive_news >= 18 and net_news >= 8:
        setup += 10
    elif negative_news > positive_news + 8:
        setup -= 16
    if fund_flow.get("available"):
        setup += float(fund_flow.get("positiveScore") or 0) * 0.16
        setup -= float(fund_flow.get("negativeScore") or 0) * 0.14

    recent_drawdown = _max_drawdown(closes, 20)
    if recent_drawdown <= 0.08:
        setup += 6
    elif recent_drawdown >= 0.18:
        setup -= 10

    return round(_clamp_score(setup), 1)


def _prediction_scores(
    metrics: dict[str, float],
    score: float,
    news: dict,
    price_change,
    breakout_setup_score: float = 0.0,
    pullback_risk_score: float = 0.0,
    fund_flow: dict | None = None,
    trend_profile: dict | None = None,
) -> tuple[float, float]:
    positive_news, negative_news, net_news = _news_strengths(news)
    positive_flow = float((fund_flow or {}).get("positiveScore") or 0)
    negative_flow = float((fund_flow or {}).get("negativeScore") or 0)
    continuation_score = float((trend_profile or {}).get("continuationScore") or 50)
    reversal_risk_score = float((trend_profile or {}).get("reversalRiskScore") or 50)
    opportunity = _clamp_score(
        score * 0.28
        + metrics["quality"] * 0.20
        + metrics["momentum"] * 0.16
        + metrics["risk"] * 0.14
        + metrics["value"] * 0.10
        + metrics["sentiment"] * 0.08
        + positive_news * 0.08
        + max(0, net_news) * 0.06
        + positive_flow * 0.12
        + breakout_setup_score * 0.18
        + continuation_score * 0.10
        + _price_action_bonus(price_change)
        - negative_news * 0.10
        - negative_flow * 0.08
        - pullback_risk_score * 0.16
        - reversal_risk_score * 0.10
    )
    downside = _clamp_score(
        (100 - score) * 0.22
        + (100 - metrics["risk"]) * 0.24
        + (100 - metrics["momentum"]) * 0.16
        + (100 - metrics["sentiment"]) * 0.12
        + (100 - metrics["quality"]) * 0.10
        + negative_news * 0.16
        + max(0, -net_news) * 0.08
        + negative_flow * 0.14
        + _price_action_risk(price_change)
        + pullback_risk_score * 0.28
        + reversal_risk_score * 0.16
        - positive_news * 0.06
        - positive_flow * 0.06
        - continuation_score * 0.05
        - breakout_setup_score * 0.04
    )
    return round(opportunity, 1), round(downside, 1)


def _round_trade_price(value: float) -> float:
    if value >= 1000:
        return round(value, 1)
    if value >= 100:
        return round(value, 2)
    if value >= 10:
        return round(value, 2)
    return round(value, 3)


def _t_trade_score(
    snapshot: MarketSnapshot,
    metrics: dict[str, float],
    news: dict,
    breakout_setup_score: float,
    pullback_risk_score: float,
    downside_risk_score: float,
) -> tuple[float, dict[str, float | None]]:
    liquidity = _liquidity_score(snapshot.info)
    liquidity_score = float(liquidity if liquidity is not None else 42)
    volatility_percent = _t_trade_volatility_percent(snapshot)
    volatility_score = _t_trade_volatility_score(volatility_percent)
    turnover_percent = _latest_turnover_percent(snapshot.info)
    turnover_score = _turnover_trade_score(turnover_percent)
    positive_news, negative_news, net_news = _news_strengths(news)
    change = _metric_number(snapshot.change)
    fund_flow = _fund_flow_profile(snapshot.info)
    positive_flow = float(fund_flow.get("positiveScore") or 0)
    negative_flow = float(fund_flow.get("negativeScore") or 0)

    score = (
        liquidity_score * 0.22
        + volatility_score * 0.24
        + breakout_setup_score * 0.20
        + metrics["momentum"] * 0.12
        + metrics["sentiment"] * 0.08
        + metrics["risk"] * 0.08
        + turnover_score * 0.06
        + max(0, net_news) * 0.06
        + positive_news * 0.04
        + positive_flow * 0.08
        - negative_news * 0.08
        - negative_flow * 0.10
        - pullback_risk_score * 0.22
        - downside_risk_score * 0.14
    )

    if liquidity_score < 42:
        score = min(score, 48)
    if volatility_score < 45:
        score = min(score, 52)
    if downside_risk_score >= DOWNSIDE_URGENT_EXIT_FLOOR or _is_severe_price_drop(change):
        score = min(score, 32)
    elif downside_risk_score >= DOWNSIDE_EXIT_FLOOR or _is_large_price_drop(change):
        score = min(score, 48)
    if _is_extreme_price_jump(change):
        score = min(score, 38)
    elif _is_overheated_price_jump(change) or pullback_risk_score >= 72:
        score = min(score, 48)
    elif pullback_risk_score >= PULLBACK_RISK_BLOCK_BUY_FLOOR:
        score = min(score, 58)

    return round(_clamp_score(score), 1), {
        "liquidityScore": round(liquidity_score, 1),
        "volatilityScore": round(volatility_score, 1),
        "volatilityPct": volatility_percent,
        "turnoverScore": round(turnover_score, 1),
        "turnoverPct": round(turnover_percent, 2) if turnover_percent is not None else None,
    }


def _t_trade_suitability(
    t_score: float,
    components: dict[str, float | None],
    pullback_risk_score: float,
    downside_risk_score: float,
    price_change: float | None,
) -> str:
    if (
        t_score >= T_TRADE_CANDIDATE_FLOOR
        and float(components.get("liquidityScore") or 0) >= 55
        and float(components.get("volatilityScore") or 0) >= 58
        and pullback_risk_score < PULLBACK_RISK_BLOCK_BUY_FLOOR
        and downside_risk_score < DOWNSIDE_EXIT_FLOOR
        and not _is_large_price_drop(price_change)
        and not _is_overheated_price_jump(price_change)
    ):
        return "candidate"
    if t_score >= T_TRADE_WATCH_FLOOR and not _is_severe_price_drop(price_change):
        return "watch"
    return "avoid"


def _zone(low: float, high: float) -> dict[str, float]:
    return {
        "low": _round_trade_price(min(low, high)),
        "high": _round_trade_price(max(low, high)),
    }


def _t_trade_plan(
    snapshot: MarketSnapshot,
    metrics: dict[str, float],
    t_score: float,
    components: dict[str, float | None],
    breakout_setup_score: float,
    pullback_risk_score: float,
    downside_risk_score: float,
) -> dict:
    change = _metric_number(snapshot.change)
    suitability = _t_trade_suitability(t_score, components, pullback_risk_score, downside_risk_score, change)
    volatility_pct = float(components.get("volatilityPct") or 2.5)
    entry_deep = min(0.045, max(0.012, volatility_pct * 0.0042))
    entry_shallow = min(0.020, max(0.004, volatility_pct * 0.0018))
    take_low = min(0.045, max(0.012, volatility_pct * 0.0032))
    take_high = min(0.085, max(0.026, volatility_pct * 0.0072))
    stop_gap = min(0.075, max(0.024, volatility_pct * 0.0065))
    price = snapshot.price

    reasons = []
    risk_controls = []
    if float(components.get("liquidityScore") or 0) >= 60:
        reasons.append({"key": "tLiquidityReady", "params": {"score": components["liquidityScore"]}})
    else:
        risk_controls.append({"key": "tLiquidityThin", "params": {"score": components["liquidityScore"]}})
    if float(components.get("volatilityScore") or 0) >= 58:
        reasons.append({"key": "tVolatilityReady", "params": {"score": components["volatilityScore"], "range": components["volatilityPct"]}})
    else:
        risk_controls.append({"key": "tVolatilityLow", "params": {"range": components["volatilityPct"]}})
    if breakout_setup_score >= 62:
        reasons.append({"key": "tSetupReady", "params": {"score": round(breakout_setup_score, 1)}})
    elif metrics["momentum"] < 52:
        risk_controls.append({"key": "tTrendWeak", "params": {"score": metrics["momentum"]}})

    if pullback_risk_score >= PULLBACK_RISK_BLOCK_BUY_FLOOR:
        risk_controls.append({"key": "tPullbackRiskHigh", "params": {"risk": round(pullback_risk_score, 1)}})
    if _is_overheated_price_jump(change):
        risk_controls.append({"key": "tNoChase", "params": {"change": round(change or 0, 1)}})
    if downside_risk_score >= DOWNSIDE_EXIT_FLOOR:
        risk_controls.append({"key": "tDownsideRiskHigh", "params": {"risk": round(downside_risk_score, 1)}})
    risk_controls.append({"key": "tUseBasePositionOnly", "params": {}})
    risk_controls.append({"key": "tCutIfBreaksSupport", "params": {}})

    summary_key = {
        "candidate": "tCandidateSummary",
        "watch": "tWatchSummary",
        "avoid": "tAvoidSummary",
    }[suitability]
    return {
        "suitability": suitability,
        "summary": {"key": summary_key, "params": {"score": t_score}},
        "score": t_score,
        "components": components,
        "entryZone": _zone(price * (1 - entry_deep), price * (1 - entry_shallow)),
        "takeProfitZone": _zone(price * (1 + take_low), price * (1 + take_high)),
        "stopLoss": _round_trade_price(price * (1 - stop_gap)),
        "reasons": reasons[:4],
        "riskControls": risk_controls[:5],
    }


def _is_quality_investment_candidate(pick: dict) -> bool:
    metrics = pick["metrics"]
    news = pick.get("newsAnalysis") or {}
    positive_news, negative_news, _ = _news_strengths(news)
    downside_score = pick.get("downsideRiskScore")
    pullback_risk = float(pick.get("pullbackRiskScore") or 0)
    trend = pick.get("trendAnalysis") or {}
    continuation = float(trend.get("continuationScore") or 50)
    reversal = float(trend.get("reversalRiskScore") or 50)
    overall = pick.get("overallAssessment") or {}
    components = overall.get("components") or {}
    overall_total = float(overall.get("totalScore") or pick["score"])
    today_buy = float(components.get("todayBuyScore") or pick["score"])
    future_rise = float(components.get("futureRiseScore") or pick.get("opportunityScore") or 0)
    profitable_exit = float(components.get("profitableExitScore") or pick.get("tScore") or 55)
    return (
        float(pick.get("opportunityScore") or 0) >= OPPORTUNITY_BUY_FLOOR
        and float(downside_score if downside_score is not None else 100) <= 45
        and pullback_risk < PULLBACK_RISK_BLOCK_BUY_FLOOR
        and continuation >= NEXT_SESSION_CONTINUATION_BUY_FLOOR
        and reversal < NEXT_SESSION_REVERSAL_BLOCK_BUY_FLOOR
        and overall_total >= 68
        and today_buy >= 60
        and future_rise >= 58
        and profitable_exit >= 54
        and pick["score"] >= STRICT_BUY_SCORE_FLOOR
        and _investment_priority(pick) >= STRICT_BUY_PRIORITY_FLOOR
        and metrics["quality"] >= STRICT_BUY_QUALITY_FLOOR
        and metrics["risk"] >= STRICT_BUY_RISK_FLOOR
        and metrics["sentiment"] >= STRICT_BUY_SENTIMENT_FLOOR
        and _investable_factor_count(metrics) >= 4
        and (metrics["sentiment"] >= 58 or metrics["momentum"] >= 62)
        and not _is_large_price_drop(pick.get("change"))
        and not _is_overheated_price_jump(pick.get("change"))
        and negative_news <= positive_news + 8
    )


def _is_breakout_setup_candidate(pick: dict) -> bool:
    metrics = pick["metrics"]
    news = pick.get("newsAnalysis") or {}
    positive_news, negative_news, _ = _news_strengths(news)
    downside_score = pick.get("downsideRiskScore")
    setup_score = float(pick.get("breakoutSetupScore") or 0)
    pullback_risk = float(pick.get("pullbackRiskScore") or 0)
    trend = pick.get("trendAnalysis") or {}
    continuation = float(trend.get("continuationScore") or 50)
    reversal = float(trend.get("reversalRiskScore") or 50)
    overall = pick.get("overallAssessment") or {}
    components = overall.get("components") or {}
    overall_total = float(overall.get("totalScore") or pick["score"])
    today_buy = float(components.get("todayBuyScore") or pick["score"])
    future_rise = float(components.get("futureRiseScore") or pick.get("opportunityScore") or 0)
    profitable_exit = float(components.get("profitableExitScore") or pick.get("tScore") or 55)
    return (
        setup_score >= BREAKOUT_SETUP_BUY_FLOOR
        and float(pick.get("opportunityScore") or 0) >= OPPORTUNITY_BUY_FLOOR
        and float(downside_score if downside_score is not None else 100) <= BREAKOUT_SETUP_DOWNSIDE_CEILING
        and pullback_risk < PULLBACK_RISK_BLOCK_BUY_FLOOR
        and continuation >= max(NEXT_SESSION_CONTINUATION_BUY_FLOOR, 56)
        and reversal < NEXT_SESSION_REVERSAL_BLOCK_BUY_FLOOR
        and overall_total >= 66
        and today_buy >= 58
        and future_rise >= 58
        and profitable_exit >= 52
        and _investment_priority(pick) >= BREAKOUT_SETUP_PRIORITY_FLOOR
        and metrics["momentum"] >= 60
        and metrics["risk"] >= 38
        and metrics["quality"] >= 42
        and metrics["sentiment"] >= 48
        and negative_news <= positive_news + 12
        and (positive_news >= 12 or setup_score >= 84)
        and not _is_large_price_drop(pick.get("change"))
        and not _is_overheated_price_jump(pick.get("change"))
    )


def _is_buy_candidate(pick: dict) -> bool:
    return _is_quality_investment_candidate(pick) or _is_breakout_setup_candidate(pick)


def _is_t_trade_candidate(pick: dict) -> bool:
    return (pick.get("tPlan") or {}).get("suitability") == "candidate"


def _is_watch_candidate(pick: dict) -> bool:
    metrics = pick["metrics"]
    return (
        not _is_exit_candidate(pick)
        and (
            pick["score"] >= 55
            or float(pick.get("tScore") or 0) >= T_TRADE_WATCH_FLOOR
            or _investment_priority(pick) >= 58
            or _investable_factor_count(metrics) >= 3
        )
    )


def _apply_auto_scan_search_algorithm(picks: list[dict]) -> None:
    for pick in picks:
        pick["reasonCodes"] = [reason for reason in pick["reasonCodes"] if reason["key"] != "rankedTopOpportunity"]
        if _is_buy_candidate(pick):
            pick["verdict"] = "buy"
            pick["reasonCodes"] = [
                reason
                for reason in pick["reasonCodes"]
                if reason["key"] not in {"notHighConviction", "clearsBuyThreshold"}
            ]
        elif _is_urgent_exit_candidate(pick):
            pick["verdict"] = "sell"
        else:
            pick["verdict"] = "watch"
        pick["decision"] = _decision_details(pick["verdict"], pick["score"], pick["metrics"], pick["signals"], pick["newsAnalysis"], pick.get("change"), pick.get("breakoutSetupScore"), pick.get("pullbackRiskScore"), pick.get("fundFlow"))
        pick["actionPlan"] = _action_plan(pick["verdict"], pick["score"], pick["metrics"], pick["newsAnalysis"], pick["financialAnalysis"], pick.get("change"), pick.get("pullbackRiskScore"))

    for index, pick in enumerate(sorted([item for item in picks if item["verdict"] == "buy"], key=_investment_priority, reverse=True), start=1):
        pick["reasonCodes"].append({"key": "rankedTopOpportunity", "params": {"rank": index}})


def _display_priority_key(pick: dict) -> tuple[int, float]:
    if pick["verdict"] == "buy":
        return (0, -_investment_priority(pick))
    if _is_t_trade_candidate(pick):
        return (1, -float(pick.get("tScore") or 0))
    if pick["verdict"] == "sell":
        return (2, -_sell_priority(pick))
    return (3, -max(_investment_priority(pick), float(pick.get("tScore") or 0)))


def _average(values: list[float]) -> float:
    return round(mean(values), 1) if values else 0.0


def _sector_name(pick: dict) -> str:
    sector = str(pick.get("sector") or "").strip()
    return sector if sector and sector.lower() != "unknown" else "Unclassified"


def _sector_id(name: str) -> str:
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in name)
    return "-".join(part for part in cleaned.split("-") if part) or "unclassified"


def _sector_recommendation(
    score: float,
    metrics: dict[str, float],
    verdict_counts: dict[str, int],
    count: int,
    t_candidate_count: int = 0,
    average_t_score: float = 0.0,
    average_downside_score: float = 0.0,
) -> str:
    sell_ratio = verdict_counts.get("sell", 0) / count if count else 0
    buy_ratio = verdict_counts.get("buy", 0) / count if count else 0
    t_ratio = t_candidate_count / count if count else 0
    if sell_ratio >= 0.42 or average_downside_score >= 68 or score < 52 or metrics["risk"] < 35:
        return "underweight"
    if (
        score >= 62
        and metrics["risk"] >= 45
        and metrics["sentiment"] >= 48
        and average_downside_score < 60
        and (buy_ratio > 0 or t_ratio >= 0.18 or average_t_score >= 62)
    ):
        return "overweight"
    if buy_ratio >= 0.35 and metrics["quality"] >= 58 and metrics["momentum"] >= 55:
        return "overweight"
    return "neutral"


def _sector_priority(sector: dict) -> float:
    metrics = sector["metrics"]
    sell_count = sector["verdictCounts"].get("sell", 0)
    sell_ratio = sell_count / sector["count"] if sector["count"] else 0
    t_ratio = sector.get("tCandidateCount", 0) / sector["count"] if sector["count"] else 0
    return round(
        sector["score"] * 0.44
        + metrics["quality"] * 0.16
        + metrics["momentum"] * 0.14
        + metrics["risk"] * 0.12
        + metrics["sentiment"] * 0.10
        + float(sector.get("averageTScore") or 0) * 0.08
        + t_ratio * 8
        - sell_ratio * 18,
        3,
    )


def _apply_relative_sector_recommendations(sectors: list[dict]) -> None:
    if not sectors or any(sector["recommendation"] == "overweight" for sector in sectors):
        return
    candidates = [
        sector
        for sector in sectors
        if (sector["verdictCounts"].get("buy", 0) > 0 or sector.get("tCandidateCount", 0) > 0)
        and sector["score"] >= 62
        and sector["metrics"]["risk"] >= 45
        and float(sector.get("averageDownsideRiskScore") or 0) < 64
        and sector["verdictCounts"].get("sell", 0) < sector["count"]
    ]
    if candidates:
        sorted(candidates, key=_sector_priority, reverse=True)[0]["recommendation"] = "overweight"


def _constituent_summary(pick: dict) -> dict:
    return {
        "symbol": pick["symbol"],
        "name": pick["name"],
        "market": pick["market"],
        "score": pick["score"],
        "verdict": pick["verdict"],
        "tScore": pick.get("tScore"),
        "tSuitability": (pick.get("tPlan") or {}).get("suitability"),
    }


def _sector_score(sector_picks: list[dict], metrics: dict[str, float]) -> float:
    base_score = _average([float(pick["score"]) for pick in sector_picks])
    opportunity_score = _average([float(pick.get("opportunityScore") or 0) for pick in sector_picks])
    t_score = _average([float(pick.get("tScore") or 0) for pick in sector_picks])
    downside_score = _average([float(pick.get("downsideRiskScore") or 0) for pick in sector_picks])
    pullback_score = _average([float(pick.get("pullbackRiskScore") or 0) for pick in sector_picks])
    buy_ratio = sum(1 for pick in sector_picks if pick["verdict"] == "buy") / len(sector_picks)
    t_ratio = sum(1 for pick in sector_picks if _is_t_trade_candidate(pick)) / len(sector_picks)
    return round(
        _clamp_score(
            base_score * 0.48
            + opportunity_score * 0.18
            + t_score * 0.14
            + metrics["risk"] * 0.06
            + metrics["sentiment"] * 0.06
            + buy_ratio * 7
            + t_ratio * 6
            - downside_score * 0.10
            - pullback_score * 0.07
        ),
        1,
    )


def _sector_leader_priority(pick: dict) -> float:
    return round(
        max(_investment_priority(pick), float(pick.get("tScore") or 0))
        + float(pick.get("opportunityScore") or 0) * 0.08
        - float(pick.get("downsideRiskScore") or 0) * 0.04,
        3,
    )


def _sector_laggard_priority(pick: dict) -> float:
    return round(
        _sell_priority(pick)
        + float(pick.get("pullbackRiskScore") or 0) * 0.18
        + (12 if _is_overheated_price_jump(pick.get("change")) else 0),
        3,
    )


def _sector_analysis(picks: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for pick in picks:
        grouped.setdefault(_sector_name(pick), []).append(pick)

    sectors = []
    for name, sector_picks in grouped.items():
        metrics = {
            factor: _average([float(pick["metrics"].get(factor, 0)) for pick in sector_picks])
            for factor in FACTOR_ORDER
        }
        score = _sector_score(sector_picks, metrics)
        verdict_counts = {
            "buy": sum(1 for pick in sector_picks if pick["verdict"] == "buy"),
            "watch": sum(1 for pick in sector_picks if pick["verdict"] == "watch"),
            "sell": sum(1 for pick in sector_picks if pick["verdict"] == "sell"),
        }
        t_candidate_count = sum(1 for pick in sector_picks if _is_t_trade_candidate(pick))
        average_t_score = _average([float(pick.get("tScore") or 0) for pick in sector_picks])
        average_downside_score = _average([float(pick.get("downsideRiskScore") or 0) for pick in sector_picks])
        average_opportunity_score = _average([float(pick.get("opportunityScore") or 0) for pick in sector_picks])
        market_counts: dict[str, int] = {}
        for pick in sector_picks:
            market_counts[pick["market"]] = market_counts.get(pick["market"], 0) + 1
        leaders = sorted(sector_picks, key=_sector_leader_priority, reverse=True)[:3]
        leader_symbols = {pick["symbol"] for pick in leaders}
        laggards = [
            pick
            for pick in sorted(sector_picks, key=_sector_laggard_priority, reverse=True)
            if pick["symbol"] not in leader_symbols
        ][:3]
        count = len(sector_picks)
        confidence = round(
            min(
                96,
                35
                + min(count, 30) * 1.4
                + abs(score - 50) * 0.38
                + metrics["quality"] * 0.08
                + max(0, average_t_score - 50) * 0.12
                - max(0, average_downside_score - 55) * 0.10,
            )
        )
        sectors.append(
            {
                "id": _sector_id(name),
                "name": name,
                "score": score,
                "recommendation": _sector_recommendation(score, metrics, verdict_counts, count, t_candidate_count, average_t_score, average_downside_score),
                "confidence": confidence,
                "count": count,
                "marketMix": [
                    {"market": market, "count": market_counts[market]}
                    for market in sorted(market_counts)
                ],
                "verdictCounts": verdict_counts,
                "tCandidateCount": t_candidate_count,
                "averageTScore": average_t_score,
                "averageOpportunityScore": average_opportunity_score,
                "averageDownsideRiskScore": average_downside_score,
                "metrics": metrics,
                "leaders": [_constituent_summary(pick) for pick in leaders],
                "laggards": [_constituent_summary(pick) for pick in laggards],
            }
        )

    _apply_relative_sector_recommendations(sectors)
    recommendation_priority = {"overweight": 0, "neutral": 1, "underweight": 2}
    return sorted(
        sectors,
        key=lambda sector: (
            recommendation_priority.get(sector["recommendation"], 3),
            -sector["score"],
            -sector["count"],
            sector["name"],
        ),
    )


def _curated_auto_scan_picks(picks: list[dict]) -> list[dict]:
    return _curated_auto_scan_picks_for_limit(picks, AUTO_SCAN_RESULT_LIMIT)


def _curated_auto_scan_picks_for_limit(picks: list[dict], result_limit: int) -> list[dict]:
    if len(picks) <= 2:
        return sorted(
            [pick for pick in picks if _is_buy_candidate(pick) or _is_urgent_exit_candidate(pick) or _is_watch_candidate(pick)],
            key=_display_priority_key,
        )

    buy_candidates = sorted(
        [pick for pick in picks if _is_buy_candidate(pick)],
        key=_investment_priority,
        reverse=True,
    )
    t_trade_candidates = sorted(
        [
            pick
            for pick in picks
            if _is_t_trade_candidate(pick)
            and not _is_buy_candidate(pick)
            and not _is_urgent_exit_candidate(pick)
        ],
        key=lambda item: float(item.get("tScore") or 0),
        reverse=True,
    )
    urgent_sell_candidates = sorted(
        [pick for pick in picks if _is_urgent_exit_candidate(pick)],
        key=_sell_priority,
        reverse=True,
    )
    watch_candidates = sorted(
        [pick for pick in picks if _is_watch_candidate(pick) and not _is_buy_candidate(pick)],
        key=_investment_priority,
        reverse=True,
    )
    fallback_watch_candidates = sorted(
        [
            pick
            for pick in picks
            if pick not in buy_candidates
            and pick not in urgent_sell_candidates
            and pick not in watch_candidates
            and not _is_exit_candidate(pick)
        ],
        key=_investment_priority,
        reverse=True,
    )

    selected: list[dict] = []
    scale = max(1.0, result_limit / AUTO_SCAN_RESULT_LIMIT)
    buy_limit = max(AUTO_SCAN_BUY_LIMIT, round(AUTO_SCAN_BUY_LIMIT * scale))
    trade_limit = max(AUTO_SCAN_TRADE_LIMIT, round(AUTO_SCAN_TRADE_LIMIT * scale))
    sell_limit = max(AUTO_SCAN_SELL_LIMIT, round(AUTO_SCAN_SELL_LIMIT * scale))

    selected.extend(buy_candidates[:buy_limit])
    remaining = result_limit - len(selected)
    if remaining > 0:
        selected.extend(t_trade_candidates[: min(trade_limit, remaining)])
    remaining = result_limit - len(selected)
    if remaining > 0:
        selected.extend(urgent_sell_candidates[: min(sell_limit, remaining)])
    remaining = result_limit - len(selected)
    if remaining > 0:
        selected.extend(watch_candidates[:remaining])
    remaining = result_limit - len(selected)
    if remaining > 0:
        selected.extend(fallback_watch_candidates[:remaining])
    remaining = result_limit - len(selected)
    if remaining > 0:
        selected_symbols = {pick["symbol"] for pick in selected}
        selected.extend(
            [
                pick
                for pick in sorted(picks, key=_display_priority_key)
                if pick["symbol"] not in selected_symbols
            ][:remaining]
        )

    seen = set()
    unique_selected = []
    for pick in selected:
        if pick["symbol"] not in seen:
            unique_selected.append(pick)
            seen.add(pick["symbol"])
    return sorted(unique_selected, key=_display_priority_key)[:result_limit]


def _reason_codes(
    metrics: dict[str, float],
    score: float,
    sentiment_delta: float,
    price_change: float | None = None,
    breakout_setup_score: float = 0.0,
    pullback_risk_score: float = 0.0,
    trend_profile: dict | None = None,
) -> list[dict]:
    strongest = sorted(metrics.items(), key=lambda item: item[1], reverse=True)[:2]
    weakest = min(metrics.items(), key=lambda item: item[1])
    reasons: list[dict] = [
        {"key": "strongestFactors", "params": {"first": strongest[0][0], "second": strongest[1][0]}},
        {"key": "sentimentImpact", "params": {"delta": round(sentiment_delta, 1)}},
    ]
    change = _metric_number(price_change)
    if _is_severe_price_drop(change):
        reasons.append({"key": "severePriceDrop", "params": {"change": round(change, 1)}})
    elif _is_large_price_drop(change):
        reasons.append({"key": "weakPriceAction", "params": {"change": round(change, 1)}})
    elif _is_extreme_price_jump(change):
        reasons.append({"key": "overheatedPriceAction", "params": {"change": round(change, 1), "risk": round(pullback_risk_score, 1)}})
    elif pullback_risk_score >= PULLBACK_RISK_BLOCK_BUY_FLOOR:
        reasons.append({"key": "pullbackRisk", "params": {"risk": round(pullback_risk_score, 1)}})
    if breakout_setup_score >= BREAKOUT_SETUP_BUY_FLOOR:
        reasons.append({"key": "breakoutSetup", "params": {"score": round(breakout_setup_score, 1)}})
    if trend_profile:
        continuation = float(trend_profile.get("continuationScore") or 0)
        reversal = float(trend_profile.get("reversalRiskScore") or 0)
        if reversal >= NEXT_SESSION_REVERSAL_BLOCK_BUY_FLOOR or continuation < NEXT_SESSION_CONTINUATION_BUY_FLOOR:
            reasons.append({"key": "nextSessionRisk", "params": {"continuation": round(continuation, 1), "risk": round(reversal, 1)}})
        elif continuation >= 64 and reversal < 60:
            reasons.append({"key": "nextSessionSupport", "params": {"continuation": round(continuation, 1), "risk": round(reversal, 1)}})
    if weakest[1] < 50:
        reasons.append({"key": "belowThreshold", "params": {"factor": weakest[0]}})
    elif score >= 72:
        reasons.append({"key": "clearsBuyThreshold", "params": {}})
    else:
        reasons.append({"key": "notHighConviction", "params": {}})
    return reasons


def _decision_details(
    verdict: str,
    score: float,
    metrics: dict[str, float],
    signals: list[dict],
    news_analysis: dict,
    price_change: float | None = None,
    breakout_setup_score: float | None = None,
    pullback_risk_score: float | None = None,
    fund_flow: dict | None = None,
) -> dict:
    positives = []
    negatives = []
    watch_items = []
    signal_count = len(signals)
    latest_signal = min((signal["ageHours"] for signal in signals), default=None)
    positive_news = float(news_analysis.get("positiveScore") or 0)
    negative_news = float(news_analysis.get("negativeScore") or 0)
    net_news = float(news_analysis.get("netScore") or positive_news - negative_news)
    news_params = {
        "score": metrics["sentiment"],
        "count": signal_count,
        "positiveScore": round(positive_news, 1),
        "negativeScore": round(negative_news, 1),
        "netScore": round(net_news, 1),
    }
    change = _metric_number(price_change)

    if _is_severe_price_drop(change):
        negatives.append({"key": "priceActionSevereDrop", "params": {"change": round(change, 1)}})
    elif _is_large_price_drop(change):
        watch_items.append({"key": "priceActionWeak", "params": {"change": round(change, 1)}})
    elif _is_extreme_price_jump(change):
        negatives.append({"key": "overheatedPriceAction", "params": {"change": round(change, 1)}})

    if pullback_risk_score is not None:
        if pullback_risk_score >= 72:
            negatives.append({"key": "pullbackRisk", "params": {"risk": round(pullback_risk_score, 1)}})
        elif pullback_risk_score >= PULLBACK_RISK_BLOCK_BUY_FLOOR:
            watch_items.append({"key": "pullbackRisk", "params": {"risk": round(pullback_risk_score, 1)}})

    if positive_news >= 18 and net_news >= 8:
        positives.append({"key": "newsSupport", "params": news_params})
    elif negative_news >= 18 and net_news <= -8:
        negatives.append({"key": "newsPressure", "params": news_params})
    else:
        watch_items.append({"key": "watchNewsFlow", "params": news_params})

    if fund_flow and fund_flow.get("available"):
        positive_flow = float(fund_flow.get("positiveScore") or 0)
        negative_flow = float(fund_flow.get("negativeScore") or 0)
        flow_params = _fund_flow_decision_params(fund_flow)
        if positive_flow >= 18:
            positives.append({"key": "fundFlowSupport", "params": flow_params})
        elif negative_flow >= 18:
            negatives.append({"key": "fundFlowPressure", "params": flow_params})
        else:
            watch_items.append({"key": "fundFlowWatch", "params": flow_params})

    if signal_count == 0:
        negatives.append({"key": "insufficientNews", "params": {}})
    elif latest_signal is not None and latest_signal <= 24:
        watch_items.append({"key": "freshNews", "params": {"hours": latest_signal}})

    if metrics["momentum"] >= 60:
        positives.append({"key": "momentumSupport", "params": {"score": metrics["momentum"]}})
    elif metrics["momentum"] <= 45:
        negatives.append({"key": "weakMomentum", "params": {"score": metrics["momentum"]}})
    else:
        watch_items.append({"key": "watchBreakout", "params": {"score": metrics["momentum"]}})

    if breakout_setup_score is not None and breakout_setup_score >= BREAKOUT_SETUP_BUY_FLOOR:
        positives.append({"key": "breakoutSetup", "params": {"score": round(breakout_setup_score, 1)}})

    if metrics["value"] >= 60:
        positives.append({"key": "valuationSupport", "params": {"score": metrics["value"]}})
    elif metrics["value"] <= 45:
        negatives.append({"key": "expensiveValuation", "params": {"score": metrics["value"]}})
    else:
        watch_items.append({"key": "watchValuation", "params": {"score": metrics["value"]}})

    if metrics["risk"] >= 62:
        positives.append({"key": "riskControlled", "params": {"score": metrics["risk"]}})
    elif metrics["risk"] <= 42:
        negatives.append({"key": "riskHigh", "params": {"score": metrics["risk"]}})
    else:
        watch_items.append({"key": "watchRisk", "params": {"score": metrics["risk"]}})

    if metrics["quality"] >= 62:
        positives.append({"key": "qualitySupport", "params": {"score": metrics["quality"]}})
    elif metrics["quality"] <= 45:
        negatives.append({"key": "weakQuality", "params": {"score": metrics["quality"]}})

    summary_key = {"buy": "buySummary", "sell": "sellSummary"}.get(verdict, "watchSummary")
    return {
        "summary": {"key": summary_key, "params": {"score": score}},
        "positives": positives[:4],
        "negatives": negatives[:4],
        "watchItems": watch_items[:4],
    }


def _english_reasons(reason_codes: list[dict]) -> list[str]:
    labels = {
        "momentum": "Momentum",
        "value": "Value",
        "sentiment": "Sentiment",
        "risk": "Risk",
        "quality": "Quality",
    }
    output = []
    for reason in reason_codes:
        params = reason["params"]
        if reason["key"] == "strongestFactors":
            output.append(f"{labels[params['first']]} and {labels[params['second']]} are the strongest factors.")
        elif reason["key"] == "sentimentImpact":
            output.append(f"Live crawled sentiment changes the score by {params['delta']:+.1f} points.")
        elif reason["key"] == "belowThreshold":
            output.append(f"{labels[params['factor']]} is below threshold and should be monitored before adding exposure.")
        elif reason["key"] == "severePriceDrop":
            output.append(f"Price action is disqualified for new buying after a {params['change']:.1f}% drop.")
        elif reason["key"] == "weakPriceAction":
            output.append(f"Price action is weak after a {params['change']:.1f}% drop; wait for stabilization.")
        elif reason["key"] == "overheatedPriceAction":
            output.append(f"Price is already up {params['change']:.1f}%, so pullback risk is {params['risk']}/100 and new buying is blocked.")
        elif reason["key"] == "pullbackRisk":
            output.append(f"Pullback risk is elevated at {params['risk']}/100; wait for follow-through or a controlled reset.")
        elif reason["key"] == "breakoutSetup":
            output.append(f"Early breakout setup scores {params['score']}/100 from recent price and volume confirmation.")
        elif reason["key"] == "nextSessionSupport":
            output.append(f"Next-session trend continuation is {params['continuation']}/100 while reversal risk is {params['risk']}/100.")
        elif reason["key"] == "nextSessionRisk":
            output.append(f"Current edge may not carry into the next session: continuation is {params['continuation']}/100 and reversal risk is {params['risk']}/100.")
        elif reason["key"] == "clearsBuyThreshold":
            output.append("Composite score clears the buy threshold under the selected strategy.")
        elif reason["key"] == "notHighConviction":
            output.append("Composite score is not strong enough for a high-conviction entry.")
        elif reason["key"] == "rankedTopOpportunity":
            output.append(f"Ranked #{params['rank']} among buy candidates in this scan.")
    return output


def _dedupe_discovered_symbols(symbols: list[DiscoveredSymbol]) -> list[DiscoveredSymbol]:
    seen = set()
    deduped = []
    for item in symbols:
        if item.symbol not in seen:
            deduped.append(item)
            seen.add(item.symbol)
    return deduped


def _is_cn_only_auto_scan(requested_markets: list[str] | set[str], auto_scan: bool) -> bool:
    return auto_scan and set(requested_markets) == {"CN"}


def _initial_discovery_limit(requested_markets: list[str] | set[str], auto_scan: bool) -> int:
    if _is_cn_only_auto_scan(requested_markets, auto_scan):
        return AUTO_SCAN_SINGLE_MARKET_DISCOVERY_LIMIT
    return AUTO_SCAN_DISCOVERY_LIMIT_PER_MARKET


def _auto_scan_display_limit(requested_markets: list[str] | set[str], auto_scan: bool) -> int:
    if _is_cn_only_auto_scan(requested_markets, auto_scan):
        return AUTO_SCAN_SINGLE_MARKET_RESULT_LIMIT
    return AUTO_SCAN_RESULT_LIMIT


def _symbols_from_payload(
    payload: dict,
    universe_provider=None,
    limit_per_market: int = AUTO_SCAN_DISCOVERY_LIMIT_PER_MARKET,
) -> tuple[list[DiscoveredSymbol], list[dict], str]:
    manual_inputs = [str(symbol).strip() for symbol in payload.get("symbols", []) if str(symbol).strip()]
    if manual_inputs:
        provider = universe_provider or MarketUniverseProvider()
        markets = payload.get("markets") or [market["id"] for market in MARKETS]
        source = "portfolio-import" if payload.get("portfolio") or payload.get("portfolioPositions") else "manual"
        manual_limit = max(25, len(manual_inputs)) if source == "portfolio-import" else 25
        if hasattr(provider, "resolve_manual_inputs"):
            resolved, discovery_errors = provider.resolve_manual_inputs(manual_inputs, markets, limit=manual_limit)
            return resolved, discovery_errors, source
        symbols = [symbol.upper() for symbol in manual_inputs]
        return [DiscoveredSymbol(symbol=symbol, name=symbol, market=infer_market(symbol), source=source) for symbol in symbols[:manual_limit]], [], source
    markets = payload.get("markets") or [market["id"] for market in MARKETS]
    provider = universe_provider or MarketUniverseProvider()
    discovered, discovery_errors = provider.discover(markets, limit_per_market=limit_per_market)
    deduped = _dedupe_discovered_symbols(discovered)
    return deduped[: limit_per_market * max(1, len(markets))], discovery_errors, "market-news"


def _price_return(closes: list[float], lookback: int) -> float:
    if len(closes) <= lookback:
        return 0.0
    base = closes[-lookback - 1]
    return closes[-1] / base - 1 if base else 0.0


def _moving_average(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return mean(closes[-window:])


def _price_distance_percent(price: float, reference: float | None) -> float | None:
    if reference is None or reference <= 0:
        return None
    return (price / reference - 1) * 100


def _ema_series(values: list[float], window: int) -> list[float]:
    if not values:
        return []
    multiplier = 2 / (window + 1)
    output = [values[0]]
    for value in values[1:]:
        output.append(value * multiplier + output[-1] * (1 - multiplier))
    return output


def _rsi_value(closes: list[float], window: int = 14) -> float | None:
    if len(closes) <= window:
        return None
    changes = [current - previous for previous, current in zip(closes[-window - 1 : -1], closes[-window:])]
    gains = [max(change, 0) for change in changes]
    losses = [abs(min(change, 0)) for change in changes]
    average_gain = mean(gains) if gains else 0
    average_loss = mean(losses) if losses else 0
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return round(100 - 100 / (1 + relative_strength), 1)


def _macd_profile(closes: list[float]) -> dict:
    if len(closes) < 35:
        return {"available": False}
    ema_12 = _ema_series(closes, 12)
    ema_26 = _ema_series(closes, 26)
    macd_line = [fast - slow for fast, slow in zip(ema_12, ema_26)]
    signal_line = _ema_series(macd_line, 9)
    histogram = [macd - signal for macd, signal in zip(macd_line, signal_line)]
    if len(histogram) < 2:
        return {"available": False}
    price = closes[-1] or 1
    histogram_pct = histogram[-1] / price * 100
    slope_pct = (histogram[-1] - histogram[-2]) / price * 100
    score = _clamp_score(50 + histogram_pct * 10 + slope_pct * 24)
    return {
        "available": True,
        "histogramPct": round(histogram_pct, 3),
        "slopePct": round(slope_pct, 3),
        "score": round(score, 1),
    }


def _trend_metric_value(value: float | None, suffix: str = "") -> str:
    return "N/A" if value is None else f"{value:.1f}{suffix}"


def _trend_profile(snapshot: MarketSnapshot, news: dict, fund_flow: dict | None = None) -> dict:
    closes = snapshot.closes
    if len(closes) < 22:
        return {
            "regime": "insufficient",
            "continuationScore": 48.0,
            "reversalRiskScore": 54.0,
            "maStructureScore": 50.0,
            "momentumShapeScore": 50.0,
            "rsiScore": 50.0,
            "macdScore": 50.0,
            "volumeConfirmationScore": 48.0,
            "supportDistancePct": None,
            "resistanceDistancePct": None,
            "rsi14": None,
            "macdHistogramPct": None,
            "macdSlopePct": None,
            "return1dPct": None,
            "return5dPct": None,
            "return20dPct": None,
            "return60dPct": None,
        }

    price = closes[-1]
    change = _metric_number(snapshot.change)
    returns = {
        "return1dPct": _price_return(closes, 1) * 100,
        "return5dPct": _price_return(closes, 5) * 100,
        "return20dPct": _price_return(closes, 20) * 100,
        "return60dPct": _price_return(closes, 60) * 100,
        "return120dPct": _price_return(closes, 120) * 100,
    }
    ma20 = _moving_average(closes, 20)
    ma60 = _moving_average(closes, 60)
    ma120 = _moving_average(closes, 120)
    ma_structure_score = 50.0
    if ma20 is not None:
        ma_structure_score += 14 if price > ma20 else -16
    if ma20 is not None and ma60 is not None:
        ma_structure_score += 14 if ma20 > ma60 else -12
    if ma60 is not None and ma120 is not None:
        ma_structure_score += 10 if ma60 > ma120 else -8
    ma_structure_score = _clamp_score(ma_structure_score)

    momentum_shape_score = _clamp_score(
        50
        + returns["return5dPct"] * 1.5
        + returns["return20dPct"] * 0.85
        + returns["return60dPct"] * 0.30
        - min(20, _max_drawdown(closes, 30) * 80)
    )

    rsi14 = _rsi_value(closes, 14)
    if rsi14 is None:
        rsi_score = 50.0
    elif 45 <= rsi14 <= 68:
        rsi_score = _clamp_score(78 - abs(rsi14 - 56) * 0.8)
    elif 68 < rsi14 <= 76:
        rsi_score = _clamp_score(70 - (rsi14 - 68) * 2.8)
    elif rsi14 > 76:
        rsi_score = _clamp_score(48 - (rsi14 - 76) * 2.5)
    elif 35 <= rsi14 < 45:
        rsi_score = _clamp_score(56 - (45 - rsi14) * 1.8)
    else:
        rsi_score = _clamp_score(34 - (35 - rsi14) * 1.5)

    macd = _macd_profile(closes)
    macd_score = float(macd.get("score") or 50.0)

    volume_surge = max(
        _metric_number(snapshot.info.get("volumeSurge20")) or 0,
        _metric_number(snapshot.info.get("amountSurge20")) or 0,
    )
    if volume_surge >= 1.35 and (change or 0) >= 0:
        volume_confirmation_score = _clamp_score(62 + min(24, (volume_surge - 1.35) * 10) + min(10, (change or 0) * 1.2))
    elif volume_surge >= 1.35 and (change or 0) < 0:
        volume_confirmation_score = _clamp_score(42 - min(18, abs(change or 0) * 2.2))
    elif (change or 0) >= 4:
        volume_confirmation_score = 43.0
    else:
        volume_confirmation_score = 50.0

    prior_window = closes[-21:-1]
    recent_window = closes[-20:]
    resistance = max(prior_window) if prior_window else None
    recent_low = min(recent_window) if recent_window else None
    support_candidates = [value for value in [recent_low, ma20 if ma20 and ma20 < price else None] if value is not None]
    support = max(support_candidates) if support_candidates else None
    support_distance_pct = _price_distance_percent(price, support)
    resistance_distance_pct = (resistance / price - 1) * 100 if resistance and price else None

    positive_news, negative_news, net_news = _news_strengths(news)
    positive_flow = float((fund_flow or {}).get("positiveScore") or 0)
    negative_flow = float((fund_flow or {}).get("negativeScore") or 0)
    continuation = _clamp_score(
        ma_structure_score * 0.24
        + momentum_shape_score * 0.22
        + volume_confirmation_score * 0.17
        + macd_score * 0.14
        + rsi_score * 0.12
        + min(100, max(0, 50 + net_news)) * 0.06
        + min(100, max(0, 50 + positive_flow - negative_flow)) * 0.05
    )

    extension_risk = 0.0
    if change is not None:
        if change >= EXTREME_PRICE_JUMP_PCT:
            extension_risk += 34
        elif change >= OVERHEATED_PRICE_JUMP_PCT:
            extension_risk += 24
        elif change >= 7:
            extension_risk += 13
    if returns["return5dPct"] >= 20:
        extension_risk += 16
    elif returns["return5dPct"] >= 13:
        extension_risk += 9
    if ma20:
        distance_to_ma20 = _price_distance_percent(price, ma20)
        if distance_to_ma20 is not None:
            if distance_to_ma20 >= 24:
                extension_risk += 18
            elif distance_to_ma20 >= 14:
                extension_risk += 10
    if rsi14 is not None and rsi14 >= 76:
        extension_risk += min(24, (rsi14 - 76) * 2.5 + 8)
    if resistance_distance_pct is not None and -0.2 <= resistance_distance_pct <= 2.0:
        extension_risk += 8
    if volume_confirmation_score < 45:
        extension_risk += 8

    reversal_risk = _clamp_score(
        (100 - ma_structure_score) * 0.17
        + (100 - momentum_shape_score) * 0.18
        + (100 - macd_score) * 0.12
        + (100 - rsi_score) * 0.10
        + (100 - volume_confirmation_score) * 0.12
        + negative_news * 0.12
        + negative_flow * 0.10
        + extension_risk
        - positive_news * 0.04
        - positive_flow * 0.03
    )

    if reversal_risk >= 72:
        regime = "overheated" if (change or 0) >= 7 or (rsi14 or 0) >= 76 else "bearish"
    elif continuation >= 66 and reversal_risk < 58:
        regime = "bullish"
    elif continuation >= 56 and reversal_risk < 64:
        regime = "constructive"
    elif continuation < 46 or reversal_risk >= 66:
        regime = "fragile"
    else:
        regime = "neutral"

    return {
        "regime": regime,
        "continuationScore": round(continuation, 1),
        "reversalRiskScore": round(reversal_risk, 1),
        "maStructureScore": round(ma_structure_score, 1),
        "momentumShapeScore": round(momentum_shape_score, 1),
        "rsiScore": round(rsi_score, 1),
        "macdScore": round(macd_score, 1),
        "volumeConfirmationScore": round(volume_confirmation_score, 1),
        "supportDistancePct": round(support_distance_pct, 1) if support_distance_pct is not None else None,
        "resistanceDistancePct": round(resistance_distance_pct, 1) if resistance_distance_pct is not None else None,
        "rsi14": rsi14,
        "macdHistogramPct": macd.get("histogramPct"),
        "macdSlopePct": macd.get("slopePct"),
        "volumeSurge": round(volume_surge, 2) if volume_surge else None,
        **{key: round(value, 1) for key, value in returns.items()},
    }


def _trend_decision_params(profile: dict) -> dict:
    return {
        "continuation": round(float(profile.get("continuationScore") or 0), 1),
        "risk": round(float(profile.get("reversalRiskScore") or 0), 1),
    }


def _trend_analysis(snapshot: MarketSnapshot, news: dict, fund_flow: dict | None = None) -> dict:
    profile = _trend_profile(snapshot, news, fund_flow)
    continuation = float(profile.get("continuationScore") or 0)
    reversal = float(profile.get("reversalRiskScore") or 0)
    regime = str(profile.get("regime") or "neutral")
    summary_key = {
        "bullish": "trendBullishSummary",
        "constructive": "trendConstructiveSummary",
        "overheated": "trendRiskSummary",
        "bearish": "trendRiskSummary",
        "fragile": "trendRiskSummary",
        "insufficient": "trendNeutralSummary",
    }.get(regime, "trendNeutralSummary")

    metrics = [
        {"key": "trendContinuation", "value": _trend_metric_value(continuation, "/100"), "score": continuation},
        {"key": "trendReversalRisk", "value": _trend_metric_value(reversal, "/100"), "score": round(_clamp_score(100 - reversal), 1)},
        {"key": "trendMaStructure", "value": _trend_metric_value(profile.get("maStructureScore"), "/100"), "score": profile.get("maStructureScore")},
        {
            "key": "trendShortReturns",
            "value": f"1d {_trend_metric_value(profile.get('return1dPct'), '%')} / 5d {_trend_metric_value(profile.get('return5dPct'), '%')} / 20d {_trend_metric_value(profile.get('return20dPct'), '%')}",
            "score": profile.get("momentumShapeScore"),
        },
        {"key": "trendRsi14", "value": _trend_metric_value(profile.get("rsi14")), "score": profile.get("rsiScore")},
        {
            "key": "trendMacd",
            "value": f"hist {_trend_metric_value(profile.get('macdHistogramPct'), '%')} / slope {_trend_metric_value(profile.get('macdSlopePct'), '%')}",
            "score": profile.get("macdScore"),
        },
        {
            "key": "trendVolume",
            "value": f"{_trend_metric_value(profile.get('volumeSurge'), 'x')}",
            "score": profile.get("volumeConfirmationScore"),
        },
        {
            "key": "trendSupportResistance",
            "value": f"support {_trend_metric_value(profile.get('supportDistancePct'), '%')} / resistance {_trend_metric_value(profile.get('resistanceDistancePct'), '%')}",
            "score": round(_clamp_score(continuation - reversal + 50), 1),
        },
    ]

    positives = []
    negatives = []
    watch_items = []
    params = _trend_decision_params(profile)
    if continuation >= 64 and reversal < 60:
        positives.append({"key": "trendContinuationSupport", "params": params})
    elif continuation < NEXT_SESSION_CONTINUATION_BUY_FLOOR or reversal >= NEXT_SESSION_REVERSAL_BLOCK_BUY_FLOOR:
        negatives.append({"key": "trendContinuationWeak", "params": params})
    else:
        watch_items.append({"key": "trendContinuationWatch", "params": params})

    ma_score = float(profile.get("maStructureScore") or 50)
    if ma_score >= 66:
        positives.append({"key": "trendStructureSupport", "params": {"score": round(ma_score, 1)}})
    elif ma_score <= 44:
        negatives.append({"key": "trendStructureWeak", "params": {"score": round(ma_score, 1)}})

    rsi14 = profile.get("rsi14")
    if rsi14 is not None:
        if rsi14 >= 76:
            negatives.append({"key": "trendOverextended", "params": {"rsi": round(float(rsi14), 1)}})
        elif 45 <= rsi14 <= 68:
            positives.append({"key": "trendRsiHealthy", "params": {"rsi": round(float(rsi14), 1)}})

    macd_score = float(profile.get("macdScore") or 50)
    if macd_score >= 58:
        positives.append({"key": "trendMacdSupport", "params": {"score": round(macd_score, 1)}})
    elif macd_score <= 42:
        negatives.append({"key": "trendMacdPressure", "params": {"score": round(macd_score, 1)}})

    volume_score = float(profile.get("volumeConfirmationScore") or 50)
    if volume_score >= 62:
        positives.append({"key": "trendVolumeConfirm", "params": {"score": round(volume_score, 1)}})
    elif volume_score <= 44:
        negatives.append({"key": "trendVolumeDivergence", "params": {"score": round(volume_score, 1)}})

    resistance_distance = profile.get("resistanceDistancePct")
    support_distance = profile.get("supportDistancePct")
    if resistance_distance is not None and -0.2 <= float(resistance_distance) <= 2.0:
        watch_items.append({"key": "trendNearResistance", "params": {"distance": round(float(resistance_distance), 1)}})
    if support_distance is not None and 0 <= float(support_distance) <= 4.0:
        watch_items.append({"key": "trendNearSupport", "params": {"distance": round(float(support_distance), 1)}})

    return {
        "summary": {"key": summary_key, "params": params},
        "regime": regime,
        "continuationScore": round(continuation, 1),
        "reversalRiskScore": round(reversal, 1),
        "metrics": [metric for metric in metrics if metric.get("score") is not None],
        "positives": positives[:4],
        "negatives": negatives[:4],
        "watchItems": watch_items[:4],
        "profile": profile,
    }


def _detailed_weight_value(detailed_weights: dict | None, key: str) -> float:
    if not isinstance(detailed_weights, dict):
        return 0.0
    try:
        return max(0.0, float(detailed_weights.get(key) or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _overall_component_weights(detailed_weights: dict | None) -> dict[str, float]:
    defaults = {
        "todayBuyScore": 0.34,
        "futureRiseScore": 0.31,
        "profitableExitScore": 0.23,
        "newsHeatImpactScore": 0.12,
    }
    if not isinstance(detailed_weights, dict):
        return defaults

    detailed_total = sum(_detailed_weight_value(detailed_weights, key) for key in DETAILED_WEIGHT_KEYS)
    if detailed_total <= 0:
        return defaults

    raw = {
        "todayBuyScore": (
            _detailed_weight_value(detailed_weights, "todayBuy") * 1.00
            + _detailed_weight_value(detailed_weights, "volumeConfirmation") * 0.32
            + _detailed_weight_value(detailed_weights, "supportResistance") * 0.25
            + _detailed_weight_value(detailed_weights, "maStructure") * 0.14
            + _detailed_weight_value(detailed_weights, "riskControl") * 0.16
        ),
        "futureRiseScore": (
            _detailed_weight_value(detailed_weights, "futureRise") * 1.00
            + _detailed_weight_value(detailed_weights, "trendContinuation") * 0.42
            + _detailed_weight_value(detailed_weights, "momentum") * 0.30
            + _detailed_weight_value(detailed_weights, "macdConfirmation") * 0.20
            + _detailed_weight_value(detailed_weights, "maStructure") * 0.20
            + _detailed_weight_value(detailed_weights, "quality") * 0.12
            + _detailed_weight_value(detailed_weights, "fundFlow") * 0.12
        ),
        "profitableExitScore": (
            _detailed_weight_value(detailed_weights, "profitableExit") * 1.00
            + _detailed_weight_value(detailed_weights, "tTrade") * 0.55
            + _detailed_weight_value(detailed_weights, "riskControl") * 0.35
            + _detailed_weight_value(detailed_weights, "supportResistance") * 0.22
            + _detailed_weight_value(detailed_weights, "volumeConfirmation") * 0.20
            + _detailed_weight_value(detailed_weights, "rsiHealth") * 0.18
        ),
        "newsHeatImpactScore": (
            _detailed_weight_value(detailed_weights, "newsHeat") * 1.00
            + _detailed_weight_value(detailed_weights, "fundFlow") * 0.28
            + _detailed_weight_value(detailed_weights, "volumeConfirmation") * 0.12
            + _detailed_weight_value(detailed_weights, "momentum") * 0.08
        ),
    }
    total = sum(raw.values())
    if total <= 0:
        return defaults
    strategy_weights = {key: value / total for key, value in raw.items()}
    return {key: defaults[key] * 0.45 + strategy_weights[key] * 0.55 for key in defaults}


def _overall_assessment(
    score: float,
    metrics: dict[str, float],
    news_heat: dict,
    trend_analysis: dict,
    t_plan: dict,
    opportunity_score: float,
    downside_risk_score: float,
    breakout_setup_score: float,
    pullback_risk_score: float,
    price_change,
    detailed_weights: dict | None = None,
) -> dict:
    continuation = float(trend_analysis.get("continuationScore") or 50)
    reversal = float(trend_analysis.get("reversalRiskScore") or 50)
    heat_impact = float(news_heat.get("impactScore") or 45)
    t_score = float(t_plan.get("score") or 50)
    t_components = t_plan.get("components") or {}
    liquidity_score = float(t_components.get("liquidityScore") or 50)
    volatility_score = float(t_components.get("volatilityScore") or 50)
    change = _metric_number(price_change)

    today_buy_score = _clamp_score(
        score * 0.28
        + breakout_setup_score * 0.18
        + (100 - pullback_risk_score) * 0.16
        + metrics["risk"] * 0.14
        + metrics["value"] * 0.08
        + metrics["sentiment"] * 0.06
        + heat_impact * 0.10
        + _price_action_bonus(change) * 0.55
    )
    future_rise_score = _clamp_score(
        opportunity_score * 0.28
        + continuation * 0.24
        + metrics["momentum"] * 0.14
        + metrics["quality"] * 0.10
        + heat_impact * 0.10
        + (100 - downside_risk_score) * 0.10
        - reversal * 0.10
    )
    profitable_exit_score = _clamp_score(
        t_score * 0.24
        + liquidity_score * 0.16
        + volatility_score * 0.10
        + continuation * 0.15
        + (100 - downside_risk_score) * 0.17
        + (100 - pullback_risk_score) * 0.11
        + heat_impact * 0.07
    )
    component_weights = _overall_component_weights(detailed_weights)
    total_score = _clamp_score(
        today_buy_score * component_weights["todayBuyScore"]
        + future_rise_score * component_weights["futureRiseScore"]
        + profitable_exit_score * component_weights["profitableExitScore"]
        + heat_impact * component_weights["newsHeatImpactScore"]
    )
    if _is_severe_price_drop(change) or downside_risk_score >= DOWNSIDE_URGENT_EXIT_FLOOR:
        total_score = min(total_score, 38)
    elif _is_large_price_drop(change) or downside_risk_score >= DOWNSIDE_EXIT_FLOOR:
        total_score = min(total_score, 52)
    if reversal >= NEXT_SESSION_REVERSAL_BLOCK_BUY_FLOOR:
        total_score = min(total_score, 62)

    if total_score >= 76 and today_buy_score >= 68 and future_rise_score >= 66 and profitable_exit_score >= 60:
        suitability = "strongBuy"
        summary_key = "overallStrongBuySummary"
    elif total_score >= 68 and today_buy_score >= 60 and future_rise_score >= 58 and profitable_exit_score >= 54:
        suitability = "buy"
        summary_key = "overallBuySummary"
    elif total_score <= 42 or downside_risk_score >= DOWNSIDE_URGENT_EXIT_FLOOR or _is_severe_price_drop(change):
        suitability = "sell"
        summary_key = "overallSellSummary"
    elif total_score <= 54 or today_buy_score < 48 or future_rise_score < 48:
        suitability = "avoid"
        summary_key = "overallAvoidSummary"
    else:
        suitability = "watch"
        summary_key = "overallWatchSummary"

    params = {
        "score": round(total_score, 1),
        "today": round(today_buy_score, 1),
        "future": round(future_rise_score, 1),
        "exit": round(profitable_exit_score, 1),
        "heat": round(float(news_heat.get("heatScore") or 0), 1),
        "impact": round(heat_impact, 1),
        "risk": round(downside_risk_score, 1),
    }
    positives = []
    negatives = []
    watch_items = []
    if today_buy_score >= 62:
        positives.append({"key": "overallTodayBuySupport", "params": params})
    elif today_buy_score <= 50:
        negatives.append({"key": "overallTodayBuyWeak", "params": params})
    else:
        watch_items.append({"key": "overallTodayBuyWatch", "params": params})

    if future_rise_score >= 62:
        positives.append({"key": "overallFutureRiseSupport", "params": params})
    elif future_rise_score <= 50:
        negatives.append({"key": "overallFutureRiseWeak", "params": params})
    else:
        watch_items.append({"key": "overallFutureRiseWatch", "params": params})

    if profitable_exit_score >= 58:
        positives.append({"key": "overallProfitableExitSupport", "params": params})
    elif profitable_exit_score <= 48:
        negatives.append({"key": "overallProfitableExitWeak", "params": params})
    else:
        watch_items.append({"key": "overallProfitableExitWatch", "params": params})

    if heat_impact >= 62:
        positives.append({"key": "overallNewsHeatSupport", "params": params})
    elif heat_impact <= 42:
        negatives.append({"key": "overallNewsHeatRisk", "params": params})
    else:
        watch_items.append({"key": "overallNewsHeatWatch", "params": params})
    if downside_risk_score >= DOWNSIDE_EXIT_FLOOR or reversal >= NEXT_SESSION_REVERSAL_BLOCK_BUY_FLOOR:
        negatives.append({"key": "overallRiskTooHigh", "params": params})

    return {
        "summary": {"key": summary_key, "params": params},
        "suitability": suitability,
        "totalScore": round(total_score, 1),
        "components": {
            "todayBuyScore": round(today_buy_score, 1),
            "futureRiseScore": round(future_rise_score, 1),
            "profitableExitScore": round(profitable_exit_score, 1),
            "newsHeatImpactScore": round(heat_impact, 1),
        },
        "componentWeights": {key: round(value * 100, 1) for key, value in component_weights.items()},
        "metrics": [
            {"key": "overallTotal", "value": f"{total_score:.1f}/100", "score": round(total_score, 1)},
            {"key": "overallTodayBuy", "value": f"{today_buy_score:.1f}/100", "score": round(today_buy_score, 1)},
            {"key": "overallFutureRise", "value": f"{future_rise_score:.1f}/100", "score": round(future_rise_score, 1)},
            {"key": "overallProfitableExit", "value": f"{profitable_exit_score:.1f}/100", "score": round(profitable_exit_score, 1)},
            {"key": "overallNewsHeatImpact", "value": f"{heat_impact:.1f}/100", "score": round(heat_impact, 1)},
        ],
        "positives": positives[:5],
        "negatives": negatives[:5],
        "watchItems": watch_items[:5],
    }


def _max_drawdown(closes: list[float], window: int = 60) -> float:
    values = closes[-window:] if len(closes) >= window else closes
    if len(values) < 2:
        return 0.0
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1)
    return abs(worst)


def _momentum_score(closes: list[float]) -> float:
    if len(closes) < 22:
        return 50
    current = closes[-1]
    returns = {
        5: _price_return(closes, 5),
        20: _price_return(closes, 20),
        60: _price_return(closes, 60),
        120: _price_return(closes, 120),
    }
    trend_score = 50 + returns[5] * 95 + returns[20] * 105 + returns[60] * 60 + returns[120] * 35
    ma20 = _moving_average(closes, 20)
    ma60 = _moving_average(closes, 60)
    ma120 = _moving_average(closes, 120)
    ma_bonus = 0.0
    if ma20 and current > ma20:
        ma_bonus += 4
    if ma20 and ma60 and ma20 > ma60:
        ma_bonus += 5
    if ma60 and ma120 and ma60 > ma120:
        ma_bonus += 4
    positive_windows = sum(1 for value in returns.values() if value > 0)
    consistency_bonus = (positive_windows - 2) * 3
    drawdown_penalty = min(22, _max_drawdown(closes, 60) * 95)
    return _clamp_score(trend_score + ma_bonus + consistency_bonus - drawdown_penalty)


def _metric_availability(snapshot: MarketSnapshot, articles: list[Article]) -> dict[str, bool]:
    info = snapshot.info
    fund_flow_available = bool(_fund_flow_profile(info).get("available"))
    has_quality = any(
        _metric_number(info.get(key)) is not None
        for key in ["returnOnEquity", "profitMargins", "revenueGrowth", "earningsGrowth", "debtToEquity", "marketCap", "regularMarketVolume"]
    )
    has_value = any(
        _metric_number(info.get(key)) is not None
        for key in ["trailingPE", "forwardPE", "priceToBook", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"]
    )
    return {
        "sentiment": bool(articles) or fund_flow_available,
        "momentum": len(snapshot.closes) >= 22,
        "value": has_value,
        "risk": len(snapshot.closes) >= 22 or _metric_number(info.get("beta")) is not None,
        "quality": has_quality,
    }


def _range_position(snapshot: MarketSnapshot) -> float | None:
    high_52 = _metric_number(snapshot.info.get("fiftyTwoWeekHigh"))
    low_52 = _metric_number(snapshot.info.get("fiftyTwoWeekLow"))
    if high_52 is None or low_52 is None or high_52 <= low_52:
        return None
    return (snapshot.price - low_52) / (high_52 - low_52) * 100


def _liquidity_score(info: dict) -> float | None:
    volume = _metric_number(info.get("regularMarketVolume"))
    amount = _metric_number(info.get("turnoverValue"))
    market_cap = _metric_number(info.get("marketCap"))
    scores = []
    if volume and volume > 0:
        scores.append(_clamp_score(20 + log10(volume) * 8))
    if amount and amount > 0:
        scores.append(_clamp_score(12 + log10(amount) * 7))
    if market_cap and market_cap > 0:
        scores.append(_clamp_score(45 + log10(market_cap / 1_000_000_000) * 8))
    return mean(scores) if scores else None


def _clamp_signed_score(value: float) -> float:
    return max(-100, min(100, value))


def _fund_flow_money_label(value: float | None) -> str:
    if value is None:
        return "N/A"
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"CNY {value / 1_000_000_000:+.2f}b"
    if absolute >= 1_000_000:
        return f"CNY {value / 1_000_000:+.1f}m"
    if absolute >= 1_000:
        return f"CNY {value / 1_000:+.1f}k"
    return f"CNY {value:+.0f}"


def _fund_flow_metric_value(amount: float | None, ratio: float | None) -> str:
    ratio_label = "N/A" if ratio is None else f"{ratio:+.1f}%"
    return f"{_fund_flow_money_label(amount)} ({ratio_label})"


def _fund_flow_profile(info: dict) -> dict:
    main_net = _metric_number(info.get("fundFlowMainNet"))
    main_ratio = _metric_number(info.get("fundFlowMainRatio"))
    super_large_net = _metric_number(info.get("fundFlowSuperLargeNet"))
    super_large_ratio = _metric_number(info.get("fundFlowSuperLargeRatio"))
    large_net = _metric_number(info.get("fundFlowLargeNet"))
    large_ratio = _metric_number(info.get("fundFlowLargeRatio"))
    medium_net = _metric_number(info.get("fundFlowMediumNet"))
    medium_ratio = _metric_number(info.get("fundFlowMediumRatio"))
    small_net = _metric_number(info.get("fundFlowSmallNet"))
    small_ratio = _metric_number(info.get("fundFlowSmallRatio"))
    turnover = _metric_number(info.get("turnoverValue"))

    if main_ratio is None and main_net is not None and turnover and turnover > 0:
        main_ratio = main_net / turnover * 100
    if main_ratio is None:
        parts = [value for value in [super_large_ratio, large_ratio] if value is not None]
        if parts:
            main_ratio = sum(parts)

    available = any(
        value is not None
        for value in [
            main_net,
            main_ratio,
            super_large_net,
            super_large_ratio,
            large_net,
            large_ratio,
            medium_net,
            medium_ratio,
            small_net,
            small_ratio,
        ]
    )
    if not available:
        return {"available": False, "score": 0.0, "positiveScore": 0.0, "negativeScore": 0.0}

    signed_score = (main_ratio or 0) * 4.0
    if super_large_ratio is not None:
        signed_score += super_large_ratio * 0.7
    if large_ratio is not None:
        signed_score += large_ratio * 0.6
    if small_ratio is not None:
        signed_score -= small_ratio * 0.4
    if main_net is not None and abs(main_net) >= 1_000_000:
        amount_bonus = min(12, log10(abs(main_net) / 1_000_000 + 1) * 4.0)
        signed_score += amount_bonus if main_net > 0 else -amount_bonus

    signed_score = round(_clamp_signed_score(signed_score), 1)
    return {
        "available": True,
        "source": info.get("fundFlowSource") or "Eastmoney",
        "score": signed_score,
        "positiveScore": round(max(0, signed_score), 1),
        "negativeScore": round(max(0, -signed_score), 1),
        "mainNet": main_net,
        "mainRatio": main_ratio,
        "superLargeNet": super_large_net,
        "superLargeRatio": super_large_ratio,
        "largeNet": large_net,
        "largeRatio": large_ratio,
        "mediumNet": medium_net,
        "mediumRatio": medium_ratio,
        "smallNet": small_net,
        "smallRatio": small_ratio,
    }


def _fund_flow_decision_params(fund_flow: dict) -> dict:
    return {
        "score": round(float(fund_flow.get("score") or 0), 1),
        "amount": _fund_flow_money_label(_metric_number(fund_flow.get("mainNet"))),
        "ratio": round(float(fund_flow.get("mainRatio") or 0), 1),
        "source": str(fund_flow.get("source") or "Eastmoney"),
    }


def _metrics(snapshot: MarketSnapshot, articles: list[Article]) -> dict[str, float]:
    closes = snapshot.closes
    momentum = _momentum_score(closes)
    fund_flow = _fund_flow_profile(snapshot.info)
    flow_score = float(fund_flow.get("score") or 0)
    if fund_flow.get("available"):
        momentum = _clamp_score(momentum + flow_score * 0.12)

    pe = _metric_number(snapshot.info.get("trailingPE") or snapshot.info.get("forwardPE"))
    pb = _metric_number(snapshot.info.get("priceToBook"))
    range_position = _range_position(snapshot)
    value_parts = []
    if pe is not None:
        value_parts.append(_clamp_score(100 - abs(pe - 18) * 2.2))
    if pb is not None:
        value_parts.append(_clamp_score(100 - abs(pb - 2.2) * 12))
    if range_position is not None:
        value_parts.append(_clamp_score(82 - range_position * 0.45))
    value = mean(value_parts) if value_parts else 55

    beta = _metric_number(snapshot.info.get("beta"))
    beta_score = 65 if beta is None else _clamp_score(100 - abs(beta - 1) * 42)
    risk = round((beta_score * 0.45) + (volatility_score(closes) * 0.55), 1)
    if fund_flow.get("available"):
        risk = round(_clamp_score(risk + flow_score * 0.08), 1)

    roe = _metric_number(snapshot.info.get("returnOnEquity"))
    margin = _metric_number(snapshot.info.get("profitMargins"))
    revenue_growth = _metric_number(snapshot.info.get("revenueGrowth"))
    earnings_growth = _metric_number(snapshot.info.get("earningsGrowth"))
    debt = _metric_number(snapshot.info.get("debtToEquity"))
    quality_parts = []
    if roe is not None:
        quality_parts.append(_clamp_score(roe * 260))
    if margin is not None:
        quality_parts.append(_clamp_score(45 + margin * 180))
    if revenue_growth is not None:
        quality_parts.append(_clamp_score(50 + revenue_growth * 180))
    if earnings_growth is not None:
        quality_parts.append(_clamp_score(50 + earnings_growth * 140))
    if debt is not None:
        quality_parts.append(_clamp_score(100 - debt / 2))
    if not quality_parts:
        liquidity = _liquidity_score(snapshot.info)
        if liquidity is not None:
            quality_parts.append(liquidity)
        quality_parts.append(volatility_score(closes))
        quality_parts.append(_clamp_score(100 - _max_drawdown(closes, 120) * 145))

    return {
        "momentum": round(momentum, 1),
        "value": round(value, 1),
        "sentiment": round(_clamp_score(_sentiment_score(articles) + (flow_score * 0.18 if fund_flow.get("available") else 0)), 1),
        "risk": risk,
        "quality": round(mean(quality_parts), 1) if quality_parts else 50,
    }


def _number(value) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _percent_value(value) -> str:
    number = _number(value)
    return "N/A" if number is None else f"{number * 100:.1f}%"


def _plain_value(value, suffix: str = "") -> str:
    number = _number(value)
    return "N/A" if number is None else f"{number:.1f}{suffix}"


def _financial_analysis(snapshot: MarketSnapshot) -> dict:
    info = snapshot.info
    price = snapshot.price
    pe = _number(info.get("trailingPE") or info.get("forwardPE"))
    pb = _number(info.get("priceToBook"))
    roe = _number(info.get("returnOnEquity"))
    margin = _number(info.get("profitMargins"))
    revenue_growth = _number(info.get("revenueGrowth"))
    earnings_growth = _number(info.get("earningsGrowth"))
    debt = _number(info.get("debtToEquity"))
    target = _number(info.get("targetMeanPrice"))
    analyst_count = _number(info.get("numberOfAnalystOpinions"))
    dividend = _number(info.get("dividendYield"))
    high_52 = _number(info.get("fiftyTwoWeekHigh"))
    low_52 = _number(info.get("fiftyTwoWeekLow"))
    liquidity = _liquidity_score(info)

    metrics = []
    positives = []
    negatives = []
    watch_items = []
    fund_flow = _fund_flow_profile(info)

    if fund_flow.get("available"):
        flow_score = round(float(fund_flow.get("score") or 0), 1)
        positive_flow = float(fund_flow.get("positiveScore") or 0)
        negative_flow = float(fund_flow.get("negativeScore") or 0)
        metrics.append(
            {
                "key": "fundFlowMain",
                "value": _fund_flow_metric_value(
                    _metric_number(fund_flow.get("mainNet")),
                    _metric_number(fund_flow.get("mainRatio")),
                ),
                "score": round(_clamp_score(50 + flow_score / 2), 1),
            }
        )
        if fund_flow.get("superLargeNet") is not None or fund_flow.get("superLargeRatio") is not None:
            metrics.append(
                {
                    "key": "fundFlowSuperLarge",
                    "value": _fund_flow_metric_value(
                        _metric_number(fund_flow.get("superLargeNet")),
                        _metric_number(fund_flow.get("superLargeRatio")),
                    ),
                    "score": round(_clamp_score(50 + (_metric_number(fund_flow.get("superLargeRatio")) or 0) * 2.6), 1),
                }
            )
        if fund_flow.get("largeNet") is not None or fund_flow.get("largeRatio") is not None:
            metrics.append(
                {
                    "key": "fundFlowLarge",
                    "value": _fund_flow_metric_value(
                        _metric_number(fund_flow.get("largeNet")),
                        _metric_number(fund_flow.get("largeRatio")),
                    ),
                    "score": round(_clamp_score(50 + (_metric_number(fund_flow.get("largeRatio")) or 0) * 2.3), 1),
                }
            )
        params = _fund_flow_decision_params(fund_flow)
        if positive_flow >= 18:
            positives.append({"key": "fundFlowSupport", "params": params})
        elif negative_flow >= 18:
            negatives.append({"key": "fundFlowPressure", "params": params})
        else:
            watch_items.append({"key": "fundFlowWatch", "params": params})

    if pe is not None:
        score = max(0, min(100, 100 - abs(pe - 18) * 2.2))
        metrics.append({"key": "pe", "value": _plain_value(pe), "score": round(score, 1)})
        if pe <= 18:
            positives.append({"key": "financialValuationReasonable", "params": {"value": round(pe, 1)}})
        elif pe >= 35:
            negatives.append({"key": "financialValuationRich", "params": {"value": round(pe, 1)}})
        else:
            watch_items.append({"key": "financialWatchValuation", "params": {"value": round(pe, 1)}})

    if pb is not None:
        score = _clamp_score(100 - abs(pb - 2.2) * 12)
        metrics.append({"key": "priceToBook", "value": _plain_value(pb), "score": round(score, 1)})

    growth_scores = []
    for key, value in [("revenueGrowth", revenue_growth), ("earningsGrowth", earnings_growth)]:
        if value is not None:
            score = max(0, min(100, 50 + value * 180))
            metrics.append({"key": key, "value": _percent_value(value), "score": round(score, 1)})
            growth_scores.append(score)
    if growth_scores and mean(growth_scores) >= 60:
        positives.append({"key": "financialGrowthSupport", "params": {"score": round(mean(growth_scores), 1)}})
    elif growth_scores and mean(growth_scores) <= 45:
        negatives.append({"key": "financialGrowthWeak", "params": {"score": round(mean(growth_scores), 1)}})
    else:
        watch_items.append({"key": "financialWatchNextReport", "params": {}})

    profitability_scores = []
    for key, value in [("returnOnEquity", roe), ("profitMargins", margin)]:
        if value is not None:
            score = max(0, min(100, value * 260 if key == "returnOnEquity" else 45 + value * 180))
            metrics.append({"key": key, "value": _percent_value(value), "score": round(score, 1)})
            profitability_scores.append(score)
    if profitability_scores and mean(profitability_scores) >= 60:
        positives.append({"key": "financialProfitabilitySupport", "params": {"score": round(mean(profitability_scores), 1)}})
    elif profitability_scores and mean(profitability_scores) <= 45:
        negatives.append({"key": "financialProfitabilityWeak", "params": {"score": round(mean(profitability_scores), 1)}})

    if debt is not None:
        debt_score = max(0, min(100, 100 - debt / 2))
        metrics.append({"key": "debtToEquity", "value": _plain_value(debt), "score": round(debt_score, 1)})
        if debt_score >= 65:
            positives.append({"key": "financialDebtControlled", "params": {"score": round(debt_score, 1)}})
        elif debt_score <= 40:
            negatives.append({"key": "financialDebtRisk", "params": {"score": round(debt_score, 1)}})

    if target is not None and price:
        upside = (target / price - 1) * 100
        metrics.append({"key": "analystTargetUpside", "value": f"{upside:.1f}%", "score": round(max(0, min(100, 50 + upside)), 1)})
        if analyst_count and analyst_count >= 3 and upside >= 12:
            positives.append({"key": "financialAnalystUpside", "params": {"upside": round(upside, 1), "count": round(analyst_count)}})
        elif upside <= -8:
            negatives.append({"key": "financialAnalystDownside", "params": {"upside": round(upside, 1)}})

    if dividend is not None and dividend > 0:
        metrics.append({"key": "dividendYield", "value": _percent_value(dividend), "score": round(max(0, min(100, 45 + dividend * 600)), 1)})
        if dividend >= 0.03:
            positives.append({"key": "financialDividendSupport", "params": {"yield": round(dividend * 100, 1)}})

    if liquidity is not None:
        metrics.append({"key": "liquidityQuality", "value": _plain_value(liquidity, "/100"), "score": round(liquidity, 1)})
        if liquidity >= 65:
            positives.append({"key": "financialLiquiditySupport", "params": {"score": round(liquidity, 1)}})
        elif liquidity <= 40:
            negatives.append({"key": "financialLiquidityRisk", "params": {"score": round(liquidity, 1)}})

    if high_52 is not None and low_52 is not None and high_52 > low_52:
        position = (price - low_52) / (high_52 - low_52) * 100
        metrics.append({"key": "fiftyTwoWeekPosition", "value": f"{position:.1f}%", "score": round(max(0, min(100, 100 - abs(position - 55) * 1.1)), 1)})
        if position >= 88:
            negatives.append({"key": "financialWatchHighRange", "params": {"position": round(position, 1)}})
        elif position <= 20:
            watch_items.append({"key": "financialWatchLowRange", "params": {"position": round(position, 1)}})

    if not metrics:
        watch_items.append({"key": "financialDataMissing", "params": {}})
        summary_key = "financialDataMissing"
    else:
        average_score = mean(metric["score"] for metric in metrics)
        if average_score >= 62:
            summary_key = "financialStrongSummary"
            if not positives:
                positives.append({"key": "financialStrongSummary", "params": {"count": len(metrics)}})
        elif average_score <= 45:
            summary_key = "financialWeakSummary"
            if not negatives:
                negatives.append({"key": "financialWeakSummary", "params": {"count": len(metrics)}})
        else:
            summary_key = "financialMixedSummary"
            if not positives and not negatives:
                watch_items.append({"key": "financialMixedSummary", "params": {"count": len(metrics)}})

    return {
        "summary": {"key": summary_key, "params": {"count": len(metrics)}},
        "metrics": metrics[:8],
        "positives": positives[:5],
        "negatives": negatives[:5],
        "watchItems": watch_items[:5],
    }


def _action_plan(
    verdict: str,
    score: float,
    metrics: dict[str, float],
    news: dict,
    financials: dict,
    price_change: float | None = None,
    pullback_risk_score: float | None = None,
) -> dict:
    negative_news = float(news.get("negativeScore", news.get("negativeCount", 0) * 10) or 0)
    positive_news = float(news.get("positiveScore", news.get("positiveCount", 0) * 10) or 0)
    net_news = float(news.get("netScore", positive_news - negative_news) or 0)
    negative_fundamentals = len(financials["negatives"])
    watch_items = []
    risk_controls = []

    if verdict == "buy":
        summary_key = "actionAccumulate"
        steps = [{"key": "actionBuyInBatches", "params": {"score": score}}]
        if positive_news < 18 or net_news < 8:
            steps.append({"key": "actionWaitNewsConfirmation", "params": {}})
        if negative_news > positive_news + 10:
            steps.append({"key": "actionDoNotAverageDown", "params": {}})
        if metrics["risk"] < 55:
            risk_controls.append({"key": "actionUseSmallPosition", "params": {"risk": metrics["risk"]}})
    elif verdict == "sell":
        summary_key = "actionReduceOrExit"
        steps = [{"key": "actionReduceExposure", "params": {"score": score}}]
        if negative_news > positive_news + 10:
            steps.append({"key": "actionDoNotAverageDown", "params": {}})
        risk_controls.append({"key": "actionSetExitReview", "params": {}})
    else:
        summary_key = "actionWait"
        steps = [{"key": "actionNoChase", "params": {"score": score}}]
        if negative_news > positive_news + 10:
            steps.append({"key": "actionDoNotAverageDown", "params": {}})
        watch_items.append({"key": "actionWatchNewsCatalyst", "params": {}})

    if negative_fundamentals:
        watch_items.append({"key": "actionWatchFinancialRepair", "params": {"count": negative_fundamentals}})
    change = _metric_number(price_change)
    if _is_severe_price_drop(change):
        risk_controls.append({"key": "actionAvoidLimitDown", "params": {"change": round(change, 1)}})
    elif _is_large_price_drop(change):
        risk_controls.append({"key": "actionWaitPriceStabilization", "params": {"change": round(change, 1)}})
    elif _is_extreme_price_jump(change):
        risk_controls.append({"key": "actionWaitPullback", "params": {"risk": round(pullback_risk_score or 0, 1)}})
    if (
        pullback_risk_score is not None
        and pullback_risk_score >= PULLBACK_RISK_BLOCK_BUY_FLOOR
        and not any(control["key"] == "actionWaitPullback" for control in risk_controls)
    ):
        risk_controls.append({"key": "actionWaitPullback", "params": {"risk": round(pullback_risk_score, 1)}})
    if metrics["momentum"] < 55:
        watch_items.append({"key": "actionWatchMomentumTurn", "params": {}})
    if metrics["risk"] < 45:
        risk_controls.append({"key": "actionRespectRisk", "params": {"risk": metrics["risk"]}})
    if not news["events"]:
        watch_items.append({"key": "actionRequireNewsEvidence", "params": {}})

    return {
        "summary": {"key": summary_key, "params": {"score": score}},
        "steps": steps[:4],
        "watchItems": watch_items[:4],
        "riskControls": risk_controls[:4],
    }


def _portfolio_context_from_payload(payload: dict) -> dict | None:
    portfolio = payload.get("portfolio") if isinstance(payload.get("portfolio"), dict) else {}
    raw_positions = portfolio.get("positions") if isinstance(portfolio, dict) else None
    if raw_positions is None:
        raw_positions = payload.get("portfolioPositions")
    if not isinstance(raw_positions, list):
        return None

    positions = []
    for raw_position in raw_positions:
        if not isinstance(raw_position, dict):
            continue
        symbol = str(raw_position.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        position = {
            "symbol": symbol,
            "code": str(raw_position.get("code") or symbol.split(".")[0]),
            "name": str(raw_position.get("name") or symbol),
            "market": str(raw_position.get("market") or infer_market(symbol)),
            "exchange": str(raw_position.get("exchange") or ""),
            "quantity": _metric_number(raw_position.get("quantity")) or 0,
            "availableQuantity": _metric_number(raw_position.get("availableQuantity")),
            "frozenQuantity": _metric_number(raw_position.get("frozenQuantity")),
            "costPrice": _metric_number(raw_position.get("costPrice")),
            "lastPrice": _metric_number(raw_position.get("lastPrice")),
            "marketValue": _metric_number(raw_position.get("marketValue")),
            "costAmount": _metric_number(raw_position.get("costAmount")),
            "unrealizedPnl": _metric_number(raw_position.get("unrealizedPnl")),
            "unrealizedPnlPct": _metric_number(raw_position.get("unrealizedPnlPct")),
            "openDate": raw_position.get("openDate"),
        }
        if position["marketValue"] is None and position["quantity"] and position["lastPrice"] is not None:
            position["marketValue"] = round(position["quantity"] * position["lastPrice"], 4)
        if position["frozenQuantity"] is None and position["availableQuantity"] is not None:
            position["frozenQuantity"] = max(0, position["quantity"] - position["availableQuantity"])
        if position["costAmount"] is None and position["quantity"] and position["costPrice"] is not None:
            position["costAmount"] = round(position["quantity"] * position["costPrice"], 4)
        if position["unrealizedPnl"] is None and position["marketValue"] is not None and position["costAmount"] is not None:
            position["unrealizedPnl"] = round(position["marketValue"] - position["costAmount"], 4)
        if position["unrealizedPnlPct"] is None and position["unrealizedPnl"] is not None and position["costAmount"]:
            position["unrealizedPnlPct"] = round(position["unrealizedPnl"] / position["costAmount"] * 100, 4)
        positions.append(position)

    if not positions:
        return None

    positions.sort(key=lambda item: item.get("marketValue") or 0, reverse=True)
    total_market_value = _metric_number(portfolio.get("totalMarketValue")) if isinstance(portfolio, dict) else None
    total_cost_amount = _metric_number(portfolio.get("totalCostAmount")) if isinstance(portfolio, dict) else None
    total_unrealized_pnl = _metric_number(portfolio.get("totalUnrealizedPnl")) if isinstance(portfolio, dict) else None
    if total_market_value is None:
        total_market_value = sum(_metric_number(position.get("marketValue")) or 0 for position in positions)
    if total_cost_amount is None:
        total_cost_amount = sum(_metric_number(position.get("costAmount")) or 0 for position in positions)
    if total_unrealized_pnl is None:
        total_unrealized_pnl = sum(_metric_number(position.get("unrealizedPnl")) or 0 for position in positions)
    total_unrealized_pnl_pct = _metric_number(portfolio.get("totalUnrealizedPnlPct")) if isinstance(portfolio, dict) else None
    if total_unrealized_pnl_pct is None and total_cost_amount:
        total_unrealized_pnl_pct = total_unrealized_pnl / total_cost_amount * 100

    return {
        "sourceName": str(portfolio.get("sourceName") or "holdings export") if isinstance(portfolio, dict) else "holdings export",
        "sourceType": str(portfolio.get("sourceType") or "portfolio-import") if isinstance(portfolio, dict) else "portfolio-import",
        "importedAt": portfolio.get("importedAt") if isinstance(portfolio, dict) else None,
        "positions": positions,
        "position_map": {position["symbol"]: position for position in positions},
        "totalMarketValue": round(total_market_value or 0, 4),
        "totalCostAmount": round(total_cost_amount or 0, 4),
        "totalUnrealizedPnl": round(total_unrealized_pnl or 0, 4),
        "totalUnrealizedPnlPct": round(total_unrealized_pnl_pct, 4) if total_unrealized_pnl_pct is not None else None,
        "importWarnings": portfolio.get("warnings", []) if isinstance(portfolio.get("warnings"), list) else [],
        "ignoredRows": portfolio.get("ignoredRows", 0) if isinstance(portfolio, dict) else 0,
    }


def _holding_note(key: str, severity: str = "info", **params) -> dict:
    return {"key": key, "severity": severity, "params": params}


def _holding_analysis(pick: dict, position: dict, total_market_value: float) -> dict:
    market_value = _metric_number(position.get("marketValue")) or 0
    position_weight = market_value / total_market_value * 100 if total_market_value else 0
    pnl_pct = _metric_number(position.get("unrealizedPnlPct"))
    downside_risk = _metric_number(pick.get("downsideRiskScore")) or 0
    pullback_risk = _metric_number(pick.get("pullbackRiskScore")) or 0
    notes = []

    if pick.get("verdict") == "sell" or downside_risk >= DOWNSIDE_URGENT_EXIT_FLOOR:
        action = "exit"
        notes.append(_holding_note("holdingStrategyExit", "danger", score=pick["score"], risk=round(downside_risk, 1)))
    elif downside_risk >= DOWNSIDE_EXIT_FLOOR or position_weight >= 35:
        action = "reduce"
        notes.append(_holding_note("holdingReduceRisk", "warning", risk=round(downside_risk, 1)))
    elif pick.get("verdict") == "buy" and pick.get("score", 0) >= STRICT_BUY_SCORE_FLOOR and (pnl_pct is None or pnl_pct > -8):
        action = "add"
        notes.append(_holding_note("holdingAddOnlyInBatches", "info", score=pick["score"]))
    else:
        action = "hold"
        notes.append(_holding_note("holdingHoldWait", "info", score=pick["score"]))

    if pnl_pct is not None and pnl_pct <= -20:
        notes.append(_holding_note("holdingLargeLoss", "danger", pnlPct=round(pnl_pct, 1)))
        notes.append(_holding_note("holdingNoAverageDown", "warning"))
    elif pnl_pct is not None and pnl_pct <= -10:
        notes.append(_holding_note("holdingBelowCost", "warning", pnlPct=round(pnl_pct, 1)))

    if position_weight >= 35:
        notes.append(_holding_note("holdingConcentration", "danger", weight=round(position_weight, 1)))
    elif position_weight >= 20:
        notes.append(_holding_note("holdingConcentration", "warning", weight=round(position_weight, 1)))

    if pnl_pct is not None and pnl_pct >= 12 and (pullback_risk >= PULLBACK_RISK_BLOCK_BUY_FLOOR or _is_overheated_price_jump(pick.get("change"))):
        notes.append(_holding_note("holdingProfitProtect", "warning", pnlPct=round(pnl_pct, 1), risk=round(pullback_risk, 1)))

    return {
        "action": action,
        "positionWeightPct": round(position_weight, 1),
        "notes": notes[:6],
    }


def _portfolio_summary(context: dict, picks: list[dict]) -> dict | None:
    portfolio = context.get("portfolio")
    if not portfolio:
        return None
    analyzed_symbols = {pick["symbol"] for pick in picks}
    position_symbols = {position["symbol"] for position in portfolio["positions"]}
    warnings = list(portfolio.get("importWarnings") or [])
    if portfolio.get("totalUnrealizedPnlPct") is not None and portfolio["totalUnrealizedPnlPct"] <= -10:
        warnings.append(_holding_note("portfolioTotalDrawdown", "danger", pnlPct=round(portfolio["totalUnrealizedPnlPct"], 1)))
    return {
        "sourceName": portfolio["sourceName"],
        "sourceType": portfolio["sourceType"],
        "importedAt": portfolio.get("importedAt"),
        "positions": portfolio["positions"],
        "recognizedCount": len(portfolio["positions"]),
        "matchedCount": len(position_symbols & analyzed_symbols),
        "unmatchedSymbols": sorted(position_symbols - analyzed_symbols),
        "ignoredRows": portfolio.get("ignoredRows", 0),
        "totalMarketValue": portfolio["totalMarketValue"],
        "totalCostAmount": portfolio["totalCostAmount"],
        "totalUnrealizedPnl": portfolio["totalUnrealizedPnl"],
        "totalUnrealizedPnlPct": portfolio["totalUnrealizedPnlPct"],
        "warnings": warnings[:8],
}


def _enrich_position_with_live_price(position: dict, pick: dict) -> dict:
    quantity = _metric_number(position.get("quantity")) or 0
    cost_price = _metric_number(position.get("costPrice"))
    live_price = _metric_number(pick.get("price"))
    if quantity <= 0 or live_price is None:
        return position

    updated = dict(position)
    updated["lastPrice"] = live_price
    updated["marketValue"] = round(quantity * live_price, 4)
    if cost_price is not None:
        updated["costAmount"] = round(quantity * cost_price, 4)
    cost_amount = _metric_number(updated.get("costAmount"))
    market_value = _metric_number(updated.get("marketValue"))
    if market_value is not None and cost_amount is not None:
        updated["unrealizedPnl"] = round(market_value - cost_amount, 4)
        updated["unrealizedPnlPct"] = round((market_value - cost_amount) / cost_amount * 100, 4) if cost_amount else None
    return updated


def _refresh_portfolio_totals(portfolio: dict) -> None:
    positions = portfolio.get("positions") or []
    total_market_value = sum(_metric_number(position.get("marketValue")) or 0 for position in positions)
    total_cost_amount = sum(_metric_number(position.get("costAmount")) or 0 for position in positions)
    total_unrealized_pnl = sum(_metric_number(position.get("unrealizedPnl")) or 0 for position in positions)
    portfolio["totalMarketValue"] = round(total_market_value, 4)
    portfolio["totalCostAmount"] = round(total_cost_amount, 4)
    portfolio["totalUnrealizedPnl"] = round(total_unrealized_pnl, 4)
    portfolio["totalUnrealizedPnlPct"] = round(total_unrealized_pnl / total_cost_amount * 100, 4) if total_cost_amount else None


def _apply_portfolio_context(context: dict, picks: list[dict]) -> dict | None:
    portfolio = context.get("portfolio")
    if not portfolio:
        return None
    position_map = portfolio["position_map"]
    for pick in picks:
        position = position_map.get(pick["symbol"])
        if not position:
            continue
        enriched = _enrich_position_with_live_price(position, pick)
        position_map[pick["symbol"]] = enriched
        for index, item in enumerate(portfolio["positions"]):
            if item["symbol"] == pick["symbol"]:
                portfolio["positions"][index] = enriched
                break

    _refresh_portfolio_totals(portfolio)
    total_market_value = portfolio.get("totalMarketValue") or 0
    for pick in picks:
        position = position_map.get(pick["symbol"])
        if not position:
            continue
        pick["holding"] = position
        pick["holdingAnalysis"] = _holding_analysis(pick, position, total_market_value)
    return _portfolio_summary(context, picks)


def _analysis_context(payload: dict, market_provider=None, news_crawler=None, universe_provider=None) -> dict:
    markets = set(payload.get("markets") or [market["id"] for market in MARKETS])
    strategy = _strategy_from_payload(payload)
    weights = _normalize_weights(strategy["weights"])
    market_provider = market_provider or YFinanceMarketDataProvider()
    news_crawler = news_crawler or RssNewsCrawler()
    universe_provider = universe_provider or MarketUniverseProvider()

    picks = []
    errors = []
    requested_symbols = [str(symbol).strip() for symbol in payload.get("symbols", []) if str(symbol).strip()]
    portfolio_context = _portfolio_context_from_payload(payload)
    portfolio_symbols = [position["symbol"] for position in portfolio_context["positions"]] if portfolio_context else []
    symbol_payload = payload
    if not requested_symbols and portfolio_symbols:
        requested_symbols = portfolio_symbols
        symbol_payload = {**payload, "symbols": requested_symbols}
    auto_scan = not requested_symbols
    requested_markets = payload.get("markets") or [market["id"] for market in MARKETS]
    discovery_limit = _initial_discovery_limit(requested_markets, auto_scan)
    discovered_symbols, discovery_errors, universe_source = _symbols_from_payload(
        symbol_payload,
        universe_provider,
        discovery_limit,
    )
    symbols = [item for item in discovered_symbols if infer_market(item.symbol) in markets]

    return {
        "strategy": strategy,
        "weights": weights,
        "market_provider": market_provider,
        "news_crawler": news_crawler,
        "universe_provider": universe_provider,
        "markets_filter": markets,
        "requested_markets": requested_markets,
        "symbols": symbols,
        "auto_scan": auto_scan,
        "display_limit": _auto_scan_display_limit(requested_markets, auto_scan),
        "refresh": bool(payload.get("refresh")),
        "discovery_errors": discovery_errors,
        "universe_source": universe_source,
        "discovery_limit": discovery_limit,
        "portfolio": portfolio_context,
    }


def _auto_scan_quality_target(context: dict) -> int:
    return min(AUTO_SCAN_BUY_LIMIT, AUTO_SCAN_TARGET_QUALITY_BUYS)


def _quality_buy_count(picks: list[dict]) -> int:
    return sum(1 for pick in picks if pick.get("verdict") == "buy" and _is_buy_candidate(pick))


def _actionable_candidate_count(picks: list[dict]) -> int:
    return sum(1 for pick in picks if _is_buy_candidate(pick) or _is_t_trade_candidate(pick))


def _next_auto_scan_limit(context: dict, picks: list[dict]) -> int | None:
    if not context["auto_scan"]:
        return None
    if (
        _quality_buy_count(picks) >= _auto_scan_quality_target(context)
        and _actionable_candidate_count(picks) >= AUTO_SCAN_TARGET_ACTIONABLE_CANDIDATES
    ):
        return None
    current_limit = int(context.get("discovery_limit") or AUTO_SCAN_DISCOVERY_LIMIT_PER_MARKET)
    for limit in AUTO_SCAN_EXPANSION_LIMITS_PER_MARKET:
        if limit > current_limit:
            return limit
    return None


def _expand_auto_scan_symbols(context: dict, limit_per_market: int) -> int:
    discovered, discovery_errors = context["universe_provider"].discover(
        context["requested_markets"],
        limit_per_market=limit_per_market,
    )
    context["discovery_errors"].extend(discovery_errors)
    existing_symbols = {item.symbol for item in context["symbols"]}
    new_symbols = []
    for item in _dedupe_discovered_symbols(discovered):
        if item.symbol in existing_symbols or infer_market(item.symbol) not in context["markets_filter"]:
            continue
        new_symbols.append(item)
        existing_symbols.add(item.symbol)
    context["symbols"].extend(new_symbols)
    context["discovery_limit"] = limit_per_market
    return len(new_symbols)


def _fetch_market_snapshot(market_provider, symbol: str, refresh: bool = False) -> MarketSnapshot:
    if refresh:
        try:
            return market_provider.fetch(symbol, refresh=True)
        except TypeError:
            pass
    return market_provider.fetch(symbol)


def _fetch_news_articles(news_crawler, symbol: str, name: str, refresh: bool = False) -> list[Article]:
    if refresh:
        try:
            return list(news_crawler.fetch(symbol, name, refresh=True))
        except TypeError:
            pass
    return list(news_crawler.fetch(symbol, name))


def _process_symbol(item: DiscoveredSymbol, market_provider, news_crawler, weights: dict[str, float], strategy: dict | None = None, refresh: bool = False) -> dict:
    snapshot = _fetch_market_snapshot(market_provider, item.symbol, refresh)
    raw_name = snapshot.name if snapshot.name and snapshot.name.upper() != snapshot.symbol.upper() else item.name
    company_name = local_company_name(snapshot.symbol, raw_name)
    articles = _dedupe_articles([*item.evidence, *_fetch_news_articles(news_crawler, snapshot.symbol, company_name, refresh)])
    metrics = _metrics(snapshot, articles)
    availability = _metric_availability(snapshot, articles)
    fund_flow = _fund_flow_profile(snapshot.info)
    sentiment_delta = _sentiment_boost(articles)
    score = round(_score_stock(metrics, weights, availability), 1)
    signals = _signals_for(articles)
    news_analysis = _news_analysis(articles)
    news_heat_analysis = _news_heat_analysis(articles, news_analysis)
    breakout_setup_score = _breakout_setup_score(snapshot, news_analysis)
    pullback_risk_score = _pullback_risk_score(snapshot, news_analysis)
    trend_analysis = _trend_analysis(snapshot, news_analysis, fund_flow)
    trend_profile = trend_analysis.get("profile") or {}
    opportunity_score, downside_risk_score = _prediction_scores(metrics, score, news_analysis, snapshot.change, breakout_setup_score, pullback_risk_score, fund_flow, trend_profile)
    t_score, t_components = _t_trade_score(snapshot, metrics, news_analysis, breakout_setup_score, pullback_risk_score, downside_risk_score)
    t_plan = _t_trade_plan(snapshot, metrics, t_score, t_components, breakout_setup_score, pullback_risk_score, downside_risk_score)
    overall_assessment = _overall_assessment(
        score,
        metrics,
        news_heat_analysis,
        trend_analysis,
        t_plan,
        opportunity_score,
        downside_risk_score,
        breakout_setup_score,
        pullback_risk_score,
        snapshot.change,
        (strategy or {}).get("detailedWeights"),
    )
    verdict = _verdict(score, metrics["risk"], metrics["quality"], metrics["sentiment"], snapshot.change)
    reason_codes = _reason_codes(metrics, score, sentiment_delta, snapshot.change, breakout_setup_score, pullback_risk_score, trend_profile)
    financial_analysis = _financial_analysis(snapshot)
    return {
        "symbol": snapshot.symbol,
        "name": company_name,
        "market": snapshot.market,
        "sector": snapshot.sector,
        "price": snapshot.price,
        "change": snapshot.change,
        "currency": snapshot.currency,
        "score": score,
        "opportunityScore": opportunity_score,
        "downsideRiskScore": downside_risk_score,
        "breakoutSetupScore": breakout_setup_score,
        "pullbackRiskScore": pullback_risk_score,
        "nextSessionContinuationScore": trend_analysis["continuationScore"],
        "nextSessionReversalRiskScore": trend_analysis["reversalRiskScore"],
        "tScore": t_score,
        "tPlan": t_plan,
        "fundFlow": fund_flow if fund_flow.get("available") else None,
        "overallAssessment": overall_assessment,
        "prediction": {
            "opportunityScore": opportunity_score,
            "downsideRiskScore": downside_risk_score,
            "breakoutSetupScore": breakout_setup_score,
            "pullbackRiskScore": pullback_risk_score,
            "nextSessionContinuationScore": trend_analysis["continuationScore"],
            "nextSessionReversalRiskScore": trend_analysis["reversalRiskScore"],
            "overallScore": overall_assessment["totalScore"],
            "todayBuyScore": overall_assessment["components"]["todayBuyScore"],
            "futureRiseScore": overall_assessment["components"]["futureRiseScore"],
            "profitableExitScore": overall_assessment["components"]["profitableExitScore"],
            "newsHeatImpactScore": overall_assessment["components"]["newsHeatImpactScore"],
            "tScore": t_score,
            "edge": round(opportunity_score - downside_risk_score, 1),
        },
        "verdict": verdict,
        "confidence": round(min(96, 45 + abs(score - 50) * 0.68 + metrics["quality"] * 0.2)),
        "reasons": _english_reasons(reason_codes),
        "reasonCodes": reason_codes,
        "signals": signals,
        "metrics": metrics,
        "scoreBreakdown": _score_breakdown(metrics, weights, availability),
        "decision": _decision_details(verdict, score, metrics, signals, news_analysis, snapshot.change, breakout_setup_score, pullback_risk_score, fund_flow),
        "newsAnalysis": news_analysis,
        "newsHeatAnalysis": news_heat_analysis,
        "trendAnalysis": trend_analysis,
        "financialAnalysis": financial_analysis,
        "actionPlan": _action_plan(verdict, score, metrics, news_analysis, financial_analysis, snapshot.change, pullback_risk_score),
    }


def _scan_state(context: dict, picks: list[dict], errors: list[dict]) -> dict:
    return {
        "auto": context["auto_scan"],
        "source": context["universe_source"],
        "requested": len(context["symbols"]),
        "succeeded": context.get("evaluated", len(picks)),
        "displayed": len(picks),
        "actionable": context.get("actionable", _actionable_candidate_count(picks)),
        "qualityBuys": context.get("quality_buys", _quality_buy_count(picks)),
        "failed": len(errors),
        "discoveryErrors": context["discovery_errors"],
    }


def _friendly_data_error(symbol: str, exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if any(
        marker in lowered
        for marker in [
            "urlopen error",
            "remote end closed connection",
            "incompleteread",
            "incomplete read",
            "0 bytes read",
            "connection aborted",
            "connection reset",
            "no such file or directory",
            "timed out",
            "temporarily unavailable",
        ]
    ):
        return f"行情资料暂时不可用，已跳过 {symbol}。请稍后重新扫描。"
    return message or f"行情资料暂时不可用，已跳过 {symbol}。"


def _finish_picks(picks: list[dict], auto_scan: bool = False, display_limit: int = AUTO_SCAN_RESULT_LIMIT) -> list[dict]:
    picks.sort(key=lambda item: item["score"], reverse=True)
    if auto_scan:
        _apply_auto_scan_search_algorithm(picks)
        display_picks = _curated_auto_scan_picks_for_limit(picks, display_limit)
    else:
        _relative_verdicts(picks)
        display_picks = sorted(picks, key=_display_priority_key)
    for pick in display_picks:
        pick["reasons"] = _english_reasons(pick["reasonCodes"])
    return display_picks


def _refresh_scan_quality_context(context: dict, picks: list[dict]) -> None:
    context["evaluated"] = len(picks)
    context["quality_buys"] = _quality_buy_count(picks)
    context["actionable"] = _actionable_candidate_count(picks)


def _process_symbol_batch(symbols: list[DiscoveredSymbol], market_provider, news_crawler, weights: dict[str, float], strategy: dict | None = None, refresh: bool = False) -> tuple[list[dict], list[dict]]:
    picks = []
    errors = []
    with ThreadPoolExecutor(max_workers=min(6, max(1, len(symbols)))) as executor:
        futures = {executor.submit(_process_symbol, item, market_provider, news_crawler, weights, strategy, refresh): item.symbol for item in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                picks.append(future.result())
            except Exception as exc:
                errors.append({"symbol": symbol, "error": _friendly_data_error(symbol, exc)})
    return picks, errors


def analyze(payload: dict, market_provider=None, news_crawler=None, universe_provider=None) -> dict:
    context = _analysis_context(payload, market_provider, news_crawler, universe_provider)
    strategy = context["strategy"]
    weights = context["weights"]
    symbols = context["symbols"]
    market_provider = context["market_provider"]
    news_crawler = context["news_crawler"]

    picks = []
    errors = []

    evaluated_symbols = set()
    display_picks: list[dict] = []
    while True:
        pending_symbols = [item for item in symbols if item.symbol not in evaluated_symbols]
        if pending_symbols:
            batch_picks, batch_errors = _process_symbol_batch(pending_symbols, market_provider, news_crawler, weights, strategy, context["refresh"])
            picks.extend(batch_picks)
            errors.extend(batch_errors)
            evaluated_symbols.update(item.symbol for item in pending_symbols)

        display_picks = _finish_picks(picks, context["auto_scan"], context["display_limit"])
        _refresh_scan_quality_context(context, picks)
        next_limit = _next_auto_scan_limit(context, picks)
        if next_limit is None:
            break
        if _expand_auto_scan_symbols(context, next_limit) <= 0:
            break
        symbols = context["symbols"]

    portfolio_summary = _apply_portfolio_context(context, display_picks)
    sectors = _sector_analysis(picks if context["auto_scan"] else display_picks)
    response = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "markets": MARKETS,
        "strategy": strategy,
        "picks": display_picks,
        "sectors": sectors,
        "errors": errors,
        "scan": _scan_state(context, display_picks, errors),
    }
    if portfolio_summary:
        response["portfolio"] = portfolio_summary
    return response


def stream_analyze(payload: dict, market_provider=None, news_crawler=None, universe_provider=None):
    context = _analysis_context(payload, market_provider, news_crawler, universe_provider)
    strategy = context["strategy"]
    weights = context["weights"]
    symbols = context["symbols"]
    market_provider = context["market_provider"]
    news_crawler = context["news_crawler"]
    generated_at = datetime.now(timezone.utc).isoformat()
    picks: list[dict] = []
    errors: list[dict] = []

    def event(event_type: str, **data) -> str:
        return json.dumps({"type": event_type, **data}, ensure_ascii=False) + "\n"

    yield event(
        "started",
        generatedAt=generated_at,
        markets=MARKETS,
        strategy=strategy,
        scan=_scan_state(context, picks, errors),
        portfolio=_portfolio_summary(context, picks),
    )

    evaluated_symbols = set()
    display_picks: list[dict] = []
    while True:
        pending_symbols = [item for item in symbols if item.symbol not in evaluated_symbols]
        if pending_symbols:
            with ThreadPoolExecutor(max_workers=min(6, max(1, len(pending_symbols)))) as executor:
                futures = {executor.submit(_process_symbol, item, market_provider, news_crawler, weights, strategy, context["refresh"]): item.symbol for item in pending_symbols}
                for future in as_completed(futures):
                    symbol = futures[future]
                    try:
                        pick = future.result()
                        picks.append(pick)
                        display_picks = _finish_picks(picks, context["auto_scan"], context["display_limit"])
                        portfolio_summary = _apply_portfolio_context(context, display_picks)
                        _refresh_scan_quality_context(context, picks)
                        sectors = _sector_analysis(picks if context["auto_scan"] else display_picks)
                        rank = next((index + 1 for index, item in enumerate(display_picks) if item["symbol"] == pick["symbol"]), len(display_picks))
                        yield event("pick", pick=pick, picks=display_picks, sectors=sectors, rank=rank, scan=_scan_state(context, display_picks, errors), portfolio=portfolio_summary)
                    except Exception as exc:
                        error_message = _friendly_data_error(symbol, exc)
                        errors.append({"symbol": symbol, "error": error_message})
                        display_picks = _finish_picks(picks, context["auto_scan"], context["display_limit"])
                        portfolio_summary = _apply_portfolio_context(context, display_picks)
                        _refresh_scan_quality_context(context, picks)
                        yield event("error", symbol=symbol, error=error_message, sectors=_sector_analysis(picks if context["auto_scan"] else display_picks), scan=_scan_state(context, display_picks, errors), portfolio=portfolio_summary)
            evaluated_symbols.update(item.symbol for item in pending_symbols)

        display_picks = _finish_picks(picks, context["auto_scan"], context["display_limit"])
        _refresh_scan_quality_context(context, picks)
        next_limit = _next_auto_scan_limit(context, picks)
        if next_limit is None:
            break
        if _expand_auto_scan_symbols(context, next_limit) <= 0:
            break
        symbols = context["symbols"]

    display_picks = display_picks or _finish_picks(picks, context["auto_scan"], context["display_limit"])
    portfolio_summary = _apply_portfolio_context(context, display_picks)
    _refresh_scan_quality_context(context, picks)
    sectors = _sector_analysis(picks if context["auto_scan"] else display_picks)
    complete_payload = {
        "generatedAt": generated_at,
        "markets": MARKETS,
        "strategy": strategy,
        "picks": display_picks,
        "sectors": sectors,
        "errors": errors,
        "scan": _scan_state(context, display_picks, errors),
    }
    if portfolio_summary:
        complete_payload["portfolio"] = portfolio_summary
    yield event("complete", **complete_payload)


def _dedupe_articles(articles: list[Article]) -> list[Article]:
    output = []
    seen = set()
    for article in articles:
        key = article.link or article.title
        if key not in seen:
            output.append(article)
            seen.add(key)
    return output
