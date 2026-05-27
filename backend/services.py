from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from statistics import mean

from backend.data import DEFAULT_SYMBOLS, MARKETS, STRATEGIES
from backend.providers import Article, MarketSnapshot, RssNewsCrawler, YFinanceMarketDataProvider, infer_market, local_company_name, volatility_score
from backend.universe import DiscoveredSymbol, MarketUniverseProvider


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


def _sentiment_score(articles: list[Article]) -> float:
    if not articles:
        return 50
    now = datetime.now(timezone.utc)
    weighted = [article.sentiment * article.credibility * article.relevance * max(0.2, 1 - _age_hours(article.published_at, now) / 168) for article in articles]
    return max(0, min(100, 50 + mean(weighted) * 50))


def _sentiment_boost(articles: list[Article]) -> float:
    if not articles:
        return 0
    return (_sentiment_score(articles) - 50) / 50 * 10


NEWS_EVENT_RULES = [
    ("earningsPositive", "positive", ["earnings beat", "beats expectations", "profit rises", "record revenue", "revenue growth", "showstopping earnings", "record $", "業績增長", "营收增长", "獲利成長", "利润增长", "盈喜", "創新高", "创新高"]),
    ("earningsNegative", "negative", ["misses expectations", "profit warning", "revenue falls", "業績下滑", "营收下滑", "獲利衰退", "利润下降", "盈警", "虧損", "亏损"]),
    ("guidancePositive", "positive", ["raises guidance", "上调指引", "上修財測", "财测上修", "展望樂觀", "展望乐观"]),
    ("guidanceNegative", "negative", ["cuts guidance", "下调指引", "財測下修", "财测下修", "展望保守", "需求放缓", "需求放緩"]),
    ("analystPositive", "positive", ["upgrade", "outperform", "buy rating", "target price raised", "上调评级", "買入評級", "目标价上调", "目標價上調"]),
    ("analystNegative", "negative", ["downgrade", "underperform", "sell rating", "target price cut", "下调评级", "賣出評級", "目标价下调", "目標價下調"]),
    ("capitalReturn", "positive", ["buyback", "repurchase", "dividend", "回购", "回購", "分红", "派息", "股息"]),
    ("shareholderSale", "negative", ["insider selling", "stake sale", "减持", "減持", "套现", "沽售"]),
    ("legalRegulatoryRisk", "negative", ["lawsuit", "probe", "investigation", "regulatory", "sanction", "诉讼", "調查", "调查", "监管", "罰款", "罚款"]),
    ("demandPositive", "positive", ["strong demand", "long-term demand", "order growth", "contract win", "新订单", "大单", "需求強勁", "需求强劲", "接單", "接单"]),
    ("demandNegative", "negative", ["weak demand", "china problem", "not enough", "isn't enough", "wobbly", "inventory correction", "order cut", "庫存調整", "库存调整", "砍单", "訂單下滑", "订单下滑"]),
    ("fundFlowPositive", "positive", ["net inflow", "institutional buying", "资金流入", "主力资金净流入", "機構買入", "机构买入", "抢筹", "搶籌"]),
    ("fundFlowNegative", "negative", ["net outflow", "institutional selling", "资金流出", "主力资金净流出", "機構賣出", "机构卖出"]),
]


def _news_events_for(article: Article) -> list[dict]:
    text = f"{article.title} {article.summary}".lower()
    events = []
    for key, impact, needles in NEWS_EVENT_RULES:
        if any(needle.lower() in text for needle in needles):
            events.append(
                {
                    "key": key,
                    "impact": impact,
                    "title": article.title,
                    "source": article.source,
                    "ageHours": _age_hours(article.published_at, datetime.now(timezone.utc)),
                    "weight": round(article.credibility * article.relevance, 2),
                }
            )
    if not events and abs(article.sentiment) >= 0.45:
        events.append(
            {
                "key": "generalPositiveNews" if article.sentiment > 0 else "generalNegativeNews",
                "impact": "positive" if article.sentiment > 0 else "negative",
                "title": article.title,
                "source": article.source,
                "ageHours": _age_hours(article.published_at, datetime.now(timezone.utc)),
                "weight": round(article.credibility * article.relevance, 2),
            }
        )
    return events


def _news_analysis(articles: list[Article]) -> dict:
    events = [event for article in articles for event in _news_events_for(article)]
    positive_count = sum(1 for event in events if event["impact"] == "positive")
    negative_count = sum(1 for event in events if event["impact"] == "negative")
    if not articles:
        summary_key = "newsNoEvidence"
    elif positive_count > negative_count:
        summary_key = "newsBullishSummary"
    elif negative_count > positive_count:
        summary_key = "newsBearishSummary"
    else:
        summary_key = "newsMixedSummary"
    return {
        "summary": {"key": summary_key, "params": {"positive": positive_count, "negative": negative_count, "total": len(articles)}},
        "positiveCount": positive_count,
        "negativeCount": negative_count,
        "events": sorted(events, key=lambda event: (event["weight"], -event["ageHours"]), reverse=True)[:8],
    }


def _score_stock(metrics: dict[str, float], weights: dict[str, float]) -> float:
    weighted_score = sum(metrics[key] * weights.get(key, 0) for key in metrics)
    return max(0, min(100, weighted_score))


def _score_breakdown(metrics: dict[str, float], weights: dict[str, float]) -> list[dict]:
    return [
        {
            "factor": factor,
            "score": round(metrics[factor], 1),
            "weight": round(weights.get(factor, 0) * 100, 1),
            "contribution": round(metrics[factor] * weights.get(factor, 0), 1),
        }
        for factor in ["sentiment", "momentum", "value", "risk", "quality"]
    ]


def _verdict(score: float, risk_metric: float) -> str:
    if score >= 72 and risk_metric >= 45:
        return "buy"
    if score < 52 or risk_metric < 42:
        return "sell"
    return "watch"


def _relative_verdicts(picks: list[dict]) -> None:
    if not picks:
        return
    sorted_scores = sorted([pick["score"] for pick in picks], reverse=True)
    buy_cutoff = sorted_scores[max(0, min(len(sorted_scores) - 1, round(len(sorted_scores) * 0.18) - 1))]
    sell_cutoff = sorted_scores[min(len(sorted_scores) - 1, max(0, round(len(sorted_scores) * 0.72)))]
    bought = 0
    for index, pick in enumerate(picks):
        risk = pick["metrics"]["risk"]
        if pick["score"] >= max(55, buy_cutoff) and risk >= 42 and bought < max(1, round(len(picks) * 0.18)):
            pick["verdict"] = "buy"
            bought += 1
            pick["reasonCodes"] = [reason for reason in pick["reasonCodes"] if reason["key"] not in {"notHighConviction", "clearsBuyThreshold"}]
            if not any(reason["key"] == "rankedTopOpportunity" for reason in pick["reasonCodes"]):
                pick["reasonCodes"].append({"key": "rankedTopOpportunity", "params": {"rank": index + 1}})
        elif pick["score"] < min(52, sell_cutoff) or risk < 25:
            pick["verdict"] = "sell"
        else:
            pick["verdict"] = "watch"
        pick["decision"] = _decision_details(pick["verdict"], pick["score"], pick["metrics"], pick["signals"])
        pick["actionPlan"] = _action_plan(pick["verdict"], pick["score"], pick["metrics"], pick["newsAnalysis"], pick["financialAnalysis"])


def _reason_codes(metrics: dict[str, float], score: float, sentiment_delta: float) -> list[dict]:
    strongest = sorted(metrics.items(), key=lambda item: item[1], reverse=True)[:2]
    weakest = min(metrics.items(), key=lambda item: item[1])
    reasons: list[dict] = [
        {"key": "strongestFactors", "params": {"first": strongest[0][0], "second": strongest[1][0]}},
        {"key": "sentimentImpact", "params": {"delta": round(sentiment_delta, 1)}},
    ]
    if weakest[1] < 50:
        reasons.append({"key": "belowThreshold", "params": {"factor": weakest[0]}})
    elif score >= 72:
        reasons.append({"key": "clearsBuyThreshold", "params": {}})
    else:
        reasons.append({"key": "notHighConviction", "params": {}})
    return reasons


def _decision_details(verdict: str, score: float, metrics: dict[str, float], signals: list[dict]) -> dict:
    positives = []
    negatives = []
    watch_items = []
    signal_count = len(signals)
    latest_signal = min((signal["ageHours"] for signal in signals), default=None)

    if metrics["sentiment"] >= 56:
        positives.append({"key": "newsSupport", "params": {"score": metrics["sentiment"], "count": signal_count}})
    elif metrics["sentiment"] <= 45:
        negatives.append({"key": "newsPressure", "params": {"score": metrics["sentiment"], "count": signal_count}})
    else:
        watch_items.append({"key": "watchNewsFlow", "params": {"score": metrics["sentiment"], "count": signal_count}})

    if signal_count == 0:
        negatives.append({"key": "insufficientNews", "params": {}})
    elif latest_signal is not None and latest_signal <= 24:
        positives.append({"key": "freshNews", "params": {"hours": latest_signal}})

    if metrics["momentum"] >= 60:
        positives.append({"key": "momentumSupport", "params": {"score": metrics["momentum"]}})
    elif metrics["momentum"] <= 45:
        negatives.append({"key": "weakMomentum", "params": {"score": metrics["momentum"]}})
    else:
        watch_items.append({"key": "watchBreakout", "params": {"score": metrics["momentum"]}})

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
        elif reason["key"] == "clearsBuyThreshold":
            output.append("Composite score clears the buy threshold under the selected strategy.")
        elif reason["key"] == "notHighConviction":
            output.append("Composite score is not strong enough for a high-conviction entry.")
        elif reason["key"] == "rankedTopOpportunity":
            output.append(f"Ranked #{params['rank']} within this scan, making it a relative buy candidate.")
    return output


def _symbols_from_payload(payload: dict, universe_provider=None) -> tuple[list[DiscoveredSymbol], list[dict], str]:
    symbols = [str(symbol).strip().upper() for symbol in payload.get("symbols", []) if str(symbol).strip()]
    if symbols:
        return [DiscoveredSymbol(symbol=symbol, name=symbol, market=infer_market(symbol), source="manual") for symbol in symbols[:25]], [], "manual"
    markets = payload.get("markets") or [market["id"] for market in MARKETS]
    provider = universe_provider or MarketUniverseProvider()
    discovered, discovery_errors = provider.discover(markets)
    seen = set()
    deduped = []
    for item in discovered:
        if item.symbol not in seen:
            deduped.append(item)
            seen.add(item.symbol)
    return deduped[:75], discovery_errors, "market-news"


def _metrics(snapshot: MarketSnapshot, articles: list[Article]) -> dict[str, float]:
    closes = snapshot.closes
    current = closes[-1]
    base_20 = closes[-21] if len(closes) > 21 else closes[0]
    base_60 = closes[-61] if len(closes) > 61 else closes[0]
    momentum = max(0, min(100, 50 + ((current / base_20 - 1) * 110) + ((current / base_60 - 1) * 60)))

    pe = snapshot.info.get("trailingPE") or snapshot.info.get("forwardPE")
    value = 55 if pe is None else max(0, min(100, 100 - abs(float(pe) - 18) * 2.2))

    beta = snapshot.info.get("beta")
    beta_score = 65 if beta is None else max(0, min(100, 100 - abs(float(beta) - 1) * 42))
    risk = round((beta_score * 0.45) + (volatility_score(closes) * 0.55), 1)

    roe = snapshot.info.get("returnOnEquity")
    margin = snapshot.info.get("profitMargins")
    revenue_growth = snapshot.info.get("revenueGrowth")
    earnings_growth = snapshot.info.get("earningsGrowth")
    debt = snapshot.info.get("debtToEquity")
    quality_parts = [
        50 if roe is None else max(0, min(100, float(roe) * 260)),
        50 if margin is None else max(0, min(100, 45 + float(margin) * 180)),
        50 if revenue_growth is None else max(0, min(100, 50 + float(revenue_growth) * 180)),
        50 if earnings_growth is None else max(0, min(100, 50 + float(earnings_growth) * 140)),
        62 if debt is None else max(0, min(100, 100 - float(debt) / 2)),
    ]

    return {
        "momentum": round(momentum, 1),
        "value": round(value, 1),
        "sentiment": round(_sentiment_score(articles), 1),
        "risk": risk,
        "quality": round(mean(quality_parts), 1),
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

    if high_52 is not None and low_52 is not None and high_52 > low_52:
        position = (price - low_52) / (high_52 - low_52) * 100
        metrics.append({"key": "fiftyTwoWeekPosition", "value": f"{position:.1f}%", "score": round(max(0, min(100, 100 - abs(position - 55) * 1.1)), 1)})
        if position >= 88:
            watch_items.append({"key": "financialWatchHighRange", "params": {"position": round(position, 1)}})
        elif position <= 20:
            watch_items.append({"key": "financialWatchLowRange", "params": {"position": round(position, 1)}})

    if not metrics:
        watch_items.append({"key": "financialDataMissing", "params": {}})
        summary_key = "financialDataMissing"
    else:
        average_score = mean(metric["score"] for metric in metrics)
        if average_score >= 62:
            summary_key = "financialStrongSummary"
        elif average_score <= 45:
            summary_key = "financialWeakSummary"
        else:
            summary_key = "financialMixedSummary"

    return {
        "summary": {"key": summary_key, "params": {"count": len(metrics)}},
        "metrics": metrics[:8],
        "positives": positives[:5],
        "negatives": negatives[:5],
        "watchItems": watch_items[:5],
    }


def _action_plan(verdict: str, score: float, metrics: dict[str, float], news: dict, financials: dict) -> dict:
    negative_news = news["negativeCount"]
    positive_news = news["positiveCount"]
    negative_fundamentals = len(financials["negatives"])
    watch_items = []
    risk_controls = []

    if verdict == "buy":
        summary_key = "actionAccumulate"
        steps = [{"key": "actionBuyInBatches", "params": {"score": score}}]
        if metrics["sentiment"] < 60:
            steps.append({"key": "actionWaitNewsConfirmation", "params": {}})
        if metrics["risk"] < 55:
            risk_controls.append({"key": "actionUseSmallPosition", "params": {"risk": metrics["risk"]}})
    elif verdict == "sell":
        summary_key = "actionReduceOrExit"
        steps = [{"key": "actionReduceExposure", "params": {"score": score}}]
        if negative_news > positive_news:
            steps.append({"key": "actionDoNotAverageDown", "params": {}})
        risk_controls.append({"key": "actionSetExitReview", "params": {}})
    else:
        summary_key = "actionWait"
        steps = [{"key": "actionNoChase", "params": {"score": score}}]
        watch_items.append({"key": "actionWatchNewsCatalyst", "params": {}})

    if negative_fundamentals:
        watch_items.append({"key": "actionWatchFinancialRepair", "params": {"count": negative_fundamentals}})
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

    picks = []
    errors = []
    requested_symbols = [str(symbol).strip() for symbol in payload.get("symbols", []) if str(symbol).strip()]
    auto_scan = not requested_symbols
    discovered_symbols, discovery_errors, universe_source = _symbols_from_payload(payload, universe_provider)
    symbols = [item for item in discovered_symbols if infer_market(item.symbol) in markets]

    return {
        "strategy": strategy,
        "weights": weights,
        "market_provider": market_provider,
        "news_crawler": news_crawler,
        "symbols": symbols,
        "auto_scan": auto_scan,
        "discovery_errors": discovery_errors,
        "universe_source": universe_source,
    }


def _process_symbol(item: DiscoveredSymbol, market_provider, news_crawler, weights: dict[str, float]) -> dict:
    snapshot = market_provider.fetch(item.symbol)
    raw_name = snapshot.name if snapshot.name and snapshot.name.upper() != snapshot.symbol.upper() else item.name
    company_name = local_company_name(snapshot.symbol, raw_name)
    articles = _dedupe_articles([*item.evidence, *news_crawler.fetch(snapshot.symbol, company_name)])
    metrics = _metrics(snapshot, articles)
    sentiment_delta = _sentiment_boost(articles)
    score = round(_score_stock(metrics, weights), 1)
    verdict = _verdict(score, metrics["risk"])
    reason_codes = _reason_codes(metrics, score, sentiment_delta)
    signals = _signals_for(articles)
    news_analysis = _news_analysis(articles)
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
        "verdict": verdict,
        "confidence": round(min(96, 45 + abs(score - 50) * 0.68 + metrics["quality"] * 0.2)),
        "reasons": _english_reasons(reason_codes),
        "reasonCodes": reason_codes,
        "signals": signals,
        "metrics": metrics,
        "scoreBreakdown": _score_breakdown(metrics, weights),
        "decision": _decision_details(verdict, score, metrics, signals),
        "newsAnalysis": news_analysis,
        "financialAnalysis": financial_analysis,
        "actionPlan": _action_plan(verdict, score, metrics, news_analysis, financial_analysis),
    }


def _scan_state(context: dict, picks: list[dict], errors: list[dict]) -> dict:
    return {
        "auto": context["auto_scan"],
        "source": context["universe_source"],
        "requested": len(context["symbols"]),
        "succeeded": len(picks),
        "failed": len(errors),
        "discoveryErrors": context["discovery_errors"],
    }


def _finish_picks(picks: list[dict]) -> None:
    picks.sort(key=lambda item: item["score"], reverse=True)
    _relative_verdicts(picks)
    for pick in picks:
        pick["reasons"] = _english_reasons(pick["reasonCodes"])


def analyze(payload: dict, market_provider=None, news_crawler=None, universe_provider=None) -> dict:
    context = _analysis_context(payload, market_provider, news_crawler, universe_provider)
    strategy = context["strategy"]
    weights = context["weights"]
    symbols = context["symbols"]
    market_provider = context["market_provider"]
    news_crawler = context["news_crawler"]

    picks = []
    errors = []

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(symbols)))) as executor:
        futures = {executor.submit(_process_symbol, item, market_provider, news_crawler, weights): item.symbol for item in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                picks.append(future.result())
            except Exception as exc:
                errors.append({"symbol": symbol, "error": str(exc)})

    _finish_picks(picks)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "markets": MARKETS,
        "strategy": strategy,
        "picks": picks,
        "errors": errors,
        "scan": _scan_state(context, picks, errors),
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

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(symbols)))) as executor:
        futures = {executor.submit(_process_symbol, item, market_provider, news_crawler, weights): item.symbol for item in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                pick = future.result()
                picks.append(pick)
                picks.sort(key=lambda item: item["score"], reverse=True)
                yield event("pick", pick=pick, rank=picks.index(pick) + 1, scan=_scan_state(context, picks, errors))
            except Exception as exc:
                errors.append({"symbol": symbol, "error": str(exc)})
                yield event("error", symbol=symbol, error=str(exc), scan=_scan_state(context, picks, errors))

    _finish_picks(picks)
    yield event(
        "complete",
        generatedAt=generated_at,
        markets=MARKETS,
        strategy=strategy,
        picks=picks,
        errors=errors,
        scan=_scan_state(context, picks, errors),
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
