import requests
import pandas as pd
import pandas_ta as ta

# === Récupère les données réelles depuis Bitget ===
def get_bitget_ohlcv(symbole="BTCUSDT", intervalle="15m", limite=100):
    url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbole}&granularity={intervalle}&limit={limite}"
    r = requests.get(url)
    data = r.json().get("data", [])

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume"])
    df = df.iloc[::-1]  # met dans l'ordre chronologique
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].astype(float)
    return df

# === MODE CLASSIQUE ===
def detect_classic_signal(df):
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=200, append=True)
    df.ta.macd(append=True)

    last = df.iloc[-1]
    ema_50 = last["EMA_50"]
    ema_200 = last["EMA_200"]
    macd_hist = last["MACDh_12_26_9"]
    price = last["close"]

    if price > ema_50 > ema_200 and macd_hist > 0:
        return "long"
    elif price < ema_50 < ema_200 and macd_hist < 0:
        return "short"
    else:
        return "none"

# === MODE SCALPING ===
def detect_scalping_signal(df):
    df.ta.stoch(length=14, append=True)
    df.ta.vwap(append=True)
    df.ta.supertrend(append=True)

    last = df.iloc[-1]
    stoch_k = last["STOCHk_14_3_3"]
    stoch_d = last["STOCHd_14_3_3"]
    price = last["close"]
    vwap = last["VWAP_D"]
    supertrend = last.get("SUPERT_7_3.0", None)

    if price > vwap and stoch_k > stoch_d and (supertrend is None or price > supertrend):
        return "long"
    elif price < vwap and stoch_k < stoch_d and (supertrend is None or price < supertrend):
        return "short"
    else:
        return "none"

