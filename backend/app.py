import os

from flask import Flask, Response, jsonify, request, stream_with_context
from flask import g
from flask_cors import CORS

from backend.auth_store import AuthStore, DEFAULT_API_ACCESS_KEY
from backend.cache import CachedMarketDataProvider, CachedNewsCrawler
from backend.charts import fetch_stock_chart
from backend.data import STRATEGIES
from backend.portfolio import parse_portfolio_export
from backend.providers import RssNewsCrawler, YFinanceMarketDataProvider
from backend.services import analyze, get_config, stream_analyze
from backend.strategy_library import all_runtime_strategies, get_strategy_catalog


AUTH_HEADER = "Authorization"


def _bearer_token() -> str:
    value = request.headers.get(AUTH_HEADER, "")
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return ""


def create_app(market_provider=None, news_crawler=None, universe_provider=None, auth_store: AuthStore | None = None) -> Flask:
    market_provider = market_provider if market_provider is not None else CachedMarketDataProvider(YFinanceMarketDataProvider())
    news_crawler = news_crawler if news_crawler is not None else CachedNewsCrawler(RssNewsCrawler())
    auth_store = auth_store or AuthStore.from_env()
    app = Flask(__name__)
    allowed_origins = [
        origin.strip()
        for origin in os.environ.get(
            "ALLOWED_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,https://tamyu321-source.github.io",
        ).split(",")
        if origin.strip()
    ]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins, "allow_headers": ["Content-Type", AUTH_HEADER]}})

    public_api_paths = {
        "/api/health",
        "/api/auth/login",
        "/api/auth/me",
        "/api/admin/login",
    }

    @app.before_request
    def require_auth_session():
        if not auth_store.enabled or not request.path.startswith("/api/") or request.method == "OPTIONS":
            return None
        if request.path in public_api_paths:
            return None
        session = auth_store.verify_session(_bearer_token())
        if not session:
            return jsonify({"error": "A valid login session is required."}), 401
        if request.path.startswith("/api/admin/") and session.get("role") != "admin":
            return jsonify({"error": "Administrator access is required."}), 403
        g.auth_session = session
        return None

    @app.get("/api/health")
    def health():
        cache = {}
        if hasattr(market_provider, "stats"):
            cache["marketData"] = market_provider.stats()
        if hasattr(news_crawler, "stats"):
            cache["news"] = news_crawler.stats()
        return jsonify({"status": "ok", "service": "open-stock-picker", "auth": {"enabled": auth_store.enabled, "adminEnabled": auth_store.admin_enabled}, "cache": cache})

    @app.post("/api/auth/login")
    def auth_login():
        if not auth_store.enabled:
            return jsonify({"error": "Login is not configured."}), 503
        payload = request.get_json(silent=True) or {}
        session = auth_store.login_with_key(str(payload.get("key") or ""))
        if not session:
            return jsonify({"error": "The access key is invalid or disabled."}), 401
        return jsonify(session)

    @app.get("/api/auth/me")
    def auth_me():
        session = auth_store.verify_session(_bearer_token())
        if not session:
            return jsonify({"authenticated": False}), 401
        return jsonify({"authenticated": True, "user": {"id": session.get("sub"), "label": session.get("label")}, "role": session.get("role"), "expiresAt": session.get("exp")})

    @app.post("/api/admin/login")
    def admin_login():
        payload = request.get_json(silent=True) or {}
        session = auth_store.login_admin(str(payload.get("username") or ""), str(payload.get("password") or ""))
        if not session:
            return jsonify({"error": "The administrator credentials are invalid or not configured."}), 401
        return jsonify(session)

    @app.get("/api/user/state")
    def user_state():
        session = getattr(g, "auth_session", {})
        if session.get("role") != "user":
            return jsonify({"error": "User login is required."}), 403
        return jsonify(auth_store.user_state(str(session.get("sub"))))

    @app.put("/api/user/state")
    def update_user_state():
        session = getattr(g, "auth_session", {})
        if session.get("role") != "user":
            return jsonify({"error": "User login is required."}), 403
        return jsonify(auth_store.update_user_state(str(session.get("sub")), request.get_json(silent=True) or {}))

    @app.get("/api/admin/users")
    def admin_users():
        return jsonify({"users": auth_store.list_users()})

    @app.post("/api/admin/users")
    def admin_create_user():
        payload = request.get_json(silent=True) or {}
        try:
            user = auth_store.create_user(
                str(payload.get("accessKey") or ""),
                label=str(payload.get("label") or ""),
                notes=str(payload.get("notes") or ""),
                enabled=bool(payload.get("enabled", True)),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"user": user}), 201

    @app.patch("/api/admin/users/<user_id>")
    def admin_update_user(user_id: str):
        try:
            user = auth_store.update_user(user_id, request.get_json(silent=True) or {})
        except KeyError:
            return jsonify({"error": "User not found."}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"user": user})

    @app.post("/api/admin/users/<user_id>/reset-state")
    def admin_reset_user_state(user_id: str):
        try:
            state = auth_store.reset_user_state(user_id)
        except KeyError:
            return jsonify({"error": "User not found."}), 404
        return jsonify({"state": state})

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
