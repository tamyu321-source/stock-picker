from __future__ import annotations

from statistics import mean
from typing import Any


REGIME_LABELS = {
    "quality_compounder",
    "momentum_breakout",
    "deep_value_turnaround",
    "event_driven",
    "falling_knife",
    "overheated",
    "balanced_watch",
    "insufficient_data",
    "defensive_etf_core",
    "sector_etf_tactical",
}


def _number(value, default: float | None = None) -> float | None:
    try:
        if value in (None, "", "-"):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _grade(score: float) -> str:
    if score >= 75:
        return "strong"
    if score >= 58:
        return "usable"
    if score >= 42:
        return "thin"
    return "weak"


def _event_scores(news_analysis: dict[str, Any]) -> tuple[float, float, float]:
    positive = _number(news_analysis.get("positiveScore"), 0.0) or 0.0
    negative = _number(news_analysis.get("negativeScore"), 0.0) or 0.0
    net = _number(news_analysis.get("netScore"), positive - negative) or 0.0
    return positive, negative, net


def _financial_score(financial_analysis: dict[str, Any]) -> float:
    metrics = financial_analysis.get("metrics") or []
    scores = [_number(metric.get("score")) for metric in metrics if _number(metric.get("score")) is not None]
    return mean(scores) if scores else 50.0


def _fundamental_coverage(info: dict[str, Any], instrument_type: str) -> float:
    if instrument_type == "etf":
        keys = [
            "totalAssets",
            "annualReportExpenseRatio",
            "regularMarketVolume",
            "marketCap",
            "dividendYield",
            "yield",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
        ]
    else:
        keys = [
            "trailingPE",
            "forwardPE",
            "returnOnEquity",
            "profitMargins",
            "debtToEquity",
            "revenueGrowth",
            "earningsGrowth",
            "marketCap",
            "regularMarketVolume",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
        ]
    present = sum(1 for key in keys if _number(info.get(key)) is not None)
    return _clamp(present / len(keys) * 100)


def data_quality_profile(
    *,
    instrument_type: str,
    closes: list[float],
    info: dict[str, Any],
    news_analysis: dict[str, Any],
    news_heat: dict[str, Any],
    financial_analysis: dict[str, Any],
    availability: dict[str, bool] | None = None,
) -> dict[str, Any]:
    availability = availability or {}
    price_points = len([value for value in closes if _number(value) is not None])
    if price_points >= 120:
        price_score = 100.0
    elif price_points >= 60:
        price_score = 78.0
    elif price_points >= 30:
        price_score = 56.0
    elif price_points >= 10:
        price_score = 35.0
    else:
        price_score = 12.0

    fundamental_score = _fundamental_coverage(info, instrument_type)
    financial_metric_count = len(financial_analysis.get("metrics") or [])
    if financial_metric_count >= 5:
        financial_score = 92.0
    elif financial_metric_count >= 3:
        financial_score = 72.0
    elif financial_metric_count >= 1:
        financial_score = 48.0
    else:
        financial_score = 18.0

    news_count = _number(news_analysis.get("positiveCount"), 0.0) or 0.0
    news_count += _number(news_analysis.get("negativeCount"), 0.0) or 0.0
    freshness = _number(news_heat.get("freshnessScore"), 0.0) or 0.0
    source_count = _number(news_heat.get("sourceCount"), 0.0) or 0.0
    news_score = _clamp(news_count * 16 + freshness * 0.42 + source_count * 11)

    available_factor_count = sum(1 for value in availability.values() if value)
    factor_score = _clamp(available_factor_count / 5 * 100) if availability else 70.0

    score = _clamp(
        price_score * 0.30
        + fundamental_score * 0.20
        + financial_score * 0.18
        + news_score * 0.17
        + factor_score * 0.15
    )
    issues: list[str] = []
    strengths: list[str] = []
    if price_score < 50:
        issues.append("priceHistoryThin")
    else:
        strengths.append("priceHistoryUsable")
    if fundamental_score < 40:
        issues.append("fundamentalDataThin")
    else:
        strengths.append("fundamentalDataUsable")
    if news_score < 35:
        issues.append("newsEvidenceThin")
    else:
        strengths.append("newsEvidenceUsable")
    if financial_score < 40:
        issues.append("financialReviewThin")
    else:
        strengths.append("financialReviewUsable")

    return {
        "score": round(score, 1),
        "level": _grade(score),
        "priceHistoryScore": round(price_score, 1),
        "fundamentalCoverageScore": round(fundamental_score, 1),
        "financialCoverageScore": round(financial_score, 1),
        "newsCoverageScore": round(news_score, 1),
        "factorCoverageScore": round(factor_score, 1),
        "issues": issues,
        "strengths": strengths,
    }


def classify_regime(
    *,
    instrument_type: str,
    metrics: dict[str, float],
    data_quality: dict[str, Any],
    news_analysis: dict[str, Any],
    news_heat: dict[str, Any],
    trend_analysis: dict[str, Any],
    financial_analysis: dict[str, Any],
    opportunity_score: float,
    downside_risk_score: float,
    breakout_setup_score: float,
    pullback_risk_score: float,
    price_change: float | None,
) -> dict[str, Any]:
    positive_news, negative_news, net_news = _event_scores(news_analysis)
    continuation = _number(trend_analysis.get("continuationScore"), 50.0) or 50.0
    reversal = _number(trend_analysis.get("reversalRiskScore"), 50.0) or 50.0
    heat_impact = _number(news_heat.get("impactScore"), 45.0) or 45.0
    financial_score = _financial_score(financial_analysis)
    change = _number(price_change, 0.0) or 0.0

    if data_quality["score"] < 40:
        regime = "insufficient_data"
    elif change <= -8.5 or downside_risk_score >= 72 or (reversal >= 74 and continuation < 45):
        regime = "falling_knife"
    elif change >= 12 or pullback_risk_score >= 72:
        regime = "overheated"
    elif instrument_type == "etf":
        if metrics.get("risk", 0) >= 58 and financial_score >= 62 and continuation >= 50:
            regime = "defensive_etf_core"
        else:
            regime = "sector_etf_tactical"
    elif breakout_setup_score >= 74 and continuation >= 58 and pullback_risk_score < 62:
        regime = "momentum_breakout"
    elif metrics.get("quality", 0) >= 64 and financial_score >= 58 and metrics.get("risk", 0) >= 50:
        regime = "quality_compounder"
    elif metrics.get("value", 0) >= 62 and continuation >= 48 and downside_risk_score < 62:
        regime = "deep_value_turnaround"
    elif heat_impact >= 62 or (positive_news >= negative_news + 14 and net_news >= 10):
        regime = "event_driven"
    else:
        regime = "balanced_watch"

    return {
        "name": regime if regime in REGIME_LABELS else "balanced_watch",
        "confidence": round(
            _clamp(
                data_quality["score"] * 0.38
                + abs(opportunity_score - downside_risk_score) * 0.20
                + abs(net_news) * 0.16
                + abs(continuation - reversal) * 0.14
                + financial_score * 0.12
            ),
            1,
        ),
        "signals": {
            "financialScore": round(financial_score, 1),
            "continuationScore": round(continuation, 1),
            "reversalRiskScore": round(reversal, 1),
            "newsImpactScore": round(heat_impact, 1),
            "netNewsScore": round(net_news, 1),
            "priceChangePct": round(change, 2),
        },
    }


def risk_gates(
    *,
    instrument_type: str,
    metrics: dict[str, float],
    data_quality: dict[str, Any],
    news_analysis: dict[str, Any],
    trend_analysis: dict[str, Any],
    financial_analysis: dict[str, Any],
    t_plan: dict[str, Any],
    downside_risk_score: float,
    pullback_risk_score: float,
    price_change: float | None,
) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    positive_news, negative_news, _ = _event_scores(news_analysis)
    reversal = _number(trend_analysis.get("reversalRiskScore"), 50.0) or 50.0
    continuation = _number(trend_analysis.get("continuationScore"), 50.0) or 50.0
    liquidity = _number(((t_plan.get("components") or {}).get("liquidityScore")), metrics.get("quality", 50)) or 50.0
    financial_negatives = len(financial_analysis.get("negatives") or [])
    change = _number(price_change, 0.0) or 0.0

    def add(kind: str, key: str, severity: str, value: float | None = None, threshold: float | None = None) -> None:
        gates.append(
            {
                "kind": kind,
                "key": key,
                "severity": severity,
                "value": round(value, 1) if value is not None else None,
                "threshold": round(threshold, 1) if threshold is not None else None,
            }
        )

    if data_quality["score"] < 45:
        add("blockBuy", "dataQualityTooWeak", "warning", data_quality["score"], 45)
    if change <= -8.5:
        add("exitCandidate", "severePriceBreakdown", "danger", change, -8.5)
    elif change <= -5:
        add("forceReduce", "largePriceBreakdown", "warning", change, -5)
    if downside_risk_score >= 72:
        add("exitCandidate", "downsideRiskUrgent", "danger", downside_risk_score, 72)
    elif downside_risk_score >= 62:
        add("forceReduce", "downsideRiskHigh", "warning", downside_risk_score, 62)
    if reversal >= 68:
        add("blockBuy", "reversalRiskHigh", "warning", reversal, 68)
    if pullback_risk_score >= 72:
        add("blockBuy", "pullbackRiskExtreme", "warning", pullback_risk_score, 72)
    if negative_news >= positive_news + 24:
        add("blockBuy", "negativeNewsDominates", "warning", negative_news - positive_news, 24)
    if negative_news >= positive_news + 38:
        add("forceReduce", "negativeNewsSevere", "danger", negative_news - positive_news, 38)
    if liquidity < 35:
        add("blockBuy", "liquidityTooWeak", "warning", liquidity, 35)
    if instrument_type == "etf" and liquidity < 45:
        add("blockBuy", "etfLiquidityWeak", "warning", liquidity, 45)
    if instrument_type != "etf" and metrics.get("quality", 50) < 35 and financial_negatives >= 2:
        add("blockBuy", "financialQualityWeak", "warning", metrics.get("quality", 0), 35)
    return gates


def _has_gate(gates: list[dict[str, Any]], *kinds: str) -> bool:
    return any(gate.get("kind") in kinds for gate in gates)


def _stock_case_scores(
    regime: str,
    metrics: dict[str, float],
    news_analysis: dict[str, Any],
    news_heat: dict[str, Any],
    trend_analysis: dict[str, Any],
    financial_analysis: dict[str, Any],
    opportunity_score: float,
    downside_risk_score: float,
    breakout_setup_score: float,
    pullback_risk_score: float,
) -> dict[str, Any]:
    positive_news, negative_news, net_news = _event_scores(news_analysis)
    continuation = _number(trend_analysis.get("continuationScore"), 50.0) or 50.0
    reversal = _number(trend_analysis.get("reversalRiskScore"), 50.0) or 50.0
    financial_score = _financial_score(financial_analysis)
    heat_impact = _number(news_heat.get("impactScore"), 45.0) or 45.0

    evidence = {
        "quality": metrics.get("quality", 50),
        "value": metrics.get("value", 50),
        "momentum": metrics.get("momentum", 50),
        "risk": metrics.get("risk", 50),
        "financialScore": financial_score,
        "continuation": continuation,
        "breakout": breakout_setup_score,
        "newsImpact": heat_impact,
        "opportunity": opportunity_score,
    }
    if regime == "quality_compounder":
        checks = [
            evidence["quality"] >= 64,
            financial_score >= 58,
            metrics.get("risk", 0) >= 50,
            continuation >= 52,
            downside_risk_score < 62,
            negative_news <= positive_news + 12,
        ]
        buy_score = 48 + sum(checks) * 7 + max(0, opportunity_score - 58) * 0.25
    elif regime == "momentum_breakout":
        checks = [
            breakout_setup_score >= 74,
            continuation >= 58,
            metrics.get("momentum", 0) >= 60,
            pullback_risk_score < 62,
            downside_risk_score < 58,
            heat_impact >= 50 or net_news >= 8,
        ]
        buy_score = 46 + sum(checks) * 7.5 + max(0, breakout_setup_score - 74) * 0.22
    elif regime == "deep_value_turnaround":
        checks = [
            metrics.get("value", 0) >= 62,
            financial_score >= 50,
            metrics.get("quality", 0) >= 56,
            continuation >= 48,
            downside_risk_score < 62,
            reversal < 68,
            net_news >= 8 or heat_impact >= 55 or financial_score >= 66,
            negative_news <= positive_news + 18,
        ]
        buy_score = 41 + sum(checks) * 5.9 + max(0, metrics.get("value", 0) - 62) * 0.18
        if metrics.get("quality", 0) < 56 or (net_news < 8 and heat_impact < 55 and financial_score < 66):
            buy_score = min(buy_score, 66)
    elif regime == "event_driven":
        checks = [
            heat_impact >= 62,
            net_news >= 10,
            positive_news > negative_news,
            metrics.get("risk", 0) >= 45,
            continuation >= 48,
            downside_risk_score < 64,
        ]
        buy_score = 42 + sum(checks) * 7.2 + max(0, heat_impact - 62) * 0.18
    elif regime in {"falling_knife", "overheated", "insufficient_data"}:
        buy_score = 24 if regime == "falling_knife" else 42 if regime == "overheated" else 38
    else:
        checks = [
            opportunity_score >= 64,
            financial_score >= 54,
            metrics.get("risk", 0) >= 48,
            continuation >= 50,
            downside_risk_score < 60,
        ]
        buy_score = 42 + sum(checks) * 5.8

    sell_score = _clamp(
        28
        + max(0, downside_risk_score - 45) * 0.90
        + max(0, reversal - 52) * 0.45
        + max(0, pullback_risk_score - 58) * 0.45
        + max(0, negative_news - positive_news) * 0.34
        + max(0, 48 - metrics.get("risk", 50)) * 0.45
        + max(0, 45 - financial_score) * 0.35
    )
    return {"buyScore": _clamp(buy_score), "sellScore": sell_score, "evidence": evidence}


def _etf_case_scores(
    regime: str,
    metrics: dict[str, float],
    news_analysis: dict[str, Any],
    news_heat: dict[str, Any],
    trend_analysis: dict[str, Any],
    financial_analysis: dict[str, Any],
    opportunity_score: float,
    downside_risk_score: float,
    pullback_risk_score: float,
    t_plan: dict[str, Any],
) -> dict[str, Any]:
    positive_news, negative_news, net_news = _event_scores(news_analysis)
    continuation = _number(trend_analysis.get("continuationScore"), 50.0) or 50.0
    reversal = _number(trend_analysis.get("reversalRiskScore"), 50.0) or 50.0
    financial_score = _financial_score(financial_analysis)
    liquidity = _number(((t_plan.get("components") or {}).get("liquidityScore")), metrics.get("quality", 50)) or 50.0
    heat_impact = _number(news_heat.get("impactScore"), 45.0) or 45.0
    evidence = {
        "risk": metrics.get("risk", 50),
        "trend": continuation,
        "drawdown": 100 - downside_risk_score,
        "liquidity": liquidity,
        "fundProfile": financial_score,
        "newsImpact": heat_impact,
        "opportunity": opportunity_score,
    }
    if regime == "defensive_etf_core":
        checks = [
            metrics.get("risk", 0) >= 58,
            financial_score >= 62,
            liquidity >= 50,
            continuation >= 50,
            downside_risk_score < 60,
            pullback_risk_score < 68,
        ]
        buy_score = 50 + sum(checks) * 6.4 + max(0, opportunity_score - 58) * 0.18
    elif regime == "sector_etf_tactical":
        checks = [
            continuation >= 55,
            opportunity_score >= 62,
            liquidity >= 45,
            downside_risk_score < 62,
            net_news >= -8,
            heat_impact >= 45,
        ]
        buy_score = 43 + sum(checks) * 6.5
    elif regime in {"falling_knife", "overheated", "insufficient_data"}:
        buy_score = 26 if regime == "falling_knife" else 42 if regime == "overheated" else 36
    else:
        buy_score = 42 + max(0, opportunity_score - downside_risk_score) * 0.32 + max(0, liquidity - 45) * 0.22

    sell_score = _clamp(
        25
        + max(0, downside_risk_score - 45) * 0.85
        + max(0, reversal - 55) * 0.42
        + max(0, pullback_risk_score - 62) * 0.38
        + max(0, 45 - liquidity) * 0.70
        + max(0, negative_news - positive_news) * 0.26
    )
    return {"buyScore": _clamp(buy_score), "sellScore": sell_score, "evidence": evidence}


def build_decision_engine(
    *,
    instrument_type: str,
    market: str,
    price: float,
    change: float | None,
    closes: list[float],
    info: dict[str, Any],
    metrics: dict[str, float],
    legacy_score: float,
    availability: dict[str, bool] | None,
    news_analysis: dict[str, Any],
    news_heat: dict[str, Any],
    trend_analysis: dict[str, Any],
    financial_analysis: dict[str, Any],
    t_plan: dict[str, Any],
    opportunity_score: float,
    downside_risk_score: float,
    breakout_setup_score: float,
    pullback_risk_score: float,
) -> dict[str, Any]:
    data_quality = data_quality_profile(
        instrument_type=instrument_type,
        closes=closes,
        info=info,
        news_analysis=news_analysis,
        news_heat=news_heat,
        financial_analysis=financial_analysis,
        availability=availability,
    )
    regime = classify_regime(
        instrument_type=instrument_type,
        metrics=metrics,
        data_quality=data_quality,
        news_analysis=news_analysis,
        news_heat=news_heat,
        trend_analysis=trend_analysis,
        financial_analysis=financial_analysis,
        opportunity_score=opportunity_score,
        downside_risk_score=downside_risk_score,
        breakout_setup_score=breakout_setup_score,
        pullback_risk_score=pullback_risk_score,
        price_change=change,
    )
    gates = risk_gates(
        instrument_type=instrument_type,
        metrics=metrics,
        data_quality=data_quality,
        news_analysis=news_analysis,
        trend_analysis=trend_analysis,
        financial_analysis=financial_analysis,
        t_plan=t_plan,
        downside_risk_score=downside_risk_score,
        pullback_risk_score=pullback_risk_score,
        price_change=change,
    )
    if instrument_type == "etf":
        case = _etf_case_scores(
            regime["name"],
            metrics,
            news_analysis,
            news_heat,
            trend_analysis,
            financial_analysis,
            opportunity_score,
            downside_risk_score,
            pullback_risk_score,
            t_plan,
        )
    else:
        case = _stock_case_scores(
            regime["name"],
            metrics,
            news_analysis,
            news_heat,
            trend_analysis,
            financial_analysis,
            opportunity_score,
            downside_risk_score,
            breakout_setup_score,
            pullback_risk_score,
        )

    buy_score = case["buyScore"]
    sell_score = case["sellScore"]
    if _has_gate(gates, "exitCandidate"):
        buy_score = min(buy_score, 30.0)
        sell_score = max(sell_score, 82.0)
    elif _has_gate(gates, "forceReduce"):
        buy_score = min(buy_score, 50.0)
        sell_score = max(sell_score, 64.0)
    elif _has_gate(gates, "blockBuy"):
        buy_score = min(buy_score, 60.0)

    risk_reward = _clamp(buy_score - sell_score + 50)
    rank_score = _clamp(buy_score * 0.62 + risk_reward * 0.26 + data_quality["score"] * 0.12)
    confidence = _clamp(data_quality["score"] * 0.50 + regime["confidence"] * 0.30 + abs(buy_score - sell_score) * 0.20)

    if sell_score >= 78:
        action = "exit"
        verdict = "sell"
    elif sell_score >= 62:
        action = "reduce"
        verdict = "watch"
    elif buy_score >= 72 and sell_score <= 50 and data_quality["score"] >= 45 and not _has_gate(gates, "blockBuy", "forceReduce", "exitCandidate"):
        action = "accumulate"
        verdict = "buy"
    else:
        action = "hold"
        verdict = "watch"

    primary_reasons = [gate["key"] for gate in gates[:4]]
    if not primary_reasons:
        primary_reasons = [
            f"regime:{regime['name']}",
            f"dataQuality:{data_quality['level']}",
            "legacyWeights:secondary",
        ]

    return {
        "version": "scenario-v1",
        "instrumentType": instrument_type,
        "market": market,
        "price": price,
        "regime": regime,
        "dataQuality": data_quality,
        "gates": gates,
        "caseEvidence": {key: round(value, 1) for key, value in case["evidence"].items()},
        "buyScore": round(buy_score, 1),
        "sellScore": round(sell_score, 1),
        "holdScore": round(_clamp(100 - abs(buy_score - sell_score) * 0.52 - max(0, sell_score - 62) * 0.42), 1),
        "rankScore": round(rank_score, 1),
        "riskRewardScore": round(risk_reward, 1),
        "confidenceScore": round(confidence, 1),
        "action": action,
        "verdict": verdict,
        "primaryReasons": primary_reasons,
        "legacyScore": round(legacy_score, 1),
        "legacyWeightRole": "secondary",
    }
