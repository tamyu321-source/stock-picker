import io
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ["API_ACCESS_KEYS"] = ""

from backend.app import create_app
from backend.cache import CachedMarketDataProvider, CachedNewsCrawler, TtlCache
from backend.portfolio import normalize_a_share_symbol, parse_portfolio_export
from backend.providers import Article, EastmoneyCnMarketDataProvider, MarketSnapshot, RssNewsCrawler, TaiwanExchangeMarketDataProvider, YahooHttpMarketDataProvider, _eastmoney_cn_fund_flow, _parse_eastmoney_datetime, _sina_cn_fund_flow, fallback_market_data_provider, infer_market, is_recent_article, local_company_name, news_queries, news_query
from backend.market_profiles import market_preferred_source_shares
from backend.services import _breakout_setup_score, _financial_analysis, _friendly_data_error, _fund_flow_profile, _metric_availability, _metrics, _news_analysis, _news_heat_analysis, _pullback_risk_score, _score_breakdown, _sentiment_score, _verdict
from backend.strategy_library import get_strategy_catalog
from backend.universe import DiscoveredSymbol, MarketUniverseProvider, is_common_equity_symbol, _manual_symbol_candidates, _symbols_from_code_mentions


class FakeMarketProvider:
    def fetch(self, symbol):
        return MarketSnapshot(
            symbol=symbol,
            name="Test Corp",
            market="TW" if symbol.endswith(".TW") else "US",
            sector="Technology",
            price=100.0,
            change=1.4,
            currency="TWD" if symbol.endswith(".TW") else "USD",
            closes=[80 + index * 0.2 for index in range(130)],
            info={"trailingPE": 20, "beta": 1.05, "returnOnEquity": 0.18, "profitMargins": 0.22, "debtToEquity": 30},
        )


class LowRiskFakeMarketProvider(FakeMarketProvider):
    def fetch(self, symbol):
        snapshot = super().fetch(symbol)
        closes = [92 + index * 0.08 + [0.0, 0.18, -0.06, 0.10, -0.12][index % 5] for index in range(130)]
        previous = closes[-2]
        price = closes[-1]
        return MarketSnapshot(
            symbol=snapshot.symbol,
            name=snapshot.name,
            market=snapshot.market,
            sector=snapshot.sector,
            price=round(price, 3),
            change=round((price / previous - 1) * 100, 2) if previous else 0,
            currency=snapshot.currency,
            closes=closes,
            info={**snapshot.info, "beta": 1.0},
        )


class FakeNewsCrawler:
    def __init__(self):
        self.calls = []

    def fetch(self, symbol, name):
        self.calls.append((symbol, name))
        return [
            Article(
                source="Test RSS",
                title=f"{name} reports strong growth",
                summary=f"{name} revenue beats expectations",
                link="https://example.com/story",
                published_at=datetime.now(timezone.utc),
                sentiment=0.5,
                credibility=0.8,
                relevance=1.0,
            )
        ]


class FakeUniverseProvider:
    def discover(self, markets, limit_per_market=18):
        symbols = []
        for market in markets:
            if market == "TW":
                symbols.extend(
                    [
                        DiscoveredSymbol("9999.TW", "Dynamic Taiwan Semiconductor", "TW", "test-search"),
                        DiscoveredSymbol("8888.TW", "Dynamic Taiwan Finance", "TW", "test-search"),
                    ]
                )
            if market == "US":
                symbols.append(DiscoveredSymbol("DYN", "Dynamic US Corp", "US", "test-search"))
        return symbols[:limit_per_market], []


def dongwu_holdings_bytes():
    text = "\r\n".join(
        [
            "\t".join(
                [
                    "\u8bc1\u5238\u4ee3\u7801",
                    "\u8bc1\u5238\u540d\u79f0",
                    "\u53ef\u7528\u4f59\u989d",
                    "\u51bb\u7ed3\u6570\u91cf",
                    "\u6210\u672c\u4ef7",
                    "\u5e02\u4ef7",
                    "\u5e02\u503c",
                    "\u76c8\u4e8f",
                    "\u76c8\u4e8f\u6bd4\u4f8b(%)",
                    "\u4ea4\u6613\u5e02\u573a",
                    "\u5b9e\u9645\u6570\u91cf",
                    "\u6210\u672c\u91d1\u989d",
                    "\u5f00\u4ed3\u65e5\u671f",
                ]
            ),
            "=\"300570\"\t\u592a\u8fb0\u5149\t100\t0\t179.150\t155.200\t15520.000\t-2407.750\t-13.440\t\u6df1\u5733\uff21\u80a1\t100\t17914.990000\t20260513",
            "=\"600176\"\t\u4e2d\u56fd\u5de8\u77f3\t0\t0\t46.923\t34.900\t6980.000\t-2413.170\t-25.714\t\u4e0a\u6d77\uff21\u80a1\t0\t9384.610000\t20260513",
        ]
    )
    return (text + "\r\n").encode("gb18030")


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.news_crawler = FakeNewsCrawler()
        self.client = create_app(FakeMarketProvider(), self.news_crawler, FakeUniverseProvider()).test_client()

    def test_config_contains_real_defaults(self):
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["markets"]), 7)
        self.assertGreaterEqual(len(payload["strategies"]), 8)
        self.assertIn("strategyLibrary", payload)
        self.assertGreaterEqual(len(payload["strategyLibrary"]["sources"]), 20)
        self.assertIn("todayBuy", payload["strategyLibrary"]["detailedWeightKeys"])
        strategy_ids = {strategy["id"] for strategy in payload["strategies"]}
        self.assertIn("ai_smart_blend", strategy_ids)
        self.assertIn("short_term_adaptive_trade", strategy_ids)
        self.assertIn("mid_long_quality_compounder", strategy_ids)
        self.assertNotIn("balanced", strategy_ids)
        self.assertNotIn("growth", strategy_ids)
        self.assertNotIn("defensive", strategy_ids)
        ai_strategy = next(strategy for strategy in payload["strategies"] if strategy["id"] == "ai_smart_blend")
        breakout_strategy = next(strategy for strategy in payload["strategies"] if strategy["id"] == "today_breakout_volume")
        self.assertIn("behavior", ai_strategy)
        self.assertIn("entryGates", ai_strategy["behavior"])
        self.assertIn("vetoRules", ai_strategy["behavior"])
        self.assertNotEqual(ai_strategy["behavior"]["mode"], breakout_strategy["behavior"]["mode"])
        self.assertTrue(all(source.get("usable") for source in payload["strategyLibrary"]["sources"]))
        self.assertIn("defaultSymbols", payload)
        self.assertIn("scanUniverseSize", payload)
        self.assertIn("2330.TW", payload["defaultSymbols"]["TW"])
        self.assertIn("7203.T", payload["defaultSymbols"]["JP"])
        self.assertIn("005930.KS", payload["defaultSymbols"]["KR"])
        self.assertEqual(payload["scanUniverseSize"]["TW"], "dynamic")
        self.assertEqual(payload["scanUniverseSize"]["JP"], "dynamic")
        self.assertEqual(payload["scanUniverseSize"]["KR"], "dynamic")
        self.assertIn("marketProfiles", payload)
        self.assertEqual(payload["marketProfiles"]["TW"]["coverageTier"], "local-deep")
        self.assertEqual(payload["marketProfiles"]["CN"]["coverageTier"], "local-deep")
        self.assertTrue(payload["marketProfiles"]["TW"]["capabilities"]["officialExchange"])
        self.assertTrue(payload["marketProfiles"]["CN"]["capabilities"]["fundFlow"])
        self.assertGreater(payload["marketProfiles"]["TW"]["sourceReliabilityScore"], payload["marketProfiles"]["JP"]["sourceReliabilityScore"])

    def test_market_profiles_prioritize_taiwan_and_china_discovery_sources(self):
        base_shares = market_preferred_source_shares("US")
        taiwan_shares = market_preferred_source_shares("TW")
        china_shares = market_preferred_source_shares("CN")

        self.assertGreater(taiwan_shares["market-universe"], base_shares["market-universe"])
        self.assertGreater(china_shares["local-news"], base_shares["local-news"])
        self.assertLess(taiwan_shares["fallback-search"], base_shares["fallback-search"])
        self.assertLess(china_shares["google-news"], base_shares["google-news"])

    def test_api_key_is_required_when_configured(self):
        with patch.dict(os.environ, {"API_ACCESS_KEYS": "19940710"}):
            client = create_app(FakeMarketProvider(), self.news_crawler, FakeUniverseProvider()).test_client()

        missing_key_response = client.get("/api/health")
        self.assertEqual(missing_key_response.status_code, 401)

        valid_key_response = client.get("/api/health", headers={"X-Stock-Picker-Key": "19940710"})
        self.assertEqual(valid_key_response.status_code, 200)

    def test_refined_strategy_affects_final_assessment_weights(self):
        response = self.client.post(
            "/api/analyze",
            json={"markets": ["US"], "symbols": ["AAPL"], "strategyId": "news_heat_catalyst"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["strategy"]["id"], "news_heat_catalyst")
        self.assertIn("detailedWeights", payload["strategy"])
        pick = payload["picks"][0]
        self.assertIn("componentWeights", pick["overallAssessment"])
        self.assertGreater(pick["overallAssessment"]["componentWeights"]["newsHeatImpactScore"], 12)
        self.assertIn("strategyAssessment", pick)
        self.assertEqual(pick["strategyAssessment"]["mode"], "news_heat_catalyst")
        self.assertTrue(pick["strategyAssessment"]["gates"])
        self.assertTrue(pick["strategyAssessment"]["vetoes"])
        self.assertIn("horizons", pick["strategyAssessment"])
        self.assertIn("shortTermScore", pick["strategyAssessment"]["horizons"])
        self.assertIn("midLongTermScore", pick["strategyAssessment"]["horizons"])

    def test_strategy_models_apply_distinct_gates_and_scores(self):
        breakout_response = self.client.post(
            "/api/analyze",
            json={"markets": ["US"], "symbols": ["AAPL"], "strategyId": "today_breakout_volume"},
        )
        defensive_response = self.client.post(
            "/api/analyze",
            json={"markets": ["US"], "symbols": ["AAPL"], "strategyId": "defensive_quality_value"},
        )

        self.assertEqual(breakout_response.status_code, 200)
        self.assertEqual(defensive_response.status_code, 200)
        breakout_pick = breakout_response.get_json()["picks"][0]
        defensive_pick = defensive_response.get_json()["picks"][0]
        breakout_assessment = breakout_pick["strategyAssessment"]
        defensive_assessment = defensive_pick["strategyAssessment"]
        self.assertEqual(breakout_assessment["mode"], "breakout_volume")
        self.assertEqual(defensive_assessment["mode"], "defensive_quality_value")
        self.assertNotEqual(
            {gate["key"] for gate in breakout_assessment["gates"]},
            {gate["key"] for gate in defensive_assessment["gates"]},
        )
        self.assertNotEqual(breakout_assessment["sortScore"], defensive_assessment["sortScore"])
        self.assertEqual(breakout_pick["overallAssessment"]["totalScore"], breakout_assessment["adjustedScore"])

    def test_short_and_mid_long_models_are_separate(self):
        short_response = self.client.post(
            "/api/analyze",
            json={"markets": ["US"], "symbols": ["AAPL"], "strategyId": "short_term_adaptive_trade"},
        )
        long_response = self.client.post(
            "/api/analyze",
            json={"markets": ["US"], "symbols": ["AAPL"], "strategyId": "mid_long_quality_compounder"},
        )

        self.assertEqual(short_response.status_code, 200)
        self.assertEqual(long_response.status_code, 200)
        short_assessment = short_response.get_json()["picks"][0]["strategyAssessment"]
        long_assessment = long_response.get_json()["picks"][0]["strategyAssessment"]
        self.assertEqual(short_assessment["mode"], "short_term_adaptive_trade")
        self.assertEqual(long_assessment["mode"], "mid_long_quality_compounder")
        self.assertIn("strategyGateShortTerm", {gate["key"] for gate in short_assessment["gates"]})
        self.assertIn("strategyGateMidLongQuality", {gate["key"] for gate in long_assessment["gates"]})
        self.assertIn(long_assessment["horizons"]["classification"], {"stableQuality", "shortTermOnly", "midLongQuality", "unstable", "balanced"})

    def test_strategy_library_uses_fallback_sources_without_refresh(self):
        catalog = get_strategy_catalog(refresh=False)
        self.assertGreaterEqual(len(catalog["sources"]), 20)
        self.assertTrue(all(source["usable"] for source in catalog["sources"]))
        self.assertTrue(any(source["fallback"] for source in catalog["sources"]))

    def test_stock_chart_endpoint_returns_intraday_and_daily_series(self):
        class FakeChartResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        def chart_payload(interval):
            timestamps = [1_720_000_000, 1_720_000_300, 1_720_000_600] if interval == "5m" else [1_719_820_800, 1_719_907_200, 1_719_993_600]
            return {
                "chart": {
                    "result": [
                        {
                            "timestamp": timestamps,
                            "meta": {"shortName": "Test Corp", "currency": "USD", "regularMarketPrice": 102.0},
                            "indicators": {
                                "quote": [
                                    {
                                        "open": [100, 101, 102],
                                        "high": [101, 102, 103],
                                        "low": [99, 100, 101],
                                        "close": [100.5, 101.5, 102.5],
                                        "volume": [1000, 1200, 1400],
                                    }
                                ]
                            },
                        }
                    ],
                    "error": None,
                }
            }

        def fake_urlopen(request, timeout=6):
            url = getattr(request, "full_url", str(request))
            return FakeChartResponse(chart_payload("5m" if "interval=5m" in url else "1d"))

        with patch("backend.charts.urlopen", side_effect=fake_urlopen):
            response = self.client.get("/api/stocks/TEST/chart")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["symbol"], "TEST")
        self.assertEqual(payload["name"], "Test Corp")
        self.assertEqual(len(payload["intraday"]), 3)
        self.assertEqual(len(payload["daily"]), 3)
        self.assertEqual(payload["daily"][-1]["close"], 102.5)

    def test_health_reports_cache_stats_for_default_app(self):
        response = create_app().test_client().get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("marketData", payload["cache"])
        self.assertIn("news", payload["cache"])
        self.assertGreater(payload["cache"]["marketData"]["ttlSeconds"], 0)

    def test_dongwu_gb18030_holdings_export_imports_current_positions(self):
        payload = parse_portfolio_export(dongwu_holdings_bytes(), "011700317559.xls")

        self.assertEqual(payload["sourceType"], "tsv-gb18030")
        self.assertEqual(payload["recognizedCount"], 1)
        self.assertEqual(payload["ignoredRows"], 1)
        self.assertEqual(payload["symbols"], ["300570.SZ"])
        position = payload["positions"][0]
        self.assertEqual(position["name"], "\u592a\u8fb0\u5149")
        self.assertEqual(position["quantity"], 100)
        self.assertEqual(position["exchange"], "\u6df1\u5733A\u80a1")
        self.assertAlmostEqual(position["unrealizedPnlPct"], -13.44)
        self.assertEqual(normalize_a_share_symbol("600176", "\u4e0a\u6d77\uff21\u80a1"), "600176.SS")

    def test_portfolio_import_endpoint_accepts_dongwu_xls_text_export(self):
        response = self.client.post(
            "/api/portfolio/import",
            data={"file": (io.BytesIO(dongwu_holdings_bytes()), "011700317559.xls")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["recognizedCount"], 1)
        self.assertEqual(payload["symbols"], ["300570.SZ"])

    def test_analyze_attaches_holding_context_to_imported_portfolio_symbols(self):
        class ChinaMarketProvider:
            def fetch(self, symbol):
                return MarketSnapshot(
                    symbol=symbol,
                    name="\u592a\u8fb0\u5149",
                    market="CN",
                    sector="Technology",
                    price=155.2,
                    change=-2.1,
                    currency="CNY",
                    closes=[130 + index * 0.2 for index in range(130)],
                    info={"trailingPE": 22, "beta": 1.1, "returnOnEquity": 0.16, "profitMargins": 0.18, "debtToEquity": 35},
                )

        class PortfolioUniverseProvider:
            def resolve_manual_inputs(self, inputs, markets, limit=25):
                return [DiscoveredSymbol(str(symbol).upper(), "\u592a\u8fb0\u5149", infer_market(str(symbol).upper()), "test-portfolio") for symbol in inputs], []

        portfolio = parse_portfolio_export(dongwu_holdings_bytes(), "011700317559.xls")
        client = create_app(ChinaMarketProvider(), self.news_crawler, PortfolioUniverseProvider()).test_client()
        response = client.post(
            "/api/analyze",
            json={"markets": ["CN"], "symbols": portfolio["symbols"], "strategyId": "balanced", "portfolio": portfolio},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["scan"]["source"], "portfolio-import")
        self.assertEqual(payload["portfolio"]["matchedCount"], 1)
        pick = payload["picks"][0]
        self.assertEqual(pick["holding"]["symbol"], "300570.SZ")
        self.assertEqual(pick["holding"]["quantity"], 100)
        self.assertIn(pick["holdingAnalysis"]["action"], {"add", "hold", "reduce", "exit"})
        self.assertTrue(pick["holdingAnalysis"]["notes"])

    def test_manual_holdings_use_live_price_for_pnl_and_position_weight(self):
        class ChinaMarketProvider:
            def fetch(self, symbol):
                return MarketSnapshot(
                    symbol=symbol,
                    name="\u5b81\u5fb7\u65f6\u4ee3",
                    market="CN",
                    sector="Industrials",
                    price=220.0,
                    change=1.6,
                    currency="CNY",
                    closes=[180 + index * 0.4 for index in range(130)],
                    info={"trailingPE": 20, "returnOnEquity": 0.17, "profitMargins": 0.16, "debtToEquity": 30},
                )

        class PortfolioUniverseProvider:
            def resolve_manual_inputs(self, inputs, markets, limit=25):
                return [DiscoveredSymbol(str(symbol).upper(), "\u5b81\u5fb7\u65f6\u4ee3", infer_market(str(symbol).upper()), "test-manual-portfolio") for symbol in inputs], []

        portfolio = {
            "sourceName": "Manual holdings",
            "sourceType": "manual-holdings",
            "positions": [
                {
                    "symbol": "300750.SZ",
                    "code": "300750",
                    "name": "\u5b81\u5fb7\u65f6\u4ee3",
                    "market": "CN",
                    "quantity": 100,
                    "availableQuantity": 80,
                    "costPrice": 200.0,
                }
            ],
        }
        client = create_app(ChinaMarketProvider(), self.news_crawler, PortfolioUniverseProvider()).test_client()
        response = client.post(
            "/api/analyze",
            json={"markets": ["CN"], "symbols": ["300750.SZ"], "strategyId": "balanced", "portfolio": portfolio},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        pick = payload["picks"][0]
        self.assertEqual(pick["holding"]["lastPrice"], 220.0)
        self.assertEqual(pick["holding"]["frozenQuantity"], 20)
        self.assertEqual(pick["holding"]["marketValue"], 22000.0)
        self.assertEqual(pick["holding"]["unrealizedPnl"], 2000.0)
        self.assertAlmostEqual(pick["holding"]["unrealizedPnlPct"], 10.0)
        self.assertEqual(pick["holdingAnalysis"]["positionWeightPct"], 100.0)
        self.assertIn("targetWeightPct", pick["holdingAnalysis"])
        self.assertIn("suggestedQuantityChange", pick["holdingAnalysis"])
        self.assertIn("stopLossPrice", pick["holdingAnalysis"])
        self.assertIn("takeProfitPrice", pick["holdingAnalysis"])
        self.assertIn("compositeModel", pick)
        self.assertEqual(payload["portfolio"]["totalMarketValue"], 22000.0)

    def test_ttl_cache_expires_entries(self):
        now = [100.0]
        cache = TtlCache(ttl_seconds=10, timer=lambda: now[0])
        cache.set("AAPL", "cached")
        self.assertEqual(cache.get("AAPL"), "cached")
        now[0] = 111.0
        self.assertIsNone(cache.get("AAPL"))

    def test_cached_providers_reuse_recent_fetches(self):
        class CountingMarketProvider:
            def __init__(self):
                self.calls = []

            def fetch(self, symbol):
                self.calls.append(symbol)
                return MarketSnapshot(
                    symbol=symbol.upper(),
                    name="Apple",
                    market="US",
                    sector="Technology",
                    price=100,
                    change=1.0,
                    currency="USD",
                    closes=[90, 95, 100],
                    info={"trailingPE": 20},
                )

        class CountingNewsCrawler:
            def __init__(self):
                self.calls = []

            def fetch(self, symbol, name, limit=8):
                self.calls.append((symbol, name, limit))
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} update",
                        summary="Growth remains steady",
                        link="https://example.com/aapl",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.2,
                        credibility=0.8,
                        relevance=1.0,
                    )
                ]

        market_provider = CountingMarketProvider()
        news_crawler = CountingNewsCrawler()
        cached_market = CachedMarketDataProvider(market_provider, ttl_seconds=60)
        cached_news = CachedNewsCrawler(news_crawler, ttl_seconds=60)

        first_snapshot = cached_market.fetch("aapl")
        first_snapshot.info["trailingPE"] = 999
        second_snapshot = cached_market.fetch("AAPL")
        self.assertEqual(market_provider.calls, ["aapl"])
        self.assertEqual(second_snapshot.info["trailingPE"], 20)
        refreshed_snapshot = cached_market.fetch("AAPL", refresh=True)
        self.assertEqual(market_provider.calls, ["aapl", "AAPL"])
        self.assertEqual(refreshed_snapshot.info["trailingPE"], 20)

        first_articles = cached_news.fetch("AAPL", "Apple", limit=8)
        second_articles = cached_news.fetch("aapl", " apple ", limit=8)
        self.assertEqual(news_crawler.calls, [("AAPL", "Apple", 8)])
        self.assertEqual(first_articles, second_articles)
        self.assertIsNot(first_articles, second_articles)
        cached_news.fetch("AAPL", "Apple", limit=8, refresh=True)
        self.assertEqual(news_crawler.calls, [("AAPL", "Apple", 8), ("AAPL", "Apple", 8)])

    def test_analyze_refresh_bypasses_cached_news(self):
        class VersionedNewsCrawler:
            def __init__(self):
                self.calls = 0

            def fetch(self, symbol, name, limit=8):
                self.calls += 1
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} refresh version {self.calls}",
                        summary="Revenue beats expectations",
                        link=f"https://example.com/{self.calls}",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.5,
                        credibility=0.8,
                        relevance=1.0,
                    )
                ]

        crawler = VersionedNewsCrawler()
        cached_news = CachedNewsCrawler(crawler, ttl_seconds=900)
        client = create_app(FakeMarketProvider(), cached_news, FakeUniverseProvider()).test_client()
        payload = {"markets": ["US"], "symbols": ["AAPL"], "strategyId": "balanced"}

        first = client.post("/api/analyze", json=payload).get_json()["picks"][0]["signals"][0]["title"]
        second = client.post("/api/analyze", json=payload).get_json()["picks"][0]["signals"][0]["title"]
        refreshed = client.post("/api/analyze", json={**payload, "refresh": True}).get_json()["picks"][0]["signals"][0]["title"]

        self.assertEqual(first, "Test Corp refresh version 1")
        self.assertEqual(second, first)
        self.assertEqual(refreshed, "Test Corp refresh version 2")
        self.assertEqual(crawler.calls, 2)

    def test_analyze_filters_market_and_returns_verdicts(self):
        response = self.client.post("/api/analyze", json={"markets": ["TW"], "symbols": ["2330.TW", "AAPL"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["picks"])
        self.assertTrue(all(pick["market"] == "TW" for pick in payload["picks"]))
        self.assertEqual(payload["scan"]["source"], "manual")
        self.assertGreater(payload["scan"]["requested"], len(payload["picks"]) - 1)
        self.assertIn(payload["picks"][0]["verdict"], {"buy", "watch", "sell"})
        self.assertEqual(payload["errors"], [])
        self.assertIn("reasonCodes", payload["picks"][0])

    def test_news_crawler_receives_company_name(self):
        response = self.client.post("/api/analyze", json={"markets": ["US"], "symbols": ["AAPL"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.news_crawler.calls[0], ("AAPL", "Test Corp"))

    def test_news_query_uses_cjk_company_name(self):
        self.assertIn("\u53f0\u7a4d\u96fb", news_query("2330.TW", "\u53f0\u7a4d\u96fb"))

    def test_news_query_uses_local_alias_for_china_and_hong_kong(self):
        self.assertEqual(local_company_name("600519.SS", "Kweichow Moutai"), "\u8d35\u5dde\u8305\u53f0")
        self.assertTrue(any("\u8d35\u5dde\u8305\u53f0" in query for query in news_queries("600519.SS", "Kweichow Moutai")))
        self.assertTrue(any("\u817e\u8baf\u63a7\u80a1" in query for query in news_queries("0700.HK", "Tencent Holdings")))
        self.assertTrue(any("\u9a30\u8a0a\u63a7\u80a1" in query for query in news_queries("0700.HK", "Tencent Holdings")))

    def test_japan_and_korea_symbols_infer_and_query_local_markets(self):
        self.assertEqual(infer_market("7203.T"), "JP")
        self.assertEqual(infer_market("005930.KS"), "KR")
        self.assertEqual(infer_market("035720.KQ"), "KR")
        self.assertTrue(any("\u65e5\u672c\u682a" in query or "\u682a\u5f0f" in query for query in news_queries("7203.T", "Toyota Motor")))
        self.assertTrue(any("\ud55c\uad6d" in query or "\uc8fc\uc2dd" in query for query in news_queries("005930.KS", "Samsung Electronics")))

    def test_manual_china_symbols_resolve_to_company_names(self):
        provider = MarketUniverseProvider()
        symbols, errors = provider.resolve_manual_inputs(
            ["605589.SS", "603986.SS", "603936.SS", "301071.SZ", "300373.SZ", "300323.SZ"],
            ["CN"],
        )
        names = {item.symbol: item.name for item in symbols}
        self.assertEqual(errors, [])
        self.assertEqual(names["605589.SS"], "\u5723\u6cc9\u96c6\u56e2")
        self.assertEqual(names["603986.SS"], "\u5146\u6613\u521b\u65b0")
        self.assertEqual(names["603936.SS"], "\u535a\u654f\u7535\u5b50")
        self.assertEqual(names["301071.SZ"], "\u529b\u91cf\u94bb\u77f3")
        self.assertEqual(names["300373.SZ"], "\u626c\u6770\u79d1\u6280")
        self.assertEqual(names["300323.SZ"], "\u534e\u707f\u5149\u7535")

    def test_manual_company_name_input_resolves_to_symbol(self):
        searched_terms = []

        class FakeResolver(MarketUniverseProvider):
            def _search_eastmoney_term(self, term, market):
                searched_terms.append((term, market))
                return [DiscoveredSymbol("605589.SS", "\u5723\u6cc9\u96c6\u56e2", "CN", "test-resolver")]

            def _search_yahoo_term(self, term, market):
                return []

        symbols, errors = FakeResolver().resolve_manual_inputs(["\u5723\u6cc9\u96c6\u56e2"], ["CN"])
        self.assertEqual(errors, [])
        self.assertEqual(searched_terms, [("\u5723\u6cc9\u96c6\u56e2", "CN")])
        self.assertEqual([(item.symbol, item.name) for item in symbols], [("605589.SS", "\u5723\u6cc9\u96c6\u56e2")])

    def test_news_relevance_prefers_company_phrase(self):
        crawler = RssNewsCrawler()
        article = Article(
            source="Google News",
            title="Ryanair stock falls after earnings",
            summary="European airlines remain under pressure.",
            link="https://example.com/ryanair",
            published_at=datetime.now(timezone.utc),
            sentiment=-0.2,
            credibility=0.7,
            relevance=1.0,
        )
        self.assertEqual(crawler._relevance(article, "C6L.SI", "Singapore Airlines"), 0.0)

    def test_china_news_uses_eastmoney_fallback_when_rss_empty(self):
        class EastmoneyFallbackCrawler(RssNewsCrawler):
            def __init__(self):
                self.keywords = []

            def _parse_feed(self, url):
                return []

            def _fetch_eastmoney_keyword_news(self, keyword, limit=10):
                self.keywords.append(keyword)
                if keyword != "605589":
                    return []
                return [
                    Article(
                        source="Eastmoney",
                        title="\u5723\u6cc9\u96c6\u56e2\u53d1\u5e03\u4e1a\u7ee9\u589e\u957f\u516c\u544a",
                        summary="\u5723\u6cc9\u96c6\u56e2\u6536\u5165\u548c\u5229\u6da6\u6539\u5584",
                        link="https://finance.eastmoney.com/a/test.html",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.2,
                        credibility=0.76,
                        relevance=1.0,
                    )
                ]

        crawler = EastmoneyFallbackCrawler()
        articles = crawler.fetch("605589.SS", "\u5723\u6cc9\u96c6\u56e2", limit=3)
        self.assertIn("605589", crawler.keywords)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].source, "Eastmoney")

    def test_eastmoney_news_datetime_is_recent_in_china_timezone(self):
        published_at = _parse_eastmoney_datetime("2026-05-27 16:46:00")
        self.assertIsNotNone(published_at)
        self.assertEqual(published_at.utcoffset(), timedelta(hours=8))
        article = Article(
            source="Eastmoney",
            title="Recent story",
            summary="",
            link="https://finance.eastmoney.com/a/test.html",
            published_at=published_at,
            sentiment=0,
            credibility=0.76,
            relevance=1.0,
        )
        self.assertTrue(is_recent_article(article, datetime(2026, 5, 27, 23, 0, tzinfo=timezone(timedelta(hours=8)))))

    def test_old_news_is_filtered(self):
        old_article = Article(
            source="Old RSS",
            title="Old story",
            summary="Old summary",
            link="https://example.com/old",
            published_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            sentiment=0,
            credibility=0.5,
            relevance=1.0,
        )
        self.assertFalse(is_recent_article(old_article, datetime(2026, 5, 26, tzinfo=timezone.utc)))

    def test_fallback_search_does_not_use_local_china_candidates_offline(self):
        class OfflineUniverse(MarketUniverseProvider):
            def _json(self, url, insecure=False, **kwargs):
                raise OSError("offline")

        symbols = OfflineUniverse()._discover_fallback_search("CN", 18)
        self.assertEqual(symbols, [])

    def test_china_market_discovery_includes_gainers_and_volume_ratio(self):
        class FakeEastmoneyUniverse(MarketUniverseProvider):
            def _json(self, url, insecure=False, **kwargs):
                if "fid=f3" in url:
                    return {"data": {"diff": [{"f12": "688108", "f14": "Top Gainer"}, {"f12": "300486", "f14": "Runner"}]}}
                if "fid=f10" in url:
                    return {"data": {"diff": [{"f12": "301360", "f14": "Volume Ratio"}]}}
                if "fid=f6" in url:
                    return {"data": {"diff": [{"f12": "600519", "f14": "Turnover"}]}}
                return {"data": {"diff": []}}

        symbols = FakeEastmoneyUniverse()._discover_eastmoney_cn(4)
        by_symbol = {item.symbol: item.source for item in symbols}

        self.assertEqual(symbols[0].symbol, "301360.SZ")
        self.assertEqual(by_symbol["301360.SZ"], "eastmoney-cn-volume-ratio")
        self.assertIn("301360.SZ", by_symbol)
        self.assertIn("600519.SS", by_symbol)
        self.assertEqual(by_symbol["688108.SS"], "eastmoney-cn-gainers-risk-review")

    def test_china_market_discovery_paginates_online_universe(self):
        class FakeEastmoneyUniverse(MarketUniverseProvider):
            def _json(self, url, insecure=False, **kwargs):
                if "fid=f10" not in url:
                    return {"data": {"diff": []}}
                page = 1
                if "pn=2" in url:
                    page = 2
                elif "pn=3" in url:
                    page = 3
                start = 600000 + (page - 1) * 80
                return {
                    "data": {
                        "diff": [
                            {"f12": str(start + index), "f14": f"Online {start + index}"}
                            for index in range(80)
                        ]
                    }
                }

        symbols = FakeEastmoneyUniverse()._discover_eastmoney_cn(120)

        self.assertEqual(len(symbols), 120)
        self.assertTrue(all(item.source == "eastmoney-cn-volume-ratio" for item in symbols[:120]))
        self.assertNotIn("curated", {item.source for item in symbols})

    def test_sina_china_discovery_paginates_online_universe(self):
        case = self

        class FakeSinaUniverse(MarketUniverseProvider):
            def _json(self, url, insecure=False, **kwargs):
                case.assertIn("sina.com.cn", url)
                page = 1
                if "page=2" in url:
                    page = 2
                start = 300000 + (page - 1) * 80
                return [
                    {"code": str(start + index), "symbol": f"sz{start + index}", "name": f"Online {start + index}"}
                    for index in range(80)
                ]

        symbols = FakeSinaUniverse()._discover_sina_cn(120)

        self.assertEqual(len(symbols), 120)
        self.assertEqual(symbols[0].symbol, "300000.SZ")
        self.assertEqual(symbols[-1].symbol, "300119.SZ")
        self.assertTrue(all(item.source == "sina-cn-turnover" for item in symbols))

    def test_fallback_search_does_not_use_default_taiwan_symbols(self):
        symbols = MarketUniverseProvider()._discover_fallback_search("TW", 5)
        self.assertEqual(symbols, [])

    def test_fallback_search_does_not_use_local_japan_and_korea_candidates_offline(self):
        class OfflineUniverse(MarketUniverseProvider):
            def _json(self, url, insecure=False, **kwargs):
                raise OSError("offline")

        japan = OfflineUniverse()._discover_fallback_search("JP", 5)
        korea = OfflineUniverse()._discover_fallback_search("KR", 5)
        self.assertEqual(japan, [])
        self.assertEqual(korea, [])

    def test_manual_japan_and_korea_symbols_resolve(self):
        self.assertEqual(_manual_symbol_candidates("7203.T", {"JP"}), ["7203.T"])
        self.assertEqual(_manual_symbol_candidates("7203", {"JP"}), ["7203.T"])
        self.assertEqual(_manual_symbol_candidates("7203", {"CN", "HK", "JP", "KR", "SG", "TW", "US"}), ["7203.T"])
        self.assertEqual(_manual_symbol_candidates("005930.KS", {"KR"}), ["005930.KS"])
        self.assertEqual(_manual_symbol_candidates("005930", {"KR"}), ["005930.KS"])

    def test_discover_prefers_local_news_then_google_news(self):
        class SparseNewsUniverse(MarketUniverseProvider):
            def _discover_local_market_news(self, market, limit):
                return [DiscoveredSymbol("AAPL", "Apple", "US", "local-news")]

            def _discover_google_market_news(self, market, limit):
                return [DiscoveredSymbol("MSFT", "Microsoft", "US", "google-news")]

            def _discover_market(self, market, limit):
                return [DiscoveredSymbol("NVDA", "Nvidia", "US", "market-universe")]

            def _discover_fallback_search(self, market, limit):
                raise AssertionError("fallback should not be needed")

        symbols, errors = SparseNewsUniverse().discover(["US"], 3)
        self.assertEqual([item.symbol for item in symbols], ["AAPL", "MSFT", "NVDA"])
        self.assertEqual(errors, [])

    def test_discover_blends_market_universe_even_when_local_news_is_enough(self):
        class LocalNewsUniverse(MarketUniverseProvider):
            def _discover_local_market_news(self, market, limit):
                return [
                    DiscoveredSymbol("2330.TW", "TSMC", "TW", "local-news"),
                    DiscoveredSymbol("2454.TW", "MediaTek", "TW", "local-news"),
                ]

            def _discover_google_market_news(self, market, limit):
                return []

            def _discover_market(self, market, limit):
                return [
                    DiscoveredSymbol("2317.TW", "Hon Hai", "TW", "market-universe"),
                    DiscoveredSymbol("2308.TW", "Delta", "TW", "market-universe"),
                ]

            def _discover_fallback_search(self, market, limit):
                raise AssertionError("fallback should not be needed")

        symbols, errors = LocalNewsUniverse().discover(["TW"], 4)
        self.assertEqual(symbols[0].source, "local-news")
        self.assertIn("local-news", {item.source for item in symbols})
        self.assertIn("market-universe", {item.source for item in symbols})
        self.assertNotIn("fallback-search", {item.source for item in symbols})
        self.assertIn("google-news", {error["source"] for error in errors})

    def test_discover_falls_back_to_defaults_when_dynamic_sources_fail(self):
        class OfflineUniverse(MarketUniverseProvider):
            def _discover_local_market_news(self, market, limit):
                return []

            def _discover_google_market_news(self, market, limit):
                return []

            def _discover_market(self, market, limit):
                raise OSError("offline")

        symbols, errors = OfflineUniverse().discover(["TW"], 5)
        self.assertEqual(symbols, [])
        self.assertIn("local-news", {error["source"] for error in errors})
        self.assertIn("google-news", {error["source"] for error in errors})
        self.assertIn("market-universe", {error["source"] for error in errors})
        self.assertIn("fallback-search", {error["source"] for error in errors})

    def test_sgx_discovery_ignores_unnamed_codes_and_uses_curated_names(self):
        class FakeSgxUniverse(MarketUniverseProvider):
            def _json(self, url, insecure=False, **kwargs):
                return {
                    "data": {
                        "prices": [
                            {"type": "stocks", "nc": "A31", "cn": None, "vl": 900},
                            {"type": "stocks", "nc": "D05", "cn": None, "vl": 800},
                        ]
                    }
                }

        symbols = FakeSgxUniverse()._discover_sgx(5)
        self.assertNotIn("A31.SI", {item.symbol for item in symbols})
        self.assertEqual(symbols[0].symbol, "D05.SI")
        self.assertEqual(symbols[0].name, "DBS Group")


    def test_blank_symbols_trigger_news_led_market_scan(self):
        response = self.client.post("/api/analyze", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["picks"])
        self.assertTrue(all(pick["market"] == "TW" for pick in payload["picks"]))
        self.assertEqual(payload["scan"]["source"], "market-news")
        self.assertEqual({pick["symbol"] for pick in payload["picks"]}, {"8888.TW", "9999.TW"})
        self.assertNotIn("2330.TW", {pick["symbol"] for pick in payload["picks"]})

    def test_streaming_analyze_emits_incremental_picks(self):
        response = self.client.post("/api/analyze/stream", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]
        self.assertEqual(events[0]["type"], "started")
        self.assertEqual(events[-1]["type"], "complete")
        pick_events = [event for event in events if event["type"] == "pick"]
        self.assertEqual(len(pick_events), 2)
        self.assertEqual({event["pick"]["symbol"] for event in pick_events}, {"8888.TW", "9999.TW"})
        self.assertEqual(events[-1]["scan"]["requested"], 2)
        self.assertEqual(events[-1]["scan"]["succeeded"], 2)
        self.assertEqual({pick["symbol"] for pick in events[-1]["picks"]}, {"8888.TW", "9999.TW"})

    def test_news_universe_extracts_symbols_from_market_articles(self):
        article = Article(
            source="Market RSS",
            title="台積電營收創高，聯發科同步受惠",
            summary="台股焦點集中在半導體族群。",
            link="https://example.com/tw-market",
            published_at=datetime.now(timezone.utc),
            sentiment=0.4,
            credibility=0.8,
            relevance=1.0,
        )
        symbols = MarketUniverseProvider()._symbols_from_news_articles("TW", [article], 5)
        self.assertEqual({item.symbol for item in symbols}, {"2330.TW", "2454.TW"})
        self.assertTrue(all(item.source == "market-news" for item in symbols))

    def test_news_universe_does_not_fallback_to_default_symbols_without_news_mentions(self):
        symbols = MarketUniverseProvider()._symbols_from_news_articles("TW", [], 5)
        self.assertEqual(symbols, [])

    def test_us_news_scan_does_not_treat_common_words_as_tickers(self):
        text = "Yahoo Finance says the stock is after the bell and what to buy on Wall Street"
        self.assertEqual(_symbols_from_code_mentions(text.lower(), "US"), [])
        article = Article(
            source="Market RSS",
            title="Yahoo Finance asks what to buy after the Wall Street rally",
            summary="The stock market is watching earnings and the Fed.",
            link="https://example.com/us-market",
            published_at=datetime.now(timezone.utc),
            sentiment=0.1,
            credibility=0.7,
            relevance=1.0,
        )
        symbols = MarketUniverseProvider()._symbols_from_news_articles("US", [article], 10)
        self.assertEqual(symbols, [])

    def test_news_mentions_extract_japan_and_korea_suffixes(self):
        text = "Toyota 7203.T and Samsung 005930.KS both report earnings."
        self.assertEqual(_symbols_from_code_mentions(text.lower(), "JP"), ["7203.T"])
        self.assertEqual(_symbols_from_code_mentions(text.lower(), "KR"), ["005930.KS"])

    def test_custom_weights_are_accepted(self):
        response = self.client.post(
            "/api/analyze",
            json={
                "markets": ["US"],
                "symbols": ["AAPL"],
                "customWeights": {"momentum": 40, "value": 0, "sentiment": 30, "risk": 10, "quality": 20},
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["strategy"]["id"], "custom")
        self.assertTrue(payload["picks"])

    def test_negative_news_reduces_sentiment_score(self):
        now = datetime.now(timezone.utc)
        positive = [
            Article("Test", "Company reports strong revenue growth", "", "https://example.com/positive", now, 0.4, 0.8, 1.0)
        ]
        negative = [
            Article("Test", "Company issues profit warning after weak demand", "", "https://example.com/negative", now, -0.4, 0.8, 1.0)
        ]
        self.assertGreater(_sentiment_score(positive), 50)
        self.assertLess(_sentiment_score(negative), 50)
        self.assertGreater(_sentiment_score(positive), _sentiment_score(negative))

    def test_news_analysis_scores_chinese_positive_and_negative_events(self):
        now = datetime.now(timezone.utc)
        positive = [
            Article(
                "Eastmoney",
                "\u4e2d\u56fd\u5de8\u77f3\u8bc4\u7ea7\u88ab\u8c03\u9ad8 \u4e3b\u529b\u8d44\u91d1\u51c0\u6d41\u5165",
                "\u76ee\u6807\u4ef7\u4e0a\u8c03",
                "https://example.com/positive-cn",
                now,
                0.3,
                0.8,
                1.0,
            )
        ]
        negative = [
            Article(
                "Eastmoney",
                "\u4e2d\u56fd\u5de8\u77f3\u4e1a\u7ee9\u6301\u7eed\u627f\u538b \u9700\u6c42\u653e\u7f13",
                "\u5229\u6da6\u4e0b\u964d",
                "https://example.com/negative-cn",
                now,
                -0.3,
                0.8,
                1.0,
            )
        ]

        positive_profile = _news_analysis(positive)
        negative_profile = _news_analysis(negative)

        self.assertGreater(positive_profile["positiveScore"], positive_profile["negativeScore"])
        self.assertGreater(positive_profile["netScore"], 0)
        self.assertEqual(positive_profile["summary"]["key"], "newsBullishSummary")
        self.assertGreater(negative_profile["negativeScore"], negative_profile["positiveScore"])
        self.assertLess(negative_profile["netScore"], 0)
        self.assertEqual(negative_profile["summary"]["key"], "newsBearishSummary")
        self.assertTrue(all("score" in event and "evidence" in event for event in positive_profile["events"]))

    def test_news_heat_scores_attention_and_direction(self):
        now = datetime.now(timezone.utc)
        positive_articles = [
            Article("Eastmoney", "Company wins large order with institutional buying", "Revenue growth and analyst upgrade", "https://example.com/a", now, 0.8, 0.9, 1.0),
            Article("Reuters", "Company raises guidance after strong demand", "Target price raised", "https://example.com/b", now - timedelta(hours=2), 0.7, 0.9, 1.0),
        ]
        negative_articles = [
            Article("Eastmoney", "Company profit warning with institutional selling", "Weak demand and target price cut", "https://example.com/c", now, -0.8, 0.9, 1.0),
            Article("Reuters", "Company faces regulatory probe after demand falls", "Downgrade follows weak demand", "https://example.com/d", now - timedelta(hours=2), -0.7, 0.9, 1.0),
        ]

        positive_heat = _news_heat_analysis(positive_articles, _news_analysis(positive_articles))
        negative_heat = _news_heat_analysis(negative_articles, _news_analysis(negative_articles))

        self.assertGreaterEqual(positive_heat["heatScore"], 50)
        self.assertGreater(positive_heat["impactScore"], negative_heat["impactScore"])
        self.assertEqual(positive_heat["summary"]["key"], "newsHeatHotPositiveSummary")
        self.assertEqual(negative_heat["summary"]["key"], "newsHeatHotNegativeSummary")

    def test_high_volatility_alone_does_not_force_sell_verdict(self):
        self.assertEqual(_verdict(61.2, 29.2), "watch")
        self.assertEqual(_verdict(56.0, 29.2), "sell")

    def test_missing_factor_weight_is_reallocated(self):
        metrics = {"sentiment": 50, "momentum": 70, "value": 60, "risk": 65, "quality": 75}
        weights = {"sentiment": 0.4, "momentum": 0.2, "value": 0.15, "risk": 0.1, "quality": 0.15}
        availability = {"sentiment": False, "momentum": True, "value": True, "risk": True, "quality": True}
        breakdown = _score_breakdown(metrics, weights, availability)
        self.assertEqual(next(item for item in breakdown if item["factor"] == "sentiment")["weight"], 0)
        self.assertAlmostEqual(sum(item["weight"] for item in breakdown), 100, delta=0.2)
        self.assertGreater(next(item for item in breakdown if item["factor"] == "momentum")["weight"], 20)

    def test_price_proxy_keeps_value_and_quality_active_when_fundamentals_are_sparse(self):
        snapshot = MarketSnapshot(
            symbol="605589.SS",
            name="\u5723\u6cc9\u96c6\u56e2",
            market="CN",
            sector="Materials",
            price=100,
            change=1.2,
            currency="CNY",
            closes=[80 + index * 0.2 for index in range(130)],
            info={
                "fiftyTwoWeekHigh": 120,
                "fiftyTwoWeekLow": 80,
                "regularMarketVolume": 5_000_000,
                "marketCap": 20_000_000_000,
            },
        )
        metrics = _metrics(snapshot, [])
        availability = _metric_availability(snapshot, [])
        weights = {"sentiment": 0.4, "momentum": 0.2, "value": 0.15, "risk": 0.1, "quality": 0.15}
        breakdown = _score_breakdown(metrics, weights, availability)
        self.assertGreater(next(item for item in breakdown if item["factor"] == "value")["weight"], 0)
        self.assertGreater(next(item for item in breakdown if item["factor"] == "quality")["weight"], 0)
        self.assertGreater(next(item for item in breakdown if item["factor"] == "value")["contribution"], 0)
        self.assertGreater(next(item for item in breakdown if item["factor"] == "quality")["contribution"], 0)

        financials = _financial_analysis(snapshot)
        self.assertTrue(financials["positives"] or financials["negatives"] or financials["watchItems"])

    def test_scan_produces_relative_buy_candidates(self):
        client = create_app(LowRiskFakeMarketProvider(), self.news_crawler, FakeUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("buy", {pick["verdict"] for pick in payload["picks"]})

    def test_blank_market_scan_curates_investment_first_results(self):
        class BroadUniverseProvider:
            def discover(self, markets, limit_per_market=18):
                symbols = []
                for prefix, count in [("7", 12), ("6", 8), ("5", 8)]:
                    for index in range(count):
                        symbol = f"{prefix}{index:03d}.TW"
                        symbols.append(DiscoveredSymbol(symbol, f"{prefix} Corp {index}", "TW", "test-broad"))
                return symbols, []

        class BroadMarketProvider:
            def fetch(self, symbol):
                if symbol.startswith("7"):
                    closes = [80 + index * 0.45 for index in range(130)]
                    info = {
                        "trailingPE": 18,
                        "priceToBook": 2.1,
                        "beta": 1.0,
                        "returnOnEquity": 0.28,
                        "profitMargins": 0.24,
                        "revenueGrowth": 0.22,
                        "earningsGrowth": 0.20,
                        "debtToEquity": 18,
                        "regularMarketVolume": 8_000_000,
                        "marketCap": 80_000_000_000,
                        "fiftyTwoWeekHigh": 150,
                        "fiftyTwoWeekLow": 70,
                    }
                elif symbol.startswith("6"):
                    closes = [130 - index * 0.35 for index in range(130)]
                    info = {
                        "trailingPE": 55,
                        "priceToBook": 7,
                        "beta": 2.3,
                        "returnOnEquity": 0.02,
                        "profitMargins": 0.01,
                        "revenueGrowth": -0.20,
                        "earningsGrowth": -0.30,
                        "debtToEquity": 220,
                        "regularMarketVolume": 200_000,
                        "marketCap": 300_000_000,
                        "fiftyTwoWeekHigh": 150,
                        "fiftyTwoWeekLow": 70,
                    }
                else:
                    closes = [100 + (index % 5) * 0.2 for index in range(130)]
                    info = {
                        "trailingPE": 26,
                        "priceToBook": 3.5,
                        "beta": 1.2,
                        "returnOnEquity": 0.10,
                        "profitMargins": 0.08,
                        "revenueGrowth": 0.04,
                        "earningsGrowth": 0.03,
                        "debtToEquity": 80,
                        "regularMarketVolume": 1_000_000,
                        "marketCap": 5_000_000_000,
                        "fiftyTwoWeekHigh": 140,
                        "fiftyTwoWeekLow": 80,
                    }
                return MarketSnapshot(
                    symbol=symbol,
                    name=symbol,
                    market="TW",
                    sector="Technology",
                    price=100,
                    change=1,
                    currency="TWD",
                    closes=closes,
                    info=info,
                )

        class BroadNewsCrawler:
            def fetch(self, symbol, name):
                if symbol.startswith("7"):
                    return [
                        Article(
                            source="Test RSS",
                            title=f"{name} earnings beat with strong demand",
                            summary="Revenue growth and analyst upgrade",
                            link=f"https://example.com/{symbol}",
                            published_at=datetime.now(timezone.utc),
                            sentiment=0.8,
                            credibility=0.9,
                            relevance=1.0,
                        )
                    ]
                if symbol.startswith("6"):
                    return [
                        Article(
                            source="Test RSS",
                            title=f"{name} profit warning and downgrade",
                            summary="Weak demand and target price cut",
                            link=f"https://example.com/{symbol}",
                            published_at=datetime.now(timezone.utc),
                            sentiment=-0.8,
                            credibility=0.9,
                            relevance=1.0,
                        )
                    ]
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} mixed results",
                        summary="Stable but limited growth",
                        link=f"https://example.com/{symbol}",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.0,
                        credibility=0.7,
                        relevance=1.0,
                    )
                ]

        client = create_app(BroadMarketProvider(), BroadNewsCrawler(), BroadUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        verdicts = [pick["verdict"] for pick in payload["picks"]]
        priority = {"buy": 0, "sell": 1, "watch": 2}

        self.assertEqual(len(payload["picks"]), payload["scan"]["requested"])
        self.assertEqual(payload["scan"]["succeeded"], payload["scan"]["requested"])
        self.assertEqual(payload["scan"]["displayed"], len(payload["picks"]))
        self.assertEqual(verdicts, sorted(verdicts, key=priority.get))
        self.assertEqual(verdicts.count("buy"), 12)
        self.assertEqual(verdicts.count("sell"), 8)
        self.assertEqual(verdicts.count("watch"), 8)

    def test_blank_market_scan_does_not_promote_mediocre_names_to_buy(self):
        class MediocreUniverseProvider:
            def discover(self, markets, limit_per_market=18):
                return [
                    DiscoveredSymbol(f"5{index:03d}.TW", f"Mediocre Corp {index}", "TW", "test-mediocre")
                    for index in range(8)
                ], []

        class MediocreMarketProvider:
            def fetch(self, symbol):
                return MarketSnapshot(
                    symbol=symbol,
                    name=symbol,
                    market="TW",
                    sector="Technology",
                    price=100,
                    change=0.2,
                    currency="TWD",
                    closes=[100 + (index % 5) * 0.2 for index in range(130)],
                    info={
                        "trailingPE": 26,
                        "priceToBook": 3.5,
                        "beta": 1.2,
                        "returnOnEquity": 0.10,
                        "profitMargins": 0.08,
                        "revenueGrowth": 0.04,
                        "earningsGrowth": 0.03,
                        "debtToEquity": 80,
                        "regularMarketVolume": 1_000_000,
                        "marketCap": 5_000_000_000,
                        "fiftyTwoWeekHigh": 140,
                        "fiftyTwoWeekLow": 80,
                    },
                )

        class NeutralNewsCrawler:
            def fetch(self, symbol, name):
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} mixed results",
                        summary="Stable but limited growth",
                        link=f"https://example.com/{symbol}",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.0,
                        credibility=0.7,
                        relevance=1.0,
                    )
                ]

        client = create_app(MediocreMarketProvider(), NeutralNewsCrawler(), MediocreUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertNotIn("buy", {pick["verdict"] for pick in payload["picks"]})
        self.assertEqual([pick["verdict"] for pick in payload["picks"]].count("watch"), 8)
        self.assertIn(payload["sectors"][0]["recommendation"], {"neutral", "underweight"})
        self.assertEqual(len(payload["picks"]), 8)
        self.assertEqual(payload["scan"]["displayed"], 8)
        self.assertEqual(payload["scan"]["succeeded"], payload["scan"]["requested"])

    def test_blank_market_scan_still_shows_analyzed_neutral_candidates(self):
        class NeutralUniverseProvider:
            def discover(self, markets, limit_per_market=18):
                return [
                    DiscoveredSymbol(f"4{index:03d}.TW", f"Neutral Corp {index}", "TW", "test-neutral")
                    for index in range(20)
                ], []

        class NeutralMarketProvider:
            def fetch(self, symbol):
                return MarketSnapshot(
                    symbol=symbol,
                    name=symbol,
                    market="TW",
                    sector="Technology",
                    price=100,
                    change=0.1,
                    currency="TWD",
                    closes=[100 + (index % 2) * 0.05 for index in range(130)],
                    info={
                        "trailingPE": 30,
                        "priceToBook": 4.0,
                        "beta": 1.0,
                        "returnOnEquity": 0.06,
                        "profitMargins": 0.04,
                        "revenueGrowth": 0.01,
                        "earningsGrowth": 0.01,
                        "debtToEquity": 95,
                        "regularMarketVolume": 1_000_000,
                        "marketCap": 5_000_000_000,
                        "fiftyTwoWeekHigh": 140,
                        "fiftyTwoWeekLow": 80,
                    },
                )

        class EmptyNewsCrawler:
            def fetch(self, symbol, name):
                return []

        client = create_app(NeutralMarketProvider(), EmptyNewsCrawler(), NeutralUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertEqual(len(payload["picks"]), 20)
        self.assertEqual(payload["scan"]["displayed"], 20)
        self.assertEqual(payload["scan"]["succeeded"], 20)
        self.assertNotIn("buy", {pick["verdict"] for pick in payload["picks"]})

    def test_auto_scan_sector_analysis_uses_full_evaluated_universe(self):
        class LargeNeutralUniverseProvider:
            def discover(self, markets, limit_per_market=18):
                return [
                    DiscoveredSymbol(f"8{index:03d}.TW", f"Full Sector Corp {index}", "TW", "test-full-sector")
                    for index in range(60)
                ], []

        class LargeNeutralMarketProvider:
            def fetch(self, symbol):
                return MarketSnapshot(
                    symbol=symbol,
                    name=symbol,
                    market="TW",
                    sector="Full Coverage Technology",
                    price=100,
                    change=0.3,
                    currency="TWD",
                    closes=[100 + (index % 4) * 0.15 for index in range(130)],
                    info={
                        "trailingPE": 28,
                        "priceToBook": 3.4,
                        "beta": 1.1,
                        "returnOnEquity": 0.09,
                        "profitMargins": 0.07,
                        "revenueGrowth": 0.03,
                        "earningsGrowth": 0.02,
                        "debtToEquity": 85,
                        "regularMarketVolume": 1_200_000,
                        "marketCap": 4_500_000_000,
                    },
                )

        class EmptyNewsCrawler:
            def fetch(self, symbol, name):
                return []

        client = create_app(LargeNeutralMarketProvider(), EmptyNewsCrawler(), LargeNeutralUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        sector = payload["sectors"][0]

        self.assertLess(len(payload["picks"]), payload["scan"]["succeeded"])
        self.assertEqual(payload["scan"]["displayed"], len(payload["picks"]))
        self.assertEqual(sector["count"], payload["scan"]["succeeded"])
        self.assertIn("averageTScore", sector)
        self.assertIn("averageDownsideRiskScore", sector)

    def test_blank_market_scan_expands_until_quality_candidates_are_found(self):
        class ExpandingUniverseProvider:
            def __init__(self):
                self.limits = []

            def discover(self, markets, limit_per_market=18):
                self.limits.append(limit_per_market)
                symbols = [
                    DiscoveredSymbol(f"5{index:03d}.TW", f"Mediocre Corp {index}", "TW", "test-expanding")
                    for index in range(6)
                ]
                if limit_per_market >= 120:
                    symbols.extend(
                        DiscoveredSymbol(f"7{index:03d}.TW", f"Quality Corp {index}", "TW", "test-expanding")
                        for index in range(4)
                    )
                return symbols, []

        class ExpandingMarketProvider:
            def fetch(self, symbol):
                if symbol.startswith("7"):
                    closes = [80 + index * 0.5 for index in range(130)]
                    info = {
                        "trailingPE": 18,
                        "priceToBook": 2.0,
                        "beta": 1.0,
                        "returnOnEquity": 0.30,
                        "profitMargins": 0.24,
                        "revenueGrowth": 0.22,
                        "earningsGrowth": 0.20,
                        "debtToEquity": 18,
                        "regularMarketVolume": 8_000_000,
                        "marketCap": 80_000_000_000,
                        "fiftyTwoWeekHigh": 150,
                        "fiftyTwoWeekLow": 70,
                    }
                else:
                    closes = [100 + (index % 5) * 0.2 for index in range(130)]
                    info = {
                        "trailingPE": 28,
                        "priceToBook": 3.6,
                        "beta": 1.2,
                        "returnOnEquity": 0.08,
                        "profitMargins": 0.06,
                        "revenueGrowth": 0.02,
                        "earningsGrowth": 0.01,
                        "debtToEquity": 90,
                        "regularMarketVolume": 900_000,
                        "marketCap": 4_000_000_000,
                        "fiftyTwoWeekHigh": 140,
                        "fiftyTwoWeekLow": 80,
                    }
                return MarketSnapshot(
                    symbol=symbol,
                    name=symbol,
                    market="TW",
                    sector="Technology",
                    price=100,
                    change=1.0,
                    currency="TWD",
                    closes=closes,
                    info=info,
                )

        class ExpandingNewsCrawler:
            def fetch(self, symbol, name):
                if symbol.startswith("7"):
                    return [
                        Article(
                            source="Test RSS",
                            title=f"{name} earnings beat and analyst upgrade",
                            summary="Revenue growth, strong demand, and target price raised",
                            link=f"https://example.com/{symbol}",
                            published_at=datetime.now(timezone.utc),
                            sentiment=0.8,
                            credibility=0.9,
                            relevance=1.0,
                        )
                    ]
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} mixed results",
                        summary="Stable but limited growth",
                        link=f"https://example.com/{symbol}",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.0,
                        credibility=0.7,
                        relevance=1.0,
                    )
                ]

        universe = ExpandingUniverseProvider()
        client = create_app(ExpandingMarketProvider(), ExpandingNewsCrawler(), universe).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        buy_symbols = {pick["symbol"] for pick in payload["picks"] if pick["verdict"] == "buy"}

        self.assertGreaterEqual(max(universe.limits), 120)
        self.assertEqual(len(buy_symbols), 4)
        self.assertTrue(all(symbol.startswith("7") for symbol in buy_symbols))
        self.assertEqual(payload["scan"]["requested"], 10)

    def test_breakout_setup_can_promote_next_day_candidate(self):
        class BreakoutProvider(FakeMarketProvider):
            def fetch(self, symbol):
                closes = [88 + index * 0.12 for index in range(120)] + [102, 103, 104, 106, 109, 112, 116, 119, 121, 127]
                return MarketSnapshot(
                    symbol=symbol,
                    name="Breakout Corp",
                    market="TW",
                    sector="Technology",
                    price=127,
                    change=5.0,
                    currency="TWD",
                    closes=closes,
                    info={
                        "trailingPE": 34,
                        "priceToBook": 4.8,
                        "beta": 1.6,
                        "returnOnEquity": 0.06,
                        "profitMargins": 0.04,
                        "revenueGrowth": 0.05,
                        "earningsGrowth": 0.03,
                        "debtToEquity": 120,
                        "regularMarketVolume": 12_000_000,
                        "marketCap": 6_000_000_000,
                        "volumeSurge20": 3.2,
                        "amountSurge20": 3.4,
                        "turnoverRate": 0.07,
                    },
                )

        class BreakoutNewsCrawler:
            def fetch(self, symbol, name):
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} wins large order and reports strong demand",
                        summary="Institutional buying, revenue growth, and analyst upgrade support the move",
                        link=f"https://example.com/{symbol}",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.8,
                        credibility=0.9,
                        relevance=1.0,
                    )
                ]

        client = create_app(BreakoutProvider(), BreakoutNewsCrawler(), FakeUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": ["8801.TW"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        pick = response.get_json()["picks"][0]

        self.assertEqual(pick["verdict"], "buy")
        self.assertGreaterEqual(pick["breakoutSetupScore"], 74)
        self.assertGreater(pick["opportunityScore"], pick["downsideRiskScore"])
        self.assertIn("breakoutSetup", {reason["key"] for reason in pick["reasonCodes"]})

    def test_breakout_setup_stays_low_without_fresh_impulse(self):
        snapshot = MarketSnapshot(
            symbol="5000.TW",
            name="Flat Corp",
            market="TW",
            sector="Technology",
            price=100.8,
            change=0.2,
            currency="TWD",
            closes=[100 + (index % 5) * 0.2 for index in range(130)],
            info={"regularMarketVolume": 1_000_000, "marketCap": 5_000_000_000},
        )

        self.assertLess(_breakout_setup_score(snapshot, _news_analysis([])), 50)

    def test_next_session_risk_downgrades_current_edge_to_watch(self):
        class FadingTrendProvider(FakeMarketProvider):
            def fetch(self, symbol):
                closes = [100 + index * 0.2 for index in range(120)] + [126, 128, 131, 134, 137, 140, 144, 148, 152, 164]
                return MarketSnapshot(
                    symbol=symbol,
                    name="Fading Edge Corp",
                    market="TW",
                    sector="Technology",
                    price=164,
                    change=7.9,
                    currency="TWD",
                    closes=closes,
                    info={
                        "trailingPE": 18,
                        "priceToBook": 2.2,
                        "beta": 1.0,
                        "returnOnEquity": 0.28,
                        "profitMargins": 0.24,
                        "revenueGrowth": 0.20,
                        "earningsGrowth": 0.20,
                        "debtToEquity": 20,
                        "regularMarketVolume": 30_000_000,
                        "marketCap": 30_000_000_000,
                        "volumeSurge20": 0.8,
                        "amountSurge20": 0.8,
                        "turnoverRate": 0.05,
                    },
                )

        class PositiveNewsCrawler:
            def fetch(self, symbol, name):
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} wins order and receives analyst upgrade",
                        summary="Revenue growth, institutional buying, and strong demand support the current move",
                        link=f"https://example.com/{symbol}",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.9,
                        credibility=0.95,
                        relevance=1.0,
                    )
                ]

        client = create_app(FadingTrendProvider(), PositiveNewsCrawler(), FakeUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": ["9901.TW"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        pick = response.get_json()["picks"][0]

        self.assertGreaterEqual(pick["score"], 90)
        self.assertGreaterEqual(pick["opportunityScore"], 70)
        self.assertEqual(pick["verdict"], "watch")
        self.assertGreaterEqual(pick["nextSessionReversalRiskScore"], 68)
        self.assertNotIn(pick["overallAssessment"]["suitability"], {"strongBuy", "buy"})
        self.assertEqual(pick["trendAnalysis"]["regime"], "overheated")
        self.assertIn("nextSessionRisk", {reason["key"] for reason in pick["reasonCodes"]})
        self.assertIn("trendReversalRisk", {metric["key"] for metric in pick["trendAnalysis"]["metrics"]})

    def test_t_trade_plan_identifies_liquid_volatile_candidate(self):
        class TTradeProvider(FakeMarketProvider):
            def fetch(self, symbol):
                closes = [48 + index * 0.08 + (0.9 if index % 2 else -0.5) for index in range(118)]
                closes.extend([58.2, 58.9, 59.6, 60.8, 62.0])
                return MarketSnapshot(
                    symbol=symbol,
                    name="Tradable Range Corp",
                    market="TW",
                    sector="Technology",
                    price=62.0,
                    change=3.6,
                    currency="TWD",
                    closes=closes,
                    info={
                        "trailingPE": 24,
                        "priceToBook": 2.8,
                        "beta": 1.1,
                        "returnOnEquity": 0.18,
                        "profitMargins": 0.16,
                        "revenueGrowth": 0.14,
                        "earningsGrowth": 0.12,
                        "debtToEquity": 35,
                        "regularMarketVolume": 20_000_000,
                        "turnoverValue": 1_200_000_000,
                        "marketCap": 12_000_000_000,
                        "volumeSurge20": 2.7,
                        "amountSurge20": 2.9,
                        "turnoverRate": 0.06,
                    },
                )

        class PositiveNewsCrawler:
            def fetch(self, symbol, name):
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} wins large order with institutional buying",
                        summary="Strong demand, revenue growth, and analyst upgrade support active trading",
                        link=f"https://example.com/{symbol}",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.78,
                        credibility=0.9,
                        relevance=1.0,
                    )
                ]

        client = create_app(TTradeProvider(), PositiveNewsCrawler(), FakeUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": ["6601.TW"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        pick = response.get_json()["picks"][0]

        self.assertGreaterEqual(pick["tScore"], 68)
        self.assertEqual(pick["tPlan"]["suitability"], "candidate")
        self.assertLess(pick["tPlan"]["entryZone"]["low"], pick["price"])
        self.assertGreater(pick["tPlan"]["takeProfitZone"]["high"], pick["price"])
        self.assertLess(pick["tPlan"]["stopLoss"], pick["tPlan"]["entryZone"]["low"])
        self.assertIn("tLiquidityReady", {item["key"] for item in pick["tPlan"]["reasons"]})
        self.assertIn("tUseBasePositionOnly", {item["key"] for item in pick["tPlan"]["riskControls"]})

    def test_already_limit_up_stock_is_analyzed_as_pullback_risk_not_buy(self):
        class LimitUpProvider(FakeMarketProvider):
            def fetch(self, symbol):
                closes = [70 + index * 0.12 for index in range(110)] + [84, 86, 89, 92, 96, 101, 107, 113, 120, 144]
                return MarketSnapshot(
                    symbol=symbol,
                    name="Limit Up Corp",
                    market="CN",
                    sector="Technology",
                    price=144,
                    change=20.0,
                    currency="CNY",
                    closes=closes,
                    info={
                        "trailingPE": 22,
                        "priceToBook": 2.4,
                        "beta": 1.2,
                        "returnOnEquity": 0.22,
                        "profitMargins": 0.18,
                        "revenueGrowth": 0.18,
                        "earningsGrowth": 0.16,
                        "debtToEquity": 30,
                        "regularMarketVolume": 30_000_000,
                        "marketCap": 20_000_000_000,
                        "volumeSurge20": 4.5,
                        "amountSurge20": 5.0,
                        "turnoverRate": 0.22,
                    },
                )

        class PositiveNewsCrawler:
            def fetch(self, symbol, name):
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} earnings beat and wins large order",
                        summary="Strong demand, institutional buying, revenue growth, and analyst upgrade",
                        link=f"https://example.com/{symbol}",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.9,
                        credibility=0.9,
                        relevance=1.0,
                    )
                ]

        client = create_app(LimitUpProvider(), PositiveNewsCrawler(), FakeUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["CN"], "symbols": ["688108.SS"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        pick = response.get_json()["picks"][0]

        self.assertNotEqual(pick["verdict"], "buy")
        self.assertGreaterEqual(pick["pullbackRiskScore"], 62)
        self.assertGreater(pick["downsideRiskScore"], pick["opportunityScore"])
        self.assertIn("overheatedPriceAction", {reason["key"] for reason in pick["reasonCodes"]})
        self.assertIn("actionWaitPullback", {item["key"] for item in pick["actionPlan"]["riskControls"]})
        self.assertEqual(pick["tPlan"]["suitability"], "avoid")
        self.assertIn("tNoChase", {item["key"] for item in pick["tPlan"]["riskControls"]})

    def test_limit_down_stock_is_not_marked_as_quality_buy(self):
        class LimitDownProvider(FakeMarketProvider):
            def fetch(self, symbol):
                snapshot = super().fetch(symbol)
                return MarketSnapshot(
                    symbol=snapshot.symbol,
                    name=snapshot.name,
                    market=snapshot.market,
                    sector=snapshot.sector,
                    price=snapshot.price,
                    change=-10.0,
                    currency=snapshot.currency,
                    closes=[80 + index * 0.5 for index in range(130)],
                    info={
                        "trailingPE": 18,
                        "priceToBook": 2.0,
                        "beta": 1.0,
                        "returnOnEquity": 0.28,
                        "profitMargins": 0.24,
                        "revenueGrowth": 0.20,
                        "earningsGrowth": 0.18,
                        "debtToEquity": 20,
                    },
                )

        client = create_app(LimitDownProvider(), self.news_crawler, FakeUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": ["2330.TW"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        pick = response.get_json()["picks"][0]

        self.assertEqual(pick["verdict"], "sell")
        self.assertIn("severePriceDrop", {reason["key"] for reason in pick["reasonCodes"]})
        self.assertIn("actionAvoidLimitDown", {item["key"] for item in pick["actionPlan"]["riskControls"]})

    def test_downside_prediction_marks_likely_falling_stock_as_sell(self):
        class WeakTrendProvider(FakeMarketProvider):
            def fetch(self, symbol):
                snapshot = super().fetch(symbol)
                return MarketSnapshot(
                    symbol=snapshot.symbol,
                    name=snapshot.name,
                    market=snapshot.market,
                    sector=snapshot.sector,
                    price=70,
                    change=-4.2,
                    currency=snapshot.currency,
                    closes=[130 - index * 0.45 for index in range(130)],
                    info={
                        "trailingPE": 55,
                        "priceToBook": 7,
                        "beta": 2.2,
                        "returnOnEquity": 0.02,
                        "profitMargins": 0.01,
                        "revenueGrowth": -0.18,
                        "earningsGrowth": -0.25,
                        "debtToEquity": 220,
                    },
                )

        class NegativeNewsCrawler:
            def fetch(self, symbol, name):
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} profit warning and analyst downgrade",
                        summary="Weak demand, target price cut, and institutional selling",
                        link=f"https://example.com/{symbol}",
                        published_at=datetime.now(timezone.utc),
                        sentiment=-0.8,
                        credibility=0.9,
                        relevance=1.0,
                    )
                ]

        client = create_app(WeakTrendProvider(), NegativeNewsCrawler(), FakeUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["TW"], "symbols": ["2330.TW"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        pick = response.get_json()["picks"][0]

        self.assertEqual(pick["verdict"], "sell")
        self.assertGreater(pick["downsideRiskScore"], pick["opportunityScore"])
        self.assertGreaterEqual(pick["downsideRiskScore"], 72)

    def test_response_contains_detailed_100_point_scoring_and_actions(self):
        response = self.client.post("/api/analyze", json={"markets": ["US"], "symbols": ["AAPL"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        pick = response.get_json()["picks"][0]
        self.assertIn("scoreBreakdown", pick)
        self.assertIn("decisionEngine", pick)
        self.assertEqual(pick["decisionEngine"]["version"], "scenario-v1")
        self.assertEqual(pick["decisionEngine"]["legacyWeightRole"], "secondary")
        self.assertIn(pick["decisionEngine"]["action"], {"accumulate", "hold", "reduce", "exit"})
        self.assertIn(pick["decisionEngine"]["regime"]["name"], {"quality_compounder", "momentum_breakout", "deep_value_turnaround", "event_driven", "falling_knife", "overheated", "balanced_watch", "insufficient_data", "defensive_etf_core", "sector_etf_tactical"})
        self.assertIn("dataQuality", pick["decisionEngine"])
        self.assertIn("marketSupport", pick["decisionEngine"])
        self.assertIn("marketSupportScore", pick["decisionEngine"]["dataQuality"])
        self.assertEqual(pick["decisionEngine"]["marketSupport"]["coverageTier"], "global")
        self.assertGreater(pick["decisionEngine"]["marketSupport"]["score"], 0)
        self.assertEqual(pick["compositeModel"]["weights"]["legacyWeights"], 0)
        self.assertIn("opportunityScore", pick)
        self.assertIn("downsideRiskScore", pick)
        self.assertIn("nextSessionContinuationScore", pick)
        self.assertIn("nextSessionReversalRiskScore", pick)
        self.assertIn("tScore", pick)
        self.assertIn("tPlan", pick)
        self.assertIn(pick["tPlan"]["suitability"], {"candidate", "watch", "avoid"})
        self.assertIn("entryZone", pick["tPlan"])
        self.assertIn("takeProfitZone", pick["tPlan"])
        self.assertIn("stopLoss", pick["tPlan"])
        self.assertAlmostEqual(pick["prediction"]["edge"], pick["opportunityScore"] - pick["downsideRiskScore"], delta=0.1)
        self.assertAlmostEqual(pick["prediction"]["tScore"], pick["tScore"], delta=0.1)
        self.assertAlmostEqual(pick["prediction"]["nextSessionContinuationScore"], pick["nextSessionContinuationScore"], delta=0.1)
        self.assertEqual({item["factor"] for item in pick["scoreBreakdown"]}, {"sentiment", "momentum", "value", "risk", "quality"})
        self.assertAlmostEqual(sum(item["contribution"] for item in pick["scoreBreakdown"]), pick["score"], delta=0.5)
        self.assertIn("decision", pick)
        self.assertIn("summary", pick["decision"])
        self.assertIn("watchItems", pick["decision"])
        self.assertIn("newsAnalysis", pick)
        self.assertEqual(pick["newsAnalysis"]["positiveCount"], 1)
        self.assertGreater(pick["newsAnalysis"]["positiveScore"], 0)
        self.assertIn("newsHeatAnalysis", pick)
        self.assertIn("newsHeat", {metric["key"] for metric in pick["newsHeatAnalysis"]["metrics"]})
        self.assertIn("overallAssessment", pick)
        self.assertIn("overallTodayBuy", {metric["key"] for metric in pick["overallAssessment"]["metrics"]})
        self.assertIn(pick["overallAssessment"]["suitability"], {"strongBuy", "buy", "watch", "avoid", "sell"})
        self.assertAlmostEqual(pick["prediction"]["overallScore"], pick["overallAssessment"]["totalScore"], delta=0.1)
        self.assertIn("trendAnalysis", pick)
        self.assertIn("trendContinuation", {metric["key"] for metric in pick["trendAnalysis"]["metrics"]})
        self.assertIn(pick["trendAnalysis"]["regime"], {"bullish", "constructive", "neutral", "fragile", "bearish", "overheated", "insufficient"})
        self.assertIn("positiveScore", pick["decision"]["positives"][0]["params"])
        self.assertEqual(pick["newsAnalysis"]["events"][0]["key"], "earningsPositive")
        self.assertIn("financialAnalysis", pick)
        self.assertTrue(pick["financialAnalysis"]["metrics"])
        self.assertIn("actionPlan", pick)
        self.assertIn("steps", pick["actionPlan"])

    def test_decision_engine_risk_gate_overrides_positive_weight_score(self):
        class PriceBreakdownProvider:
            def fetch(self, symbol):
                closes = [100 + index * 0.05 for index in range(128)] + [108.0, 96.0]
                return MarketSnapshot(
                    symbol=symbol,
                    name="Risk Gate Corp",
                    market="US",
                    sector="Technology",
                    price=96.0,
                    change=-11.1,
                    currency="USD",
                    closes=closes,
                    info={
                        "trailingPE": 18,
                        "returnOnEquity": 0.2,
                        "profitMargins": 0.18,
                        "debtToEquity": 24,
                        "regularMarketVolume": 9_000_000,
                        "marketCap": 40_000_000_000,
                        "fiftyTwoWeekHigh": 125,
                        "fiftyTwoWeekLow": 82,
                    },
                )

        class PositiveNewsCrawler:
            def fetch(self, symbol, name):
                return [
                    Article(
                        source="Test RSS",
                        title=f"{name} reports strong growth and analyst upgrade",
                        summary="Revenue beats expectations and guidance raised",
                        link="https://example.com/risk-gate",
                        published_at=datetime.now(timezone.utc),
                        sentiment=0.85,
                        credibility=0.9,
                        relevance=1.0,
                    )
                ]

        client = create_app(PriceBreakdownProvider(), PositiveNewsCrawler(), FakeUniverseProvider()).test_client()
        response = client.post(
            "/api/analyze",
            json={
                "markets": ["US"],
                "symbols": ["RISK"],
                "strategyId": "balanced",
                "customWeights": {"sentiment": 95, "momentum": 1, "value": 1, "risk": 1, "quality": 2},
            },
        )

        self.assertEqual(response.status_code, 200)
        pick = response.get_json()["picks"][0]
        gate_keys = {gate["key"] for gate in pick["decisionEngine"]["gates"]}
        self.assertIn("severePriceBreakdown", gate_keys)
        self.assertEqual(pick["decisionEngine"]["action"], "exit")
        self.assertEqual(pick["verdict"], "sell")
        self.assertLessEqual(pick["decisionEngine"]["buyScore"], 30)
        self.assertEqual(pick["decisionEngine"]["legacyWeightRole"], "secondary")

    def test_etf_analysis_uses_fund_specific_metrics_and_composite_model(self):
        class EtfMarketProvider:
            def fetch(self, symbol):
                closes = [420 + index * 0.55 + (index % 7) * 0.12 for index in range(130)]
                return MarketSnapshot(
                    symbol=symbol,
                    name="SPDR S&P 500 ETF Trust",
                    market="US",
                    sector="ETF / Fund",
                    price=round(closes[-1], 3),
                    change=0.4,
                    currency="USD",
                    closes=closes,
                    info={
                        "quoteType": "ETF",
                        "instrumentType": "etf",
                        "shortName": "SPDR S&P 500 ETF Trust",
                        "regularMarketVolume": 64_000_000,
                        "marketCap": 550_000_000_000,
                        "totalAssets": 550_000_000_000,
                        "annualReportExpenseRatio": 0.0009,
                        "dividendYield": 0.012,
                        "fiftyTwoWeekHigh": 505,
                        "fiftyTwoWeekLow": 390,
                    },
                    instrument_type="etf",
                )

        client = create_app(EtfMarketProvider(), self.news_crawler, FakeUniverseProvider()).test_client()
        response = client.post("/api/analyze", json={"markets": ["US"], "symbols": ["SPY"], "strategyId": "balanced"})

        self.assertEqual(response.status_code, 200)
        pick = response.get_json()["picks"][0]
        self.assertEqual(pick["instrumentType"], "etf")
        self.assertEqual(pick["compositeModel"]["instrumentType"], "etf")
        self.assertEqual(pick["decisionEngine"]["instrumentType"], "etf")
        self.assertIn(pick["decisionEngine"]["regime"]["name"], {"defensive_etf_core", "sector_etf_tactical"})
        self.assertIn(pick["compositeModel"]["decision"], {"accumulate", "hold", "reduce", "exit"})
        metric_keys = {metric["key"] for metric in pick["financialAnalysis"]["metrics"]}
        self.assertIn("etfTrend", metric_keys)
        self.assertIn("etfExpenseRatio", metric_keys)
        self.assertIn("etfLiquidity", metric_keys)
        self.assertEqual(_manual_symbol_candidates("510300", {"CN"}), ["510300.SS"])
        self.assertTrue(is_common_equity_symbol("510300.SS", "CN"))

    def test_response_contains_sector_analysis(self):
        response = self.client.post("/api/analyze", json={"markets": ["US"], "symbols": ["AAPL", "MSFT"], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("sectors", payload)
        self.assertEqual(len(payload["sectors"]), 1)
        sector = payload["sectors"][0]
        self.assertEqual(sector["name"], "Technology")
        self.assertEqual(sector["count"], 2)
        self.assertIn(sector["recommendation"], {"overweight", "neutral", "underweight"})
        self.assertEqual(set(sector["metrics"]), {"sentiment", "momentum", "value", "risk", "quality"})
        self.assertEqual(sum(sector["verdictCounts"].values()), 2)
        self.assertIn("tCandidateCount", sector)
        self.assertIn("averageTScore", sector)
        self.assertIn("averageOpportunityScore", sector)
        self.assertIn("averageDownsideRiskScore", sector)
        self.assertTrue(sector["leaders"])
        self.assertIn("symbol", sector["leaders"][0])

    def test_eastmoney_fallback_builds_cn_market_snapshot(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        def fake_urlopen(request, timeout=10):
            url = request.full_url
            if "kline/get" in url:
                return FakeResponse(
                    {
                        "data": {
                            "name": "测试A股",
                            "klines": [
                                f"2026-01-{day:02d},{10 + day / 10:.2f},{10 + day / 8:.2f},{11 + day / 8:.2f},9,1000,10000,1,1.2,0.1,2"
                                for day in range(1, 32)
                            ],
                        }
                    }
                )
            return FakeResponse(
                {
                    "data": {
                        "f58": "测试A股",
                        "f47": 1000,
                        "f48": 1000000,
                        "f116": 5000000000,
                        "f117": 3000000000,
                        "f162": 1800,
                        "f167": 210,
                        "f168": 200,
                        "f170": 120,
                    }
                }
            )

        with patch("backend.providers.urlopen", fake_urlopen):
            snapshot = EastmoneyCnMarketDataProvider().fetch("603006.SS")

        self.assertEqual(snapshot.symbol, "603006.SS")
        self.assertEqual(snapshot.market, "CN")
        self.assertEqual(snapshot.currency, "CNY")
        self.assertEqual(snapshot.name, "测试A股")
        self.assertGreater(len(snapshot.closes), 20)
        self.assertAlmostEqual(snapshot.info["trailingPE"], 18)

    def test_eastmoney_fund_flow_parses_intraday_capital_flow(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(
                    {
                        "data": {
                            "diff": [
                                {
                                    "f62": 87_515_554,
                                    "f184": 6.2,
                                    "f66": 42_000_000,
                                    "f69": 3.1,
                                    "f72": 45_515_554,
                                    "f75": 3.1,
                                    "f78": -21_000_000,
                                    "f81": -1.5,
                                    "f84": -66_515_554,
                                    "f87": -4.7,
                                }
                            ]
                        }
                    }
                ).encode("utf-8")

        with patch("backend.providers.urlopen", return_value=FakeResponse()):
            flow = _eastmoney_cn_fund_flow("300750.SZ")

        self.assertEqual(flow["fundFlowSource"], "Eastmoney")
        self.assertEqual(flow["fundFlowMainNet"], 87_515_554)
        self.assertEqual(flow["fundFlowMainRatio"], 6.2)
        self.assertEqual(flow["fundFlowSuperLargeRatio"], 3.1)
        self.assertEqual(flow["fundFlowSmallRatio"], -4.7)

    def test_sina_fund_flow_parses_online_capital_flow(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(
                    [
                        {
                            "opendate": "2026-06-10",
                            "netamount": "394283846.5900",
                            "ratioamount": "0.0818154",
                            "r0_net": "437468832.1200",
                            "r0_ratio": "0.09077645",
                            "r1_net": "-30361953.6700",
                            "r2_net": "-12597959.8600",
                            "r3_net": "-225072.0000",
                        }
                    ]
                ).encode("utf-8")

        with patch("backend.providers.urlopen", return_value=FakeResponse()):
            flow = _sina_cn_fund_flow("002129.SZ")

        self.assertEqual(flow["fundFlowSource"], "Sina")
        self.assertEqual(flow["fundFlowMainNet"], 437468832.12)
        self.assertAlmostEqual(flow["fundFlowMainRatio"], 9.077645)
        self.assertEqual(flow["fundFlowLargeNet"], -30361953.67)
        self.assertEqual(flow["fundFlowMediumNet"], -12597959.86)
        self.assertEqual(flow["fundFlowSmallNet"], -225072.0)

    def test_eastmoney_fundamentals_still_fetches_fund_flow_when_quote_payload_fails(self):
        from backend.providers import _eastmoney_cn_fundamentals

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        def fake_urlopen(request, timeout=10):
            url = request.full_url
            if "ulist.np/get" in url:
                return FakeResponse({"data": {"diff": [{"f62": -50_000_000, "f184": -8.5, "f66": -20_000_000, "f69": -3.4}]}})
            return FakeResponse({"data": None})

        with patch("backend.providers.urlopen", fake_urlopen):
            fundamentals = _eastmoney_cn_fundamentals("300750.SZ")

        self.assertEqual(fundamentals["fundFlowMainNet"], -50_000_000)
        self.assertEqual(fundamentals["fundFlowMainRatio"], -8.5)

    def test_fund_flow_changes_scoring_and_financial_evidence(self):
        base_info = {
            "trailingPE": 18,
            "priceToBook": 2.2,
            "regularMarketVolume": 5_000_000,
            "turnoverValue": 1_000_000_000,
            "marketCap": 50_000_000_000,
        }
        positive_snapshot = MarketSnapshot(
            symbol="300750.SZ",
            name="CATL",
            market="CN",
            sector="Industrials",
            price=100,
            change=2.2,
            currency="CNY",
            closes=[80 + index * 0.2 for index in range(130)],
            info={
                **base_info,
                "fundFlowSource": "Eastmoney",
                "fundFlowMainNet": 90_000_000,
                "fundFlowMainRatio": 6.5,
                "fundFlowSuperLargeNet": 40_000_000,
                "fundFlowSuperLargeRatio": 3.0,
                "fundFlowLargeNet": 50_000_000,
                "fundFlowLargeRatio": 3.5,
                "fundFlowSmallNet": -70_000_000,
                "fundFlowSmallRatio": -5.0,
            },
        )
        negative_snapshot = MarketSnapshot(
            **{
                **positive_snapshot.__dict__,
                "info": {
                    **base_info,
                    "fundFlowSource": "Eastmoney",
                    "fundFlowMainNet": -90_000_000,
                    "fundFlowMainRatio": -6.5,
                    "fundFlowSuperLargeNet": -40_000_000,
                    "fundFlowSuperLargeRatio": -3.0,
                    "fundFlowLargeNet": -50_000_000,
                    "fundFlowLargeRatio": -3.5,
                    "fundFlowSmallNet": 70_000_000,
                    "fundFlowSmallRatio": 5.0,
                },
            }
        )
        news = _news_analysis([])
        positive_metrics = _metrics(positive_snapshot, [])
        negative_metrics = _metrics(negative_snapshot, [])
        positive_financials = _financial_analysis(positive_snapshot)
        negative_financials = _financial_analysis(negative_snapshot)

        self.assertGreater(positive_metrics["sentiment"], negative_metrics["sentiment"])
        self.assertGreater(positive_metrics["momentum"], negative_metrics["momentum"])
        self.assertLess(_pullback_risk_score(positive_snapshot, news), _pullback_risk_score(negative_snapshot, news))
        self.assertGreater(_breakout_setup_score(positive_snapshot, news), _breakout_setup_score(negative_snapshot, news))
        self.assertIn("fundFlowMain", {metric["key"] for metric in positive_financials["metrics"]})
        self.assertIn("fundFlowSupport", {item["key"] for item in positive_financials["positives"]})
        self.assertIn("fundFlowPressure", {item["key"] for item in negative_financials["negatives"]})
        self.assertTrue(_fund_flow_profile(positive_snapshot.info)["available"])

    def test_yahoo_http_retries_alternate_hosts_for_market_snapshot(self):
        calls = []

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        def fake_urlopen(request, timeout=10):
            url = request.full_url
            calls.append(url)
            if "query1.finance.yahoo.com" in url:
                raise OSError("Remote end closed connection without response")
            if "quoteSummary" in url:
                return FakeResponse(
                    {
                        "quoteSummary": {
                            "result": [
                                {
                                    "price": {"shortName": "Apple", "currency": "USD", "marketCap": {"raw": 1_000_000}},
                                    "summaryProfile": {"sector": "Technology"},
                                    "summaryDetail": {"trailingPE": {"raw": 30}, "beta": {"raw": 1.2}},
                                }
                            ]
                        }
                    }
                )
            return FakeResponse(
                {
                    "chart": {
                        "result": [
                            {
                                "meta": {"regularMarketPrice": 101, "currency": "USD", "regularMarketVolume": 123},
                                "indicators": {"quote": [{"close": [99, 100, 101]}]},
                            }
                        ],
                        "error": None,
                    }
                }
            )

        with patch("backend.providers.urlopen", fake_urlopen):
            snapshot = YahooHttpMarketDataProvider().fetch("AAPL")

        self.assertTrue(any("query1.finance.yahoo.com" in url for url in calls))
        self.assertTrue(any("query2.finance.yahoo.com" in url for url in calls))
        self.assertEqual(snapshot.symbol, "AAPL")
        self.assertEqual(snapshot.name, "Apple")
        self.assertEqual(snapshot.price, 101)
        self.assertEqual(snapshot.currency, "USD")
        self.assertAlmostEqual(snapshot.info["trailingPE"], 30)

    def test_taiwan_exchange_provider_builds_snapshot_from_twse_rows(self):
        class FakeTaiwanProvider(TaiwanExchangeMarketDataProvider):
            def _json(self, url, attempts=2, timeout=4):
                return {
                    "stat": "OK",
                    "title": "115\u5e7405\u6708 6239 \u529b\u6210             \u5404\u65e5\u6210\u4ea4\u8cc7\u8a0a",
                    "data": [
                        ["115/05/25", "1,000", "100,000", "99.00", "101.00", "98.00", "100.00", "+1.00", "20", ""],
                        ["115/05/26", "2,000", "204,000", "101.00", "104.00", "100.00", "102.00", "+2.00", "30", ""],
                        ["115/05/27", "3,000", "315,000", "103.00", "106.00", "101.00", "105.00", "+3.00", "40", ""],
                    ],
                }

        snapshot = FakeTaiwanProvider().fetch("6239.TW")

        self.assertEqual(snapshot.symbol, "6239.TW")
        self.assertEqual(snapshot.name, "\u529b\u6210")
        self.assertEqual(snapshot.market, "TW")
        self.assertEqual(snapshot.currency, "TWD")
        self.assertEqual(snapshot.price, 105)
        self.assertEqual(snapshot.closes, [100, 102, 105])
        self.assertEqual(snapshot.info["regularMarketVolume"], 3000)
        self.assertEqual(snapshot.info["turnoverValue"], 315000)

    def test_taiwan_symbol_falls_back_to_exchange_when_yahoo_fails(self):
        fallback_snapshot = MarketSnapshot(
            symbol="6239.TW",
            name="\u529b\u6210",
            market="TW",
            sector="Semiconductors",
            price=105,
            change=2.94,
            currency="TWD",
            closes=[100, 102, 105],
            info={"shortName": "\u529b\u6210"},
        )

        with patch("backend.providers.YahooHttpMarketDataProvider.fetch", side_effect=OSError("Remote end closed connection")):
            with patch("backend.providers.TaiwanExchangeMarketDataProvider.fetch", return_value=fallback_snapshot):
                snapshot = fallback_market_data_provider("6239.TW")

        self.assertEqual(snapshot.name, "\u529b\u6210")
        self.assertEqual(snapshot.price, 105)

    def test_raw_provider_errors_are_hidden_from_scan_response(self):
        class BrokenMarketProvider:
            def fetch(self, symbol):
                raise OSError("[Errno 2] No such file or directory")

        response = create_app(BrokenMarketProvider(), self.news_crawler, FakeUniverseProvider()).test_client().post(
            "/api/analyze",
            json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"},
        )
        payload = response.get_json()
        self.assertTrue(payload["errors"])
        self.assertIn("行情资料暂时不可用", payload["errors"][0]["error"])
        self.assertNotIn("urlopen", payload["errors"][0]["error"])
        self.assertNotIn("No such file", payload["errors"][0]["error"])

    def test_incomplete_read_provider_errors_are_hidden(self):
        message = _friendly_data_error("002384.SZ", OSError("IncompleteRead(0 bytes read)"))
        self.assertIn("行情资料暂时不可用", message)
        self.assertNotIn("IncompleteRead", message)


if __name__ == "__main__":
    unittest.main()
