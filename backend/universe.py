from __future__ import annotations

import html as html_lib
import json
import re
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import quote_plus, urljoin, urlparse
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
    sentiment,
    source_credibility,
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
    "JP": [
        "7203.T",
        "6758.T",
        "8306.T",
        "6861.T",
        "9984.T",
        "6098.T",
        "9432.T",
        "8035.T",
        "9983.T",
        "7974.T",
        "Toyota Motor Japan",
        "Sony Group Japan",
        "Mitsubishi UFJ Japan",
        "Keyence Japan",
        "SoftBank Group Japan",
        "Recruit Holdings Japan",
        "NTT Japan",
        "Tokyo Electron Japan",
        "Fast Retailing Japan",
        "Nintendo Japan",
    ],
    "KR": [
        "005930.KS",
        "000660.KS",
        "035420.KS",
        "051910.KS",
        "005380.KS",
        "006400.KS",
        "068270.KS",
        "035720.KS",
        "207940.KS",
        "373220.KS",
        "Samsung Electronics Korea",
        "SK hynix Korea",
        "NAVER Korea",
        "LG Chem Korea",
        "Hyundai Motor Korea",
        "Samsung SDI Korea",
        "Celltrion Korea",
        "Kakao Korea",
        "Samsung Biologics Korea",
        "LG Energy Solution Korea",
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
    "JP": [
        "7203.T",
        "6758.T",
        "8306.T",
        "6861.T",
        "9984.T",
        "6098.T",
        "9432.T",
        "8035.T",
        "9983.T",
        "7974.T",
    ],
    "KR": [
        "005930.KS",
        "000660.KS",
        "035420.KS",
        "051910.KS",
        "005380.KS",
        "006400.KS",
        "068270.KS",
        "035720.KS",
        "207940.KS",
        "373220.KS",
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
    "JP": [
        "日本株 決算 業績 上方修正",
        "東証 上場企業 株価 決算",
        "site:nikkei.com 日本株 決算",
        "site:kabutan.jp 決算 業績",
    ],
    "KR": [
        "한국 주식 실적 주가 목표주가",
        "코스피 코스닥 상장사 실적",
        "site:mk.co.kr 주식 실적",
        "site:businesskorea.co.kr stock earnings",
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

LOCAL_MARKET_NEWS_URLS = {
    "CN": [
        "https://roll.eastmoney.com/stock.html",
        "https://finance.eastmoney.com/a/cgsxw.html",
        "https://www.cnstock.com/",
    ],
    "HK": [
        "https://www.aastocks.com/en/stocks/news/aafn/latest-news",
        "https://www.aastocks.com/tc/stocks/news/aafn/latest-news",
    ],
    "TW": [
        "https://news.cnyes.com/news/cat/tw_stock_news",
        "https://www.moneydj.com/KMDJ/News/NewsRealList.aspx",
    ],
    "JP": [
        "https://finance.yahoo.co.jp/news",
        "https://kabutan.jp/news/marketnews/",
    ],
    "KR": [
        "https://www.koreaherald.com/list.php?ct=020000000000",
        "https://www.businesskorea.co.kr/news/articleList.html?sc_section_code=S1N1",
    ],
    "SG": [
        "https://www.businesstimes.com.sg/rss/companies-markets",
        "https://www.businesstimes.com.sg/rss/reits-property",
        "https://www.businesstimes.com.sg/rss/transport-logistics",
        "https://www.channelnewsasia.com/business",
    ],
    "US": [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.cnbc.com/id/15839135/device/rss/rss.html",
        "https://www.marketwatch.com/rss/topstories",
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
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

    def resolve_manual_inputs(self, inputs: Iterable[str], markets: Iterable[str], limit: int = 25) -> tuple[list[DiscoveredSymbol], list[dict]]:
        allowed_markets = set(markets or configured_markets())
        resolved: list[DiscoveredSymbol] = []
        errors: list[dict] = []
        seen = set()

        for raw_value in inputs:
            query = str(raw_value or "").strip()
            if not query:
                continue

            candidates = self._resolve_manual_input(query, allowed_markets)
            if not candidates:
                errors.append(
                    {
                        "market": ",".join(sorted(allowed_markets)),
                        "source": "manual-resolve",
                        "query": query,
                        "error": "No matching listed equity was found for this code or company name.",
                    }
                )
                continue

            for item in candidates:
                if item.symbol in seen:
                    continue
                resolved.append(item)
                seen.add(item.symbol)
                if len(resolved) >= limit:
                    return resolved, errors

        return resolved, errors

    def _resolve_manual_input(self, query: str, allowed_markets: set[str]) -> list[DiscoveredSymbol]:
        symbol_candidates = _manual_symbol_candidates(query, allowed_markets)
        if symbol_candidates:
            return [self._manual_symbol(symbol) for symbol in symbol_candidates]

        candidates: list[DiscoveredSymbol] = []
        for market in _preferred_manual_markets(allowed_markets):
            if market in {"CN", "HK"}:
                candidates.extend(self._search_eastmoney_term(query, market))
            candidates.extend(self._search_yahoo_term(query, market))
        return _dedupe_discovered([item for item in candidates if item.market in allowed_markets])

    def _manual_symbol(self, symbol: str) -> DiscoveredSymbol:
        market = infer_market(symbol)
        name = local_company_name(symbol, "")
        if not name:
            for term in [symbol, symbol.split(".")[0]]:
                resolved: list[DiscoveredSymbol] = []
                if market in {"CN", "HK"}:
                    resolved.extend(self._search_eastmoney_term(term, market))
                resolved.extend(self._search_yahoo_term(term, market))
                match = next((item for item in resolved if item.symbol == symbol), None)
                if match:
                    name = match.name
                    break
        return DiscoveredSymbol(symbol=symbol, name=name or symbol, market=market, source="manual-resolve")

    def discover(self, markets: Iterable[str], limit_per_market: int = 18) -> tuple[list[DiscoveredSymbol], list[dict]]:
        symbols: list[DiscoveredSymbol] = []
        errors: list[dict] = []
        for market in markets:
            source_results: list[tuple[str, list[DiscoveredSymbol]]] = []
            for source, discover, empty_message in [
                ("local-news", self._discover_local_market_news, "No recent company mentions were extracted from local market news."),
                ("google-news", self._discover_google_market_news, "No recent company mentions were extracted from Google News."),
                ("market-universe", self._discover_market, "No live market-universe symbols were returned."),
            ]:
                try:
                    candidates = discover(market, max(limit_per_market, min(limit_per_market * 2, 240)))
                except Exception as exc:
                    errors.append({"market": market, "source": source, "error": str(exc)})
                    continue

                if not candidates:
                    errors.append({"market": market, "source": source, "error": empty_message})
                    continue

                source_results.append((source, candidates))

            if _unique_symbol_count(source_results) < limit_per_market:
                try:
                    fallback_candidates = self._discover_fallback_search(market, limit_per_market)
                except Exception as exc:
                    errors.append({"market": market, "source": "fallback-search", "error": str(exc)})
                    fallback_candidates = []
                if fallback_candidates:
                    source_results.append(("fallback-search", fallback_candidates))
                else:
                    errors.append({"market": market, "source": "fallback-search", "error": "No fallback symbols were available."})

            market_symbols = _blend_discovery_sources(source_results, limit_per_market)
            symbols.extend(market_symbols[:limit_per_market])

        seen = set()
        deduped = []
        for item in symbols:
            if item.symbol not in seen:
                deduped.append(item)
                seen.add(item.symbol)
        return deduped, errors

    def _discover_local_market_news(self, market: str, limit: int) -> list[DiscoveredSymbol]:
        crawler = RssNewsCrawler()
        articles: list[Article] = []
        for url in LOCAL_MARKET_NEWS_URLS.get(market, []):
            parsed: list[Article] = []
            try:
                parsed = crawler._parse_feed(url)
            except Exception:
                parsed = []
            if parsed:
                articles.extend(parsed)
                continue
            try:
                articles.extend(self._parse_html_news_page(url))
            except Exception:
                continue
        return self._symbols_from_news_articles(market, articles, limit, source="local-news")

    def _discover_google_market_news(self, market: str, limit: int) -> list[DiscoveredSymbol]:
        crawler = RssNewsCrawler()
        articles = []
        for query in MARKET_NEWS_QUERIES.get(market, []):
            try:
                articles.extend(crawler._parse_feed(google_news_url(_market_locale_symbol(market), query)))
            except Exception:
                continue
        return self._symbols_from_news_articles(market, articles, limit, source="google-news")

    def _parse_html_news_page(self, url: str, limit: int = 100) -> list[Article]:
        context = ssl._create_unverified_context() if "moneydj.com" in urlparse(url).netloc else None
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "text/html,*/*"})
        with urlopen(request, timeout=12, context=context) as response:
            payload = response.read(350000)
            charset = response.headers.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        articles: list[Article] = []
        for match in re.finditer(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", text, flags=re.IGNORECASE | re.DOTALL):
            attrs = match.group("attrs")
            href = _html_attr(attrs, "href")
            if not href or href.startswith(("#", "javascript:", "mailto:")):
                continue
            title = _clean_html_text(_html_attr(attrs, "title") or match.group("body"))
            if not _looks_like_news_title(title):
                continue
            link = urljoin(url, html_lib.unescape(href))
            source = urlparse(link).netloc or urlparse(url).netloc
            articles.append(
                Article(
                    source=source,
                    title=title,
                    summary="",
                    link=link,
                    published_at=datetime.now(timezone.utc),
                    sentiment=sentiment(title),
                    credibility=source_credibility(source, link),
                    relevance=1.0,
                )
            )
            if len(articles) >= limit:
                break
        return _dedupe_articles(articles)

    def _symbols_from_news_articles(self, market: str, articles: list[Article], limit: int, source: str = "market-news") -> list[DiscoveredSymbol]:
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
                source=source,
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
            security_type_name = str(row.get("SecurityTypeName") or "").upper()
            symbol = ""
            is_hk = classify == "HK" or jys == "HK" or "HK" in security_type_name or "港" in security_type_name
            if market == "HK" and is_hk and code.isdigit():
                symbol = f"{int(code):04d}.HK"
            elif market == "CN" and code.isdigit() and is_common_equity_symbol(f"{code}.SS" if code.startswith('6') else f"{code}.SZ", "CN"):
                symbol = f"{code}.SS" if code.startswith("6") else f"{code}.SZ"
            if symbol:
                name = _repair_mojibake(str(row.get("Name") or term))
                output.append(
                    DiscoveredSymbol(
                        symbol=symbol,
                        name=local_company_name(symbol, name),
                        market=market,
                        source=f"market-news-eastmoney:{term}",
                    )
                )
        return output

    def _discover_market(self, market: str, limit: int) -> list[DiscoveredSymbol]:
        if market == "US":
            return self._discover_us(limit)
        if market == "CN":
            return self._discover_cn_online(limit)
        if market == "HK":
            return self._discover_eastmoney_hk(limit)
        if market == "TW":
            return self._discover_twse(limit)
        if market in {"JP", "KR"}:
            return self._discover_fallback_search(market, limit)
        if market == "SG":
            return self._discover_sgx(limit)
        return []

    def _discover_cn_online(self, limit: int) -> list[DiscoveredSymbol]:
        output: list[DiscoveredSymbol] = []
        for discover in [self._discover_sina_cn, self._discover_eastmoney_cn]:
            try:
                output = _merge_unique_symbols(output, discover(limit))
            except Exception:
                continue
            if len(output) >= limit:
                break
        return output[:limit]

    def _discover_fallback_search(self, market: str, limit: int) -> list[DiscoveredSymbol]:
        output: list[DiscoveredSymbol] = []
        if market == "CN":
            try:
                output = _merge_unique_symbols(output, self._discover_cn_online(limit))
            except Exception:
                output = []
        for term in FALLBACK_SEARCH_TERMS.get(market, []):
            try:
                url = f"https://query1.finance.yahoo.com/v1/finance/search?q={quote_plus(term)}&quotesCount=8&newsCount=0"
                payload = self._json(url, timeout=6, attempts=2)
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
        sources = [
            ("f10", "eastmoney-cn-volume-ratio"),
            ("f6", "eastmoney-cn-turnover"),
            ("f3", "eastmoney-cn-gainers-risk-review"),
        ]
        output: list[DiscoveredSymbol] = []
        for sort_field, source in sources:
            try:
                output = _merge_unique_symbols(output, self._discover_eastmoney_cn_sorted(sort_field, source, max(limit, 18)))
            except Exception:
                continue
            if len(output) >= limit:
                break
        return output[:limit]

    def _discover_sina_cn(self, limit: int) -> list[DiscoveredSymbol]:
        output: list[DiscoveredSymbol] = []
        page_size = min(80, max(30, limit))
        max_pages = max(1, min(5, (limit * 2 + page_size - 1) // page_size))
        for sort_field, source in [("amount", "sina-cn-turnover"), ("turnoverratio", "sina-cn-turnover-ratio")]:
            for page in range(1, max_pages + 1):
                url = (
                    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                    "Market_Center.getHQNodeData?page={page}&num={page_size}&sort={sort_field}"
                    "&asc=0&node=hs_a&symbol=&_s_r_a=page"
                ).format(page=page, page_size=page_size, sort_field=sort_field)
                try:
                    rows = self._json(url, timeout=8, attempts=2)
                except Exception:
                    if output:
                        break
                    raise
                if not isinstance(rows, list) or not rows:
                    break
                for row in rows:
                    code = str(row.get("code") or "").strip()
                    if not code.isdigit():
                        symbol_text = str(row.get("symbol") or "").lower()
                        code = re.sub(r"^(?:sh|sz)", "", symbol_text)
                    if not code.isdigit():
                        continue
                    symbol = f"{code}.SS" if code.startswith("6") else f"{code}.SZ"
                    if not is_common_equity_symbol(symbol, "CN"):
                        continue
                    output.append(
                        DiscoveredSymbol(
                            symbol=symbol,
                            name=str(row.get("name") or code),
                            market="CN",
                            source=source,
                        )
                    )
                    if len(output) >= limit:
                        break
                if len(output) >= limit:
                    break
            if len(output) >= limit:
                break
        return _dedupe_discovered(output)[:limit]

    def _discover_eastmoney_cn_sorted(self, sort_field: str, source: str, limit: int) -> list[DiscoveredSymbol]:
        output = []
        page_size = min(80, max(30, limit))
        max_pages = max(1, min(5, (limit * 2 + page_size - 1) // page_size))
        for page in range(1, max_pages + 1):
            url = (
                "https://push2.eastmoney.com/api/qt/clist/get"
                "?pn={page}&pz={page_size}&po=1&np=1&fltt=2&invt=2&fid={sort_field}"
                "&fs=m:1+t:2,m:0+t:6,m:0+t:80&fields=f12,f14,f3,f6,f10"
            ).format(page=page, page_size=page_size, sort_field=sort_field)
            try:
                rows = self._json(url, timeout=6, attempts=2).get("data", {}).get("diff", [])
            except Exception:
                if output:
                    break
                raise
            if not rows:
                break
            for row in rows:
                code = str(row.get("f12") or "")
                if not code.isdigit():
                    continue
                suffix = ".SS" if code.startswith("6") else ".SZ"
                symbol = f"{code}{suffix}"
                if not is_common_equity_symbol(symbol, "CN"):
                    continue
                output.append(DiscoveredSymbol(symbol=symbol, name=str(row.get("f14") or code), market="CN", source=source))
                if len(output) >= limit:
                    break
            if len(output) >= limit:
                break
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
        seen = set()
        deduped = []
        for item in output:
            if item.symbol not in seen:
                deduped.append(item)
                seen.add(item.symbol)
        return deduped[:limit]

    def _json(self, url: str, insecure: bool = False, timeout: int = 12, attempts: int = 3) -> dict | list:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://quote.eastmoney.com/",
        }
        context = ssl._create_unverified_context() if insecure else None
        last_error = None
        for attempt in range(attempts):
            try:
                request = Request(url, headers=headers)
                with urlopen(request, timeout=timeout, context=context) as response:
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
    if market == "JP":
        return base.isdigit() and len(base) == 4 and symbol.upper().endswith(".T")
    if market == "KR":
        return base.isdigit() and len(base) == 6 and symbol.upper().endswith((".KS", ".KQ"))
    return True


def configured_markets() -> list[str]:
    return [market["id"] for market in MARKETS]


def _market_locale_symbol(market: str) -> str:
    return {
        "CN": "600519.SS",
        "HK": "0700.HK",
        "JP": "7203.T",
        "KR": "005930.KS",
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
    if market == "JP":
        return [f"{code}.T" for code in re.findall(r"(?<!\d)(\d{4})\.?t(?![a-z0-9])", text)]
    if market == "KR":
        return [
            f"{code}.{suffix.upper()}"
            for code, suffix in re.findall(r"(?<!\d)(\d{6})\.?(ks|kq)(?![a-z0-9])", text)
        ]
    if market == "SG":
        return [f"{code.upper()}.SI" for code in re.findall(r"(?<![a-z0-9])([a-z0-9]{3,4})\.?si(?![a-z0-9])", text)]
    return []


def _manual_symbol_candidates(query: str, allowed_markets: set[str]) -> list[str]:
    normalized = query.strip().upper()
    if not normalized:
        return []

    if re.fullmatch(r"\d{6}\.(?:SS|SZ)", normalized):
        symbol = normalized
        market = infer_market(symbol)
        return [symbol] if market in allowed_markets and is_common_equity_symbol(symbol, market) else []

    if re.fullmatch(r"\d{6}", normalized) and "CN" in allowed_markets:
        symbol = f"{normalized}.SS" if normalized.startswith("6") else f"{normalized}.SZ"
        return [symbol] if is_common_equity_symbol(symbol, "CN") else []

    if re.fullmatch(r"\d{4,5}\.HK", normalized):
        symbol = f"{int(normalized.split('.')[0]):04d}.HK"
        return [symbol] if "HK" in allowed_markets and is_common_equity_symbol(symbol, "HK") else []

    if re.fullmatch(r"\d{4}\.TW", normalized):
        return [normalized] if "TW" in allowed_markets else []

    if re.fullmatch(r"\d{4}\.T", normalized):
        return [normalized] if "JP" in allowed_markets else []

    if re.fullmatch(r"\d{6}\.(?:KS|KQ)", normalized):
        symbol = normalized
        market = infer_market(symbol)
        return [symbol] if market in allowed_markets and is_common_equity_symbol(symbol, market) else []

    if re.fullmatch(r"[A-Z0-9]{2,5}\.SI", normalized):
        return [normalized] if "SG" in allowed_markets else []

    if re.fullmatch(r"\d{4,5}", normalized):
        known_symbols = set(LOCAL_COMPANY_NAMES)
        for symbols in [*CURATED_FALLBACK_SYMBOLS.values(), *DEFAULT_SYMBOLS.values()]:
            known_symbols.update(symbols)
        market_symbols = []
        if len(normalized) == 4:
            market_symbols.extend([("TW", f"{normalized}.TW"), ("JP", f"{normalized}.T")])
        if "HK" in allowed_markets:
            market_symbols.append(("HK", f"{int(normalized):04d}.HK"))
        for market, symbol in market_symbols:
            if market in allowed_markets and symbol in known_symbols and is_common_equity_symbol(symbol, market):
                return [symbol]
        if "JP" in allowed_markets and "TW" not in allowed_markets and "HK" not in allowed_markets and len(normalized) == 4:
            return [f"{normalized}.T"]
        if "TW" in allowed_markets and "HK" not in allowed_markets and len(normalized) == 4:
            return [f"{normalized}.TW"]
        if "HK" in allowed_markets:
            symbol = f"{int(normalized):04d}.HK"
            return [symbol] if is_common_equity_symbol(symbol, "HK") else []

    if re.fullmatch(r"\d{6}", normalized) and "KR" in allowed_markets and "CN" not in allowed_markets:
        return [f"{normalized}.KS"]

    if re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", normalized) and "." not in normalized and "US" in allowed_markets:
        return [normalized]

    return []


def _preferred_manual_markets(allowed_markets: set[str]) -> list[str]:
    preferred = ["CN", "HK", "TW", "JP", "KR", "SG", "US"]
    return [market for market in preferred if market in allowed_markets]


def _html_attr(attrs: str, name: str) -> str:
    match = re.search(rf"{name}\s*=\s*([\"'])(.*?)\1", attrs, flags=re.IGNORECASE | re.DOTALL)
    return match.group(2).strip() if match else ""


def _clean_html_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    for _ in range(2):
        text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_news_title(title: str) -> bool:
    if not 8 <= len(title) <= 180:
        return False
    lower = title.lower()
    navigation = {
        "about us",
        "advertise",
        "contact us",
        "home",
        "latest",
        "latest news",
        "login",
        "market+ (android)",
        "market+ (iphone)",
        "mobile site",
        "privacy policy",
        "quote service",
        "register",
        "search",
        "skip to main content",
        "subscribe",
        "terms of service",
        "top stories",
    }
    if lower in navigation:
        return False
    if lower.startswith(("skip to ", "copyright ", "all rights reserved")):
        return False
    return bool(re.search(r"[A-Za-z0-9\u3400-\u9fff]", title))


def _company_terms_from_article(text: str, market: str) -> list[str]:
    terms = []

    if market in {"CN", "HK", "TW"}:
        patterns = [
            r"([\u4e00-\u9fffA-Za-z0-9]{2,8}?)(?:等\d*股|披露|擬|拟|增持|減持|减持|漲停|涨停|復牌|复牌|業績|业绩|股價|股价|股份|公司)",
            r"^([\u4e00-\u9fffA-Za-z0-9]{2,8})(?:衝|冲|聚焦|攜手|携手|布局|大漲|大涨|下跌|上漲|上涨|跌|漲|涨|獲|获|推|宣布|看好|營收|营收|法說|法说)",
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

    if market in {"HK", "SG"}:
        terms.extend(_english_company_terms_from_article(text))

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


def _english_company_terms_from_article(text: str) -> list[str]:
    terms = []
    headline = re.sub(r"\s+", " ", text).strip()
    prefix = re.split(
        r"\b(?:repurchases?|buys?|sells?|posts?|reports?|announces?|declares?|launches?|raises?|cuts?|wins?|secures?|jumps?|surges?|falls?|drops?|slides?|plans?|to\s)\b",
        headline,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    if 2 <= len(prefix) <= 36:
        terms.append(prefix)

    colon_parts = re.split(r"[:：]", headline, maxsplit=1)
    if len(colon_parts) == 2 and len(colon_parts[1]) <= 90:
        terms.extend(part.strip() for part in re.split(r"[,;/]", colon_parts[1])[:4])

    cleaned = []
    seen = set()
    stop_terms = {"market", "markets", "stocks", "shares", "company", "companies", "earnings", "results", "latest news"}
    for term in terms:
        term = re.sub(r"\([^)]*\)", "", term)
        term = re.sub(r"[^A-Za-z0-9&'. -]", " ", term)
        term = re.sub(r"\b(?:HK|SG|Singapore|Hong Kong|shares?|stocks?)\b", " ", term, flags=re.IGNORECASE)
        term = re.sub(r"\s+", " ", term).strip(" -'\".")
        key = term.lower()
        if 2 <= len(term) <= 32 and key not in stop_terms and key not in seen:
            cleaned.append(term)
            seen.add(key)
    return cleaned[:6]


def _dedupe_articles(articles: list[Article]) -> list[Article]:
    output = []
    seen = set()
    for article in articles:
        key = article.link or article.title
        if key not in seen:
            output.append(article)
            seen.add(key)
    return output


def _dedupe_discovered(items: list[DiscoveredSymbol]) -> list[DiscoveredSymbol]:
    output = []
    seen = set()
    for item in items:
        if item.symbol in seen:
            continue
        output.append(item)
        seen.add(item.symbol)
    return output


def _repair_mojibake(value: str) -> str:
    if not value:
        return value
    if re.search(r"[\u3400-\u9fff]", value):
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return repaired if re.search(r"[\u3400-\u9fff]", repaired) else value


def _merge_unique_symbols(existing: list[DiscoveredSymbol], candidates: list[DiscoveredSymbol]) -> list[DiscoveredSymbol]:
    seen = {item.symbol for item in existing}
    output = [*existing]
    for item in candidates:
        if item.symbol not in seen:
            output.append(item)
            seen.add(item.symbol)
    return output


def _unique_symbol_count(source_results: list[tuple[str, list[DiscoveredSymbol]]]) -> int:
    return len({item.symbol for _, candidates in source_results for item in candidates})


def _blend_discovery_sources(source_results: list[tuple[str, list[DiscoveredSymbol]]], limit: int) -> list[DiscoveredSymbol]:
    if limit <= 0:
        return []
    source_shares = {
        "local-news": 0.30,
        "google-news": 0.22,
        "market-universe": 0.38,
        "fallback-search": 0.10,
    }
    output: list[DiscoveredSymbol] = []
    seen = set()
    leftovers: list[DiscoveredSymbol] = []

    for source, candidates in source_results:
        quota = max(1, round(limit * source_shares.get(source, 0.15)))
        taken = 0
        for item in candidates:
            if item.symbol in seen:
                continue
            if taken < quota and len(output) < limit:
                output.append(item)
                seen.add(item.symbol)
                taken += 1
            else:
                leftovers.append(item)

    for item in leftovers:
        if len(output) >= limit:
            break
        if item.symbol in seen:
            continue
        output.append(item)
        seen.add(item.symbol)
    return output[:limit]
