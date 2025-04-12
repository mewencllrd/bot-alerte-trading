import requests
import pandas as pd
import pandas_ta as ta

# === Récupère les données OHLC depuis Bitget ===
def get_bitget_ohlcv(symbol="BTCUSDT", interval="15m", limit=100):
    url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()['data']

    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# === Mode CLASSIQUE : analyse M15/M30/H1 avec SSL Hybrid, MACD, Price Action ===
def detect_classic_signal(df):
    df['ema50'] = ta.ema(df['close'], length=50)
    df['ema200'] = ta.ema(df['close'], length=200)
    macd = ta.macd(df['close'])
    df['macd_hist'] = macd['MACDh_12_26_9']

    latest = df.iloc[-1]
    signal_long = latest['ema50'] > latest['ema200'] and latest['macd_hist'] > 0
    signal_short = latest['ema50'] < latest['ema200'] and latest['macd_hist'] < 0

    if signal_long:
        return "long"
    elif signal_short:
        return "short"
    return None

# === Mode SCALPING : analyse M1/M5/M10 avec VWAP, Supertrend, Stoch RSI ===
def detect_scalping_signal(df):
    stoch = ta.stochrsi(df['close'], length=14)
    df['stoch_k'] = stoch['STOCHRSIk_14_14_3_3']
    df['stoch_d'] = stoch['STOCHRSId_14_14_3_3']

    df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    supertrend = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3.0)
    df['supertrend'] = supertrend['SUPERT_10_3.0']

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signal_long = (
        latest['close'] > latest['vwap']
        and latest['stoch_k'] > latest['stoch_d']
        and latest['supertrend'] > prev['supertrend']
    )

    signal_short = (
        latest['close'] < latest['vwap']
        and latest['stoch_k'] < latest['stoch_d']
        and latest['supertrend'] < prev['supertrend']
    )

    if signal_long:
        return "long"
    elif signal_short:
        return "short"
    return None


