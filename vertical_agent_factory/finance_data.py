"""Financial market data adapters and deterministic analysis helpers."""

import json
import math
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import RuntimeExecutionError


DISCLAIMER = "仅供研究和信息参考，不构成投资建议、收益承诺或交易指令。"


class FinanceDataError(RuntimeExecutionError):
    """A configured financial data provider failed or rejected a request."""


class FinanceHttpTransport(object):
    def __init__(self, timeout_seconds=8, maximum_response_bytes=5 * 1024 * 1024):
        self.timeout_seconds = timeout_seconds
        self.maximum_response_bytes = maximum_response_bytes

    def get_json(self, url, params):
        request = Request(
            "{}?{}".format(url, urlencode(params)),
            headers={"Accept": "application/json", "User-Agent": "vertical-agent-factory/0.3"},
            method="GET",
        )
        return self._read(request)

    def post_json(self, url, payload):
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        return self._read(request)

    def _read(self, request):
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(self.maximum_response_bytes + 1)
        except Exception as exc:
            raise FinanceDataError("Financial data provider connection failed: {}".format(exc))
        if len(raw) > self.maximum_response_bytes:
            raise FinanceDataError("Financial data response exceeded size limit")
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise FinanceDataError("Financial data provider returned invalid JSON")


FIXTURE_EQUITIES = {
    "600000.SH": [10.12, 10.18, 10.08, 10.25, 10.31, 10.28, 10.44, 10.51, 10.47, 10.62,
                  10.58, 10.71, 10.66, 10.79, 10.91, 10.86, 10.98, 11.04, 10.96, 11.12,
                  11.18, 11.11, 11.24, 11.31, 11.28, 11.43, 11.39, 11.52, 11.48, 11.61],
    "000001.SZ": [11.20, 11.14, 11.31, 11.28, 11.42, 11.38, 11.51, 11.47, 11.62, 11.70,
                  11.65, 11.77, 11.72, 11.88, 11.93, 11.85, 12.01, 12.08, 12.02, 12.16,
                  12.10, 12.25, 12.31, 12.27, 12.41, 12.36, 12.52, 12.47, 12.60, 12.68],
    "AAPL": [205.1, 207.4, 206.8, 209.2, 211.0, 210.3, 212.9, 214.1, 213.7, 216.5,
             215.2, 218.0, 219.1, 217.8, 220.4, 221.3, 219.9, 222.6, 224.0, 223.2,
             225.8, 227.1, 226.4, 228.9, 230.2, 229.3, 231.7, 232.4, 231.8, 234.1],
    "MSFT": [488.0, 491.3, 489.8, 494.1, 496.2, 493.9, 498.5, 500.1, 497.8, 502.6,
              504.0, 501.7, 506.2, 508.4, 505.9, 510.3, 512.1, 509.8, 514.5, 516.0,
              513.7, 518.2, 520.4, 517.9, 522.3, 524.1, 521.8, 526.0, 528.2, 530.1],
    "NVDA": [176.0, 178.4, 175.9, 181.2, 183.1, 180.5, 185.4, 187.0, 184.2, 189.6,
              191.1, 187.8, 193.5, 195.2, 191.9, 197.1, 199.4, 196.0, 201.5, 203.8,
              200.1, 205.6, 208.0, 204.3, 210.2, 212.5, 208.8, 214.1, 216.7, 218.3],
}


def _fixture_points(symbol):
    closes = FIXTURE_EQUITIES.get(symbol)
    if closes is None:
        return []
    start = datetime(2026, 7, 6)
    return [
        {
            "date": (start + timedelta(days=index)).strftime("%Y-%m-%d"),
            "open": round(close * 0.997, 4),
            "high": round(close * 1.012, 4),
            "low": round(close * 0.988, 4),
            "close": close,
            "volume": 1000000 + index * 23000,
        }
        for index, close in enumerate(closes)
    ]


class FinanceDataGateway(object):
    def __init__(self, mode=None, transport=None):
        self.mode = (mode or os.environ.get("VAF_FINANCE_DATA_MODE", "fixture")).lower()
        if self.mode not in ("fixture", "live"):
            raise FinanceDataError("VAF_FINANCE_DATA_MODE must be fixture or live")
        self.transport = transport or FinanceHttpTransport()

    def macro(self, payload):
        if payload.get("simulate_failure"):
            raise FinanceDataError("Simulated macro data provider failure")
        region = str(payload.get("region") or "global").lower()
        if region not in ("global", "china", "us"):
            return self._empty("macro", region)
        if self.mode == "fixture":
            return self._fixture_macro(region)
        series = []
        sources = []
        if region in ("global", "us"):
            fred_key = os.environ.get("FRED_API_KEY", "")
            if not fred_key:
                raise FinanceDataError("FRED_API_KEY is required for live US macro data")
            fred_series = {
                "GDPC1": "美国实际 GDP",
                "CPIAUCSL": "美国 CPI",
                "UNRATE": "美国失业率",
                "FEDFUNDS": "联邦基金有效利率",
            }
            for series_id, label in fred_series.items():
                data = self.transport.get_json(
                    "https://api.stlouisfed.org/fred/series/observations",
                    {
                        "series_id": series_id,
                        "api_key": fred_key,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": 2,
                    },
                )
                observations = [item for item in data.get("observations", []) if item.get("value") not in (None, ".")]
                if observations:
                    series.append(self._macro_series(label, series_id, observations))
            sources.append({"name": "FRED", "url": "https://fred.stlouisfed.org/docs/api/fred/series_observations.html"})
        if region in ("global", "china"):
            token = os.environ.get("TUSHARE_TOKEN", "")
            if not token:
                raise FinanceDataError("TUSHARE_TOKEN is required for live China macro data")
            result = self._tushare("cn_gdp", {}, "quarter,gdp,gdp_yoy", token)
            if result:
                latest = result[0]
                previous = result[1] if len(result) > 1 else {}
                series.append({"name": "中国 GDP 同比", "series_id": "cn_gdp", "latest_date": str(latest.get("quarter", "")), "latest": self._float(latest.get("gdp_yoy")), "previous": self._float(previous.get("gdp_yoy"))})
            sources.append({"name": "Tushare Pro", "url": "https://tushare.pro/document/2?doc_id=227"})
        return {"kind": "macro", "region": region, "series": series, "as_of": self._latest_macro_date(series), "sources": sources}

    def a_share(self, payload):
        symbol = normalize_a_share_symbol(payload.get("symbol"))
        if payload.get("simulate_failure"):
            raise FinanceDataError("Simulated A-share data provider failure")
        if not symbol:
            return self._empty("a_share", "")
        if self.mode == "fixture":
            return self._equity_fixture("a_share", symbol, "Tushare fixture")
        token = os.environ.get("TUSHARE_TOKEN", "")
        if not token:
            raise FinanceDataError("TUSHARE_TOKEN is required for live A-share data")
        end = datetime.utcnow().strftime("%Y%m%d")
        start = (datetime.utcnow() - timedelta(days=int(payload.get("lookback_days") or 120))).strftime("%Y%m%d")
        rows = self._tushare(
            "daily",
            {"ts_code": symbol, "start_date": start, "end_date": end},
            "ts_code,trade_date,open,high,low,close,vol,amount",
            token,
        )
        points = [
            {
                "date": self._date_string(row.get("trade_date")),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("vol"),
            }
            for row in rows
        ]
        points.sort(key=lambda item: item["date"])
        return {"kind": "a_share", "symbol": symbol, "points": points, "as_of": points[-1]["date"] if points else "", "sources": [{"name": "Tushare Pro", "url": "https://tushare.pro/document/2?doc_id=27"}]}

    def us_stock(self, payload):
        symbol = normalize_us_symbol(payload.get("symbol"))
        if payload.get("simulate_failure"):
            raise FinanceDataError("Simulated US stock data provider failure")
        if not symbol:
            return self._empty("us_stock", "")
        if self.mode == "fixture":
            return self._equity_fixture("us_stock", symbol, "Alpha Vantage fixture")
        api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        if not api_key:
            raise FinanceDataError("ALPHAVANTAGE_API_KEY is required for live US stock data")
        data = self.transport.get_json(
            "https://www.alphavantage.co/query",
            {"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact", "apikey": api_key},
        )
        if data.get("Error Message") or data.get("Note") or data.get("Information"):
            raise FinanceDataError("Alpha Vantage rejected or rate-limited the request")
        points = []
        for date, row in (data.get("Time Series (Daily)") or {}).items():
            points.append({"date": date, "open": self._float(row.get("1. open")), "high": self._float(row.get("2. high")), "low": self._float(row.get("3. low")), "close": self._float(row.get("4. close")), "volume": self._float(row.get("5. volume"))})
        points.sort(key=lambda item: item["date"])
        return {"kind": "us_stock", "symbol": symbol, "points": points, "as_of": points[-1]["date"] if points else "", "sources": [{"name": "Alpha Vantage", "url": "https://www.alphavantage.co/documentation/#daily"}]}

    def _tushare(self, api_name, params, fields, token):
        data = self.transport.post_json(
            "https://api.tushare.pro",
            {"api_name": api_name, "token": token, "params": params, "fields": fields},
        )
        if int(data.get("code", -1)) != 0:
            raise FinanceDataError("Tushare rejected the request: {}".format(data.get("msg") or "unknown error"))
        table = data.get("data") or {}
        names = table.get("fields") or []
        return [dict(zip(names, item)) for item in table.get("items") or []]

    @staticmethod
    def _macro_series(label, series_id, observations):
        latest = observations[0]
        previous = observations[1] if len(observations) > 1 else {}
        return {"name": label, "series_id": series_id, "latest_date": latest.get("date", ""), "latest": FinanceDataGateway._float(latest.get("value")), "previous": FinanceDataGateway._float(previous.get("value"))}

    @staticmethod
    def _latest_macro_date(series):
        dates = [str(item.get("latest_date") or "") for item in series]
        return max(dates) if dates else ""

    @staticmethod
    def _fixture_macro(region):
        all_series = [
            {"name": "中国 GDP 同比", "series_id": "cn_gdp", "latest_date": "2026Q2", "latest": 5.1, "previous": 5.0},
            {"name": "中国 CPI 同比", "series_id": "cn_cpi", "latest_date": "2026-07", "latest": 0.8, "previous": 0.6},
            {"name": "美国实际 GDP 年化环比", "series_id": "GDPC1", "latest_date": "2026Q2", "latest": 2.4, "previous": 1.9},
            {"name": "美国失业率", "series_id": "UNRATE", "latest_date": "2026-07", "latest": 4.2, "previous": 4.1},
            {"name": "联邦基金有效利率", "series_id": "FEDFUNDS", "latest_date": "2026-07", "latest": 4.33, "previous": 4.33},
        ]
        if region == "china":
            all_series = all_series[:2]
        elif region == "us":
            all_series = all_series[2:]
        return {"kind": "macro", "region": region, "series": all_series, "as_of": "2026-08-14", "sources": [{"name": "Local audited macro fixture", "url": "domains/finance/knowledge.yaml"}]}

    @staticmethod
    def _equity_fixture(kind, symbol, source):
        points = _fixture_points(symbol)
        return {"kind": kind, "symbol": symbol, "points": points, "as_of": points[-1]["date"] if points else "", "sources": [{"name": source, "url": "domains/finance/knowledge.yaml"}]}

    @staticmethod
    def _empty(kind, identifier):
        return {"kind": kind, "symbol": identifier, "series": [], "points": [], "as_of": "", "sources": []}

    @staticmethod
    def _date_string(value):
        value = str(value or "")
        if len(value) == 8 and value.isdigit():
            return "{}-{}-{}".format(value[:4], value[4:6], value[6:])
        return value

    @staticmethod
    def _float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


def normalize_a_share_symbol(value):
    value = str(value or "").strip().upper()
    if value.endswith((".SH", ".SZ", ".BJ")) and value[:-3].isdigit() and len(value[:-3]) == 6:
        return value
    if not (value.isdigit() and len(value) == 6):
        return ""
    if value.startswith(("6", "68")):
        return value + ".SH"
    if value.startswith(("4", "8")):
        return value + ".BJ"
    return value + ".SZ"


def normalize_us_symbol(value):
    value = str(value or "").strip().upper()
    if not value or len(value) > 12:
        return ""
    if not all(character.isalnum() or character in ".-" for character in value):
        return ""
    return value


def build_finance_result(market_data):
    kind = market_data.get("kind")
    if kind == "macro":
        return _macro_result(market_data)
    return _equity_result(market_data)


def _macro_result(data):
    series = data.get("series") or []
    if not series:
        return _insufficient("未取得可验证的宏观数据，暂不生成判断。")
    facts = []
    inferences = []
    for item in series:
        latest = item.get("latest")
        previous = item.get("previous")
        facts.append("{}：{}（{}）".format(item.get("name"), latest, item.get("latest_date")))
        if isinstance(latest, (int, float)) and isinstance(previous, (int, float)):
            direction = "上行" if latest > previous else "下行" if latest < previous else "持平"
            inferences.append("{}较上一期{}。".format(item.get("name"), direction))
    summary = "宏观数据呈现分化，应同时观察增长、通胀、就业与利率的后续确认。"
    return _success(summary, facts, inferences, data)


def _equity_result(data):
    points = [item for item in data.get("points") or [] if isinstance(item.get("close"), (int, float)) and item.get("close") > 0]
    symbol = data.get("symbol") or "未知标的"
    if len(points) < 5:
        return _insufficient("{} 的有效历史数据不足，暂不生成分析。".format(symbol))
    closes = [float(item["close"]) for item in points]
    returns = [math.log(closes[index] / closes[index - 1]) for index in range(1, len(closes))]
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / max(1, len(returns) - 1)
    volatility = math.sqrt(variance) * math.sqrt(252) * 100
    window = min(20, len(closes) - 1)
    period_return = (closes[-1] / closes[-1 - window] - 1) * 100
    peak = closes[0]
    max_drawdown = 0.0
    for close in closes:
        peak = max(peak, close)
        max_drawdown = min(max_drawdown, close / peak - 1)
    direction = "偏强" if period_return > 3 else "偏弱" if period_return < -3 else "震荡"
    facts = [
        "{} 最新收盘价为 {:.2f}，数据日期 {}。".format(symbol, closes[-1], data.get("as_of") or "未知"),
        "最近 {} 个交易日区间收益为 {:.2f}%。".format(window, period_return),
        "样本年化波动率约 {:.2f}%，样本最大回撤约 {:.2f}%。".format(volatility, max_drawdown * 100),
    ]
    inferences = ["基于当前样本，价格状态为{}；该判断不代表未来表现。".format(direction)]
    summary = "{}：{}，波动率与回撤仍需结合基本面、估值和事件风险进一步核验。".format(symbol, direction)
    return _success(summary, facts, inferences, data, metrics={"period_return_pct": round(period_return, 4), "annualized_volatility_pct": round(volatility, 4), "max_drawdown_pct": round(max_drawdown * 100, 4)})


def _success(summary, facts, inferences, data, metrics=None):
    evidence = [
        {"id": "finance-source-{}".format(index + 1), "source": item.get("url"), "title": item.get("name"), "timestamp": data.get("as_of")}
        for index, item in enumerate(data.get("sources") or [])
    ]
    return {
        "status": "SUCCESS",
        "summary": summary,
        "facts": facts,
        "inferences": inferences,
        "evidence": evidence,
        "actions": [],
        "warnings": [DISCLAIMER, "数据可能存在延迟、修订、复权和供应商覆盖差异。"],
        "uncertainties": ["历史数据和统计关系不能保证未来结果。"],
        "metadata": {"as_of": data.get("as_of"), "data_kind": data.get("kind"), "metrics": metrics or {}, "validated": False},
    }


def _insufficient(summary):
    return {
        "status": "INSUFFICIENT_EVIDENCE",
        "summary": summary,
        "facts": [],
        "inferences": [],
        "evidence": [],
        "actions": [],
        "warnings": [DISCLAIMER],
        "uncertainties": ["标的、地区或数据源可能未配置，或数据不足。"],
        "metadata": {"as_of": None, "data_kind": None, "metrics": {}, "validated": False},
    }
