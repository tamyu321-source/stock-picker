from __future__ import annotations

from datetime import datetime, time, timezone
from statistics import mean
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - Python always ships zoneinfo in supported runtimes.
    ZoneInfo = None


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

HIGH_BETA_ETF_SYMBOLS = {
    "159915.SZ",
    "588000.SS",
    "512100.SS",
    "512880.SS",
    "159995.SZ",
    "159949.SZ",
    "159605.SZ",
    "3033.HK",
    "3088.HK",
    "QQQ",
    "IWM",
    "XLK",
    "XBI",
    "ARKK",
    "229200.KS",
    "305720.KS",
}

CORE_ETF_SYMBOLS = {
    "SPY",
    "VOO",
    "IVV",
    "VTI",
    "510300.SS",
    "159919.SZ",
    "2828.HK",
    "3067.HK",
    "0050.TW",
    "006208.TW",
    "1306.T",
    "1321.T",
    "069500.KS",
    "102110.KS",
    "ES3.SI",
}

DEFENSIVE_ETF_SYMBOLS = {
    "SCHD",
    "TLT",
    "GLD",
    "0056.TW",
    "00878.TW",
    "00713.TW",
    "A35.SI",
    "MBH.SI",
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


def _source_warnings(info: dict[str, Any]) -> list[str]:
    raw = info.get("sourceWarnings") or info.get("dataWarnings") or []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return []


def _source_penalty(info: dict[str, Any]) -> float:
    warnings = _source_warnings(info)
    penalty = min(18.0, len(warnings) * 5.5)
    if info.get("primarySourceFailed"):
        penalty += 6.0
    if info.get("stalePriceData"):
        penalty += 8.0
    return _clamp(penalty, 0, 28)


def _parse_analysis_time(info: dict[str, Any]) -> datetime:
    value = info.get("analysisTimeUtc")
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _local_time(market: str, now_utc: datetime) -> datetime:
    zone_name = {
        "CN": "Asia/Shanghai",
        "TW": "Asia/Taipei",
        "HK": "Asia/Hong_Kong",
        "JP": "Asia/Tokyo",
        "KR": "Asia/Seoul",
        "SG": "Asia/Singapore",
        "US": "America/New_York",
    }.get(str(market).upper(), "UTC")
    if ZoneInfo is None:
        return now_utc
    return now_utc.astimezone(ZoneInfo(zone_name))


def _between(value: time, start: time, end: time) -> bool:
    return start <= value <= end


MARKET_RULE_SOURCES = {
    "TW": ["TWSE Trading", "TWSE Service"],
    "CN": ["SSE Trading Mechanism", "SZSE Trading Overview"],
    "HK": ["HKEX Securities Market"],
    "US": ["US exchange regular session"],
    "JP": ["Japan exchange regular session"],
    "KR": ["Korea exchange regular session"],
    "SG": ["Singapore exchange regular session"],
}


MARKET_RULES: dict[str, dict[str, Any]] = {
    "TW": {
        "ruleDepth": "deep",
        "timezone": "Asia/Taipei",
        "currency": "TWD",
        "sessionWindows": [{"label": "regular", "start": "09:00", "end": "13:30"}],
        "openingConfirmationMinutes": 10,
        "settlement": "T+2",
        "sellRule": "cash-market",
        "priceLimitPct": 10,
        "enforcesBuySessionGate": True,
        "nonRealtimeBuyPolicy": "watchlist",
        "orderSizing": {
            "boardLotSize": 1000,
            "buyLotSize": 1000,
            "sellLotSize": 1000,
            "minBuyQuantity": 1,
            "allowsOddLotBuy": True,
            "allowsOddLotSell": True,
            "oddLotPolicy": "separate_odd_lot_market",
            "normalization": "odd_lot_allowed",
            "source": "TWSE round lot plus odd lot trading",
        },
    },
    "CN": {
        "ruleDepth": "deep",
        "timezone": "Asia/Shanghai",
        "currency": "CNY",
        "sessionWindows": [
            {"label": "morning", "start": "09:30", "end": "11:30"},
            {"label": "afternoon", "start": "13:00", "end": "15:00"},
        ],
        "lunchBreak": {"start": "11:30", "end": "13:00"},
        "openingConfirmationMinutes": 15,
        "settlement": "T+1",
        "sellRule": "T+1",
        "priceLimitPct": 10,
        "enforcesBuySessionGate": True,
        "nonRealtimeBuyPolicy": "watchlist",
        "orderSizing": {
            "boardLotSize": 100,
            "buyLotSize": 100,
            "sellLotSize": 100,
            "minBuyQuantity": 100,
            "allowsOddLotBuy": False,
            "allowsOddLotSell": True,
            "oddLotPolicy": "sell_remaining_odd_lot_once",
            "normalization": "round_lot_except_full_exit",
            "maxOrderQuantity": 1_000_000,
            "source": "SSE/SZSE A-share board lot",
        },
    },
    "HK": {
        "ruleDepth": "basic",
        "timezone": "Asia/Hong_Kong",
        "currency": "HKD",
        "sessionWindows": [
            {"label": "morning", "start": "09:30", "end": "12:00"},
            {"label": "afternoon", "start": "13:00", "end": "16:00"},
        ],
        "lunchBreak": {"start": "12:00", "end": "13:00"},
        "openingConfirmationMinutes": 0,
        "settlement": "T+2",
        "sellRule": "market-specific",
        "priceLimitPct": None,
        "enforcesBuySessionGate": False,
        "nonRealtimeBuyPolicy": "downgrade",
        "orderSizing": {
            "boardLotSize": None,
            "buyLotSize": None,
            "sellLotSize": None,
            "minBuyQuantity": None,
            "allowsOddLotBuy": True,
            "allowsOddLotSell": True,
            "oddLotPolicy": "issuer_board_lot_and_odd_lot_market",
            "normalization": "advisory_only",
            "source": "HKEX issuer-defined board lot",
        },
    },
    "US": {
        "ruleDepth": "basic",
        "timezone": "America/New_York",
        "currency": "USD",
        "sessionWindows": [{"label": "regular", "start": "09:30", "end": "16:00"}],
        "openingConfirmationMinutes": 0,
        "settlement": "T+1",
        "sellRule": "market-specific",
        "priceLimitPct": None,
        "enforcesBuySessionGate": False,
        "nonRealtimeBuyPolicy": "downgrade",
        "orderSizing": {
            "boardLotSize": 1,
            "buyLotSize": 1,
            "sellLotSize": 1,
            "minBuyQuantity": 1,
            "allowsOddLotBuy": True,
            "allowsOddLotSell": True,
            "oddLotPolicy": "odd_lot_supported",
            "normalization": "share_level",
            "source": "US share-level odd lot orders",
        },
    },
    "JP": {
        "ruleDepth": "basic",
        "timezone": "Asia/Tokyo",
        "currency": "JPY",
        "sessionWindows": [
            {"label": "morning", "start": "09:00", "end": "11:30"},
            {"label": "afternoon", "start": "12:30", "end": "15:30"},
        ],
        "lunchBreak": {"start": "11:30", "end": "12:30"},
        "openingConfirmationMinutes": 0,
        "settlement": "T+2",
        "sellRule": "market-specific",
        "priceLimitPct": None,
        "enforcesBuySessionGate": False,
        "nonRealtimeBuyPolicy": "downgrade",
        "orderSizing": {
            "boardLotSize": 100,
            "buyLotSize": 100,
            "sellLotSize": 100,
            "minBuyQuantity": 100,
            "allowsOddLotBuy": False,
            "allowsOddLotSell": False,
            "oddLotPolicy": "unit_share_services_outside_regular_lot",
            "normalization": "round_lot_except_full_exit",
            "source": "JPX 100-share trading unit",
        },
    },
    "KR": {
        "ruleDepth": "basic",
        "timezone": "Asia/Seoul",
        "currency": "KRW",
        "sessionWindows": [{"label": "regular", "start": "09:00", "end": "15:30"}],
        "openingConfirmationMinutes": 0,
        "settlement": "T+2",
        "sellRule": "market-specific",
        "priceLimitPct": 30,
        "enforcesBuySessionGate": False,
        "nonRealtimeBuyPolicy": "downgrade",
        "orderSizing": {
            "boardLotSize": 1,
            "buyLotSize": 1,
            "sellLotSize": 1,
            "minBuyQuantity": 1,
            "allowsOddLotBuy": True,
            "allowsOddLotSell": True,
            "oddLotPolicy": "share_level",
            "normalization": "share_level",
            "source": "KRX share-level trading unit",
        },
    },
    "SG": {
        "ruleDepth": "basic",
        "timezone": "Asia/Singapore",
        "currency": "SGD",
        "sessionWindows": [{"label": "regular", "start": "09:00", "end": "17:00"}],
        "openingConfirmationMinutes": 0,
        "settlement": "T+2",
        "sellRule": "market-specific",
        "priceLimitPct": None,
        "enforcesBuySessionGate": False,
        "nonRealtimeBuyPolicy": "downgrade",
        "orderSizing": {
            "boardLotSize": 100,
            "buyLotSize": 100,
            "sellLotSize": 100,
            "minBuyQuantity": 100,
            "allowsOddLotBuy": True,
            "allowsOddLotSell": True,
            "oddLotPolicy": "unit_share_market_for_odd_lots",
            "normalization": "odd_lot_allowed",
            "source": "SGX standard board lot plus unit share market",
        },
    },
}


def _parse_clock(value: str) -> time:
    hour, minute = [int(part) for part in str(value).split(":", 1)]
    return time(hour, minute)


def _minutes_after(start: time, minutes: int) -> time:
    total = start.hour * 60 + start.minute + max(0, int(minutes or 0))
    return time((total // 60) % 24, total % 60)


def market_rule_profile(market: str, instrument_type: str = "stock") -> dict[str, Any]:
    market = str(market or "").upper()
    base = dict(MARKET_RULES.get(market) or {})
    if not base:
        base = {
            "ruleDepth": "basic",
            "timezone": "UTC",
            "currency": "",
            "sessionWindows": [],
            "openingConfirmationMinutes": 0,
            "settlement": "market-specific",
            "sellRule": "market-specific",
            "priceLimitPct": None,
            "enforcesBuySessionGate": False,
            "nonRealtimeBuyPolicy": "downgrade",
            "orderSizing": {
                "boardLotSize": 1,
                "buyLotSize": 1,
                "sellLotSize": 1,
                "minBuyQuantity": 1,
                "allowsOddLotBuy": True,
                "allowsOddLotSell": True,
                "oddLotPolicy": "unknown_share_level",
                "normalization": "share_level",
                "source": "default",
            },
        }
    is_etf = str(instrument_type or "stock").lower() == "etf"
    return {
        "version": "market-rule-v1",
        "market": market,
        "ruleDepth": base["ruleDepth"],
        "timezone": base["timezone"],
        "currency": base["currency"],
        "sessionWindows": list(base.get("sessionWindows") or []),
        "lunchBreak": base.get("lunchBreak"),
        "openingConfirmationMinutes": base.get("openingConfirmationMinutes", 0),
        "settlement": base.get("settlement"),
        "sellRule": base.get("sellRule"),
        "priceLimitPct": base.get("priceLimitPct"),
        "enforcesBuySessionGate": bool(base.get("enforcesBuySessionGate")),
        "nonRealtimeBuyPolicy": base.get("nonRealtimeBuyPolicy", "downgrade"),
        "orderSizing": dict(base.get("orderSizing") or {}),
        "etfRiskPolicy": "high-volatility-gates" if is_etf and market in {"CN", "TW"} else "basic-etf-liquidity-check" if is_etf else "not-etf",
        "sources": MARKET_RULE_SOURCES.get(market, []),
    }


def market_session_profile(market: str, info: dict[str, Any]) -> dict[str, Any]:
    market = str(market or "").upper()
    source = str(info.get("priceSource") or info.get("quoteSource") or "").strip()
    profile = market_rule_profile(market, str(info.get("instrumentType") or "stock"))
    if info.get("marketSessionOverride"):
        override = str(info.get("marketSessionOverride"))
        return {
            "market": market,
            "state": override,
            "priceSource": source,
            "gated": bool(profile.get("enforcesBuySessionGate")),
            "regularSession": override == "regular",
            "openConfirmed": override == "regular",
            "allowNewBuy": override == "regular" or not profile.get("enforcesBuySessionGate"),
            "rawAllowNewBuy": override == "regular",
            "ruleDepth": profile["ruleDepth"],
            "timezone": profile["timezone"],
            "reason": "override",
        }
    if profile.get("enforcesBuySessionGate") and not source and not info.get("analysisTime"):
        return {
            "market": market,
            "state": "unknown",
            "priceSource": source,
            "gated": False,
            "regularSession": True,
            "openConfirmed": True,
            "allowNewBuy": True,
            "rawAllowNewBuy": True,
            "ruleDepth": profile["ruleDepth"],
            "timezone": profile["timezone"],
            "reason": "missing-session-source",
        }
    if not profile.get("sessionWindows"):
        return {
            "market": market,
            "state": "unknown",
            "priceSource": source,
            "gated": False,
            "regularSession": True,
            "openConfirmed": True,
            "allowNewBuy": True,
            "rawAllowNewBuy": True,
            "ruleDepth": profile["ruleDepth"],
            "timezone": profile["timezone"],
            "reason": "unknown-market-rules",
        }

    now_local = _local_time(market, _parse_analysis_time(info))
    clock = now_local.time()
    weekday = now_local.weekday()
    if weekday >= 5:
        state = "closed"
        regular = False
        confirmed = False
    else:
        matched_window = None
        for window in profile.get("sessionWindows") or []:
            start = _parse_clock(window["start"])
            end = _parse_clock(window["end"])
            if _between(clock, start, end):
                matched_window = window
                break
        regular = matched_window is not None
        confirmed = False
        if regular and matched_window:
            start = _parse_clock(matched_window["start"])
            confirm_at = _minutes_after(start, int(profile.get("openingConfirmationMinutes") or 0))
            confirmed = clock >= confirm_at
        lunch = profile.get("lunchBreak") or {}
        in_lunch = bool(lunch) and _between(clock, _parse_clock(lunch["start"]), _parse_clock(lunch["end"]))
        state = "regular" if confirmed else "opening_confirmation" if regular else "lunch_break" if in_lunch else "closed"

    raw_allow_new_buy = regular and confirmed
    gated = bool(profile.get("enforcesBuySessionGate"))

    return {
        "market": market,
        "state": state,
        "priceSource": source,
        "gated": gated,
        "regularSession": regular,
        "openConfirmed": confirmed,
        "allowNewBuy": raw_allow_new_buy if gated else True,
        "rawAllowNewBuy": raw_allow_new_buy,
        "localTime": now_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "ruleDepth": profile["ruleDepth"],
        "timezone": profile["timezone"],
        "reason": "confirmed-live-session" if regular and confirmed else "wait-for-open-confirmation" if regular else "lunch-break" if state == "lunch_break" else "outside-live-session",
    }


def market_rule_state(market: str, info: dict[str, Any], instrument_type: str = "stock") -> dict[str, Any]:
    enriched_info = {**(info or {}), "instrumentType": instrument_type}
    profile = market_rule_profile(market, instrument_type)
    session = market_session_profile(market, enriched_info)
    source = str(enriched_info.get("priceSource") or enriched_info.get("quoteSource") or "").strip()
    warnings = enriched_info.get("sourceWarnings") if isinstance(enriched_info.get("sourceWarnings"), list) else []
    if session.get("state") in {"regular", "opening_confirmation"} and source and not warnings:
        data_freshness = "realtime"
    elif source or warnings:
        data_freshness = "delayed_or_fallback"
    else:
        data_freshness = "unknown"
    return {
        "version": "market-rule-state-v1",
        "profile": profile,
        "market": profile["market"],
        "ruleDepth": profile["ruleDepth"],
        "status": session.get("state"),
        "trading": bool(session.get("regularSession")),
        "openConfirmed": bool(session.get("openConfirmed")),
        "allowNewBuy": bool(session.get("rawAllowNewBuy")),
        "enforcedBuyGate": bool(session.get("gated")),
        "reason": session.get("reason"),
        "localTime": session.get("localTime"),
        "dataFreshness": data_freshness,
        "priceSource": source,
        "settlement": profile.get("settlement"),
        "sellRule": profile.get("sellRule"),
        "priceLimitPct": profile.get("priceLimitPct"),
        "orderSizing": profile.get("orderSizing"),
    }


def etf_risk_profile(market: str, info: dict[str, Any]) -> dict[str, Any]:
    symbol = str(info.get("symbol") or info.get("underlyingSymbol") or "").upper()
    text = " ".join(
        str(info.get(key) or "")
        for key in ["shortName", "longName", "category", "fundFamily", "quoteType", "instrumentType"]
    ).lower()
    high_beta_terms = ["创业", "創業", "chinext", "科创", "科創", "star", "nasdaq", "technology", "semiconductor", "battery", "biotech", "kosdaq", "1000", "growth"]
    defensive_terms = ["dividend", "high dividend", "bond", "treasury", "gold", "low volatility", "低波", "高息", "債", "bond"]

    if symbol in HIGH_BETA_ETF_SYMBOLS or any(term in text for term in high_beta_terms):
        category = "high_beta_tactical"
        risk_tier = "high"
        block_buy_drop = -2.0
        force_reduce_drop = -3.2
    elif symbol in DEFENSIVE_ETF_SYMBOLS or any(term in text for term in defensive_terms):
        category = "defensive_income"
        risk_tier = "defensive"
        block_buy_drop = -3.2
        force_reduce_drop = -4.8
    elif symbol in CORE_ETF_SYMBOLS:
        category = "broad_core"
        risk_tier = "core"
        block_buy_drop = -2.6
        force_reduce_drop = -4.0
    else:
        category = "sector_tactical"
        risk_tier = "medium_high"
        block_buy_drop = -2.4
        force_reduce_drop = -3.8

    return {
        "instrumentType": "etf",
        "category": category,
        "riskTier": risk_tier,
        "highBeta": risk_tier == "high",
        "blockBuyDropPct": block_buy_drop,
        "forceReduceDropPct": force_reduce_drop,
        "maxWeightPct": 18 if risk_tier == "high" else 22 if risk_tier == "core" else 16,
        "market": str(market or "").upper(),
    }


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


def _market_support_profile(market_profile: dict[str, Any] | None) -> dict[str, Any]:
    profile = market_profile or {}
    capabilities = profile.get("capabilities") or {}
    capability_values = list(capabilities.values())
    capability_score = _clamp(sum(1 for value in capability_values if value) / max(1, len(capability_values)) * 100)
    reliability = _number(profile.get("sourceReliabilityScore"), 58.0) or 58.0
    official_bonus = 5.0 if capabilities.get("officialExchange") else 0.0
    local_bonus = 4.0 if profile.get("localPriority") else 0.0
    score = _clamp(reliability * 0.64 + capability_score * 0.28 + official_bonus + local_bonus)
    sources = []
    for source in profile.get("primarySources") or []:
        label = source.get("label")
        if label:
            sources.append(label)
    return {
        "market": profile.get("market"),
        "coverageTier": profile.get("coverageTier", "basic"),
        "score": round(score, 1),
        "sourceReliabilityScore": round(reliability, 1),
        "capabilityScore": round(capability_score, 1),
        "localPriority": bool(profile.get("localPriority")),
        "preferred": bool(profile.get("preferred")),
        "focusRank": profile.get("focusRank"),
        "capabilities": capabilities,
        "sources": sources[:4],
        "limitations": list(profile.get("limitations") or [])[:3],
        "professionalAnchors": list(profile.get("professionalAnchors") or [])[:4],
    }


def data_quality_profile(
    *,
    instrument_type: str,
    closes: list[float],
    info: dict[str, Any],
    news_analysis: dict[str, Any],
    news_heat: dict[str, Any],
    financial_analysis: dict[str, Any],
    availability: dict[str, bool] | None = None,
    market_profile: dict[str, Any] | None = None,
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
    market_support = _market_support_profile(market_profile)

    source_penalty = _source_penalty(info)
    score = _clamp(
        price_score * 0.28
        + fundamental_score * 0.18
        + financial_score * 0.17
        + news_score * 0.16
        + factor_score * 0.13
        + market_support["score"] * 0.08
        - source_penalty
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
    if market_support["score"] >= 78:
        strengths.append("marketSourceStackStrong")
    elif market_support["score"] < 62:
        issues.append("marketSourceStackBasic")
    if source_penalty:
        issues.append("sourceFallbackOrStale")

    return {
        "score": round(score, 1),
        "level": _grade(score),
        "priceHistoryScore": round(price_score, 1),
        "fundamentalCoverageScore": round(fundamental_score, 1),
        "financialCoverageScore": round(financial_score, 1),
        "newsCoverageScore": round(news_score, 1),
        "factorCoverageScore": round(factor_score, 1),
        "marketSupportScore": market_support["score"],
        "marketCoverageTier": market_support["coverageTier"],
        "priceSource": info.get("priceSource") or info.get("quoteSource"),
        "sourcePenalty": round(source_penalty, 1),
        "sourceWarnings": _source_warnings(info)[:5],
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
    market: str,
    info: dict[str, Any],
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
    market = str(market or "").upper()
    session = market_session_profile(market, {**info, "instrumentType": instrument_type})
    etf_profile = etf_risk_profile(market, info) if instrument_type == "etf" else {}

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
    elif data_quality.get("sourcePenalty", 0) >= 14:
        add("blockBuy", "sourceStackUnstable", "warning", data_quality.get("sourcePenalty"), 14)
    if session.get("gated") and not session.get("regularSession"):
        add("blockBuy", "outsideTradingSession", "warning")
    elif session.get("gated") and not session.get("openConfirmed"):
        add("blockBuy", "openingConfirmationPending", "warning")
    if change <= -8.5:
        add("exitCandidate", "severePriceBreakdown", "danger", change, -8.5)
    elif market in {"CN", "TW"} and change <= -4.2:
        add("forceReduce", "localMarketFastDrop", "warning", change, -4.2)
    elif change <= -5:
        add("forceReduce", "largePriceBreakdown", "warning", change, -5)
    elif market in {"CN", "TW"} and change <= -2.8:
        add("blockBuy", "localMarketIntradayDrop", "warning", change, -2.8)
    if instrument_type == "etf" and etf_profile:
        if change <= float(etf_profile["forceReduceDropPct"]):
            add("forceReduce", "etfTrendBreakdown", "warning", change, float(etf_profile["forceReduceDropPct"]))
        elif change <= float(etf_profile["blockBuyDropPct"]):
            add(
                "blockBuy",
                "etfHighBetaIntradayDrop" if etf_profile.get("highBeta") else "etfIntradayDrop",
                "warning",
                change,
                float(etf_profile["blockBuyDropPct"]),
            )
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
    market_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data_quality = data_quality_profile(
        instrument_type=instrument_type,
        closes=closes,
        info=info,
        news_analysis=news_analysis,
        news_heat=news_heat,
        financial_analysis=financial_analysis,
        availability=availability,
        market_profile=market_profile,
    )
    market_support = _market_support_profile(market_profile)
    session = market_session_profile(market, {**info, "instrumentType": instrument_type})
    rule_state = market_rule_state(market, info, instrument_type)
    instrument_profile = etf_risk_profile(market, info) if instrument_type == "etf" else {
        "instrumentType": "stock",
        "category": "common_equity",
        "riskTier": "single_stock",
        "market": str(market or "").upper(),
    }
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
        market=market,
        info=info,
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
    if data_quality.get("sourcePenalty", 0) >= 6:
        buy_score = min(buy_score, max(52.0, 72.0 - float(data_quality.get("sourcePenalty") or 0) * 0.7))
        confidence_penalty = min(16.0, float(data_quality.get("sourcePenalty") or 0) * 0.8)
    else:
        confidence_penalty = 0.0

    risk_reward = _clamp(buy_score - sell_score + 50)
    rank_score = _clamp(buy_score * 0.62 + risk_reward * 0.26 + data_quality["score"] * 0.12)
    confidence = _clamp(data_quality["score"] * 0.50 + regime["confidence"] * 0.30 + abs(buy_score - sell_score) * 0.20 - confidence_penalty)

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
            f"marketSupport:{market_support['coverageTier']}",
            "legacyWeights:secondary",
        ]

    return {
        "version": "scenario-v1",
        "instrumentType": instrument_type,
        "market": market,
        "price": price,
        "regime": regime,
        "dataQuality": data_quality,
        "marketSupport": market_support,
        "marketSession": session,
        "marketRuleState": rule_state,
        "instrumentProfile": instrument_profile,
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
