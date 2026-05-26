MARKETS = [
    {"id": "CN", "label": "China A-shares", "currency": "CNY"},
    {"id": "HK", "label": "Hong Kong", "currency": "HKD"},
    {"id": "SG", "label": "Singapore", "currency": "SGD"},
    {"id": "US", "label": "United States", "currency": "USD"},
    {"id": "TW", "label": "Taiwan", "currency": "TWD"},
]

STRATEGIES = [
    {
        "id": "balanced",
        "name": "Balanced AI Core",
        "description": "News-led strategy balancing market sentiment with trend, valuation, risk, and quality.",
        "weights": {"momentum": 20, "value": 15, "sentiment": 40, "risk": 10, "quality": 15},
        "riskTolerance": 55,
    },
    {
        "id": "growth",
        "name": "Growth Momentum",
        "description": "Favors accelerating revenue narratives, price momentum, and positive institutional coverage.",
        "weights": {"momentum": 30, "value": 8, "sentiment": 38, "risk": 8, "quality": 16},
        "riskTolerance": 68,
    },
    {
        "id": "defensive",
        "name": "Defensive Value",
        "description": "Favors lower drawdown, strong cash flow, cheaper valuation, and stable signal quality.",
        "weights": {"momentum": 10, "value": 24, "sentiment": 30, "risk": 22, "quality": 14},
        "riskTolerance": 38,
    },
]

DEFAULT_SYMBOLS = {
    "US": ["AAPL", "MSFT", "NVDA"],
    "CN": ["600519.SS", "300750.SZ"],
    "HK": ["0700.HK", "9988.HK"],
    "SG": ["D05.SI", "C38U.SI"],
    "TW": ["2330.TW", "2317.TW"],
}

RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US",
    "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
]
