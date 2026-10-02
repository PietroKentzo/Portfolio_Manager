import math

import yfinance as yf
from agents import function_tool


def fetch_history(ticker: str, period: str = "2y"):
    """Internal Python function shared by the agent-facing tools."""
    if period not in {"1y", "2y"}:
        raise ValueError("period must be '1y' or '2y'")

    data = yf.Ticker(ticker).history(
        period=period,
        interval="1d",
        auto_adjust=True,
    )

    if data.empty or "Close" not in data.columns:
        raise ValueError(f"No usable daily price history for {ticker}")

    return data.sort_index()


def finite_number(value, name: str) -> float:
    result = float(value)

    if not math.isfinite(result):
        raise ValueError(f"{name} is missing or not finite")

    return result


@function_tool
def get_stock_price(ticker: str) -> dict:
    """Return the latest adjusted daily closing price for a ticker."""
    data = fetch_history(ticker)

    return {
        "ticker": ticker.upper(),
        "as_of": data.index[-1].isoformat(),
        "price_type": "adjusted daily close; not a live quote",
        "close": finite_number(data["Close"].iloc[-1], "close"),
    }


@function_tool
def get_technical_indicators(ticker: str) -> dict:
    """Return the latest moving averages and RSI for a ticker."""
    data = fetch_history(ticker)

    if len(data) < 200:
        raise ValueError(
            f"{ticker} has {len(data)} daily prices; "
            "at least 200 are needed for SMA_200"
        )

    close = data["Close"]

    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()

    delta = close.diff()
    average_gain = delta.clip(lower=0).ewm(
        alpha=1 / 14,
        adjust=False,
    ).mean()
    average_loss = (-delta.clip(upper=0)).ewm(
        alpha=1 / 14,
        adjust=False,
    ).mean()

    if average_loss.iloc[-1] == 0:
        rsi_14 = 100.0 if average_gain.iloc[-1] > 0 else 50.0
    else:
        relative_strength = (
            average_gain.iloc[-1] / average_loss.iloc[-1]
        )
        rsi_14 = 100 - 100 / (1 + relative_strength)

    return {
        "ticker": ticker.upper(),
        "as_of": data.index[-1].isoformat(),
        "close": finite_number(close.iloc[-1], "close"),
        "sma_20": finite_number(sma_20.iloc[-1], "sma_20"),
        "sma_50": finite_number(sma_50.iloc[-1], "sma_50"),
        "sma_200": finite_number(sma_200.iloc[-1], "sma_200"),
        "rsi_14": finite_number(rsi_14, "rsi_14"),
    }


@function_tool
def get_macd(ticker: str) -> dict:
    """Return the latest 12/26/9 MACD values for a ticker."""
    data = fetch_history(ticker, period="1y")

    if len(data) < 35:
        raise ValueError(
            f"{ticker} has too little daily history to calculate MACD"
        )

    close = data["Close"]
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()

    macd = ema_12 - ema_26
    signal = macd.ewm(span=9, adjust=False).mean()

    return {
        "ticker": ticker.upper(),
        "as_of": data.index[-1].isoformat(),
        "macd": finite_number(macd.iloc[-1], "macd"),
        "macd_signal": finite_number(signal.iloc[-1], "macd_signal"),
        "macd_histogram": finite_number(
            (macd - signal).iloc[-1],
            "macd_histogram",
        ),
    }