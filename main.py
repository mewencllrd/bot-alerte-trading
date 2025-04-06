# === IMPORTATIONS ===
import ccxt
import time
import pandas as pd
import requests
import ta
from datetime import datetime

# === CONFIGURATION ===
TELEGRAM_TOKEN = "TON_TOKEN"
TELEGRAM_CHAT_ID = -1002516223605
SYMBOLS = ["BTC/USDT", "ETH/USDT"]
SCAN_INTERVAL = 60

exchange = ccxt.binance()

# === FONCTIONS GÉNÉRALES ===
def fetch_data(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except:
        return None

def fetch_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

def send_alert(symbol, data):
    message = f"{data['confidence']}\n"
    message += f"💰 *Crypto* : {symbol}\n"
    message += f"📈 *Direction* : {data['signal']}\n"
    message += f"🎯 *Prix d\'entrée* : {round(data['entry'], 2)}\n"
    message += f"🎯 TP : {round(data['tp'], 2)}\n"
    message += f"🛡️ SL : {round(data['sl'], 2)}\n"
    message += f"🕓 Timeframe : {data['timeframe']}"
    send_telegram_message(message)

# === INDICATEURS CLASSIQUES ===
def compute_indicators(df):
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()
    df['macd'] = ta.trend.macd_diff(df['close'])
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    return df

def detect_classic_signal(df):
    if len(df) < 200:
        return None
    last = df.iloc[-1]
    signal = None

    ema_signal = "Achat" if last['ema50'] > last['ema200'] else "Vente"
    macd_signal = "Achat" if last['macd'] > 0 else "Vente"
    rsi_signal = "Achat" if last['rsi'] < 30 else ("Vente" if last['rsi'] > 70 else None)

    indicators = [ema_signal, macd_signal, rsi_signal]
    counts = {"Achat": indicators.count("Achat"), "Vente": indicators.count("Vente")}

    if counts["Achat"] >= 2:
        signal = "Achat"
    elif counts["Vente"] >= 2:
        signal = "Vente"

    return signal

def check_market():
    for symbol in SYMBOLS:
        df = fetch_data(symbol, "30m")
        if df is None:
            continue
        df = compute_indicators(df)
        signal = detect_classic_signal(df)

        if signal:
            price = df['close'].iloc[-1]
            rr = 2.0
            if signal == "Achat":
                sl = price - (price * 0.005)
                tp = price + ((price - sl) * rr)
            else:
                sl = price + (price * 0.005)
                tp = price - ((sl - price) * rr)

            indicators_ok = 0
            last = df.iloc[-1]
            if (last['ema50'] > last['ema200'] and signal == "Achat") or (last['ema50'] < last['ema200'] and signal == "Vente"):
                indicators_ok += 1
            if (last['macd'] > 0 and signal == "Achat") or (last['macd'] < 0 and signal == "Vente"):
                indicators_ok += 1
            if (last['rsi'] < 30 and signal == "Achat") or (last['rsi'] > 70 and signal == "Vente"):
                indicators_ok += 1

            if indicators_ok >= 2:
                confidence = "🔒 Signal très fiable" if indicators_ok == 3 else "🔎 Signal modéré"
                send_alert(symbol, {
                    "confidence": confidence,
                    "signal": signal,
                    "entry": price,
                    "tp": tp,
                    "sl": sl,
                    "timeframe": "M30"
                })

# === SCALPING MODE ===
def compute_scalping_indicators(df):
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['stoch_rsi'] = (df['rsi'] - df['rsi'].rolling(14).min()) / (df['rsi'].rolling(14).max() - df['rsi'].rolling(14).min())
    df['supertrend'] = (df['high'] + df['low']) / 2  # Placeholder
    return df

def detect_scalping_direction(df):
    if len(df) < 20:
        return None
    stoch = df['stoch_rsi'].iloc[-1]
    ema20 = df['ema20'].iloc[-1]
    ema50 = df['ema50'].iloc[-1]
    close = df['close'].iloc[-1]

    if stoch < 0.2 and ema20 > ema50 and close > ema20:
        return "Achat"
    elif stoch > 0.8 and ema20 < ema50 and close < ema20:
        return "Vente"
    return None

def detect_signal_scalping(symbol):
    timeframes = {"M1": "1m", "M5": "5m", "M10": "10m"}
    signals = []

    for tf_name, tf in timeframes.items():
        try:
            df = fetch_data(symbol, tf)
            df = compute_scalping_indicators(df)
            signal = detect_scalping_direction(df)
            if signal:
                signals.append(signal)
        except Exception as e:
            print(f"Erreur scalping {symbol} - {tf_name} :", e)

    if signals.count("Achat") >= 2:
        direction = "Achat"
    elif signals.count("Vente") >= 2:
        direction = "Vente"
    else:
        return

    price = fetch_price(symbol)
    rr = 1.5
    if direction == "Achat":
        sl = price - (price * 0.003)
        tp = price + ((price - sl) * rr)
    else:
        sl = price + (price * 0.003)
        tp = price - ((sl - price) * rr)

    send_alert(symbol, {
        "confidence": "⚡ Signal Scalping",
        "signal": direction,
        "entry": price,
        "tp": tp,
        "sl": sl,
        "timeframe": "M1/M5/M10"
    })

# === BOUCLE PRINCIPALE ===
def run_bot():
    print("🤖 Bot actif...")
    while True:
        check_market()  # Bot classique
        for symbol in SYMBOLS:
            detect_signal_scalping(symbol)  # Bot scalping
        time.sleep(SCAN_INTERVAL)

# === LANCEMENT ===
if __name__ == "__main__":
    run_bot()

