from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36"
YAHOO_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")


def _json(urls: list[str], timeout: int = 6) -> dict:
    last_error: Exception | None = None
    for url in urls:
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json,text/plain,*/*",
                    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                    "Cache-Control": "no-cache",
                    "Connection": "close",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8-sig"))
        except Exception as exc:
            last_error = exc
    raise last_error or ValueError("Chart request failed.")


def _chart_urls(symbol: str, range_value: str, interval: str) -> list[str]:
    encoded = quote(symbol.upper())
    return [
        f"https://{host}/v8/finance/chart/{encoded}?range={range_value}&interval={interval}&events=history&includePrePost=false"
        for host in YAHOO_HOSTS
    ]


def _timestamp_label(timestamp: int | float | None) -> str:
    if timestamp is None:
        return ""
    return datetime.fromtimestamp(float(timestamp), timezone.utc).isoformat()


def _number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _parse_chart(payload: dict) -> tuple[list[dict], dict]:
    result = payload.get("chart", {}).get("result", [])
    if not result:
        error = payload.get("chart", {}).get("error") or {}
        raise ValueError(error.get("description") or "No chart data returned.")

    chart = result[0]
    timestamps = chart.get("timestamp") or []
    quote_payload = chart.get("indicators", {}).get("quote", [{}])[0]
    opens = quote_payload.get("open") or []
    highs = quote_payload.get("high") or []
    lows = quote_payload.get("low") or []
    closes = quote_payload.get("close") or []
    volumes = quote_payload.get("volume") or []

    points = []
    for index, timestamp in enumerate(timestamps):
        close = _number(closes[index] if index < len(closes) else None)
        if close is None:
            continue
        points.append(
            {
                "time": _timestamp_label(timestamp),
                "open": _number(opens[index] if index < len(opens) else None),
                "high": _number(highs[index] if index < len(highs) else None),
                "low": _number(lows[index] if index < len(lows) else None),
                "close": close,
                "volume": _number(volumes[index] if index < len(volumes) else None),
            }
        )
    if not points:
        raise ValueError("No usable chart points returned.")
    return points, chart.get("meta", {})


def _fetch_series(symbol: str, range_value: str, interval: str) -> tuple[list[dict], dict]:
    return _parse_chart(_json(_chart_urls(symbol, range_value, interval)))


def _moving_average(points: list[dict], index: int, window: int) -> float | None:
    if index + 1 < window:
        return None
    values = [point.get("close") for point in points[index + 1 - window : index + 1]]
    if any(value is None for value in values):
        return None
    return round(sum(float(value) for value in values) / window, 4)


def _cn_limit_pct(symbol: str) -> float | None:
    upper = symbol.upper()
    if not (upper.endswith(".SS") or upper.endswith(".SZ")):
        return None
    code = upper.split(".", 1)[0]
    if code.startswith(("300", "301", "688", "689")):
        return 0.20
    return 0.10


def _enrich_daily_points(symbol: str, points: list[dict]) -> list[dict]:
    limit_pct = _cn_limit_pct(symbol)
    enriched = []
    for index, point in enumerate(points):
        item = dict(point)
        item["ma5"] = _moving_average(points, index, 5)
        item["ma10"] = _moving_average(points, index, 10)
        item["ma20"] = _moving_average(points, index, 20)
        if limit_pct is not None and index > 0:
            previous_close = _number(points[index - 1].get("close"))
            if previous_close:
                limit_up_price = round(previous_close * (1 + limit_pct), 2)
                high = _number(point.get("high")) or _number(point.get("close")) or 0
                close = _number(point.get("close")) or 0
                tolerance = max(0.02, previous_close * 0.0015)
                item["limitUpPrice"] = limit_up_price
                item["isLimitUp"] = close >= limit_up_price - tolerance or high >= limit_up_price - tolerance
        enriched.append(item)
    return enriched


def fetch_stock_chart(symbol: str) -> dict:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        raise ValueError("Missing symbol.")

    intraday, intraday_meta = _fetch_series(normalized, "1d", "5m")
    daily, daily_meta = _fetch_series(normalized, "6mo", "1d")
    daily = _enrich_daily_points(normalized, daily)
    meta = {**daily_meta, **intraday_meta}
    return {
        "symbol": normalized,
        "name": meta.get("shortName") or meta.get("longName") or normalized,
        "currency": meta.get("currency") or "",
        "exchangeTimezoneName": meta.get("exchangeTimezoneName") or "",
        "regularMarketPrice": _number(meta.get("regularMarketPrice")),
        "source": "Yahoo Finance chart API",
        "refreshedAt": datetime.now(timezone.utc).isoformat(),
        "intraday": intraday,
        "daily": daily,
    }
