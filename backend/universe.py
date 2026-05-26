from __future__ import annotations

import json
import ssl
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from backend.data import DEFAULT_SYMBOLS, MARKETS
from backend.providers import LOCAL_COMPANY_NAMES, infer_market, local_company_name

FALLBACK_SEARCH_TERMS = {
    "CN": [
        "600519.SS",
        "300750.SZ",
        "002594.SZ",
        "601318.SS",
        "600036.SS",
        "601899.SS",
        "600276.SS",
        "601012.SS",
        "000333.SZ",
        "000858.SZ",
        "000651.SZ",
        "300760.SZ",
        "Kweichow Moutai",
        "CATL",
        "BYD A shares",
        "Ping An Insurance A shares",
        "China Merchants Bank A shares",
        "Zijin Mining A shares",
        "Hengrui Medicine",
        "LONGi Green Energy",
        "Midea Group",
        "Wuliangye",
        "Gree Electric",
        "Mindray Medical",
    ],
    "HK": [
        "0700.HK",
        "9988.HK",
        "3690.HK",
        "9618.HK",
        "0005.HK",
        "0939.HK",
        "1299.HK",
        "0388.HK",
        "0883.HK",
        "2318.HK",
        "1024.HK",
        "1810.HK",
        "Tencent Holdings",
        "Alibaba Group Hong Kong",
        "Meituan Hong Kong",
        "JD.com Hong Kong",
        "HSBC Holdings Hong Kong",
        "China Construction Bank Hong Kong",
        "AIA Group Hong Kong",
        "Hong Kong Exchanges and Clearing",
        "CNOOC Hong Kong",
        "Ping An Insurance Hong Kong",
        "Kuaishou Hong Kong",
        "Xiaomi Hong Kong",
    ],
}

CURATED_FALLBACK_SYMBOLS = {
    "CN": [
        "600519.SS",
        "300750.SZ",
        "002594.SZ",
        "601318.SS",
        "600036.SS",
        "601899.SS",
        "600276.SS",
        "601012.SS",
        "000333.SZ",
        "000858.SZ",
        "000651.SZ",
        "300760.SZ",
    ],
    "HK": [
        "0700.HK",
        "9988.HK",
        "3690.HK",
        "9618.HK",
        "0005.HK",
        "0939.HK",
        "1299.HK",
        "0388.HK",
        "0883.HK",
        "2318.HK",
        "1024.HK",
        "1810.HK",
    ],
    "SG": [
        "D05.SI",
        "O39.SI",
        "U11.SI",
        "Z74.SI",
        "C6L.SI",
        "S68.SI",
        "A17U.SI",
        "C38U.SI",
        "BN4.SI",
        "F34.SI",
        "G13.SI",
        "Y92.SI",
    ],
}


@dataclass(frozen=True)
class DiscoveredSymbol:
    symbol: str
    name: str
    market: str
    source: str


class MarketUniverseProvider:
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 OpenStockPicker/0.1"

    def discover(self, markets: Iterable[str], limit_per_market: int = 18) -> tuple[list[DiscoveredSymbol], list[dict]]:
        symbols: list[DiscoveredSymbol] = []
        errors: list[dict] = []
        for market in markets:
            try:
                market_symbols = self._discover_market(market, limit_per_market)
            except Exception as exc:
                errors.append({"market": market, "source": "market-universe", "error": str(exc)})
                market_symbols = self._discover_fallback_search(market, limit_per_market)

            if not market_symbols:
                market_symbols = self._discover_fallback_search(market, limit_per_market)

            if not market_symbols:
                market_symbols = [
                    DiscoveredSymbol(symbol=symbol, name=symbol, market=market, source="fallback-default-symbol")
                    for symbol in DEFAULT_SYMBOLS.get(market, [])
                ]
            symbols.extend(market_symbols[:limit_per_market])

        seen = set()
        deduped = []
        for item in symbols:
            if item.symbol not in seen:
                deduped.append(item)
                seen.add(item.symbol)
        return deduped, errors

    def _discover_market(self, market: str, limit: int) -> list[DiscoveredSymbol]:
        if market == "US":
            return self._discover_us(limit)
        if market == "CN":
            return self._discover_eastmoney_cn(limit)
        if market == "HK":
            return self._discover_eastmoney_hk(limit)
        if market == "TW":
            return self._discover_twse(limit)
        if market == "SG":
            return self._discover_sgx(limit)
        return []

    def _discover_fallback_search(self, market: str, limit: int) -> list[DiscoveredSymbol]:
        output: list[DiscoveredSymbol] = []
        for term in FALLBACK_SEARCH_TERMS.get(market, []):
            try:
                url = f"https://query1.finance.yahoo.com/v1/finance/search?q={quote_plus(term)}&quotesCount=8&newsCount=0"
                payload = self._json(url)
            except Exception:
                continue
            for quote in payload.get("quotes", []):
                symbol = str(quote.get("symbol") or "").upper()
                if not symbol or infer_market(symbol) != market:
                    continue
                if not is_common_equity_symbol(symbol, market):
                    continue
                if quote.get("quoteType") and quote.get("quoteType") != "EQUITY":
                    continue
                name = local_company_name(symbol, quote.get("shortname") or quote.get("longname") or quote.get("name") or symbol)
                output.append(DiscoveredSymbol(symbol=symbol, name=name, market=market, source=f"yahoo-search-fallback:{term}"))
            if len(output) >= limit:
                break
        for symbol in CURATED_FALLBACK_SYMBOLS.get(market, []):
            if len(output) >= limit:
                break
            output.append(DiscoveredSymbol(symbol=symbol, name=local_company_name(symbol, symbol), market=market, source="curated-liquid-fallback"))
        seen = set()
        deduped = []
        for item in output:
            if item.symbol not in seen:
                deduped.append(item)
                seen.add(item.symbol)
        return deduped[:limit]

    def _discover_us(self, limit: int) -> list[DiscoveredSymbol]:
        symbols: list[DiscoveredSymbol] = []
        for screener in ["most_actives", "day_gainers", "undervalued_growth_stocks"]:
            url = f"https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds={screener}&count={limit}"
            payload = self._json(url)
            quotes = payload.get("finance", {}).get("result", [{}])[0].get("quotes", [])
            for quote in quotes:
                symbol = str(quote.get("symbol") or "").upper()
                if symbol and infer_market(symbol) == "US" and quote.get("quoteType", "EQUITY") == "EQUITY":
                    name = quote.get("shortName") or quote.get("longName") or symbol
                    symbols.append(DiscoveredSymbol(symbol=symbol, name=name, market="US", source=f"yahoo-screener:{screener}"))
            if len(symbols) >= limit:
                break
        return symbols[:limit]

    def _discover_eastmoney_cn(self, limit: int) -> list[DiscoveredSymbol]:
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get"
            "?pn=1&pz={limit}&po=1&np=1&fltt=2&invt=2&fid=f6"
            "&fs=m:1+t:2,m:0+t:6,m:0+t:80&fields=f12,f14,f6"
        ).format(limit=limit * 3)
        rows = self._json(url).get("data", {}).get("diff", [])
        output = []
        for row in rows:
            code = str(row.get("f12") or "")
            if not code.isdigit():
                continue
            suffix = ".SS" if code.startswith("6") else ".SZ"
            output.append(DiscoveredSymbol(symbol=f"{code}{suffix}", name=str(row.get("f14") or code), market="CN", source="eastmoney-cn-turnover"))
        return output[:limit]

    def _discover_eastmoney_hk(self, limit: int) -> list[DiscoveredSymbol]:
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get"
            "?pn=1&pz={limit}&po=1&np=1&fltt=2&invt=2&fid=f6"
            "&fs=m:116+t:3,m:128+t:3,m:132+t:3&fields=f12,f14,f6"
        ).format(limit=limit * 4)
        rows = self._json(url).get("data", {}).get("diff", [])
        output = []
        for row in rows:
            code = str(row.get("f12") or "").strip()
            if not code.isdigit():
                continue
            symbol = f"{int(code):04d}.HK"
            output.append(DiscoveredSymbol(symbol=symbol, name=str(row.get("f14") or symbol), market="HK", source="eastmoney-hk-turnover"))
        seen = set()
        deduped = []
        for item in output:
            if item.symbol not in seen:
                deduped.append(item)
                seen.add(item.symbol)
        return deduped[:limit]

    def _discover_twse(self, limit: int) -> list[DiscoveredSymbol]:
        rows = self._json("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", insecure=True)
        common_stocks = [
            row
            for row in rows
            if str(row.get("Code") or "").isdigit()
            and len(str(row.get("Code"))) == 4
            and _number(row.get("TradeValue")) > 0
        ]
        common_stocks.sort(key=lambda row: _number(row.get("TradeValue")), reverse=True)
        return [
            DiscoveredSymbol(symbol=f"{row['Code']}.TW", name=str(row.get("Name") or row["Code"]), market="TW", source="twse-openapi-turnover")
            for row in common_stocks[:limit]
        ]

    def _discover_sgx(self, limit: int) -> list[DiscoveredSymbol]:
        url = "https://api.sgx.com/securities/v1.1?params=nc,cn,lt,vl&pagestart=0&pagesize=200"
        payload = self._json(url)
        rows = payload.get("data", {}).get("prices", [])
        stocks = [
            row
            for row in rows
            if row.get("type") == "stocks"
            and row.get("nc")
            and _number(row.get("vl")) > 0
            and (str(row.get("cn") or "").strip() or f"{row['nc']}.SI" in LOCAL_COMPANY_NAMES)
        ]
        stocks.sort(key=lambda row: _number(row.get("vl")), reverse=True)
        output = [
            DiscoveredSymbol(
                symbol=f"{row['nc']}.SI",
                name=local_company_name(f"{row['nc']}.SI", str(row.get("cn") or row["nc"])),
                market="SG",
                source="sgx-api-volume",
            )
            for row in stocks[:limit]
        ]
        for symbol in CURATED_FALLBACK_SYMBOLS["SG"]:
            if len(output) >= limit:
                break
            output.append(DiscoveredSymbol(symbol=symbol, name=local_company_name(symbol, symbol), market="SG", source="curated-liquid-fallback"))
        seen = set()
        deduped = []
        for item in output:
            if item.symbol not in seen:
                deduped.append(item)
                seen.add(item.symbol)
        return deduped[:limit]

    def _json(self, url: str, insecure: bool = False) -> dict | list:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://quote.eastmoney.com/",
        }
        context = ssl._create_unverified_context() if insecure else None
        last_error = None
        for attempt in range(3):
            try:
                request = Request(url, headers=headers)
                with urlopen(request, timeout=12, context=context) as response:
                    return json.loads(response.read().decode("utf-8-sig"))
            except Exception as exc:
                last_error = exc
                time.sleep(0.3 * (attempt + 1))
        raise last_error


def _number(value) -> float:
    try:
        if value in (None, "-", ""):
            return 0
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0


def is_common_equity_symbol(symbol: str, market: str) -> bool:
    base = symbol.split(".")[0]
    if market == "CN":
        return base.startswith(("600", "601", "603", "605", "688", "000", "001", "002", "003", "300", "301"))
    if market == "HK":
        return base.isdigit() and len(base) == 4 and not base.startswith("8")
    return True


def configured_markets() -> list[str]:
    return [market["id"] for market in MARKETS]
