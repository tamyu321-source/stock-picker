import os
from hmac import compare_digest

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS

from backend.cache import CachedMarketDataProvider, CachedNewsCrawler
from backend.charts import fetch_stock_chart
from backend.data import STRATEGIES
from backend.portfolio import parse_portfolio_export
from backend.providers import RssNewsCrawler, YFinanceMarketDataProvider
from backend.services import analyze, get_config, stream_analyze
from backend.strategy_library import all_runtime_strategies, get_strategy_catalog


DEFAULT_API_ACCESS_KEY = "19940710"
API_KEY_HEADER = "X-Stock-Picker-Key"


def create_app(market_provider=None, news_crawler=None, universe_provider=None) -> Flask:
    market_provider = market_provider if market_provider is not None else CachedMarketDataProvider(YFinanceMarketDataProvider())
    news_crawler = news_crawler if news_crawler is not None else CachedNewsCrawler(RssNewsCrawler())
    app = Flask(__name__)
    allowed_origins = [
        origin.strip()
        for origin in os.environ.get(
            "ALLOWED_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,https://tamyu321-source.github.io",
        ).split(",")
        if origin.strip()
    ]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins, "allow_headers": ["Content-Type", API_KEY_HEADER]}})
    api_access_keys = [
        key.strip()
        for key in os.environ.get("API_ACCESS_KEYS", DEFAULT_API_ACCESS_KEY).split(",")
        if key.strip()
    ]

    @app.before_request
    def require_api_key():
        if not api_access_keys or not request.path.startswith("/api/") or request.method == "OPTIONS":
            return None
        provided_key = request.headers.get(API_KEY_HEADER, "")
        if any(compare_digest(provided_key, access_key) for access_key in api_access_keys):
            return None
        return jsonify({"error": "A valid API access key is required."}), 401

    @app.get("/api/health")
    def health():
        cache = {}
        if hasattr(market_provider, "stats"):
            cache["marketData"] = market_provider.stats()
        if hasattr(news_crawler, "stats"):
            cache["news"] = news_crawler.stats()
        return jsonify({"status": "ok", "service": "open-stock-picker", "cache": cache})

    @app.get("/api/config")
    def config():
        return jsonify(get_config())

    @app.get("/api/strategies/refresh")
    def strategy_refresh():
        catalog = get_strategy_catalog(refresh=True)
        return jsonify({**catalog, "runtimeStrategies": all_runtime_strategies(STRATEGIES, refresh=False)})

    @app.get("/api/stocks/<path:symbol>/chart")
    def stock_chart(symbol: str):
        try:
            return jsonify(fetch_stock_chart(symbol))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/analyze")
    def analyze_endpoint():
        return jsonify(
            analyze(
                request.get_json(silent=True) or {},
                market_provider=market_provider,
                news_crawler=news_crawler,
                universe_provider=universe_provider,
            )
        )

    @app.post("/api/analyze/stream")
    def analyze_stream_endpoint():
        events = stream_analyze(
            request.get_json(silent=True) or {},
            market_provider=market_provider,
            news_crawler=news_crawler,
            universe_provider=universe_provider,
        )
        return Response(
            stream_with_context(events),
            mimetype="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/portfolio/import")
    def portfolio_import_endpoint():
        uploaded = request.files.get("file")
        if uploaded is None:
            return jsonify({"error": "No holdings file was uploaded."}), 400
        try:
            return jsonify(parse_portfolio_export(uploaded.read(), uploaded.filename or "holdings export"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
