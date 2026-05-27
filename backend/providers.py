from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import json
import re
from math import sqrt
from typing import Any
from urllib.parse import quote, quote_plus, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from backend.data import RSS_FEEDS

try:
    import feedparser
except Exception:  # pragma: no cover
    feedparser = None

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    name: str
    market: str
    sector: str
    price: float
    change: float
    currency: str
    closes: list[float]
    info: dict[str, Any]


@dataclass(frozen=True)
class Article:
    source: str
    title: str
    summary: str
    link: str
    published_at: datetime | None
    sentiment: float
    credibility: float
    relevance: float


MAX_ARTICLE_AGE_HOURS = 168


POSITIVE_WORDS = {
    "approval",
    "beat",
    "beats",
    "bullish",
    "expansion",
    "growth",
    "profit",
    "raise",
    "record",
    "resilient",
    "strong",
    "surge",
    "upgrade",
    "outperform",
    "guidance",
    "contract",
    "dividend",
    "rebound",
    "acceleration",
}

NEGATIVE_WORDS = {
    "bearish",
    "cut",
    "cuts",
    "delay",
    "downgrade",
    "lawsuit",
    "loss",
    "miss",
    "pressure",
    "probe",
    "risk",
    "slump",
    "warning",
    "weak",
    "missed",
    "decline",
    "falls",
    "plunge",
    "investigation",
    "default",
    "亏损",
    "下滑",
    "下跌",
    "减持",
    "降级",
    "警告",
    "压力",
    "裁员",
    "風險",
    "虧損",
    "下跌",
    "下滑",
    "警告",
}

POSITIVE_PHRASES = [
    "beats expectations",
    "raises guidance",
    "record revenue",
    "strong demand",
    "profit rises",
    "earnings beat",
    "業績增長",
    "营收增长",
    "獲利成長",
    "利润增长",
    "上调评级",
    "目標價上調",
    "目标价上调",
    "創新高",
    "创新高",
    "漲停",
    "涨停",
    "商機",
    "商机",
    "買點",
    "买点",
    "回購",
    "回购",
    "資金新寵",
    "资金新宠",
    "上調",
    "上调",
]

NEGATIVE_PHRASES = [
    "misses expectations",
    "cuts guidance",
    "profit warning",
    "revenue falls",
    "margin pressure",
    "downgraded",
    "業績下滑",
    "营收下滑",
    "獲利衰退",
    "利润下降",
    "下调评级",
    "目標價下調",
    "目标价下调",
    "財測下修",
    "财测下修",
    "翻黑",
    "重挫",
    "急跌",
    "下修",
    "跌破",
    "減持",
    "减持",
]

SOURCE_CREDIBILITY = {
    "reuters": 0.9,
    "bloomberg": 0.9,
    "cnbc": 0.82,
    "marketwatch": 0.78,
    "yahoo finance": 0.76,
    "eastmoney": 0.76,
    "证券时报": 0.78,
    "上海证券报": 0.78,
    "cnstock": 0.78,
    "cnyes": 0.76,
    "鉅亨": 0.76,
    "moneydj": 0.74,
    "中央社": 0.82,
    "aastocks": 0.76,
    "etnet": 0.74,
    "hket": 0.76,
    "經濟日報": 0.76,
    "futubull": 0.68,
    "business times": 0.8,
    "straits times": 0.78,
    "channel newsasia": 0.78,
}

LOCAL_COMPANY_NAMES = {
    "600519.SS": "贵州茅台",
    "300750.SZ": "宁德时代",
    "002594.SZ": "比亚迪",
    "601318.SS": "中国平安",
    "600036.SS": "招商银行",
    "601899.SS": "紫金矿业",
    "600276.SS": "恒瑞医药",
    "601012.SS": "隆基绿能",
    "000333.SZ": "美的集团",
    "000858.SZ": "五粮液",
    "000651.SZ": "格力电器",
    "300760.SZ": "迈瑞医疗",
    "605589.SS": "圣泉集团",
    "603986.SS": "兆易创新",
    "603936.SS": "博敏电子",
    "301071.SZ": "力量钻石",
    "300373.SZ": "扬杰科技",
    "300323.SZ": "华灿光电",
    "0700.HK": "腾讯控股",
    "9988.HK": "阿里巴巴",
    "3690.HK": "美团",
    "9618.HK": "京东集团",
    "0005.HK": "汇丰控股",
    "0939.HK": "建设银行",
    "1299.HK": "友邦保险",
    "0388.HK": "香港交易所",
    "0883.HK": "中国海洋石油",
    "2318.HK": "中国平安",
    "1024.HK": "快手",
    "1810.HK": "小米集团",
    "D05.SI": "DBS Group",
    "O39.SI": "OCBC",
    "U11.SI": "UOB",
    "Z74.SI": "Singtel",
    "A17U.SI": "CapitaLand Ascendas REIT",
    "C38U.SI": "CapitaLand Integrated Commercial Trust",
    "C6L.SI": "Singapore Airlines",
    "S68.SI": "Singapore Exchange",
    "BN4.SI": "Keppel",
    "F34.SI": "Wilmar",
    "G13.SI": "Genting Singapore",
    "Y92.SI": "Thai Beverage",
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "2308.TW": "台達電",
    "2412.TW": "中華電",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    "2303.TW": "聯電",
    "3711.TW": "日月光投控",
    "2382.TW": "廣達",
    "2891.TW": "中信金",
    "2886.TW": "兆豐金",
    "2344.TW": "華邦電",
    "3481.TW": "群創",
}

COMPANY_SEARCH_ALIASES = {
    "AAPL": ["Apple", "Apple Inc"],
    "MSFT": ["Microsoft"],
    "NVDA": ["Nvidia", "NVIDIA"],
    "AMZN": ["Amazon"],
    "GOOGL": ["Alphabet", "Google"],
    "META": ["Meta Platforms", "Facebook"],
    "TSLA": ["Tesla"],
    "AVGO": ["Broadcom"],
    "AMD": ["Advanced Micro Devices", "AMD"],
    "JPM": ["JPMorgan", "JP Morgan"],
    "V": ["Visa"],
    "LLY": ["Eli Lilly"],
    "UNH": ["UnitedHealth", "UnitedHealth Group"],
    "XOM": ["Exxon Mobil", "ExxonMobil"],
    "COST": ["Costco"],
    "600519.SS": ["贵州茅台", "Kweichow Moutai"],
    "300750.SZ": ["宁德时代", "CATL"],
    "002594.SZ": ["比亚迪", "BYD"],
    "601318.SS": ["中国平安", "Ping An Insurance"],
    "600036.SS": ["招商银行", "China Merchants Bank"],
    "601899.SS": ["紫金矿业", "Zijin Mining"],
    "600276.SS": ["恒瑞医药", "Hengrui Medicine"],
    "601012.SS": ["隆基绿能", "LONGi"],
    "000333.SZ": ["美的集团", "Midea Group"],
    "000858.SZ": ["五粮液", "Wuliangye"],
    "000651.SZ": ["格力电器", "Gree Electric"],
    "300760.SZ": ["迈瑞医疗", "Mindray"],
    "605589.SS": ["圣泉集团", "Jinan Shengquan"],
    "603986.SS": ["兆易创新", "GigaDevice"],
    "603936.SS": ["博敏电子", "Bomin Electronics"],
    "301071.SZ": ["力量钻石", "Power Diamond"],
    "300373.SZ": ["扬杰科技", "Yangjie Technology"],
    "300323.SZ": ["华灿光电", "HC Semitek"],
    "0700.HK": ["腾讯控股", "騰訊控股", "Tencent"],
    "9988.HK": ["阿里巴巴", "Alibaba"],
    "3690.HK": ["美团", "美團", "Meituan"],
    "9618.HK": ["京东集团", "京東集團", "JD.com"],
    "0005.HK": ["汇丰控股", "滙豐控股", "匯豐控股", "HSBC"],
    "0939.HK": ["建设银行", "建設銀行", "China Construction Bank"],
    "1299.HK": ["友邦保险", "友邦保險", "AIA"],
    "0388.HK": ["香港交易所", "港交所", "HKEX"],
    "0883.HK": ["中国海洋石油", "中國海洋石油", "中海油", "CNOOC"],
    "2318.HK": ["中国平安", "中國平安", "Ping An Insurance"],
    "1024.HK": ["快手", "Kuaishou"],
    "1810.HK": ["小米集团", "小米集團", "Xiaomi"],
    "2330.TW": ["台積電", "台积电", "TSMC"],
    "2317.TW": ["鴻海", "鸿海", "Foxconn", "Hon Hai"],
    "2454.TW": ["聯發科", "联发科", "MediaTek"],
    "2308.TW": ["台達電", "台达电", "Delta Electronics"],
    "2412.TW": ["中華電", "中华电", "Chunghwa Telecom"],
    "2881.TW": ["富邦金", "Fubon Financial"],
    "2882.TW": ["國泰金", "国泰金", "Cathay Financial"],
    "2303.TW": ["聯電", "联电", "UMC"],
    "3711.TW": ["日月光投控", "ASE"],
    "2382.TW": ["廣達", "广达", "Quanta"],
    "2891.TW": ["中信金", "CTBC"],
    "2886.TW": ["兆豐金", "Mega Financial"],
    "D05.SI": ["DBS", "DBS Group"],
    "O39.SI": ["OCBC"],
    "U11.SI": ["UOB", "United Overseas Bank"],
    "Z74.SI": ["Singtel", "Singapore Telecommunications"],
    "A17U.SI": ["CapitaLand Ascendas REIT", "Ascendas REIT"],
    "C38U.SI": ["CapitaLand Integrated Commercial Trust", "CICT"],
    "C6L.SI": ["Singapore Airlines", "SIA"],
    "S68.SI": ["Singapore Exchange", "SGX"],
    "BN4.SI": ["Keppel"],
    "F34.SI": ["Wilmar"],
    "G13.SI": ["Genting Singapore"],
    "Y92.SI": ["Thai Beverage", "ThaiBev"],
}

KNOWN_SECTORS = {
    "AAPL": "Consumer Technology",
    "MSFT": "Cloud Software",
    "NVDA": "Semiconductors",
    "600519.SS": "Consumer Staples",
    "300750.SZ": "Battery Manufacturing",
    "0700.HK": "Internet Platforms",
    "9988.HK": "E-commerce",
    "D05.SI": "Banking",
    "C38U.SI": "Real Estate Investment Trust",
    "2330.TW": "Semiconductors",
    "2317.TW": "Electronics Manufacturing",
    "AMZN": "E-commerce",
    "GOOGL": "Internet Platforms",
    "META": "Internet Platforms",
    "TSLA": "Electric Vehicles",
    "AVGO": "Semiconductors",
    "AMD": "Semiconductors",
    "JPM": "Banking",
    "V": "Payments",
    "LLY": "Pharmaceuticals",
    "UNH": "Managed Healthcare",
    "XOM": "Energy",
    "COST": "Retail",
    "601318.SS": "Insurance",
    "600036.SS": "Banking",
    "601899.SS": "Metals and Mining",
    "600276.SS": "Pharmaceuticals",
    "601012.SS": "Solar Manufacturing",
    "000333.SZ": "Home Appliances",
    "000858.SZ": "Consumer Staples",
    "002594.SZ": "Electric Vehicles",
    "000651.SZ": "Home Appliances",
    "300760.SZ": "Medical Devices",
    "605589.SS": "Chemical Materials",
    "603986.SS": "Semiconductors",
    "603936.SS": "Electronic Components",
    "301071.SZ": "Synthetic Diamond Materials",
    "300373.SZ": "Semiconductors",
    "300323.SZ": "LED Semiconductors",
    "3690.HK": "Local Services",
    "9618.HK": "E-commerce",
    "0005.HK": "Banking",
    "0939.HK": "Banking",
    "1299.HK": "Insurance",
    "0388.HK": "Exchange Operator",
    "0883.HK": "Energy",
    "2318.HK": "Insurance",
    "1024.HK": "Healthcare Technology",
    "1810.HK": "Consumer Electronics",
    "O39.SI": "Banking",
    "U11.SI": "Banking",
    "Z74.SI": "Telecommunications",
    "A17U.SI": "Real Estate Investment Trust",
    "C6L.SI": "Airlines",
    "S68.SI": "Exchange Operator",
    "BN4.SI": "Engineering",
    "F34.SI": "Consumer Staples",
    "G13.SI": "Consumer Staples",
    "Y92.SI": "Manufacturing",
    "2454.TW": "Semiconductors",
    "2308.TW": "Electronics Components",
    "2412.TW": "Telecommunications",
    "2881.TW": "Financial Services",
    "2882.TW": "Financial Services",
    "2303.TW": "Semiconductors",
    "3711.TW": "Electronics Manufacturing",
    "2382.TW": "Computer Hardware",
    "2891.TW": "Financial Services",
    "2886.TW": "Financial Services",
}


def infer_market(symbol: str) -> str:
    upper = symbol.upper()
    if upper.endswith((".SS", ".SZ")):
        return "CN"
    if upper.endswith(".HK"):
        return "HK"
    if upper.endswith(".SI"):
        return "SG"
    if upper.endswith(".TW"):
        return "TW"
    return "US"


def fallback_sector(symbol: str) -> str:
    upper = symbol.upper()
    if upper in KNOWN_SECTORS:
        return KNOWN_SECTORS[upper]
    return f"{infer_market(symbol)} Equity"


def local_company_name(symbol: str, fallback: str = "") -> str:
    return LOCAL_COMPANY_NAMES.get(symbol.upper(), fallback or symbol.upper())


def company_search_names(symbol: str, fallback: str = "") -> list[str]:
    names = [local_company_name(symbol, fallback), *COMPANY_SEARCH_ALIASES.get(symbol.upper(), [])]
    if fallback and fallback.upper() != symbol.upper():
        names.append(fallback)
    deduped = []
    seen = set()
    for name in names:
        cleaned = str(name or "").strip()
        key = cleaned.lower()
        if cleaned and key not in seen and cleaned.upper() != symbol.upper():
            deduped.append(cleaned)
            seen.add(key)
    return deduped


class YFinanceMarketDataProvider:
    def fetch(self, symbol: str) -> MarketSnapshot:
        if yf is None:
            return YahooHttpMarketDataProvider().fetch(symbol)

        ticker = yf.Ticker(symbol)
        history = ticker.history(period="6mo", interval="1d", auto_adjust=True)
        if history.empty:
            raise ValueError(f"No market data returned for {symbol}. Check the ticker suffix.")

        closes = [float(value) for value in history["Close"].dropna().tail(130).tolist()]
        if not closes:
            raise ValueError(f"No closing prices returned for {symbol}.")

        try:
            info = dict(ticker.get_info())
        except Exception:
            info = {}
        info = _merge_market_fundamentals(symbol, info)

        price = closes[-1]
        previous = closes[-2] if len(closes) > 1 else price
        change = ((price - previous) / previous * 100) if previous else 0
        name = info.get("shortName") or info.get("longName") or symbol
        sector = info.get("sector") or info.get("industry") or fallback_sector(symbol)

        return MarketSnapshot(
            symbol=symbol.upper(),
            name=name,
            market=infer_market(symbol),
            sector=sector,
            price=round(price, 3),
            change=round(change, 2),
            currency=info.get("currency") or "",
            closes=closes,
            info=info,
        )


class YahooHttpMarketDataProvider:
    user_agent = "OpenStockPicker/0.1 (+https://github.com/open-stock-picker)"

    def fetch(self, symbol: str) -> MarketSnapshot:
        chart = self._json(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?range=6mo&interval=1d")
        result = chart.get("chart", {}).get("result", [])
        if not result:
            error = chart.get("chart", {}).get("error") or {}
            raise ValueError(error.get("description") or f"No market data returned for {symbol}.")

        payload = result[0]
        meta = payload.get("meta", {})
        close_values = payload.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [float(value) for value in close_values if value is not None]
        if not closes:
            raise ValueError(f"No closing prices returned for {symbol}.")

        info = self._quote_summary(symbol)
        fundamentals = _merge_market_fundamentals(symbol, self._fundamentals(info, meta))
        price = float(meta.get("regularMarketPrice") or closes[-1])
        previous = closes[-2] if len(closes) > 1 else price
        change = ((price - previous) / previous * 100) if previous else 0
        price_info = info.get("price", {})
        profile = info.get("summaryProfile", {})

        return MarketSnapshot(
            symbol=symbol.upper(),
            name=_raw(price_info.get("shortName")) or _raw(price_info.get("longName")) or symbol.upper(),
            market=infer_market(symbol),
            sector=_raw(profile.get("sector")) or _raw(profile.get("industry")) or fallback_sector(symbol),
            price=round(price, 3),
            change=round(change, 2),
            currency=meta.get("currency") or _raw(price_info.get("currency")) or "",
            closes=closes[-130:],
            info=fundamentals,
        )

    def _json(self, url: str) -> dict:
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def _quote_summary(self, symbol: str) -> dict:
        modules = "price,summaryProfile,defaultKeyStatistics,financialData,summaryDetail,calendarEvents,earningsTrend"
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{quote(symbol)}?modules={modules}"
        try:
            payload = self._json(url)
            results = payload.get("quoteSummary", {}).get("result") or []
            return results[0] if results else {}
        except Exception:
            return {}

    def _fundamentals(self, info: dict, meta: dict | None = None) -> dict[str, Any]:
        meta = meta or {}
        stats = info.get("defaultKeyStatistics", {})
        financial = info.get("financialData", {})
        detail = info.get("summaryDetail", {})
        price_info = info.get("price", {})
        return {
            "trailingPE": _raw(detail.get("trailingPE")),
            "forwardPE": _raw(stats.get("forwardPE")),
            "beta": _raw(detail.get("beta")),
            "returnOnEquity": _raw(financial.get("returnOnEquity")),
            "profitMargins": _raw(stats.get("profitMargins")),
            "debtToEquity": _raw(financial.get("debtToEquity")),
            "revenueGrowth": _raw(financial.get("revenueGrowth")),
            "earningsGrowth": _raw(financial.get("earningsGrowth")),
            "grossMargins": _raw(financial.get("grossMargins")),
            "operatingMargins": _raw(financial.get("operatingMargins")),
            "currentRatio": _raw(financial.get("currentRatio")),
            "freeCashflow": _raw(financial.get("freeCashflow")),
            "targetMeanPrice": _raw(financial.get("targetMeanPrice")),
            "recommendationMean": _raw(financial.get("recommendationMean")),
            "recommendationKey": _raw(financial.get("recommendationKey")),
            "numberOfAnalystOpinions": _raw(financial.get("numberOfAnalystOpinions")),
            "marketCap": _raw(price_info.get("marketCap")),
            "dividendYield": _raw(detail.get("dividendYield")),
            "fiftyTwoWeekHigh": _raw(detail.get("fiftyTwoWeekHigh")) or meta.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": _raw(detail.get("fiftyTwoWeekLow")) or meta.get("fiftyTwoWeekLow"),
            "regularMarketVolume": meta.get("regularMarketVolume"),
            "earningsDate": _raw(info.get("calendarEvents", {}).get("earnings", {}).get("earningsDate")),
        }


class RssNewsCrawler:
    user_agent = "OpenStockPicker/0.1 (+https://github.com/open-stock-picker)"

    def fetch(self, symbol: str, name: str, limit: int = 8) -> list[Article]:
        name = local_company_name(symbol, name)
        articles: list[Article] = []
        market = infer_market(symbol)
        urls = [google_news_url(symbol, query) for query in news_queries(symbol, name)]
        if market == "US":
            urls.append(RSS_FEEDS[0].format(symbol=quote_plus(symbol), query=quote_plus(news_query(symbol, name))))
        for url in urls:
            try:
                articles.extend(self._parse_feed(url))
            except Exception:
                continue
        if market in {"CN", "HK", "TW"}:
            articles.extend(self._fetch_eastmoney_stock_news(symbol, name, max(limit * 2, 10)))

        unique: dict[str, Article] = {}
        now = datetime.now(timezone.utc)
        for article in articles:
            if not is_recent_article(article, now):
                continue
            relevance = self._relevance(article, symbol, name)
            if relevance <= 0:
                continue
            article = Article(
                source=article.source,
                title=article.title,
                summary=article.summary,
                link=article.link,
                published_at=article.published_at,
                sentiment=article.sentiment,
                credibility=article.credibility,
                relevance=relevance,
            )
            unique.setdefault(article.link or article.title, article)
        ranked = sorted(unique.values(), key=lambda item: item.credibility * item.relevance * recency_weight(item, now), reverse=True)
        return ranked[:limit]

    def _relevance(self, article: Article, symbol: str, name: str) -> float:
        haystack = f"{article.title} {article.summary}".lower()
        base_symbol = symbol.split(".")[0].lower()
        full_symbol = symbol.lower()
        name_tokens = company_name_tokens(symbol, name)
        phrases = [normalize_company_phrase(candidate) for candidate in company_search_names(symbol, name)]
        if any(phrase and phrase in haystack for phrase in phrases):
            return 1.0
        if name_tokens:
            hits = sum(1 for token in name_tokens[:4] if token in haystack)
            if full_symbol in haystack:
                hits += 1
            return min(1.0, hits / max(1, min(3, len(name_tokens))))
        if base_symbol.isdigit():
            return 1.0 if full_symbol in haystack else 0.0
        return 1.0 if base_symbol in haystack else 0.0

    def _parse_feed(self, url: str) -> list[Article]:
        if feedparser is not None:
            parsed = feedparser.parse(url, request_headers={"User-Agent": self.user_agent})
            source = parsed.feed.get("title", "RSS")
            return [self._article_from_feedparser(entry, source) for entry in parsed.entries[:10]]
        return self._parse_feed_stdlib(url)

    def _article_from_feedparser(self, entry: Any, fallback_source: str) -> Article:
        title = entry.get("title", "")
        summary = clean_summary(entry.get("summary") or entry.get("description") or "")
        published = entry.get("published") or entry.get("updated")
        source = entry.get("source", {})
        if isinstance(source, dict):
            fallback_source = source.get("title", fallback_source)
        return Article(
            source=fallback_source,
            title=title,
            summary=summary,
            link=entry.get("link", ""),
            published_at=parse_datetime(published),
            sentiment=sentiment(f"{title} {summary}"),
            credibility=source_credibility(fallback_source, entry.get("link", "")),
            relevance=1.0,
        )

    def _parse_feed_stdlib(self, url: str) -> list[Article]:
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/rss+xml, application/xml"})
        with urlopen(request, timeout=8) as response:
            root = ElementTree.fromstring(response.read())
        channel = root.find("channel")
        source = xml_text(channel, "title", "RSS") if channel is not None else "RSS"
        articles = []
        for item in root.findall(".//item")[:10]:
            title = xml_text(item, "title", "")
            summary = clean_summary(xml_text(item, "description", ""))
            articles.append(
                Article(
                    source=source,
                    title=title,
                    summary=summary,
                    link=xml_text(item, "link", ""),
                    published_at=parse_datetime(xml_text(item, "pubDate", "")),
                    sentiment=sentiment(f"{title} {summary}"),
                    credibility=source_credibility(source, xml_text(item, "link", "")),
                    relevance=1.0,
                )
            )
        return articles

    def _fetch_eastmoney_stock_news(self, symbol: str, name: str, limit: int = 10) -> list[Article]:
        articles: list[Article] = []
        for keyword in self._eastmoney_news_keywords(symbol, name):
            try:
                articles.extend(self._fetch_eastmoney_keyword_news(keyword, limit))
            except Exception:
                continue
        return articles

    def _eastmoney_news_keywords(self, symbol: str, name: str) -> list[str]:
        keywords = [symbol.split(".")[0]]
        keywords.extend(company_search_names(symbol, name)[:2])
        deduped: list[str] = []
        seen: set[str] = set()
        for keyword in keywords:
            cleaned = str(keyword or "").strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                deduped.append(cleaned)
                seen.add(key)
        return deduped

    def _fetch_eastmoney_keyword_news(self, keyword: str, limit: int = 10) -> list[Article]:
        callback = "jQuery351_stock_picker"
        inner_param = {
            "uid": "",
            "keyword": keyword,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "default",
                    "pageIndex": 1,
                    "pageSize": limit,
                    "preTag": "",
                    "postTag": "",
                }
            },
        }
        params = {
            "cb": callback,
            "param": json.dumps(inner_param, ensure_ascii=False),
            "_": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        }
        url = f"https://search-api-web.eastmoney.com/search/jsonp?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": f"https://so.eastmoney.com/news/s?keyword={quote_plus(keyword)}",
            },
        )
        with urlopen(request, timeout=8) as response:
            text = response.read().decode("utf-8-sig", errors="replace")
        payload = _parse_jsonp(text)
        rows = payload.get("result", {}).get("cmsArticleWebOld", [])
        articles: list[Article] = []
        for row in rows[:limit]:
            title = clean_summary(str(row.get("title") or ""))
            summary = clean_summary(str(row.get("content") or ""))
            if not title and not summary:
                continue
            link = str(row.get("url") or "")
            if not link and row.get("code"):
                link = f"http://finance.eastmoney.com/a/{row.get('code')}.html"
            source = str(row.get("mediaName") or "Eastmoney")
            articles.append(
                Article(
                    source=source,
                    title=title,
                    summary=summary,
                    link=link,
                    published_at=_parse_eastmoney_datetime(row.get("date")),
                    sentiment=sentiment(f"{title} {summary}"),
                    credibility=source_credibility(source, link),
                    relevance=1.0,
                )
            )
        return articles


def xml_text(node: ElementTree.Element | None, tag: str, default: str) -> str:
    if node is None:
        return default
    child = node.find(tag)
    return child.text if child is not None and child.text else default


def clean_summary(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def _parse_jsonp(text: str) -> dict[str, Any]:
    start = text.find("(")
    end = text.rfind(")")
    if start >= 0 and end > start:
        text = text[start + 1 : end]
    payload = json.loads(text)
    return payload if isinstance(payload, dict) else {}


def _parse_eastmoney_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    china_tz = timezone(timedelta(hours=8))
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, pattern).replace(tzinfo=china_tz)
        except ValueError:
            continue
    return parse_datetime(text)


def _raw(value: Any) -> Any:
    if isinstance(value, dict) and "raw" in value:
        return value["raw"]
    return value


def _merge_market_fundamentals(symbol: str, info: dict[str, Any]) -> dict[str, Any]:
    fallback = _eastmoney_cn_fundamentals(symbol)
    if not fallback:
        return info
    merged = dict(fallback)
    merged.update({key: value for key, value in info.items() if value not in (None, "", "-")})
    return merged


def _eastmoney_cn_fundamentals(symbol: str) -> dict[str, Any]:
    market = infer_market(symbol)
    if market != "CN":
        return {}

    upper = symbol.upper()
    code = upper.split(".")[0]
    secid_prefix = "1" if upper.endswith(".SS") else "0"
    fields = "f57,f58,f47,f48,f116,f117,f162,f167,f168,f170"
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid_prefix}.{quote(code)}&fields={fields}"
    try:
        request = Request(url, headers={"User-Agent": YahooHttpMarketDataProvider.user_agent, "Accept": "application/json,text/plain,*/*"})
        with urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8-sig")).get("data") or {}
    except Exception:
        return {}

    pe = _eastmoney_scaled(data.get("f162"))
    pb = _eastmoney_scaled(data.get("f167"))
    turnover = _eastmoney_scaled(data.get("f168"))
    change = _eastmoney_scaled(data.get("f170"))
    volume = _eastmoney_number(data.get("f47"))
    return {
        "shortName": data.get("f58"),
        "trailingPE": pe if pe and pe > 0 else None,
        "priceToBook": pb if pb and pb > 0 else None,
        "turnoverRate": turnover / 100 if turnover is not None else None,
        "regularMarketChangePercent": change / 100 if change is not None else None,
        "regularMarketVolume": volume * 100 if volume else None,
        "turnoverValue": _eastmoney_number(data.get("f48")),
        "marketCap": _eastmoney_number(data.get("f116")),
        "floatMarketCap": _eastmoney_number(data.get("f117")),
    }


def _eastmoney_scaled(value: Any) -> float | None:
    number = _eastmoney_number(value)
    if number in (None, 0):
        return None
    return number / 100


def _eastmoney_number(value: Any) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def company_name_tokens(symbol: str, name: str) -> list[str]:
    names = company_search_names(symbol, name)
    stop_words = {
        "inc",
        "corp",
        "corporation",
        "limited",
        "ltd",
        "plc",
        "holdings",
        "holding",
        "company",
        "group",
        "bank",
        "airlines",
        "airline",
        "singapore",
        "china",
        "hong",
        "kong",
        "taiwan",
        "co",
        "stock",
    }
    tokens = []
    for cleaned_name in names:
        for part in cleaned_name.replace("-", " ").replace(",", " ").split():
            token = part.strip(".,:;!?()[]'\"").lower()
            if token and _has_cjk(token) and len(token) >= 2:
                tokens.append(token)
            elif len(token) >= 4 and token not in stop_words:
                tokens.append(token)
    return tokens


def news_queries(symbol: str, name: str) -> list[str]:
    market = infer_market(symbol)
    search_names = company_search_names(symbol, name)[:3]
    base_queries = [news_query(symbol, search_name) for search_name in search_names] or [news_query(symbol, name)]
    base = base_queries[0]
    source_terms = {
        "CN": ["site:finance.eastmoney.com", "site:stcn.com", "site:cnstock.com", "site:wallstreetcn.com", "site:sina.com.cn/finance"],
        "TW": ["site:cnyes.com", "site:moneydj.com", "site:tw.stock.yahoo.com"],
        "HK": ["site:aastocks.com", "site:etnet.com.hk", "site:hket.com", "site:hk.finance.yahoo.com", "site:futunn.com"],
        "SG": ["site:businesstimes.com.sg", "site:straitstimes.com", "site:channelnewsasia.com", "site:sg.finance.yahoo.com"],
        "US": ["site:reuters.com", "site:finance.yahoo.com", "site:marketwatch.com"],
    }.get(market, [])
    queries = [*base_queries, *[f"{base} {term}" for term in source_terms]]
    name = search_names[0] if search_names else local_company_name(symbol, name)
    if market == "CN":
        queries.extend([f'"{name}" A股 公告 业绩', f'"{name}" 股价 研报 财报'])
    elif market == "HK":
        queries.extend([f'"{name}" 港股 業績 公告', f'"{name}" 股價 目標價'])
    elif market == "TW":
        queries.extend([f'"{name}" 台股 法說 財報', f'"{name}" 股價 營收'])
    elif market == "SG":
        queries.extend([f'"{name}" Singapore stock earnings', f'"{name}" SGX results dividend'])
    return list(dict.fromkeys(queries))


def news_query(symbol: str, name: str) -> str:
    tokens = company_name_tokens(symbol, name)
    phrase = company_phrase(symbol, name)
    if phrase or tokens:
        company = phrase or " ".join(tokens[:4])
        if infer_market(symbol) in {"CN", "HK", "TW"}:
            return f'"{company}" 股票 財報 業績 OR "{symbol}"'
        return f'"{company}" OR "{symbol}" stock earnings revenue'
    return f'"{symbol}" stock earnings revenue'


def google_news_url(symbol: str, query_text: str) -> str:
    locale = {
        "CN": ("zh-CN", "CN", "CN:zh-Hans"),
        "HK": ("zh-HK", "HK", "HK:zh-Hant"),
        "TW": ("zh-TW", "TW", "TW:zh-Hant"),
        "SG": ("en-SG", "SG", "SG:en"),
        "US": ("en-US", "US", "US:en"),
    }.get(infer_market(symbol), ("en-US", "US", "US:en"))
    hl, gl, ceid = locale
    return f"https://news.google.com/rss/search?q={quote_plus(query_text)}&hl={hl}&gl={gl}&ceid={ceid}"


def is_recent_article(article: Article, now: datetime | None = None) -> bool:
    if article.published_at is None:
        return False
    current = now or datetime.now(timezone.utc)
    age_hours = (current - article.published_at.astimezone(timezone.utc)).total_seconds() / 3600
    return 0 <= age_hours <= MAX_ARTICLE_AGE_HOURS


def recency_weight(article: Article, now: datetime | None = None) -> float:
    if article.published_at is None:
        return 0.0
    current = now or datetime.now(timezone.utc)
    age_hours = max(0, (current - article.published_at.astimezone(timezone.utc)).total_seconds() / 3600)
    return max(0.2, 1 - age_hours / MAX_ARTICLE_AGE_HOURS)


def _has_cjk(text: str) -> bool:
    return any("\u3400" <= char <= "\u9fff" for char in text)


def company_phrase(symbol: str, name: str) -> str:
    if not name or name.upper() == symbol.upper():
        name = company_search_names(symbol, name)[0] if company_search_names(symbol, name) else ""
    if not name or name.upper() == symbol.upper():
        return ""
    return normalize_company_phrase(name)


def normalize_company_phrase(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name.replace(",", " ")).strip().lower()
    suffixes = [" inc", " corporation", " corp", " co ltd", " co. ltd", " limited", " holdings", " holding", " plc"]
    for suffix in suffixes:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned


def sentiment(text: str) -> float:
    lower = text.lower()
    phrase_score = sum(2 for phrase in POSITIVE_PHRASES if phrase.lower() in lower) - sum(2 for phrase in NEGATIVE_PHRASES if phrase.lower() in lower)
    cjk_score = sum(1 for word in POSITIVE_WORDS if _has_cjk(word) and word in text) - sum(1 for word in NEGATIVE_WORDS if _has_cjk(word) and word in text)
    tokens = {part.strip(".,:;!?()[]'\"").lower() for part in text.split()}
    token_score = sum(1 for word in tokens if word in POSITIVE_WORDS) - sum(1 for word in tokens if word in NEGATIVE_WORDS)
    return max(-1.0, min(1.0, (phrase_score + cjk_score + token_score) / 6))


def source_credibility(source: str, link: str = "") -> float:
    text = f"{source} {link}".lower()
    for needle, score in SOURCE_CREDIBILITY.items():
        if needle.lower() in text:
            return score
    return 0.66


def volatility_score(closes: list[float]) -> float:
    if len(closes) < 22:
        return 50
    returns = [(closes[index] - closes[index - 1]) / closes[index - 1] for index in range(1, len(closes)) if closes[index - 1]]
    if len(returns) < 2:
        return 50
    avg = sum(returns) / len(returns)
    variance = sum((value - avg) ** 2 for value in returns) / (len(returns) - 1)
    annualized = sqrt(variance) * sqrt(252)
    return max(0, min(100, 100 - annualized * 180))
