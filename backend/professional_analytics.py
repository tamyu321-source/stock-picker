from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from statistics import mean
from typing import Any


MARKET_BENCHMARKS = {
    "US": {"symbol": "SPY", "name": "S&P 500 ETF", "baselineReturnPct": 0.35},
    "CN": {"symbol": "510300.SS", "name": "CSI 300 ETF", "baselineReturnPct": 0.15},
    "HK": {"symbol": "2800.HK", "name": "Tracker Fund of Hong Kong", "baselineReturnPct": 0.10},
    "TW": {"symbol": "0050.TW", "name": "Taiwan 50 ETF", "baselineReturnPct": 0.25},
    "JP": {"symbol": "1321.T", "name": "Nikkei 225 ETF", "baselineReturnPct": 0.15},
    "KR": {"symbol": "069500.KS", "name": "KODEX 200 ETF", "baselineReturnPct": 0.12},
    "SG": {"symbol": "ES3.SI", "name": "Straits Times Index ETF", "baselineReturnPct": 0.08},
}


def _number(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, "", "-"):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _pct_change(closes: list[float], periods: int) -> float:
    values = [float(value) for value in closes if _number(value) is not None]
    if len(values) <= periods or values[-periods - 1] == 0:
        return 0.0
    return (values[-1] / values[-periods - 1] - 1) * 100


def _volatility_score(closes: list[float]) -> float:
    values = [float(value) for value in closes[-31:] if _number(value) is not None]
    if len(values) < 5:
        return 50.0
    returns = [(values[index] / values[index - 1] - 1) * 100 for index in range(1, len(values)) if values[index - 1]]
    if not returns:
        return 50.0
    avg = mean(returns)
    variance = mean((item - avg) ** 2 for item in returns)
    return _clamp((variance ** 0.5) * 18)


def _market_cap_score(info: dict[str, Any]) -> float:
    market_cap = _number(info.get("marketCap")) or _number(info.get("totalAssets"))
    if not market_cap or market_cap <= 0:
        return 50.0
    if market_cap >= 200_000_000_000:
        return 88.0
    if market_cap >= 50_000_000_000:
        return 76.0
    if market_cap >= 10_000_000_000:
        return 62.0
    if market_cap >= 2_000_000_000:
        return 48.0
    return 34.0


def _tone(score: float, inverse: bool = False) -> str:
    value = 100 - score if inverse else score
    if value >= 68:
        return "positive"
    if value <= 42:
        return "negative"
    return "neutral"


def build_factor_model(snapshot: Any, metrics: dict[str, float], decision_engine: dict[str, Any], financial_analysis: dict[str, Any]) -> dict[str, Any]:
    closes = list(getattr(snapshot, "closes", []) or [])
    info = dict(getattr(snapshot, "info", {}) or {})
    evidence = decision_engine.get("caseEvidence") or {}
    volatility = _volatility_score(closes)
    exposures = [
        {"key": "marketBeta", "label": "Market beta", "score": round(_clamp(45 + volatility * 0.35 + max(0, abs(_pct_change(closes, 20)) - 4) * 1.8), 1), "tone": "risk"},
        {"key": "momentum", "label": "Momentum", "score": round(_clamp(metrics.get("momentum", 50)), 1), "tone": _tone(metrics.get("momentum", 50))},
        {"key": "quality", "label": "Quality", "score": round(_clamp(metrics.get("quality", 50)), 1), "tone": _tone(metrics.get("quality", 50))},
        {"key": "value", "label": "Value", "score": round(_clamp(metrics.get("value", 50)), 1), "tone": _tone(metrics.get("value", 50))},
        {"key": "volatility", "label": "Volatility risk", "score": round(volatility, 1), "tone": _tone(volatility, inverse=True)},
        {"key": "liquidity", "label": "Liquidity", "score": round(_clamp(evidence.get("liquidity", metrics.get("quality", 50))), 1), "tone": _tone(evidence.get("liquidity", metrics.get("quality", 50)))},
        {"key": "size", "label": "Size / assets", "score": round(_market_cap_score(info), 1), "tone": "neutral"},
        {"key": "eventRisk", "label": "Event risk", "score": round(_clamp(max(0, decision_engine.get("sellScore", 0) - 35) * 1.2), 1), "tone": _tone(_clamp(max(0, decision_engine.get("sellScore", 0) - 35) * 1.2), inverse=True)},
    ]
    dominant = sorted(exposures, key=lambda item: abs(float(item["score"]) - 50), reverse=True)[:3]
    return {
        "version": "professional-factor-v1",
        "style": "ETF factor profile" if decision_engine.get("instrumentType") == "etf" else "Equity factor profile",
        "exposures": exposures,
        "dominantExposures": [item["key"] for item in dominant],
        "coverageScore": round(_clamp((decision_engine.get("dataQuality") or {}).get("factorCoverageScore", 65)), 1),
        "financialScore": round(mean([_number(metric.get("score"), 50.0) or 50.0 for metric in financial_analysis.get("metrics", [])]) if financial_analysis.get("metrics") else 50.0, 1),
    }


def build_benchmark_relative_score(snapshot: Any, decision_engine: dict[str, Any], factor_model: dict[str, Any]) -> dict[str, Any]:
    market = str(getattr(snapshot, "market", "") or decision_engine.get("market") or "US").upper()
    benchmark = MARKET_BENCHMARKS.get(market, {"symbol": "SPY", "name": "Global equity proxy", "baselineReturnPct": 0.20})
    closes = list(getattr(snapshot, "closes", []) or [])
    short_return = _pct_change(closes, 5)
    mid_return = _pct_change(closes, 20)
    long_return = _pct_change(closes, 60)
    baseline = float(benchmark["baselineReturnPct"])
    relative_short = short_return - baseline
    relative_mid = mid_return - baseline * 4
    relative_long = long_return - baseline * 12
    risk_penalty = max(0.0, float(decision_engine.get("sellScore") or 0) - 55) * 0.32
    factor_bonus = mean([float(item.get("score") or 50) for item in factor_model.get("exposures", [])[:4]]) - 50
    score = _clamp(50 + relative_short * 1.8 + relative_mid * 0.9 + relative_long * 0.35 + factor_bonus * 0.45 - risk_penalty)
    if score >= 70:
        rank = "outperforming"
    elif score <= 40:
        rank = "lagging"
    else:
        rank = "in-line"
    return {
        "benchmark": {"market": market, **benchmark},
        "relativeScore": round(score, 1),
        "rank": rank,
        "returns": {
            "shortTermPct": round(short_return, 2),
            "midTermPct": round(mid_return, 2),
            "longTermPct": round(long_return, 2),
            "relativeShortPct": round(relative_short, 2),
            "relativeMidPct": round(relative_mid, 2),
            "relativeLongPct": round(relative_long, 2),
        },
        "peerPercentileEstimate": round(_clamp(score), 1),
    }


def build_recommendation_tracker(snapshot: Any, decision_engine: dict[str, Any], benchmark_relative: dict[str, Any]) -> dict[str, Any]:
    symbol = str(getattr(snapshot, "symbol", "") or "")
    price = _number(getattr(snapshot, "price", None), 0.0) or 0.0
    action = str(decision_engine.get("action") or "hold")
    sell_score = float(decision_engine.get("sellScore") or 0)
    rank_score = float(decision_engine.get("rankScore") or 0)
    edge = max(-20.0, min(22.0, (rank_score - sell_score) * 0.10 + (float(benchmark_relative.get("relativeScore") or 50) - 50) * 0.08))
    tracking_id = hashlib.sha1(f"{symbol}|{price:.4f}|{action}|{rank_score:.1f}".encode("utf-8")).hexdigest()[:12]
    checkpoint_base = max(1.0, abs(edge))
    return {
        "trackingId": tracking_id,
        "status": "new",
        "openedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entryPrice": round(price, 4),
        "action": action,
        "expectedEdgePct": round(edge, 2),
        "checkpoints": [
            {"horizon": "1D", "targetReturnPct": round(edge * 0.22, 2), "maxDrawdownPct": round(-checkpoint_base * 0.45, 2)},
            {"horizon": "5D", "targetReturnPct": round(edge * 0.58, 2), "maxDrawdownPct": round(-checkpoint_base * 0.82, 2)},
            {"horizon": "20D", "targetReturnPct": round(edge * 1.18, 2), "maxDrawdownPct": round(-checkpoint_base * 1.35, 2)},
        ],
        "reviewTriggers": ["price-target-hit", "stop-loss-hit", "decision-action-changed", "benchmark-rank-deteriorated"],
    }


def build_attribution_engine(decision_engine: dict[str, Any], factor_model: dict[str, Any], benchmark_relative: dict[str, Any]) -> dict[str, Any]:
    evidence = decision_engine.get("caseEvidence") or {}
    rows = [
        {"key": "scenario", "label": "Scenario fit", "contribution": round((float(decision_engine.get("buyScore") or 0) - 50) * 0.32, 2)},
        {"key": "risk", "label": "Risk control", "contribution": round((50 - float(decision_engine.get("sellScore") or 0)) * 0.28, 2)},
        {"key": "benchmark", "label": "Benchmark relative", "contribution": round((float(benchmark_relative.get("relativeScore") or 50) - 50) * 0.24, 2)},
        {"key": "dataQuality", "label": "Data quality", "contribution": round((float((decision_engine.get("dataQuality") or {}).get("score") or 50) - 50) * 0.18, 2)},
        {"key": "financial", "label": "Financial/fund profile", "contribution": round((float(evidence.get("financialScore") or evidence.get("fundProfile") or 50) - 50) * 0.20, 2)},
    ]
    support = [row for row in rows if row["contribution"] > 1.0]
    drag = [row for row in rows if row["contribution"] < -1.0]
    net = sum(float(row["contribution"]) for row in rows)
    return {
        "version": "attribution-v1",
        "netContribution": round(net, 2),
        "drivers": sorted(rows, key=lambda item: abs(float(item["contribution"])), reverse=True),
        "supportDrivers": support[:3],
        "dragDrivers": drag[:3],
        "factorDrivers": factor_model.get("dominantExposures", []),
    }


def build_alert_monitor(decision_engine: dict[str, Any], benchmark_relative: dict[str, Any], tracker: dict[str, Any]) -> dict[str, Any]:
    rules = []
    action = decision_engine.get("action")
    if action == "accumulate":
        rules.append({"key": "accumulate-confirmed", "severity": "info", "condition": "buy score remains above 72 and sell score below 50"})
    if action in {"reduce", "exit"}:
        rules.append({"key": "risk-action-active", "severity": "danger" if action == "exit" else "warning", "condition": f"decision action is {action}"})
    if float(benchmark_relative.get("relativeScore") or 50) < 42:
        rules.append({"key": "benchmark-lagging", "severity": "warning", "condition": "relative score falls below 42"})
    for gate in decision_engine.get("gates") or []:
        if gate.get("severity") in {"warning", "danger"}:
            rules.append({"key": gate.get("key"), "severity": gate.get("severity"), "condition": gate.get("kind")})
    rules.append({"key": "scheduled-review", "severity": "info", "condition": "review 1D, 5D, and 20D checkpoints"})
    priority = "high" if any(rule["severity"] == "danger" for rule in rules) else "medium" if any(rule["severity"] == "warning" for rule in rules) else "normal"
    return {
        "priority": priority,
        "rules": rules[:6],
        "nextReview": (tracker.get("checkpoints") or [{}])[0].get("horizon", "1D"),
    }


def build_portfolio_optimizer(pick: dict[str, Any], position: dict[str, Any] | None = None, total_market_value: float | None = None) -> dict[str, Any]:
    engine = pick.get("decisionEngine") or {}
    instrument = pick.get("instrumentType") or engine.get("instrumentType") or "stock"
    action = (pick.get("finalDecision") or {}).get("action") or engine.get("action") or (pick.get("compositeModel") or {}).get("decision") or "hold"
    max_weight = 22.0 if instrument == "etf" else 15.0
    base_target = 0.0 if action == "exit" else max_weight * 0.42 if action == "reduce" else max_weight * 0.72 if action == "accumulate" else max_weight * 0.48
    current_value = _number((position or {}).get("marketValue"), 0.0) or 0.0
    current_weight = current_value / total_market_value * 100 if total_market_value else None
    target_weight = min(max_weight, max(0.0, base_target))
    if current_weight is not None and action == "hold":
        target_weight = min(max_weight, current_weight)
    marginal_risk = _clamp(float(engine.get("sellScore") or 0) * 0.58 + max(0, (current_weight or 0) - target_weight) * 1.4)
    suggested_change = None if current_weight is None else round(target_weight - current_weight, 1)
    return {
        "version": "portfolio-optimizer-v1",
        "targetWeightPct": round(target_weight, 1),
        "currentWeightPct": round(current_weight, 1) if current_weight is not None else None,
        "suggestedChangePct": suggested_change,
        "maxWeightPct": max_weight,
        "marginalRiskScore": round(marginal_risk, 1),
        "concentrationAction": "trim" if suggested_change is not None and suggested_change < -2 else "add" if suggested_change is not None and suggested_change > 2 else "hold",
        "overlapTags": [str(pick.get("market") or ""), str(pick.get("sector") or ""), str(instrument)],
    }


def build_professional_analytics(snapshot: Any, metrics: dict[str, float], decision_engine: dict[str, Any], financial_analysis: dict[str, Any]) -> dict[str, Any]:
    factor_model = build_factor_model(snapshot, metrics, decision_engine, financial_analysis)
    benchmark_relative = build_benchmark_relative_score(snapshot, decision_engine, factor_model)
    tracker = build_recommendation_tracker(snapshot, decision_engine, benchmark_relative)
    attribution = build_attribution_engine(decision_engine, factor_model, benchmark_relative)
    alerts = build_alert_monitor(decision_engine, benchmark_relative, tracker)
    return {
        "factorModel": factor_model,
        "benchmarkRelative": benchmark_relative,
        "recommendationTracker": tracker,
        "attribution": attribution,
        "portfolioOptimizer": None,
        "alertMonitor": alerts,
    }
