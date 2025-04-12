import requests
import pandas as pd
import pandas_ta as ta

# --- Récupère les données réelles depuis Bitget ---
def get_bitget_ohlcv(symbol="btc_usdt", interval="15m", limit=100):
    url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()["data"]
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.astype(float)
    df.set_index("timestamp", inplace=True)
    return df

# --- Mode classique (M15 / M30 / H1) ---
def detect_classic_signal(df):
    df["EMA_50"] = ta.ema(df["close"], length=50)
    df["EMA_200"] = ta.ema(df["close"], length=200)
    macd = ta.macd(df["close"])
    df["MACD_hist"] = macd["MACDh_12_26_9"]

    last = df.iloc[-1]

    signal_long = last["EMA_50"] > last["EMA_200"] and last["MACD_hist"] > 0
    signal_short = last["EMA_50"] < last["EMA_200"] and last["MACD_hist"] < 0

    if signal_long:
        return "long"
    elif signal_short:
        return "short"
    return "none"

# --- Mode scalping rapide (M1 / M5 / M10) ---
def detect_scalping_signal(df):
    stoch = ta.stochrsi(df["close"], length=14)
    df["K"], df["D"] = stoch.iloc[:, 0], stoch.iloc[:, 1]
    df["VWAP"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])

    last = df.iloc[-1]
    signal_long = last["K"] > 80 and last["K"] > last["D"] and last["close"] > last["VWAP"]
    signal_short = last["K"] < 20 and last["K"] < last["D"] and last["close"] < last["VWAP"]

    if signal_long:
        return "long"
    elif signal_short:
        return "short"
    return "none"
