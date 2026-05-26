from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
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


def _score_stock(metrics: dict[str, float], weights: dict[str, float]) -> float:
    weighted_score = sum(metrics[key] * weights.get(key, 0) for key in metrics)
    return max(0, min(100, weighted_score))


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
        if pick["score"] >= max(55, buy_cutoff) and risk >= 25 and bought < max(1, round(len(picks) * 0.18)):
            pick["verdict"] = "buy"
            bought += 1
            pick["reasonCodes"] = [reason for reason in pick["reasonCodes"] if reason["key"] not in {"notHighConviction", "clearsBuyThreshold"}]
            if not any(reason["key"] == "rankedTopOpportunity" for reason in pick["reasonCodes"]):
                pick["reasonCodes"].append({"key": "rankedTopOpportunity", "params": {"rank": index + 1}})
        elif pick["score"] < min(52, sell_cutoff) or risk < 25:
            pick["verdict"] = "sell"
        else:
            pick["verdict"] = "watch"


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
    return deduped[:75], discovery_errors, "market-universe"


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
    debt = snapshot.info.get("debtToEquity")
    quality_parts = [
        50 if roe is None else max(0, min(100, float(roe) * 260)),
        50 if margin is None else max(0, min(100, 45 + float(margin) * 180)),
        62 if debt is None else max(0, min(100, 100 - float(debt) / 2)),
    ]

    return {
        "momentum": round(momentum, 1),
        "value": round(value, 1),
        "sentiment": round(_sentiment_score(articles), 1),
        "risk": risk,
        "quality": round(mean(quality_parts), 1),
    }


def analyze(payload: dict, market_provider=None, news_crawler=None, universe_provider=None) -> dict:
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

    def process_symbol(item: DiscoveredSymbol) -> dict:
        snapshot = market_provider.fetch(item.symbol)
        raw_name = snapshot.name if snapshot.name and snapshot.name.upper() != snapshot.symbol.upper() else item.name
        company_name = local_company_name(snapshot.symbol, raw_name)
        articles = news_crawler.fetch(snapshot.symbol, company_name)
        metrics = _metrics(snapshot, articles)
        sentiment_delta = _sentiment_boost(articles)
        score = round(_score_stock(metrics, weights), 1)
        verdict = _verdict(score, metrics["risk"])
        reason_codes = _reason_codes(metrics, score, sentiment_delta)
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
            "signals": _signals_for(articles),
            "metrics": metrics,
        }

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(symbols)))) as executor:
        futures = {executor.submit(process_symbol, item): item.symbol for item in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                picks.append(future.result())
            except Exception as exc:
                errors.append({"symbol": symbol, "error": str(exc)})

    picks.sort(key=lambda item: item["score"], reverse=True)
    _relative_verdicts(picks)
    for pick in picks:
        pick["reasons"] = _english_reasons(pick["reasonCodes"])
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "markets": MARKETS,
        "strategy": strategy,
        "picks": picks,
        "errors": errors,
        "scan": {
            "auto": auto_scan,
            "source": universe_source,
            "requested": len(symbols),
            "succeeded": len(picks),
            "failed": len(errors),
            "discoveryErrors": discovery_errors,
        },
    }
