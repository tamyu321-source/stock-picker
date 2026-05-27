from flask import Flask, Response, jsonify, request, stream_with_context

from backend.services import analyze, get_config, stream_analyze


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

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
