from flask import Flask, jsonify, request

from backend.services import analyze, get_config


def create_app(market_provider=None, news_crawler=None, universe_provider=None) -> Flask:
    app = Flask(__name__)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "open-stock-picker"})

    @app.get("/api/config")
    def config():
        return jsonify(get_config())

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

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
