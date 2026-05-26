from __future__ import annotations

import json
import re
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from backend.data import DEFAULT_SYMBOLS, MARKETS
from backend.providers import (
    COMPANY_SEARCH_ALIASES,
    LOCAL_COMPANY_NAMES,
    Article,
    RssNewsCrawler,
    google_news_url,
    infer_market,
    is_recent_article,
    local_company_name,
    recency_weight,
)

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
    "US": [
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "META",
        "TSLA",
        "AVGO",
        "AMD",
        "JPM",
        "V",
        "LLY",
        "UNH",
        "XOM",
        "COST",
    ],
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

MARKET_NEWS_QUERIES = {
    "CN": [
        "A股 公司 财报 业绩 股价",
        "A股 上市公司 公告 增持 减持",
        "A股 龙虎榜 资金 流入 个股",
        "site:finance.eastmoney.com A股 公司 业绩",
        "site:stcn.com A股 上市公司",
    ],
    "HK": [
        "港股 公司 業績 股價 公告",
        "港股 目標價 盈喜 盈警 個股",
        "site:aastocks.com 港股 業績",
        "site:etnet.com.hk 港股 公司",
    ],
    "TW": [
        "台股 公司 營收 財報 股價",
        "台股 法說 目標價 個股",
        "site:cnyes.com 台股 營收",
        "site:moneydj.com 台股 公司",
    ],
    "SG": [
        "Singapore stocks earnings results dividend SGX",
        "Singapore market company results shares",
        "site:businesstimes.com.sg SGX results stocks",
        "site:channelnewsasia.com Singapore company shares",
    ],
    "US": [
        "US stocks earnings revenue upgrade downgrade",
        "Wall Street stocks analyst rating earnings",
        "site:reuters.com stocks earnings shares",
        "site:finance.yahoo.com stocks earnings",
    ],
}


@dataclass(frozen=True)
class DiscoveredSymbol:
    symbol: str
    name: str
    market: str
    source: str
    news_score: float = 0.0
    news_hits: int = 0
    evidence: tuple[Article, ...] = ()


class MarketUniverseProvider:
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 OpenStockPicker/0.1"

    def discover(self, markets: Iterable[str], limit_per_market: int = 18) -> tuple[list[DiscoveredSymbol], list[dict]]:
        symbols: list[DiscoveredSymbol] = []
        errors: list[dict] = []
        for market in markets:
            try:
                market_symbols = self._discover_market_news(market, limit_per_market)
            except Exception as exc:
                errors.append({"market": market, "source": "market-news", "error": str(exc)})
                market_symbols = []

            if not market_symbols:
                errors.append({"market": market, "source": "market-news", "error": "No recent company mentions were extracted from market news."})
            symbols.extend(market_symbols[:limit_per_market])

        seen = set()
        deduped = []
        for item in symbols:
            if item.symbol not in seen:
                deduped.append(item)
                seen.add(item.symbol)
        return deduped, errors

    def _discover_market_news(self, market: str, limit: int) -> list[DiscoveredSymbol]:
        crawler = RssNewsCrawler()
        articles = []
        for query in MARKET_NEWS_QUERIES.get(market, []):
            try:
                articles.extend(crawler._parse_feed(google_news_url(_market_locale_symbol(market), query)))
            except Exception:
                continue
        return self._symbols_from_news_articles(market, articles, limit)

    def _symbols_from_news_articles(self, market: str, articles: list[Article], limit: int) -> list[DiscoveredSymbol]:
        index = _news_symbol_index(market)
        now = datetime.now(timezone.utc)
        scores: dict[str, float] = {}
        hits: dict[str, int] = {}
        symbol_names: dict[str, str] = {}
        evidence: dict[str, list[Article]] = {}
        unresolved_terms: dict[str, float] = {}
        term_evidence: dict[str, list[Article]] = {}
        for article in articles:
            if not is_recent_article(article, now):
                continue
            text = f"{article.title} {article.summary}".lower()
            display_text = f"{article.title} {article.summary}"
            article_weight = article.credibility * recency_weight(article, now) * (0.35 + abs(article.sentiment))
            for symbol, alias_names in index.items():
                if any(_alias_in_text(alias, text) for alias in alias_names):
                    scores[symbol] = scores.get(symbol, 0.0) + article_weight
                    hits[symbol] = hits.get(symbol, 0) + 1
                    symbol_names[symbol] = local_company_name(symbol, symbol)
                    evidence.setdefault(symbol, []).append(article)
            for symbol in _symbols_from_code_mentions(text, market):
                if infer_market(symbol) == market and is_common_equity_symbol(symbol, market):
                    scores[symbol] = scores.get(symbol, 0.0) + article_weight
                    hits[symbol] = hits.get(symbol, 0) + 1
                    symbol_names[symbol] = local_company_name(symbol, symbol)
                    evidence.setdefault(symbol, []).append(article)
            for term in _company_terms_from_article(display_text, market):
                unresolved_terms[term] = unresolved_terms.get(term, 0.0) + article_weight
                term_evidence.setdefault(term, []).append(article)
        for term, term_score in sorted(unresolved_terms.items(), key=lambda item: item[1], reverse=True)[:12]:
            if len(scores) >= limit * 2:
                break
            resolved = self._search_eastmoney_term(term, market) if market in {"CN", "HK"} else []
            if not resolved:
                resolved = self._search_yahoo_term(term, market)
            for item in resolved[:2]:
                if item.symbol in scores:
                    continue
                scores[item.symbol] = term_score
                hits[item.symbol] = 1
                symbol_names[item.symbol] = item.name
                evidence[item.symbol] = term_evidence.get(term, [])
        ranked_symbols = sorted(scores, key=lambda symbol: (scores[symbol], hits[symbol]), reverse=True)
        return [
            DiscoveredSymbol(
                symbol=symbol,
                name=symbol_names.get(symbol) or local_company_name(symbol, symbol),
                market=market,
                source="market-news",
                news_score=round(scores[symbol], 4),
                news_hits=hits[symbol],
                evidence=tuple(_dedupe_articles(evidence.get(symbol, []))[:4]),
            )
            for symbol in ranked_symbols[:limit]
        ]

    def _search_yahoo_term(self, term: str, market: str) -> list[DiscoveredSymbol]:
        try:
            payload = self._json(f"https://query1.finance.yahoo.com/v1/finance/search?q={quote_plus(term)}&quotesCount=6&newsCount=0")
        except Exception:
            return []
        output = []
        for quote in payload.get("quotes", []):
            symbol = str(quote.get("symbol") or "").upper()
            if not symbol or infer_market(symbol) != market or not is_common_equity_symbol(symbol, market):
                continue
            if quote.get("quoteType") and quote.get("quoteType") != "EQUITY":
                continue
            name = local_company_name(symbol, quote.get("shortname") or quote.get("longname") or quote.get("name") or term)
            output.append(DiscoveredSymbol(symbol=symbol, name=name, market=market, source=f"market-news-search:{term}"))
        return output

    def _search_eastmoney_term(self, term: str, market: str) -> list[DiscoveredSymbol]:
        try:
            payload = self._json(f"https://searchapi.eastmoney.com/api/suggest/get?input={quote_plus(term)}&type=14&token=")
        except Exception:
            return []
        rows = payload.get("QuotationCodeTable", {}).get("Data") or []
        output = []
        for row in rows:
            code = str(row.get("Code") or row.get("UnifiedCode") or "").strip()
            classify = str(row.get("Classify") or "").upper()
            jys = str(row.get("JYS") or "").upper()
            symbol = ""
            if market == "HK" and (classify == "HK" or jys == "HK") and code.isdigit():
                symbol = f"{int(code):04d}.HK"
            elif market == "CN" and code.isdigit() and is_common_equity_symbol(f"{code}.SS" if code.startswith('6') else f"{code}.SZ", "CN"):
                symbol = f"{code}.SS" if code.startswith("6") else f"{code}.SZ"
            if symbol:
                output.append(
                    DiscoveredSymbol(
                        symbol=symbol,
                        name=local_company_name(symbol, str(row.get("Name") or term)),
                        market=market,
                        source=f"market-news-eastmoney:{term}",
                    )
                )
        return output

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


def _market_locale_symbol(market: str) -> str:
    return {
        "CN": "600519.SS",
        "HK": "0700.HK",
        "TW": "2330.TW",
        "SG": "D05.SI",
        "US": "AAPL",
    }.get(market, "AAPL")


def _news_symbol_index(market: str) -> dict[str, list[str]]:
    symbols = set(CURATED_FALLBACK_SYMBOLS.get(market, []))
    symbols.update(symbol for symbol in LOCAL_COMPANY_NAMES if infer_market(symbol) == market)
    symbols.update(symbol for symbol in COMPANY_SEARCH_ALIASES if infer_market(symbol) == market)
    index: dict[str, list[str]] = {}
    for symbol in symbols:
        names = [local_company_name(symbol, symbol), *COMPANY_SEARCH_ALIASES.get(symbol, [])]
        if not symbol.split(".")[0].isdigit() and len(symbol.split(".")[0]) > 1:
            names.append(symbol.split(".")[0])
        index[symbol] = list(dict.fromkeys(name for name in names if name and name.upper() != symbol.upper()))
    return index


def _alias_in_text(alias: str, text: str) -> bool:
    alias = alias.strip().lower()
    if not alias:
        return False
    if any("\u3400" <= char <= "\u9fff" for char in alias):
        return alias in text
    if len(alias) <= 2:
        return re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text) is not None
    return alias in text


def _symbols_from_code_mentions(text: str, market: str) -> list[str]:
    if market == "CN":
        return [f"{code}.SS" if code.startswith("6") else f"{code}.SZ" for code in re.findall(r"(?<!\d)([036]\d{5})(?!\d)", text)]
    if market == "HK":
        return [f"{int(code):04d}.HK" for code in re.findall(r"(?<!\d)(\d{4,5})\.?hk(?![a-z0-9])", text)]
    if market == "TW":
        return [f"{code}.TW" for code in re.findall(r"(?<!\d)(\d{4})\.?tw(?![a-z0-9])", text)]
    if market == "SG":
        return [f"{code.upper()}.SI" for code in re.findall(r"(?<![a-z0-9])([a-z0-9]{3,4})\.?si(?![a-z0-9])", text)]
    return []


def _company_terms_from_article(text: str, market: str) -> list[str]:
    if market not in {"CN", "HK", "TW"}:
        return []
    terms = []
    patterns = [
        r"([\u4e00-\u9fffA-Za-z0-9]{2,8}?)(?:等\d*股|披露|擬|拟|增持|減持|减持|漲停|涨停|復牌|复牌|業績|业绩|股價|股价|股份|公司)",
        r"(?:公告|掘金|異動|异动|焦點|焦点)[|丨：:\s]+([\u4e00-\u9fffA-Za-z0-9]{2,12})",
        r"(?:抢筹|搶籌|狂买|狂買|买入|買入|增持)([\u4e00-\u9fffA-Za-z0-9]{2,8})",
    ]
    for pattern in patterns:
        terms.extend(re.findall(pattern, text))
    for separator in ["，", ",", "；", ";", "、"]:
        for part in text.split(separator):
            match = re.search(r"([\u4e00-\u9fffA-Za-z0-9]{2,12})(?:等\d*股|披露|增持|減持|减持|漲停|涨停)", part)
            if match:
                terms.append(match.group(1))
    stop_terms = {"公司", "上市公司", "港股", "台股", "股票", "個股", "个股", "業績", "业绩", "公告", "財報", "财报"}
    deduped = []
    seen = set()
    for term in terms:
        cleaned = str(term).strip(" 「」“”：《》()（）[]【】")
        cleaned = re.sub(r"^\d+月\d+日?", "", cleaned)
        cleaned = re.sub(r"(?:等\d*股|披露|擬|拟|增持|減持|减持).*$", "", cleaned)
        if len(cleaned) >= 2 and "月" not in cleaned and cleaned not in stop_terms and cleaned not in seen:
            deduped.append(cleaned)
            seen.add(cleaned)
    return deduped[:8]


def _dedupe_articles(articles: list[Article]) -> list[Article]:
    output = []
    seen = set()
    for article in articles:
        key = article.link or article.title
        if key not in seen:
            output.append(article)
            seen.add(key)
    return output
