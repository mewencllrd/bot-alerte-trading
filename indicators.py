import requests
import pandas as pd
import pandas_ta as ta

def get_bitget_ohlcv(symbol="BTCUSDT", interval="15m", limit=100):
    url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()["data"]
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.iloc[::-1]
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.astype(float)
    df.ta.atr(length=14, append=True)  # Calcul ATR pour TP/SL
    return df

def detect_classic_signal(df):
    df["ema_50"] = ta.ema(df["close"], length=50)
    df["ema_200"] = ta.ema(df["close"], length=200)
    macd = ta.macd(df["close"])
    df["macd_hist"] = macd["MACDh_12_26_9"]
    last = df.iloc[-1]

    if last["close"] > last["ema_50"] > last["ema_200"] and last["macd_hist"] > 0:
        return "long"
    elif last["close"] < last["ema_50"] < last["ema_200"] and last["macd_hist"] < 0:
        return "short"
    return None

def detect_scalping_signal(df):
    stoch = ta.stoch(df["high"], df["low"], df["close"])
    df["stoch_k"] = stoch["STOCHk_14_3_3"]
    df["stoch_d"] = stoch["STOCHd_14_3_3"]
    df["vwap"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])

    supertrend = ta.supertrend(df["high"], df["low"], df["close"])[f"SUPERT_7_3.0"]
    df["supertrend"] = supertrend

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["close"] > last["vwap"] and last["stoch_k"] > last["stoch_d"] and last["supertrend"] > prev["supertrend"]:
        return "long"
    elif last["close"] < last["vwap"] and last["stoch_k"] < last["stoch_d"] and last["supertrend"] < prev["supertrend"]:
        return "short"
    return None
