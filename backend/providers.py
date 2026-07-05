from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import json
import re
import ssl
import time
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
    instrument_type: str = "stock"


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


def _surge_ratio(values: list[float], window: int = 20) -> float | None:
    if len(values) < 3:
        return None
    latest = values[-1]
    previous = values[-window - 1 : -1] if len(values) > window else values[:-1]
    baseline = sum(value for value in previous if value > 0) / max(1, sum(1 for value in previous if value > 0))
    if latest <= 0 or baseline <= 0:
        return None
    return latest / baseline


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
    "増益",
    "上方修正",
    "最高益",
    "실적개선",
    "상향",
    "호실적",
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
    "減益",
    "下方修正",
    "急落",
    "실적부진",
    "하향",
    "급락",
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
    "上方修正",
    "最高益",
    "増益",
    "自社株買い",
    "실적 개선",
    "목표주가 상향",
    "자사주 매입",
    "호실적",
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
    "下方修正",
    "減益",
    "業績悪化",
    "急落",
    "실적 부진",
    "목표주가 하향",
    "급락",
    "매도 의견",
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
    "nikkei": 0.84,
    "kabutan": 0.74,
    "finance.yahoo.co.jp": 0.74,
    "mk.co.kr": 0.76,
    "businesskorea": 0.74,
    "koreaherald": 0.76,
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
    "6239.TW": "力成",
    "2891.TW": "中信金",
    "2886.TW": "兆豐金",
    "2344.TW": "華邦電",
    "3481.TW": "群創",
    "7203.T": "Toyota Motor",
    "6758.T": "Sony Group",
    "8306.T": "Mitsubishi UFJ Financial Group",
    "6861.T": "Keyence",
    "9984.T": "SoftBank Group",
    "6098.T": "Recruit Holdings",
    "9432.T": "Nippon Telegraph and Telephone",
    "8035.T": "Tokyo Electron",
    "9983.T": "Fast Retailing",
    "7974.T": "Nintendo",
    "005930.KS": "Samsung Electronics",
    "000660.KS": "SK hynix",
    "035420.KS": "NAVER",
    "051910.KS": "LG Chem",
    "005380.KS": "Hyundai Motor",
    "006400.KS": "Samsung SDI",
    "068270.KS": "Celltrion",
    "035720.KS": "Kakao",
    "207940.KS": "Samsung Biologics",
    "373220.KS": "LG Energy Solution",
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
    "6239.TW": ["力成", "Powertech Technology", "PTI"],
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
    "7203.T": ["Toyota", "Toyota Motor", "トヨタ自動車"],
    "6758.T": ["Sony", "Sony Group", "ソニーグループ"],
    "8306.T": ["Mitsubishi UFJ", "MUFG", "三菱UFJフィナンシャル・グループ"],
    "6861.T": ["Keyence", "キーエンス"],
    "9984.T": ["SoftBank Group", "ソフトバンクグループ"],
    "6098.T": ["Recruit Holdings", "リクルートホールディングス"],
    "9432.T": ["NTT", "Nippon Telegraph and Telephone", "日本電信電話"],
    "8035.T": ["Tokyo Electron", "東京エレクトロン"],
    "9983.T": ["Fast Retailing", "ファーストリテイリング"],
    "7974.T": ["Nintendo", "任天堂"],
    "005930.KS": ["Samsung Electronics", "삼성전자"],
    "000660.KS": ["SK hynix", "SK하이닉스"],
    "035420.KS": ["NAVER", "네이버"],
    "051910.KS": ["LG Chem", "LG화학"],
    "005380.KS": ["Hyundai Motor", "현대차"],
    "006400.KS": ["Samsung SDI", "삼성SDI"],
    "068270.KS": ["Celltrion", "셀트리온"],
    "035720.KS": ["Kakao", "카카오"],
    "207940.KS": ["Samsung Biologics", "삼성바이오로직스"],
    "373220.KS": ["LG Energy Solution", "LG에너지솔루션"],
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
    "6239.TW": "Semiconductors",
    "2891.TW": "Financial Services",
    "2886.TW": "Financial Services",
    "7203.T": "Automobiles",
    "6758.T": "Consumer Electronics",
    "8306.T": "Banking",
    "6861.T": "Factory Automation",
    "9984.T": "Telecommunications and Investments",
    "6098.T": "Human Capital Technology",
    "9432.T": "Telecommunications",
    "8035.T": "Semiconductor Equipment",
    "9983.T": "Retail",
    "7974.T": "Interactive Entertainment",
    "005930.KS": "Semiconductors",
    "000660.KS": "Semiconductors",
    "035420.KS": "Internet Platforms",
    "051910.KS": "Chemicals",
    "005380.KS": "Automobiles",
    "006400.KS": "Battery Manufacturing",
    "068270.KS": "Biopharmaceuticals",
    "035720.KS": "Internet Platforms",
    "207940.KS": "Biopharmaceuticals",
    "373220.KS": "Battery Manufacturing",
}

ETF_SYMBOLS_BY_MARKET = {
    "US": ["SPY", "VOO", "IVV", "QQQ", "VTI", "IWM", "SCHD", "XLK", "GLD", "TLT"],
    "CN": ["510300.SS", "510500.SS", "588000.SS", "159919.SZ", "159915.SZ", "512100.SS"],
    "HK": ["2800.HK", "2828.HK", "3033.HK", "3067.HK", "3088.HK"],
    "TW": ["0050.TW", "0056.TW", "00878.TW", "006208.TW", "00713.TW"],
    "JP": ["1306.T", "1321.T", "1348.T", "1545.T", "2558.T"],
    "KR": ["069500.KS", "102110.KS", "229200.KS", "305720.KS", "360750.KS"],
    "SG": ["ES3.SI", "G3B.SI", "CLR.SI", "A35.SI", "MBH.SI"],
}

ETF_NAMES = {
    "SPY": "SPDR S&P 500 ETF Trust",
    "VOO": "Vanguard S&P 500 ETF",
    "IVV": "iShares Core S&P 500 ETF",
    "QQQ": "Invesco QQQ Trust",
    "VTI": "Vanguard Total Stock Market ETF",
    "IWM": "iShares Russell 2000 ETF",
    "SCHD": "Schwab U.S. Dividend Equity ETF",
    "XLK": "Technology Select Sector SPDR Fund",
    "GLD": "SPDR Gold Shares",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    "510300.SS": "CSI 300 ETF",
    "510500.SS": "CSI 500 ETF",
    "588000.SS": "STAR 50 ETF",
    "159919.SZ": "CSI 300 ETF",
    "159915.SZ": "ChiNext ETF",
    "512100.SS": "CSI 1000 ETF",
    "2800.HK": "Tracker Fund of Hong Kong",
    "2828.HK": "Hang Seng China Enterprises ETF",
    "3033.HK": "CSOP Hang Seng TECH Index ETF",
    "3067.HK": "iShares Core Hang Seng Index ETF",
    "3088.HK": "Hang Seng TECH ETF",
    "0050.TW": "Yuanta Taiwan 50 ETF",
    "0056.TW": "Yuanta Taiwan High Dividend ETF",
    "00878.TW": "Cathay Taiwan ESG Sustainability High Dividend ETF",
    "006208.TW": "Fubon Taiwan 50 ETF",
    "00713.TW": "Yuanta Taiwan High Dividend Low Volatility ETF",
    "1306.T": "NEXT FUNDS TOPIX ETF",
    "1321.T": "NEXT FUNDS Nikkei 225 ETF",
    "1348.T": "MAXIS TOPIX ETF",
    "1545.T": "NEXT FUNDS NASDAQ-100 ETF",
    "2558.T": "MAXIS S&P 500 ETF",
    "069500.KS": "KODEX 200 ETF",
    "102110.KS": "TIGER 200 ETF",
    "229200.KS": "KODEX KOSDAQ150 ETF",
    "305720.KS": "KODEX Secondary Battery Industry ETF",
    "360750.KS": "TIGER US S&P 500 ETF",
    "ES3.SI": "SPDR Straits Times Index ETF",
    "G3B.SI": "Nikko AM Singapore STI ETF",
    "CLR.SI": "Lion-OCBC Securities Hang Seng TECH ETF",
    "A35.SI": "ABF Singapore Bond Index Fund",
    "MBH.SI": "Nikko AM SGD Investment Grade Corporate Bond ETF",
}

ETF_SEARCH_ALIASES = {
    "SPY": ["S&P 500 ETF", "SPDR S&P 500", "SPY ETF"],
    "VOO": ["Vanguard S&P 500", "VOO ETF"],
    "IVV": ["iShares Core S&P 500", "IVV ETF"],
    "QQQ": ["Nasdaq 100 ETF", "Invesco QQQ", "QQQ ETF"],
    "VTI": ["Total Stock Market ETF", "VTI ETF"],
    "IWM": ["Russell 2000 ETF", "IWM ETF"],
    "SCHD": ["Dividend ETF", "SCHD ETF"],
    "XLK": ["Technology ETF", "XLK ETF"],
    "GLD": ["Gold ETF", "GLD ETF"],
    "TLT": ["Treasury bond ETF", "TLT ETF"],
    "510300.SS": ["CSI 300 ETF", "沪深300 ETF", "510300"],
    "510500.SS": ["CSI 500 ETF", "中证500 ETF", "510500"],
    "588000.SS": ["STAR 50 ETF", "科创50 ETF", "588000"],
    "159919.SZ": ["CSI 300 ETF", "沪深300 ETF", "159919"],
    "159915.SZ": ["ChiNext ETF", "创业板 ETF", "159915"],
    "512100.SS": ["CSI 1000 ETF", "中证1000 ETF", "512100"],
    "2800.HK": ["Tracker Fund", "Hong Kong tracker fund", "盈富基金"],
    "2828.HK": ["Hang Seng China Enterprises ETF", "H-share ETF"],
    "3033.HK": ["Hang Seng TECH ETF", "恒生科技 ETF"],
    "3067.HK": ["Hang Seng Index ETF"],
    "3088.HK": ["Hang Seng TECH ETF"],
    "0050.TW": ["Taiwan 50 ETF", "元大台灣50", "0050"],
    "0056.TW": ["Taiwan high dividend ETF", "元大高股息", "0056"],
    "00878.TW": ["Taiwan ESG high dividend ETF", "國泰永續高股息", "00878"],
    "006208.TW": ["Fubon Taiwan 50", "富邦台50", "006208"],
    "00713.TW": ["Taiwan low volatility high dividend ETF", "元大台灣高息低波", "00713"],
    "1306.T": ["TOPIX ETF", "1306 ETF"],
    "1321.T": ["Nikkei 225 ETF", "1321 ETF"],
    "1348.T": ["TOPIX ETF", "1348 ETF"],
    "1545.T": ["NASDAQ 100 ETF Japan", "1545 ETF"],
    "2558.T": ["S&P 500 ETF Japan", "2558 ETF"],
    "069500.KS": ["KODEX 200", "KOSPI 200 ETF"],
    "102110.KS": ["TIGER 200", "KOSPI 200 ETF"],
    "229200.KS": ["KODEX KOSDAQ150", "KOSDAQ 150 ETF"],
    "305720.KS": ["Secondary battery ETF", "KODEX battery ETF"],
    "360750.KS": ["TIGER US S&P 500", "S&P 500 Korea ETF"],
    "ES3.SI": ["STI ETF", "SPDR Straits Times ETF"],
    "G3B.SI": ["Nikko AM STI ETF", "Singapore STI ETF"],
    "CLR.SI": ["Hang Seng TECH ETF Singapore"],
    "A35.SI": ["Singapore bond ETF", "ABF Singapore Bond Index Fund"],
    "MBH.SI": ["Singapore corporate bond ETF"],
}

KNOWN_ETF_SYMBOLS = {symbol for symbols in ETF_SYMBOLS_BY_MARKET.values() for symbol in symbols}
LOCAL_COMPANY_NAMES.update(ETF_NAMES)
COMPANY_SEARCH_ALIASES.update(ETF_SEARCH_ALIASES)
KNOWN_SECTORS.update({symbol: "ETF / Fund" for symbol in KNOWN_ETF_SYMBOLS})


def is_known_etf_symbol(symbol: str) -> bool:
    return symbol.upper() in KNOWN_ETF_SYMBOLS


def instrument_type(symbol: str, info: dict[str, Any] | None = None) -> str:
    info = info or {}
    quote_type = str(info.get("quoteType") or info.get("instrumentType") or "").strip().upper()
    if quote_type in {"ETF", "MUTUALFUND", "FUND"}:
        return "etf"
    if is_known_etf_symbol(symbol):
        return "etf"
    text = " ".join(
        str(info.get(key) or "")
        for key in ["shortName", "longName", "category", "fundFamily", "sector", "industry"]
    ).lower()
    if "etf" in text or "exchange traded fund" in text or "index fund" in text:
        return "etf"
    return "stock"


def infer_market(symbol: str) -> str:
    upper = symbol.upper()
    if upper.endswith((".SS", ".SZ")):
        return "CN"
    if upper.endswith(".HK"):
        return "HK"
    if upper.endswith(".T"):
        return "JP"
    if upper.endswith((".KS", ".KQ")):
        return "KR"
    if upper.endswith(".SI"):
        return "SG"
    if upper.endswith(".TW"):
        return "TW"
    return "US"


def fallback_sector(symbol: str) -> str:
    upper = symbol.upper()
    if is_known_etf_symbol(upper):
        return "ETF / Fund"
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
            return fallback_market_data_provider(symbol)

        try:
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
            if "Volume" in history:
                volumes = [float(value) for value in history["Volume"].dropna().tail(130).tolist()]
                volume_surge = _surge_ratio(volumes)
                if volume_surge is not None:
                    info["volumeSurge20"] = round(volume_surge, 2)
            info = _merge_market_fundamentals(symbol, info)
            kind = instrument_type(symbol, info)
            info["instrumentType"] = kind

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
                instrument_type=kind,
            )
        except Exception:
            return fallback_market_data_provider(symbol)


def fallback_market_data_provider(symbol: str) -> MarketSnapshot:
    if infer_market(symbol) == "CN":
        try:
            return EastmoneyCnMarketDataProvider().fetch(symbol)
        except Exception:
            pass
    try:
        return YahooHttpMarketDataProvider().fetch(symbol)
    except Exception:
        if infer_market(symbol) == "TW":
            return TaiwanExchangeMarketDataProvider().fetch(symbol)
        raise


class EastmoneyCnMarketDataProvider:
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36"

    def fetch(self, symbol: str) -> MarketSnapshot:
        if infer_market(symbol) != "CN":
            raise ValueError(f"Eastmoney fallback only supports China A-shares, got {symbol}.")

        upper = symbol.upper()
        code = upper.split(".")[0]
        secid_prefix = "1" if upper.endswith(".SS") else "0"
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get?"
            f"secid={secid_prefix}.{quote(code)}&klt=101&fqt=1&beg=0&end=20500101"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        )
        payload = self._json(url)
        data = payload.get("data") or {}
        klines = data.get("klines") or []
        rows = [self._parse_kline(row) for row in klines[-130:]]
        closes = [row["close"] for row in rows if row["close"] > 0]
        if not closes:
            raise ValueError(f"No Eastmoney closing prices returned for {symbol}.")

        info = _eastmoney_cn_fundamentals(symbol)
        volumes = [float(row["volume"] or 0) for row in rows]
        amounts = [float(row["amount"] or 0) for row in rows]
        volume_surge = _surge_ratio(volumes)
        amount_surge = _surge_ratio(amounts)
        latest = rows[-1]
        if volume_surge is not None:
            info["volumeSurge20"] = round(volume_surge, 2)
        if amount_surge is not None:
            info["amountSurge20"] = round(amount_surge, 2)
        if latest.get("turnoverRate") is not None:
            info["latestTurnoverRate"] = latest["turnoverRate"] / 100
        if latest.get("amount") and not info.get("turnoverValue"):
            info["turnoverValue"] = latest["amount"]
        if latest.get("volume") and not info.get("regularMarketVolume"):
            info["regularMarketVolume"] = latest["volume"] * 100
        kind = instrument_type(upper, info)
        info["instrumentType"] = kind
        price = closes[-1]
        previous = closes[-2] if len(closes) > 1 else price
        change = latest.get("changePercent")
        if change is None:
            change = ((price - previous) / previous * 100) if previous else 0
        name = info.get("shortName") or local_company_name(upper, data.get("name") or upper)

        return MarketSnapshot(
            symbol=upper,
            name=name,
            market="CN",
            sector=fallback_sector(upper),
            price=round(price, 3),
            change=round(change, 2),
            currency="CNY",
            closes=closes,
            info=info,
            instrument_type=kind,
        )

    def _json(self, url: str) -> dict | list:
        last_error = None
        for attempt in range(3):
            try:
                request = Request(
                    url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "application/json,text/plain,*/*",
                        "Referer": "https://quote.eastmoney.com/",
                    },
                )
                with urlopen(request, timeout=10) as response:
                    return json.loads(response.read().decode("utf-8-sig"))
            except Exception as exc:
                last_error = exc
                time.sleep(0.25 * (attempt + 1))
        raise last_error

    def _parse_kline(self, row: str) -> dict[str, float | None]:
        parts = str(row).split(",")
        close = _eastmoney_number(parts[2] if len(parts) > 2 else None) or 0.0
        volume = _eastmoney_number(parts[5] if len(parts) > 5 else None) or 0.0
        amount = _eastmoney_number(parts[6] if len(parts) > 6 else None) or 0.0
        change_percent = _eastmoney_number(parts[8] if len(parts) > 8 else None)
        turnover_rate = _eastmoney_number(parts[10] if len(parts) > 10 else None)
        return {"close": close, "volume": volume, "amount": amount, "changePercent": change_percent, "turnoverRate": turnover_rate}


class YahooHttpMarketDataProvider:
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36"
    hosts = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")

    def fetch(self, symbol: str) -> MarketSnapshot:
        chart = self._json(self._chart_urls(symbol))
        result = chart.get("chart", {}).get("result", [])
        if not result:
            error = chart.get("chart", {}).get("error") or {}
            raise ValueError(error.get("description") or f"No market data returned for {symbol}.")

        payload = result[0]
        meta = payload.get("meta", {})
        quote = payload.get("indicators", {}).get("quote", [{}])[0]
        close_values = quote.get("close", [])
        closes = [float(value) for value in close_values if value is not None]
        if not closes:
            raise ValueError(f"No closing prices returned for {symbol}.")

        info = self._quote_summary(symbol)
        fundamentals = _merge_market_fundamentals(symbol, self._fundamentals(info, meta))
        volumes = [float(value) for value in quote.get("volume", []) if value is not None]
        volume_surge = _surge_ratio(volumes)
        if volume_surge is not None:
            fundamentals["volumeSurge20"] = round(volume_surge, 2)
        kind = instrument_type(symbol, fundamentals)
        fundamentals["instrumentType"] = kind
        price = float(meta.get("regularMarketPrice") or closes[-1])
        previous = closes[-2] if len(closes) > 1 else price
        change = ((price - previous) / previous * 100) if previous else 0
        price_info = info.get("price", {})
        profile = info.get("summaryProfile", {})
        name = (
            _raw(price_info.get("shortName"))
            or _raw(price_info.get("longName"))
            or meta.get("shortName")
            or meta.get("longName")
            or symbol.upper()
        )

        return MarketSnapshot(
            symbol=symbol.upper(),
            name=name,
            market=infer_market(symbol),
            sector=_raw(profile.get("sector")) or _raw(profile.get("industry")) or fallback_sector(symbol),
            price=round(price, 3),
            change=round(change, 2),
            currency=meta.get("currency") or _raw(price_info.get("currency")) or "",
            closes=closes[-130:],
            info=fundamentals,
            instrument_type=kind,
        )

    def _chart_urls(self, symbol: str) -> list[str]:
        return [
            f"https://{host}/v8/finance/chart/{quote(symbol)}?range=6mo&interval=1d&events=history&includeAdjustedClose=true"
            for host in self.hosts
        ]

    def _quote_summary_urls(self, symbol: str, modules: str) -> list[str]:
        return [
            f"https://{host}/v10/finance/quoteSummary/{quote(symbol)}?modules={modules}"
            for host in self.hosts
        ]

    def _json(self, urls: str | list[str], attempts: int = 3, timeout: int = 6) -> dict:
        if isinstance(urls, str):
            urls = [urls]
        last_error: Exception | None = None
        for attempt in range(attempts):
            for url in urls:
                try:
                    request = Request(
                        url,
                        headers={
                            "User-Agent": self.user_agent,
                            "Accept": "application/json,text/plain,*/*",
                            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                            "Cache-Control": "no-cache",
                            "Connection": "close",
                        },
                    )
                    with urlopen(request, timeout=timeout) as response:
                        return json.loads(response.read().decode("utf-8-sig"))
                except Exception as exc:
                    last_error = exc
            time.sleep(0.25 * (attempt + 1))
        raise last_error or ValueError("Yahoo Finance request failed.")

    def _quote_summary(self, symbol: str) -> dict:
        modules = "price,summaryProfile,defaultKeyStatistics,financialData,summaryDetail,calendarEvents,earningsTrend,fundProfile,topHoldings,fundPerformance"
        try:
            payload = self._json(self._quote_summary_urls(symbol, modules), attempts=1, timeout=3)
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
        fund_profile = info.get("fundProfile", {})
        top_holdings = info.get("topHoldings", {})
        fund_performance = info.get("fundPerformance", {})
        return {
            "quoteType": _raw(price_info.get("quoteType")) or meta.get("instrumentType"),
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
            "totalAssets": _raw(stats.get("totalAssets")) or _raw(fund_profile.get("totalAssets")) or _raw(top_holdings.get("totalAssets")),
            "annualReportExpenseRatio": _raw(fund_profile.get("annualReportExpenseRatio")) or _raw(fund_profile.get("expenses")),
            "category": _raw(fund_profile.get("categoryName")) or _raw(fund_profile.get("category")),
            "fundFamily": _raw(fund_profile.get("family")),
            "ytdReturn": _raw(fund_performance.get("trailingReturns", {}).get("ytd")) if isinstance(fund_performance.get("trailingReturns"), dict) else None,
            "dividendYield": _raw(detail.get("dividendYield")),
            "yield": _raw(detail.get("yield")),
            "navPrice": _raw(detail.get("navPrice")) or meta.get("regularMarketPrice"),
            "fiftyTwoWeekHigh": _raw(detail.get("fiftyTwoWeekHigh")) or meta.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": _raw(detail.get("fiftyTwoWeekLow")) or meta.get("fiftyTwoWeekLow"),
            "regularMarketVolume": meta.get("regularMarketVolume"),
            "earningsDate": _raw(info.get("calendarEvents", {}).get("earnings", {}).get("earningsDate")),
        }


class TaiwanExchangeMarketDataProvider:
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36"

    def fetch(self, symbol: str) -> MarketSnapshot:
        if infer_market(symbol) != "TW":
            raise ValueError(f"Taiwan exchange fallback only supports Taiwan stocks, got {symbol}.")

        code = symbol.upper().split(".")[0]
        daily_row = self._daily_all_row(code)
        rows = [daily_row] if daily_row else self._history_rows(code)
        closes = [_market_number(row[6]) for row in rows if len(row) > 6 and _market_number(row[6]) > 0]
        if not closes:
            raise ValueError(f"No Taiwan exchange closing prices returned for {symbol}.")

        latest = rows[-1]
        price = closes[-1]
        previous = closes[-2] if len(closes) > 1 else price
        change = ((price - previous) / previous * 100) if previous else 0
        latest_change = _market_number(latest[7]) if len(latest) > 7 else None
        if latest_change is not None and previous:
            change = latest_change / previous * 100
        name = local_company_name(symbol.upper(), symbol.upper())
        volume = _market_number(latest[1]) if len(latest) > 1 else None
        turnover = _market_number(latest[2]) if len(latest) > 2 else None
        kind = instrument_type(symbol.upper(), {"shortName": name})

        return MarketSnapshot(
            symbol=symbol.upper(),
            name=name,
            market="TW",
            sector=fallback_sector(symbol),
            price=round(price, 3),
            change=round(change, 2),
            currency="TWD",
            closes=closes[-130:],
            info={
                "shortName": name,
                "fiftyTwoWeekHigh": max(closes),
                "fiftyTwoWeekLow": min(closes),
                "regularMarketVolume": volume,
                "turnoverValue": turnover,
                "instrumentType": kind,
            },
            instrument_type=kind,
        )

    def _history_rows(self, code: str) -> list[list[str]]:
        rows: list[list[str]] = []
        for month in _recent_month_starts(1):
            try:
                payload = self._json(
                    f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date={month:%Y%m%d}&stockNo={quote(code)}&response=json",
                    attempts=1,
                    timeout=3,
                )
                if payload.get("stat") == "OK":
                    rows.extend(payload.get("data") or [])
            except Exception:
                continue
        return rows

    def _daily_all_row(self, code: str) -> list[str]:
        rows = self._json("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", attempts=2, timeout=4)
        if not isinstance(rows, list):
            return []
        for row in rows:
            if str(row.get("Code") or "").strip() == code:
                return [
                    str(row.get("Date") or ""),
                    str(row.get("TradeVolume") or ""),
                    str(row.get("TradeValue") or ""),
                    str(row.get("OpeningPrice") or ""),
                    str(row.get("HighestPrice") or ""),
                    str(row.get("LowestPrice") or ""),
                    str(row.get("ClosingPrice") or ""),
                    str(row.get("Change") or ""),
                    str(row.get("Transaction") or ""),
                    "",
                ]
        return []

    def _json(self, url: str, attempts: int = 2, timeout: int = 4) -> dict | list:
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                request = Request(
                    url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "application/json,text/plain,*/*",
                        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                        "Connection": "close",
                    },
                )
                with urlopen(request, timeout=timeout, context=ssl._create_unverified_context()) as response:
                    return json.loads(response.read().decode("utf-8-sig"))
            except Exception as exc:
                last_error = exc
                time.sleep(0.25 * (attempt + 1))
        raise last_error or ValueError("Taiwan exchange request failed.")


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
    data = {}
    headers = {
        "User-Agent": EastmoneyCnMarketDataProvider.user_agent,
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://quote.eastmoney.com/",
    }
    for attempt in range(6):
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8-sig")).get("data") or {}
            if data:
                break
        except Exception:
            time.sleep(0.25 * (attempt + 1))
    if not data:
        return _cn_fund_flow(symbol)

    pe = _eastmoney_scaled(data.get("f162"))
    pb = _eastmoney_scaled(data.get("f167"))
    turnover = _eastmoney_scaled(data.get("f168"))
    change = _eastmoney_scaled(data.get("f170"))
    volume = _eastmoney_number(data.get("f47"))
    fundamentals = {
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
    fundamentals.update(_cn_fund_flow(symbol))
    return fundamentals


def _cn_fund_flow(symbol: str) -> dict[str, Any]:
    for provider in [_sina_cn_fund_flow, _eastmoney_cn_fund_flow]:
        try:
            flow = provider(symbol)
        except Exception:
            flow = {}
        if any(key != "fundFlowSource" for key in flow):
            return flow
    return {}


def _sina_cn_symbol(symbol: str) -> str:
    upper = symbol.upper()
    code = upper.split(".")[0]
    prefix = "sh" if upper.endswith(".SS") else "sz"
    return f"{prefix}{code}"


def _sina_ratio_percent(value: Any) -> float | None:
    number = _eastmoney_number(value)
    if number is None:
        return None
    return number * 100 if abs(number) <= 1 else number


def _sina_cn_fund_flow(symbol: str) -> dict[str, Any]:
    market = infer_market(symbol)
    if market != "CN":
        return {}

    sina_symbol = _sina_cn_symbol(symbol)
    url = (
        "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        f"MoneyFlow.ssl_qsfx_lscjfb?page=1&num=1&sort=opendate&asc=0&daima={quote(sina_symbol)}"
    )
    request = Request(
        url,
        headers={
            "User-Agent": EastmoneyCnMarketDataProvider.user_agent,
            "Accept": "application/json,text/plain,*/*",
            "Referer": f"https://vip.stock.finance.sina.com.cn/moneyflow/#!ssfx!{quote(sina_symbol)}",
        },
    )
    row = {}
    for attempt in range(2):
        try:
            with urlopen(request, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8-sig"))
            if isinstance(payload, list) and payload:
                row = payload[0] or {}
                break
        except Exception:
            time.sleep(0.2 * (attempt + 1))
    if not row:
        return {}

    has_main_ratio = row.get("r0_ratio") not in (None, "", "-")
    fund_flow = {
        "fundFlowSource": "Sina",
        "fundFlowMainNet": _eastmoney_number(row.get("r0_net") if has_main_ratio else row.get("netamount")),
        "fundFlowMainRatio": _sina_ratio_percent(row.get("r0_ratio") or row.get("ratioamount")),
        "fundFlowSuperLargeNet": _eastmoney_number(row.get("r0_net")),
        "fundFlowLargeNet": _eastmoney_number(row.get("r1_net")),
        "fundFlowMediumNet": _eastmoney_number(row.get("r2_net")),
        "fundFlowSmallNet": _eastmoney_number(row.get("r3_net")),
    }
    parsed = {key: value for key, value in fund_flow.items() if value is not None}
    if not any(key != "fundFlowSource" for key in parsed):
        return {}
    return parsed


def _eastmoney_cn_fund_flow(symbol: str) -> dict[str, Any]:
    market = infer_market(symbol)
    if market != "CN":
        return {}

    upper = symbol.upper()
    code = upper.split(".")[0]
    secid_prefix = "1" if upper.endswith(".SS") else "0"
    fields = "f62,f184,f66,f69,f72,f75,f78,f81,f84,f87"
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get?"
        f"fltt=2&secids={secid_prefix}.{quote(code)}&fields={fields}"
    )
    headers = {
        "User-Agent": EastmoneyCnMarketDataProvider.user_agent,
        "Accept": "application/json,text/plain,*/*",
        "Referer": f"https://data.eastmoney.com/zjlx/{quote(code)}.html",
    }
    row = {}
    for attempt in range(3):
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8-sig"))
            rows = (payload.get("data") or {}).get("diff") or []
            if rows:
                row = rows[0] or {}
                break
        except Exception:
            time.sleep(0.2 * (attempt + 1))
    if not row:
        return {}

    def number(field: str) -> float | None:
        return _eastmoney_number(row.get(field))

    fund_flow = {
        "fundFlowSource": "Eastmoney",
        "fundFlowMainNet": number("f62"),
        "fundFlowMainRatio": number("f184"),
        "fundFlowSuperLargeNet": number("f66"),
        "fundFlowSuperLargeRatio": number("f69"),
        "fundFlowLargeNet": number("f72"),
        "fundFlowLargeRatio": number("f75"),
        "fundFlowMediumNet": number("f78"),
        "fundFlowMediumRatio": number("f81"),
        "fundFlowSmallNet": number("f84"),
        "fundFlowSmallRatio": number("f87"),
    }
    parsed = {key: value for key, value in fund_flow.items() if value is not None}
    if not any(key != "fundFlowSource" for key in parsed):
        return {}
    return parsed


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


def _market_number(value: Any) -> float:
    try:
        if value in (None, "", "-", "--"):
            return 0.0
        return float(str(value).replace(",", "").replace("+", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _recent_month_starts(count: int) -> list[datetime]:
    now = datetime.now()
    months = []
    for offset in range(count):
        month = now.month - offset
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        months.append(datetime(year, month, 1))
    return months


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
        "JP": ["site:nikkei.com", "site:finance.yahoo.co.jp", "site:kabutan.jp", "site:reuters.com/markets/asia"],
        "KR": ["site:mk.co.kr", "site:businesskorea.co.kr", "site:koreaherald.com", "site:reuters.com/markets/asia"],
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
    elif market == "JP":
        queries.extend([f'"{name}" 日本株 決算 業績', f'"{name}" 株価 目標株価'])
    elif market == "KR":
        queries.extend([f'"{name}" 한국 주식 실적 주가', f'"{name}" 목표주가 매수'])
    elif market == "SG":
        queries.extend([f'"{name}" Singapore stock earnings', f'"{name}" SGX results dividend'])
    return list(dict.fromkeys(queries))


def news_query(symbol: str, name: str) -> str:
    tokens = company_name_tokens(symbol, name)
    phrase = company_phrase(symbol, name)
    if phrase or tokens:
        company = phrase or " ".join(tokens[:4])
        market = infer_market(symbol)
        if market in {"CN", "HK", "TW"}:
            return f'"{company}" 股票 財報 業績 OR "{symbol}"'
        if market == "JP":
            return f'"{company}" 株式 決算 業績 OR "{symbol}"'
        if market == "KR":
            return f'"{company}" 주식 실적 주가 OR "{symbol}"'
        return f'"{company}" OR "{symbol}" stock earnings revenue'
    return f'"{symbol}" stock earnings revenue'


def google_news_url(symbol: str, query_text: str) -> str:
    locale = {
        "CN": ("zh-CN", "CN", "CN:zh-Hans"),
        "HK": ("zh-HK", "HK", "HK:zh-Hant"),
        "JP": ("ja-JP", "JP", "JP:ja"),
        "KR": ("ko-KR", "KR", "KR:ko"),
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
