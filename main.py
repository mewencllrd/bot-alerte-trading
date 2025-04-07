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
active_trades = {}
trade_history = []
symbol_last_alert = {}

exchange = ccxt.binance()

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
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

def check_direction(df):
    last = df.iloc[-1]
    buy = last["close"] > last["ema50"] > last["ema200"] and last["macd"] > 0 and last["rsi"] > 50
    sell = last["close"] < last["ema50"] < last["ema200"] and last["macd"] < 0 and last["rsi"] < 50
    return "Achat" if buy else ("Vente" if sell else None)

def calculate_tp_sl(entry, direction, rr=2.0):
    if direction == "Achat":
        sl = entry - (entry * 0.003)
        tp = entry + ((entry - sl) * rr)
    else:
        sl = entry + (entry * 0.003)
        tp = entry - ((sl - entry) * rr)
    return round(tp, 2), round(sl, 2)

def fetch_price(symbol):
    return exchange.fetch_ticker(symbol)["last"]

def is_duplicate_alert(symbol, direction):
    if symbol in symbol_last_alert:
        last = symbol_last_alert[symbol]
        if last["direction"] == direction and (datetime.now() - last["time"]).seconds < 900:
            return True
    return False

def register_alert(symbol, direction):
    symbol_last_alert[symbol] = {"direction": direction, "time": datetime.now()}

def send_signal(symbol, direction, entry, tp, sl, rr, confiance, mode, tf):
    message = f"<b>{symbol}</b> [{mode}]\n<b>Confiance:</b> {confiance}\n<b>Signal:</b> {direction}\n<b>Entrée:</b> {entry}\n<b>TP:</b> {tp}\n<b>SL:</b> {sl}\n<b>RR:</b> {rr}\n<b>TF:</b> {tf}\n<b>Heure:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(message)
    active_trades[f"{symbol}_{mode}"] = {
        "direction": direction,
        "entrée": entry,
        "tp": tp,
        "sl": sl,
        "time": datetime.now()
    }

def detect_signal(symbol, mode):
    timeframes = {
        "classique": ["15m", "30m", "1h"],
        "scalping": ["1m", "5m", "10m"]
    }
    confirmations = []
    for tf in timeframes[mode]:
        df = fetch_ohlcv(symbol, tf)
        if df is None:
            continue
        df = apply_indicators(df)
        direction = check_direction(df)
        if direction:
            confirmations.append(direction)

    if len(confirmations) < 2:
        return

    final_direction = max(set(confirmations), key=confirmations.count)
    if is_duplicate_alert(symbol + "_" + mode, final_direction):
        return
    register_alert(symbol + "_" + mode, final_direction)

    entry = fetch_price(symbol)
    rr = 1.5 if mode == "scalping" else 2.0
    tp, sl = calculate_tp_sl(entry, final_direction, rr)
    confiance = "🔐 Signal très fiable" if len(confirmations) >= 3 else "⚠️ Signal modéré"

    send_signal(symbol, final_direction, entry, tp, sl, rr, confiance, mode, ",".join(timeframes[mode]))

def check_tp_sl():
    now = datetime.now()
    for key in list(active_trades.keys()):
        trade = active_trades[key]
        symbol = key.split("_")[0]
        price = fetch_price(symbol)
        direction = trade["direction"]
        if direction == "Achat" and price >= trade["tp"] or direction == "Vente" and price <= trade["tp"]:
            result = "TP"
        elif direction == "Achat" and price <= trade["sl"] or direction == "Vente" and price >= trade["sl"]:
            result = "SL"
        else:
            continue

        duration = int((now - trade["time"]).total_seconds() / 60)
        pips = round(abs(price - trade["entrée"]), 2)
        msg = f"{result} touché sur {symbol} ({pips} pips, {duration} min)"
        send_telegram_message(msg)
        trade_history.append({"hit": result, "symbol": symbol})
        del active_trades[key]

def weekly_recap():
    total = len(trade_history)
    tp = sum(1 for t in trade_history if t["hit"] == "TP")
    sl = sum(1 for t in trade_history if t["hit"] == "SL")
    wr = round((tp / total) * 100, 1) if total else 0
    msg = f"📅 Récap Hebdo\nTP: {tp}\nSL: {sl}\nWin Rate: {wr}%"
    send_telegram_message(msg)
    trade_history.clear()

def run_bot():
    schedule.every().sunday.at("22:00").do(weekly_recap)
    send_telegram_message("✅ Bot de trading activé.")
    while True:
        check_tp_sl()
        for symbol in SYMBOLS:
            detect_signal(symbol, "classique")
            detect_signal(symbol, "scalping")
        schedule.run_pending()
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_bot()

