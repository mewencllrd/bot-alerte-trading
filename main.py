import ccxt
import time
import requests
import threading
import schedule
from datetime import datetime, timedelta
import pandas as pd
import ta

# === CONFIGURATION ===
TELEGRAM_TOKEN = "TON_TOKEN"
TELEGRAM_CHAT_ID = -1002516223605
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
SCAN_INTERVAL = 60

exchange = ccxt.binance()
active_trades = {}
trade_history = []

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Erreur Telegram:", e)

def fetch_ohlcv(symbol, timeframe="30m"):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=200)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        print(f"Erreur fetch {symbol} : {e}")
        return None

def apply_indicators(df):
    df["ema50"] = ta.trend.ema_indicator(df["close"], window=50).ema_indicator()
    df["ema200"] = ta.trend.ema_indicator(df["close"], window=200).ema_indicator()
    df["macd"] = ta.trend.macd_diff(df["close"])
    df["rsi"] = ta.momentum.rsi(df["close"])
    df.dropna(inplace=True)
    return df

def calculate_tp_sl(entry, direction, rr=2.0):
    if direction == "Achat":
        sl = entry - (entry * 0.003)
        tp = entry + ((entry - sl) * rr)
    else:
        sl = entry + (entry * 0.003)
        tp = entry - ((sl - entry) * rr)
    return round(tp, 2), round(sl, 2)

def is_new_signal(symbol, direction, mode):
    key = f"{symbol}_{mode}"
    if key in active_trades:
        return False
    return True

def send_signal(symbol, direction, entry, tp, sl, rr, confiance, tf, mode):
    msg = f"{symbol} [{confiance}]\nSignal : {direction}\nEntrée : {entry}\nTP : {tp}\nSL : {sl}\nRR : {rr}\nTF : {tf}"
    send_telegram_message(msg)
    key = f"{symbol}_{mode}"
    active_trades[key] = {"direction": direction, "entrée": entry, "tp": tp, "sl": sl, "time": datetime.now()}

def detect_signal(symbol, mode):
    timeframes = {"classique": ["15m", "30m", "1h"], "scalping": ["1m", "5m", "10m"]}
    confirmations = 0
    directions = []

    for tf in timeframes[mode]:
        df = fetch_ohlcv(symbol, tf)
        if df is None:
            continue
        df = apply_indicators(df)
        last = df.iloc[-1]
        buy = last["close"] > last["ema50"] > last["ema200"] and last["macd"] > 0 and last["rsi"] > 50
        sell = last["close"] < last["ema50"] < last["ema200"] and last["macd"] < 0 and last["rsi"] < 50
        if buy:
            confirmations += 1
            directions.append("Achat")
        elif sell:
            confirmations += 1
            directions.append("Vente")

    if confirmations < 2:
        return

    direction = max(set(directions), key=directions.count)
    entry = fetch_price(symbol)
    rr = 1.5 if mode == "scalping" else 2.0
    tp, sl = calculate_tp_sl(entry, direction, rr)

    confiance = "🔐 Signal très fiable" if confirmations >= 3 else "⚠️ Signal modéré"
    if is_new_signal(symbol, direction, mode):
        send_signal(symbol, direction, entry, tp, sl, rr, confiance, ",".join(timeframes[mode]), mode)

def fetch_price(symbol):
    return exchange.fetch_ticker(symbol)["last"]

def check_tp_sl():
    now = datetime.now()
    for key in list(active_trades.keys()):
        trade = active_trades[key]
        symbol = key.split("_")[0]
        price = fetch_price(symbol)
        direction = trade["direction"]
        tp_hit = price >= trade["tp"] if direction == "Achat" else price <= trade["tp"]
        sl_hit = price <= trade["sl"] if direction == "Achat" else price >= trade["sl"]
        if tp_hit or sl_hit:
            result = "TP" if tp_hit else "SL"
            pips = abs(price - trade["entrée"])
            duration = int((now - trade["time"]).total_seconds() / 60)
            send_telegram_message(f"{result} touché sur {symbol} ({pips} points, {duration} min)")
            trade_history.append({"hit": result, "symbol": symbol})
            del active_trades[key]

def weekly_recap():
    total = len(trade_history)
    tp = sum(1 for t in trade_history if t["hit"] == "TP")
    sl = sum(1 for t in trade_history if t["hit"] == "SL")
    wr = round((tp / total) * 100, 1) if total else 0
    send_telegram_message(f"📊 Récapitulatif Hebdo\nTP : {tp}\nSL : {sl}\nWin Rate : {wr}%")
    trade_history.clear()

def run_bot():
    schedule.every().sunday.at("22:00").do(weekly_recap)
    send_telegram_message("✅ Bot lancé")
    while True:
        check_tp_sl()
        for symbol in SYMBOLS:
            detect_signal(symbol, "classique")
            detect_signal(symbol, "scalping")
        schedule.run_pending()
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_bot()

