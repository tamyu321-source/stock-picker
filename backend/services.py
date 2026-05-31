from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from math import exp, log10
from statistics import mean

from backend.data import DEFAULT_SYMBOLS, MARKETS, STRATEGIES
from backend.providers import Article, MarketSnapshot, RssNewsCrawler, YFinanceMarketDataProvider, infer_market, local_company_name, volatility_score
from backend.universe import DiscoveredSymbol, MarketUniverseProvider


FACTOR_ORDER = ["sentiment", "momentum", "value", "risk", "quality"]
AUTO_SCAN_DISCOVERY_LIMIT_PER_MARKET = 72
AUTO_SCAN_EXPANSION_LIMITS_PER_MARKET = (72, 120, 180)
AUTO_SCAN_TARGET_QUALITY_BUYS = 4
AUTO_SCAN_RESULT_LIMIT = 36
AUTO_SCAN_BUY_LIMIT = 12
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


def get_config() -> dict:
    return {
        "markets": MARKETS,
        "strategies": STRATEGIES,
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
        return {
            "id": "custom",
            "name": "Custom AI Strategy",
            "description": "User-defined scoring weights from the web interface.",
            "weights": custom_weights,
            "riskTolerance": 55,
        }

    strategy_id = payload.get("strategyId", "balanced")
    return next((strategy for strategy in STRATEGIES if strategy["id"] == strategy_id), STRATEGIES[0])


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
        pick["decision"] = _decision_details(pick["verdict"], pick["score"], pick["metrics"], pick["signals"], pick["newsAnalysis"], pick.get("change"), pick.get("breakoutSetupScore"), pick.get("pullbackRiskScore"))
        pick["actionPlan"] = _action_plan(pick["verdict"], pick["score"], pick["metrics"], pick["newsAnalysis"], pick["financialAnalysis"], pick.get("change"), pick.get("pullbackRiskScore"))

    for index, pick in enumerate(sorted([item for item in picks if item["verdict"] == "buy"], key=_investment_priority, reverse=True), start=1):
        pick["reasonCodes"].append({"key": "rankedTopOpportunity", "params": {"rank": index}})


def _investment_priority(pick: dict) -> float:
    metrics = pick["metrics"]
    setup_score = float(pick.get("breakoutSetupScore") or 0)
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


def _latest_turnover_percent(info: dict) -> float | None:
    value = _metric_number(info.get("latestTurnoverRate"))
    if value is None:
        value = _metric_number(info.get("turnoverRate"))
    if value is None:
        return None
    return value * 100 if value <= 1 else value


def _pullback_risk_score(snapshot: MarketSnapshot, news: dict) -> float:
    closes = snapshot.closes
    change = _metric_number(snapshot.change)
    volume_surge = max(
        _metric_number(snapshot.info.get("volumeSurge20")) or 0,
        _metric_number(snapshot.info.get("amountSurge20")) or 0,
    )
    turnover_percent = _latest_turnover_percent(snapshot.info)
    positive_news, negative_news, net_news = _news_strengths(news)

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
) -> tuple[float, float]:
    positive_news, negative_news, net_news = _news_strengths(news)
    opportunity = _clamp_score(
        score * 0.28
        + metrics["quality"] * 0.20
        + metrics["momentum"] * 0.16
        + metrics["risk"] * 0.14
        + metrics["value"] * 0.10
        + metrics["sentiment"] * 0.08
        + positive_news * 0.08
        + max(0, net_news) * 0.06
        + breakout_setup_score * 0.18
        + _price_action_bonus(price_change)
        - negative_news * 0.10
        - pullback_risk_score * 0.16
    )
    downside = _clamp_score(
        (100 - score) * 0.22
        + (100 - metrics["risk"]) * 0.24
        + (100 - metrics["momentum"]) * 0.16
        + (100 - metrics["sentiment"]) * 0.12
        + (100 - metrics["quality"]) * 0.10
        + negative_news * 0.16
        + max(0, -net_news) * 0.08
        + _price_action_risk(price_change)
        + pullback_risk_score * 0.28
        - positive_news * 0.06
        - breakout_setup_score * 0.04
    )
    return round(opportunity, 1), round(downside, 1)


def _is_quality_investment_candidate(pick: dict) -> bool:
    metrics = pick["metrics"]
    news = pick.get("newsAnalysis") or {}
    positive_news, negative_news, _ = _news_strengths(news)
    downside_score = pick.get("downsideRiskScore")
    pullback_risk = float(pick.get("pullbackRiskScore") or 0)
    return (
        float(pick.get("opportunityScore") or 0) >= OPPORTUNITY_BUY_FLOOR
        and float(downside_score if downside_score is not None else 100) <= 45
        and pullback_risk < PULLBACK_RISK_BLOCK_BUY_FLOOR
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
    return (
        setup_score >= BREAKOUT_SETUP_BUY_FLOOR
        and float(pick.get("opportunityScore") or 0) >= OPPORTUNITY_BUY_FLOOR
        and float(downside_score if downside_score is not None else 100) <= BREAKOUT_SETUP_DOWNSIDE_CEILING
        and pullback_risk < PULLBACK_RISK_BLOCK_BUY_FLOOR
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


def _is_watch_candidate(pick: dict) -> bool:
    metrics = pick["metrics"]
    return (
        not _is_exit_candidate(pick)
        and (
            pick["score"] >= 55
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
        pick["decision"] = _decision_details(pick["verdict"], pick["score"], pick["metrics"], pick["signals"], pick["newsAnalysis"], pick.get("change"), pick.get("breakoutSetupScore"), pick.get("pullbackRiskScore"))
        pick["actionPlan"] = _action_plan(pick["verdict"], pick["score"], pick["metrics"], pick["newsAnalysis"], pick["financialAnalysis"], pick.get("change"), pick.get("pullbackRiskScore"))

    for index, pick in enumerate(sorted([item for item in picks if item["verdict"] == "buy"], key=_investment_priority, reverse=True), start=1):
        pick["reasonCodes"].append({"key": "rankedTopOpportunity", "params": {"rank": index}})


def _display_priority_key(pick: dict) -> tuple[int, float]:
    if pick["verdict"] == "buy":
        return (0, -_investment_priority(pick))
    if pick["verdict"] == "sell":
        return (1, -_sell_priority(pick))
    return (2, -_investment_priority(pick))


def _average(values: list[float]) -> float:
    return round(mean(values), 1) if values else 0.0


def _sector_name(pick: dict) -> str:
    sector = str(pick.get("sector") or "").strip()
    return sector if sector and sector.lower() != "unknown" else "Unclassified"


def _sector_id(name: str) -> str:
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in name)
    return "-".join(part for part in cleaned.split("-") if part) or "unclassified"


def _sector_recommendation(score: float, metrics: dict[str, float], verdict_counts: dict[str, int], count: int) -> str:
    sell_ratio = verdict_counts.get("sell", 0) / count if count else 0
    buy_ratio = verdict_counts.get("buy", 0) / count if count else 0
    if buy_ratio > 0 and score >= 66 and metrics["risk"] >= 48 and metrics["sentiment"] >= 52 and sell_ratio < 0.34:
        return "overweight"
    if score < 54 or metrics["risk"] < 38 or sell_ratio >= 0.45:
        return "underweight"
    if buy_ratio >= 0.45 and metrics["quality"] >= 58 and metrics["momentum"] >= 55:
        return "overweight"
    return "neutral"


def _sector_priority(sector: dict) -> float:
    metrics = sector["metrics"]
    sell_count = sector["verdictCounts"].get("sell", 0)
    sell_ratio = sell_count / sector["count"] if sector["count"] else 0
    return round(
        sector["score"] * 0.48
        + metrics["quality"] * 0.16
        + metrics["momentum"] * 0.14
        + metrics["risk"] * 0.12
        + metrics["sentiment"] * 0.10
        - sell_ratio * 18,
        3,
    )


def _apply_relative_sector_recommendations(sectors: list[dict]) -> None:
    if not sectors or any(sector["recommendation"] == "overweight" for sector in sectors):
        return
    candidates = [
        sector
        for sector in sectors
        if sector["verdictCounts"].get("buy", 0) > 0
        and sector["score"] >= 62
        and sector["metrics"]["risk"] >= 45
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
    }


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
        score = _average([float(pick["score"]) for pick in sector_picks])
        verdict_counts = {
            "buy": sum(1 for pick in sector_picks if pick["verdict"] == "buy"),
            "watch": sum(1 for pick in sector_picks if pick["verdict"] == "watch"),
            "sell": sum(1 for pick in sector_picks if pick["verdict"] == "sell"),
        }
        market_counts: dict[str, int] = {}
        for pick in sector_picks:
            market_counts[pick["market"]] = market_counts.get(pick["market"], 0) + 1
        leaders = sorted(sector_picks, key=_investment_priority, reverse=True)[:3]
        leader_symbols = {pick["symbol"] for pick in leaders}
        laggards = [
            pick
            for pick in sorted(sector_picks, key=_sell_priority, reverse=True)
            if pick["symbol"] not in leader_symbols
        ][:3]
        count = len(sector_picks)
        sectors.append(
            {
                "id": _sector_id(name),
                "name": name,
                "score": score,
                "recommendation": _sector_recommendation(score, metrics, verdict_counts, count),
                "confidence": round(min(96, 42 + abs(score - 50) * 0.46 + min(count, 8) * 4 + metrics["quality"] * 0.12)),
                "count": count,
                "marketMix": [
                    {"market": market, "count": market_counts[market]}
                    for market in sorted(market_counts)
                ],
                "verdictCounts": verdict_counts,
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
    selected.extend(buy_candidates[:AUTO_SCAN_BUY_LIMIT])
    remaining = AUTO_SCAN_RESULT_LIMIT - len(selected)
    if remaining > 0:
        selected.extend(urgent_sell_candidates[: min(AUTO_SCAN_SELL_LIMIT, remaining)])
    remaining = AUTO_SCAN_RESULT_LIMIT - len(selected)
    if remaining > 0:
        selected.extend(watch_candidates[:remaining])
    remaining = AUTO_SCAN_RESULT_LIMIT - len(selected)
    if remaining > 0:
        selected.extend(fallback_watch_candidates[:remaining])

    seen = set()
    unique_selected = []
    for pick in selected:
        if pick["symbol"] not in seen:
            unique_selected.append(pick)
            seen.add(pick["symbol"])
    return sorted(unique_selected, key=_display_priority_key)


def _reason_codes(
    metrics: dict[str, float],
    score: float,
    sentiment_delta: float,
    price_change: float | None = None,
    breakout_setup_score: float = 0.0,
    pullback_risk_score: float = 0.0,
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


def _symbols_from_payload(
    payload: dict,
    universe_provider=None,
    limit_per_market: int = AUTO_SCAN_DISCOVERY_LIMIT_PER_MARKET,
) -> tuple[list[DiscoveredSymbol], list[dict], str]:
    manual_inputs = [str(symbol).strip() for symbol in payload.get("symbols", []) if str(symbol).strip()]
    if manual_inputs:
        provider = universe_provider or MarketUniverseProvider()
        markets = payload.get("markets") or [market["id"] for market in MARKETS]
        if hasattr(provider, "resolve_manual_inputs"):
            resolved, discovery_errors = provider.resolve_manual_inputs(manual_inputs, markets, limit=25)
            return resolved, discovery_errors, "manual"
        symbols = [symbol.upper() for symbol in manual_inputs]
        return [DiscoveredSymbol(symbol=symbol, name=symbol, market=infer_market(symbol), source="manual") for symbol in symbols[:25]], [], "manual"
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
    has_quality = any(
        _metric_number(info.get(key)) is not None
        for key in ["returnOnEquity", "profitMargins", "revenueGrowth", "earningsGrowth", "debtToEquity", "marketCap", "regularMarketVolume"]
    )
    has_value = any(
        _metric_number(info.get(key)) is not None
        for key in ["trailingPE", "forwardPE", "priceToBook", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"]
    )
    return {
        "sentiment": bool(articles),
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


def _metrics(snapshot: MarketSnapshot, articles: list[Article]) -> dict[str, float]:
    closes = snapshot.closes
    momentum = _momentum_score(closes)

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
        "sentiment": round(_sentiment_score(articles), 1),
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
    auto_scan = not requested_symbols
    requested_markets = payload.get("markets") or [market["id"] for market in MARKETS]
    discovered_symbols, discovery_errors, universe_source = _symbols_from_payload(
        payload,
        universe_provider,
        AUTO_SCAN_DISCOVERY_LIMIT_PER_MARKET,
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
        "refresh": bool(payload.get("refresh")),
        "discovery_errors": discovery_errors,
        "universe_source": universe_source,
        "discovery_limit": AUTO_SCAN_DISCOVERY_LIMIT_PER_MARKET,
    }


def _auto_scan_quality_target(context: dict) -> int:
    return min(AUTO_SCAN_BUY_LIMIT, AUTO_SCAN_TARGET_QUALITY_BUYS)


def _quality_buy_count(picks: list[dict]) -> int:
    return sum(1 for pick in picks if pick.get("verdict") == "buy" and _is_buy_candidate(pick))


def _next_auto_scan_limit(context: dict, picks: list[dict]) -> int | None:
    if not context["auto_scan"]:
        return None
    if _quality_buy_count(picks) >= _auto_scan_quality_target(context):
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


def _process_symbol(item: DiscoveredSymbol, market_provider, news_crawler, weights: dict[str, float], refresh: bool = False) -> dict:
    snapshot = _fetch_market_snapshot(market_provider, item.symbol, refresh)
    raw_name = snapshot.name if snapshot.name and snapshot.name.upper() != snapshot.symbol.upper() else item.name
    company_name = local_company_name(snapshot.symbol, raw_name)
    articles = _dedupe_articles([*item.evidence, *_fetch_news_articles(news_crawler, snapshot.symbol, company_name, refresh)])
    metrics = _metrics(snapshot, articles)
    availability = _metric_availability(snapshot, articles)
    sentiment_delta = _sentiment_boost(articles)
    score = round(_score_stock(metrics, weights, availability), 1)
    signals = _signals_for(articles)
    news_analysis = _news_analysis(articles)
    breakout_setup_score = _breakout_setup_score(snapshot, news_analysis)
    pullback_risk_score = _pullback_risk_score(snapshot, news_analysis)
    opportunity_score, downside_risk_score = _prediction_scores(metrics, score, news_analysis, snapshot.change, breakout_setup_score, pullback_risk_score)
    verdict = _verdict(score, metrics["risk"], metrics["quality"], metrics["sentiment"], snapshot.change)
    reason_codes = _reason_codes(metrics, score, sentiment_delta, snapshot.change, breakout_setup_score, pullback_risk_score)
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
        "prediction": {
            "opportunityScore": opportunity_score,
            "downsideRiskScore": downside_risk_score,
            "breakoutSetupScore": breakout_setup_score,
            "pullbackRiskScore": pullback_risk_score,
            "edge": round(opportunity_score - downside_risk_score, 1),
        },
        "verdict": verdict,
        "confidence": round(min(96, 45 + abs(score - 50) * 0.68 + metrics["quality"] * 0.2)),
        "reasons": _english_reasons(reason_codes),
        "reasonCodes": reason_codes,
        "signals": signals,
        "metrics": metrics,
        "scoreBreakdown": _score_breakdown(metrics, weights, availability),
        "decision": _decision_details(verdict, score, metrics, signals, news_analysis, snapshot.change, breakout_setup_score, pullback_risk_score),
        "newsAnalysis": news_analysis,
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


def _finish_picks(picks: list[dict], auto_scan: bool = False) -> list[dict]:
    picks.sort(key=lambda item: item["score"], reverse=True)
    if auto_scan:
        _apply_auto_scan_search_algorithm(picks)
        display_picks = _curated_auto_scan_picks(picks)
    else:
        _relative_verdicts(picks)
        display_picks = sorted(picks, key=_display_priority_key)
    for pick in display_picks:
        pick["reasons"] = _english_reasons(pick["reasonCodes"])
    return display_picks


def _process_symbol_batch(symbols: list[DiscoveredSymbol], market_provider, news_crawler, weights: dict[str, float], refresh: bool = False) -> tuple[list[dict], list[dict]]:
    picks = []
    errors = []
    with ThreadPoolExecutor(max_workers=min(6, max(1, len(symbols)))) as executor:
        futures = {executor.submit(_process_symbol, item, market_provider, news_crawler, weights, refresh): item.symbol for item in symbols}
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
            batch_picks, batch_errors = _process_symbol_batch(pending_symbols, market_provider, news_crawler, weights, context["refresh"])
            picks.extend(batch_picks)
            errors.extend(batch_errors)
            evaluated_symbols.update(item.symbol for item in pending_symbols)

        context["evaluated"] = len(picks)
        display_picks = _finish_picks(picks, context["auto_scan"])
        next_limit = _next_auto_scan_limit(context, display_picks)
        if next_limit is None:
            break
        if _expand_auto_scan_symbols(context, next_limit) <= 0:
            break
        symbols = context["symbols"]

    sectors = _sector_analysis(display_picks)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "markets": MARKETS,
        "strategy": strategy,
        "picks": display_picks,
        "sectors": sectors,
        "errors": errors,
        "scan": _scan_state(context, display_picks, errors),
    }


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
    )

    evaluated_symbols = set()
    display_picks: list[dict] = []
    while True:
        pending_symbols = [item for item in symbols if item.symbol not in evaluated_symbols]
        if pending_symbols:
            with ThreadPoolExecutor(max_workers=min(6, max(1, len(pending_symbols)))) as executor:
                futures = {executor.submit(_process_symbol, item, market_provider, news_crawler, weights, context["refresh"]): item.symbol for item in pending_symbols}
                for future in as_completed(futures):
                    symbol = futures[future]
                    try:
                        pick = future.result()
                        picks.append(pick)
                        context["evaluated"] = len(picks)
                        display_picks = _finish_picks(picks, context["auto_scan"])
                        sectors = _sector_analysis(display_picks)
                        rank = next((index + 1 for index, item in enumerate(display_picks) if item["symbol"] == pick["symbol"]), len(display_picks))
                        yield event("pick", pick=pick, picks=display_picks, sectors=sectors, rank=rank, scan=_scan_state(context, display_picks, errors))
                    except Exception as exc:
                        error_message = _friendly_data_error(symbol, exc)
                        errors.append({"symbol": symbol, "error": error_message})
                        display_picks = _finish_picks(picks, context["auto_scan"])
                        yield event("error", symbol=symbol, error=error_message, sectors=_sector_analysis(display_picks), scan=_scan_state(context, display_picks, errors))
            evaluated_symbols.update(item.symbol for item in pending_symbols)

        context["evaluated"] = len(picks)
        display_picks = _finish_picks(picks, context["auto_scan"])
        next_limit = _next_auto_scan_limit(context, display_picks)
        if next_limit is None:
            break
        if _expand_auto_scan_symbols(context, next_limit) <= 0:
            break
        symbols = context["symbols"]

    context["evaluated"] = len(picks)
    display_picks = display_picks or _finish_picks(picks, context["auto_scan"])
    sectors = _sector_analysis(display_picks)
    yield event(
        "complete",
        generatedAt=generated_at,
        markets=MARKETS,
        strategy=strategy,
        picks=display_picks,
        sectors=sectors,
        errors=errors,
        scan=_scan_state(context, display_picks, errors),
    )


def _dedupe_articles(articles: list[Article]) -> list[Article]:
    output = []
    seen = set()
    for article in articles:
        key = article.link or article.title
        if key not in seen:
            output.append(article)
            seen.add(key)
    return output
