import unittest
from datetime import datetime, timezone

from backend.app import create_app
from backend.providers import Article, MarketSnapshot, RssNewsCrawler, is_recent_article, local_company_name, news_queries, news_query
from backend.universe import DiscoveredSymbol, MarketUniverseProvider


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


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.news_crawler = FakeNewsCrawler()
        self.client = create_app(FakeMarketProvider(), self.news_crawler, FakeUniverseProvider()).test_client()

    def test_config_contains_real_defaults(self):
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["markets"]), 5)
        self.assertGreaterEqual(len(payload["strategies"]), 3)
        self.assertIn("defaultSymbols", payload)
        self.assertIn("scanUniverseSize", payload)
        self.assertIn("2330.TW", payload["defaultSymbols"]["TW"])
        self.assertEqual(payload["scanUniverseSize"]["TW"], "dynamic")

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

    def test_fallback_search_keeps_broad_china_universe_without_yahoo(self):
        class OfflineUniverse(MarketUniverseProvider):
            def _json(self, url, insecure=False):
                raise OSError("offline")

        symbols = OfflineUniverse()._discover_fallback_search("CN", 18)
        self.assertGreaterEqual(len(symbols), 10)
        self.assertIn("600519.SS", {item.symbol for item in symbols})
        self.assertIn("\u8d35\u5dde\u8305\u53f0", {item.name for item in symbols})

    def test_sgx_discovery_ignores_unnamed_codes_and_uses_curated_names(self):
        class FakeSgxUniverse(MarketUniverseProvider):
            def _json(self, url, insecure=False):
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


    def test_blank_symbols_trigger_default_market_scan(self):
        response = self.client.post("/api/analyze", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["picks"])
        self.assertTrue(all(pick["market"] == "TW" for pick in payload["picks"]))
        self.assertEqual(payload["scan"]["source"], "market-universe")
        self.assertEqual({pick["symbol"] for pick in payload["picks"]}, {"8888.TW", "9999.TW"})
        self.assertNotIn("2330.TW", {pick["symbol"] for pick in payload["picks"]})

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

    def test_scan_produces_relative_buy_candidates(self):
        response = self.client.post("/api/analyze", json={"markets": ["TW"], "symbols": [], "strategyId": "balanced"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("buy", {pick["verdict"] for pick in payload["picks"]})


if __name__ == "__main__":
    unittest.main()
