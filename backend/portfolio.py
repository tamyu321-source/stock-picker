from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any


OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class _HtmlTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._row is not None and self._cell_parts is not None:
            self._row.append("".join(self._cell_parts))
            self._cell_parts = None
        elif tag == "tr" and self._row is not None:
            if any(_clean_cell(cell) for cell in self._row):
                self.rows.append(self._row)
            self._row = None


def parse_portfolio_export(data: bytes, filename: str = "") -> dict[str, Any]:
    if not data:
        raise ValueError("The uploaded holdings file is empty.")

    rows, source_type = _rows_from_export(data)
    if not rows:
        raise ValueError("No table rows were found in the uploaded holdings file.")

    header_index, header_map = _find_header(rows)
    if header_index is None:
        raise ValueError("No supported holdings header row was found. Expected columns such as security code, name, quantity, cost price, market price, and P/L.")

    positions = []
    ignored_rows = 0
    for raw_row in rows[header_index + 1 :]:
        row = [_clean_cell(cell) for cell in raw_row]
        if not any(row):
            continue
        position = _position_from_row(row, header_map)
        if not position:
            ignored_rows += 1
            continue
        quantity = _number(position.get("quantity")) or 0
        if quantity <= 0:
            ignored_rows += 1
            continue
        positions.append(position)

    positions = _dedupe_positions(positions)
    positions.sort(key=lambda item: _number(item.get("marketValue")) or 0, reverse=True)
    totals = _portfolio_totals(positions)
    return {
        "sourceName": filename or "holdings export",
        "sourceType": source_type,
        "importedAt": datetime.now(timezone.utc).isoformat(),
        "positions": positions,
        "symbols": [position["symbol"] for position in positions],
        "recognizedCount": len(positions),
        "ignoredRows": ignored_rows,
        "totalMarketValue": totals["totalMarketValue"],
        "totalCostAmount": totals["totalCostAmount"],
        "totalUnrealizedPnl": totals["totalUnrealizedPnl"],
        "totalUnrealizedPnlPct": totals["totalUnrealizedPnlPct"],
        "warnings": _portfolio_warnings(positions, totals),
    }


def normalize_a_share_symbol(code: str, exchange: str = "") -> str | None:
    cleaned = _clean_cell(code).upper()
    if re.fullmatch(r"\d{6}\.(SS|SZ)", cleaned):
        return cleaned
    digits = "".join(re.findall(r"\d+", cleaned))
    if len(digits) != 6:
        return None
    exchange_text = unicodedata.normalize("NFKC", exchange or "")
    if "\u4e0a\u6d77" in exchange_text or digits.startswith(("600", "601", "603", "605", "688", "689", "900")):
        return f"{digits}.SS"
    if "\u6df1\u5733" in exchange_text or digits.startswith(("000", "001", "002", "003", "200", "300", "301")):
        return f"{digits}.SZ"
    return f"{digits}.SS" if digits.startswith("6") else f"{digits}.SZ"


def _rows_from_export(data: bytes) -> tuple[list[list[str]], str]:
    if data.startswith(OLE2_MAGIC):
        return _rows_from_binary_xls(data)

    text, encoding = _decode_text(data)
    if "<table" in text[:5000].lower() or "<tr" in text[:5000].lower():
        parser = _HtmlTableParser()
        parser.feed(text)
        return parser.rows, f"html-{encoding}"

    delimiter = _guess_delimiter(text)
    rows = [
        [_clean_cell(cell) for cell in row]
        for row in csv.reader(io.StringIO(text), delimiter=delimiter)
        if any(_clean_cell(cell) for cell in row)
    ]
    label = "tsv" if delimiter == "\t" else "csv" if delimiter == "," else "delimited"
    return rows, f"{label}-{encoding}"


def _rows_from_binary_xls(data: bytes) -> tuple[list[list[str]], str]:
    try:
        import xlrd  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on optional runtime package
        raise ValueError("Binary .xls files require xlrd. Dongwu text/HTML .xls exports are supported without extra packages.") from exc

    workbook = xlrd.open_workbook(file_contents=data)
    sheet = workbook.sheet_by_index(0)
    rows = []
    for row_index in range(sheet.nrows):
        rows.append([str(sheet.cell_value(row_index, col_index)) for col_index in range(sheet.ncols)])
    return rows, "binary-xls-xlrd"


def _decode_text(data: bytes) -> tuple[str, str]:
    encodings = ["utf-8-sig", "gb18030", "big5", "utf-16", "latin1"]
    scored: list[tuple[int, str, str]] = []
    for encoding in encodings:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        score = sum(text.count(token) for token in _HEADER_SCORE_TOKENS) - text.count("\ufffd") * 5
        if "\t" in text:
            score += 2
        scored.append((score, text, encoding))
    if not scored:
        raise ValueError("The uploaded holdings file could not be decoded as text.")
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1], scored[0][2]


def _guess_delimiter(text: str) -> str:
    sample = text[:4096]
    counts = {"\t": sample.count("\t"), ",": sample.count(","), ";": sample.count(";")}
    delimiter, count = max(counts.items(), key=lambda item: item[1])
    return delimiter if count > 0 else "\t"


def _find_header(rows: list[list[str]]) -> tuple[int | None, dict[str, int]]:
    for index, row in enumerate(rows[:20]):
        header_map = _header_map(row)
        if "code" in header_map and ("name" in header_map or "exchange" in header_map):
            return index, header_map
    return None, {}


def _header_map(row: list[str]) -> dict[str, int]:
    output: dict[str, int] = {}
    for index, cell in enumerate(row):
        label = _normalize_header(cell)
        field = HEADER_ALIASES.get(label)
        if field and field not in output:
            output[field] = index
    return output


def _position_from_row(row: list[str], header_map: dict[str, int]) -> dict[str, Any] | None:
    code = _cell(row, header_map, "code")
    name = _cell(row, header_map, "name")
    exchange = _cell(row, header_map, "exchange")
    symbol = normalize_a_share_symbol(code, exchange)
    if not symbol:
        return None

    quantity = _first_number(
        _cell(row, header_map, "quantity"),
        (_number(_cell(row, header_map, "availableQuantity")) or 0) + (_number(_cell(row, header_map, "frozenQuantity")) or 0),
    )
    cost_price = _number(_cell(row, header_map, "costPrice"))
    last_price = _number(_cell(row, header_map, "lastPrice"))
    market_value = _number(_cell(row, header_map, "marketValue"))
    cost_amount = _number(_cell(row, header_map, "costAmount"))
    pnl = _number(_cell(row, header_map, "unrealizedPnl"))
    pnl_pct = _number(_cell(row, header_map, "unrealizedPnlPct"))

    if market_value is None and quantity is not None and last_price is not None:
        market_value = quantity * last_price
    if cost_amount is None and quantity is not None and cost_price is not None:
        cost_amount = quantity * cost_price
    if pnl is None and market_value is not None and cost_amount is not None:
        pnl = market_value - cost_amount
    if pnl_pct is None and pnl is not None and cost_amount:
        pnl_pct = pnl / cost_amount * 100

    return {
        "symbol": symbol,
        "code": symbol.split(".")[0],
        "name": name or symbol,
        "market": "CN",
        "exchange": exchange,
        "quantity": quantity or 0,
        "availableQuantity": _number(_cell(row, header_map, "availableQuantity")),
        "frozenQuantity": _number(_cell(row, header_map, "frozenQuantity")),
        "costPrice": cost_price,
        "lastPrice": last_price,
        "marketValue": _round_or_none(market_value),
        "costAmount": _round_or_none(cost_amount),
        "unrealizedPnl": _round_or_none(pnl),
        "unrealizedPnlPct": _round_or_none(pnl_pct),
        "openDate": _parse_date(_cell(row, header_map, "openDate")),
    }


def _cell(row: list[str], header_map: dict[str, int], field: str) -> str:
    index = header_map.get(field)
    if index is None or index >= len(row):
        return ""
    return row[index]


def _clean_cell(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).replace("\ufeff", "").strip()
    if len(text) >= 3 and text.startswith('="') and text.endswith('"'):
        text = text[2:-1]
    elif len(text) >= 3 and text.startswith("='") and text.endswith("'"):
        text = text[2:-1]
    return text.strip()


def _normalize_header(value: str) -> str:
    return re.sub(r"[\s:_\-]+", "", _clean_cell(value)).lower()


def _number(value: Any) -> float | None:
    text = _clean_cell(value).replace(",", "").replace("%", "")
    if text in {"", "-", "--", "None", "nan"}:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _first_number(*values: Any) -> float | None:
    for value in values:
        number = _number(value)
        if number is not None:
            return number
    return None


def _round_or_none(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _parse_date(value: Any) -> str | None:
    text = _clean_cell(value)
    digits = "".join(re.findall(r"\d+", text))
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    if len(digits) == 6:
        return f"20{digits[:2]}-{digits[2:4]}-{digits[4:6]}"
    return text or None


def _dedupe_positions(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for position in positions:
        symbol = position["symbol"]
        if symbol not in merged:
            merged[symbol] = dict(position)
            continue
        existing = merged[symbol]
        for field in ["quantity", "availableQuantity", "frozenQuantity", "marketValue", "costAmount", "unrealizedPnl"]:
            existing[field] = (_number(existing.get(field)) or 0) + (_number(position.get(field)) or 0)
        existing["unrealizedPnlPct"] = _weighted_pnl_pct(existing)
    return list(merged.values())


def _weighted_pnl_pct(position: dict[str, Any]) -> float | None:
    pnl = _number(position.get("unrealizedPnl"))
    cost = _number(position.get("costAmount"))
    return round(pnl / cost * 100, 4) if pnl is not None and cost else None


def _portfolio_totals(positions: list[dict[str, Any]]) -> dict[str, float | None]:
    total_market_value = sum(_number(position.get("marketValue")) or 0 for position in positions)
    total_cost = sum(_number(position.get("costAmount")) or 0 for position in positions)
    total_pnl = sum(_number(position.get("unrealizedPnl")) or 0 for position in positions)
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else None
    return {
        "totalMarketValue": round(total_market_value, 4),
        "totalCostAmount": round(total_cost, 4),
        "totalUnrealizedPnl": round(total_pnl, 4),
        "totalUnrealizedPnlPct": _round_or_none(total_pnl_pct),
    }


def _portfolio_warnings(positions: list[dict[str, Any]], totals: dict[str, float | None]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    total_value = _number(totals.get("totalMarketValue")) or 0
    total_pnl_pct = _number(totals.get("totalUnrealizedPnlPct"))
    if not positions:
        return [{"key": "portfolioNoCurrentHolding", "severity": "warning", "params": {}}]
    if total_pnl_pct is not None and total_pnl_pct <= -10:
        warnings.append({"key": "portfolioTotalDrawdown", "severity": "danger", "params": {"pnlPct": round(total_pnl_pct, 1)}})
    for position in positions:
        weight = (_number(position.get("marketValue")) or 0) / total_value * 100 if total_value else 0
        pnl_pct = _number(position.get("unrealizedPnlPct"))
        if weight >= 35:
            warnings.append({"key": "portfolioConcentration", "severity": "danger", "params": {"symbol": position["symbol"], "weight": round(weight, 1)}})
        elif weight >= 20:
            warnings.append({"key": "portfolioConcentration", "severity": "warning", "params": {"symbol": position["symbol"], "weight": round(weight, 1)}})
        if pnl_pct is not None and pnl_pct <= -20:
            warnings.append({"key": "portfolioLargeLoss", "severity": "danger", "params": {"symbol": position["symbol"], "pnlPct": round(pnl_pct, 1)}})
    return warnings[:8]


_HEADER_SCORE_TOKENS = [
    "\u8bc1\u5238\u4ee3\u7801",
    "\u8bc1\u5238\u540d\u79f0",
    "\u5b9e\u9645\u6570\u91cf",
    "\u76c8\u4e8f",
    "\u4ea4\u6613\u5e02\u573a",
]


def _labels(*values: str) -> set[str]:
    return {_normalize_header(value) for value in values}


HEADER_ALIASES: dict[str, str] = {}
for _field, _labels_for_field in {
    "code": _labels("\u8bc1\u5238\u4ee3\u7801", "\u8b49\u5238\u4ee3\u78bc", "\u80a1\u7968\u4ee3\u7801", "\u4ee3\u7801"),
    "name": _labels("\u8bc1\u5238\u540d\u79f0", "\u8b49\u5238\u540d\u7a31", "\u80a1\u7968\u540d\u79f0", "\u540d\u79f0"),
    "availableQuantity": _labels("\u53ef\u7528\u4f59\u989d", "\u53ef\u7528\u9918\u984d", "\u53ef\u7528\u6570\u91cf"),
    "frozenQuantity": _labels("\u51bb\u7ed3\u6570\u91cf", "\u51cd\u7d50\u6578\u91cf"),
    "quantity": _labels("\u5b9e\u9645\u6570\u91cf", "\u5be6\u969b\u6578\u91cf", "\u6301\u4ed3\u6570\u91cf", "\u6301\u5009\u6578\u91cf", "\u80a1\u7968\u4f59\u989d"),
    "costPrice": _labels("\u6210\u672c\u4ef7", "\u6210\u672c\u50f9", "\u6301\u4ed3\u6210\u672c", "\u6301\u5009\u6210\u672c"),
    "lastPrice": _labels("\u5e02\u4ef7", "\u6700\u65b0\u4ef7", "\u73b0\u4ef7", "\u73fe\u50f9"),
    "marketValue": _labels("\u5e02\u503c", "\u8bc1\u5238\u5e02\u503c", "\u6301\u4ed3\u5e02\u503c"),
    "unrealizedPnl": _labels("\u76c8\u4e8f", "\u6d6e\u52a8\u76c8\u4e8f", "\u53c3\u8003\u76c8\u4e8f"),
    "unrealizedPnlPct": _labels("\u76c8\u4e8f\u6bd4\u4f8b(%)", "\u76c8\u4e8f\u6bd4\u4f8b", "\u76c8\u4e8f\u6bd4\u7387(%)", "\u76c8\u4e8f\u6bd4\u7387"),
    "exchange": _labels("\u4ea4\u6613\u5e02\u573a", "\u4ea4\u6613\u5e02\u5834", "\u5e02\u573a", "\u5e02\u5834"),
    "costAmount": _labels("\u6210\u672c\u91d1\u989d", "\u6210\u672c\u91d1\u984d"),
    "openDate": _labels("\u5f00\u4ed3\u65e5\u671f", "\u958b\u5009\u65e5\u671f", "\u4e70\u5165\u65e5\u671f", "\u8cb7\u5165\u65e5\u671f"),
}.items():
    for _label in _labels_for_field:
        HEADER_ALIASES[_label] = _field
