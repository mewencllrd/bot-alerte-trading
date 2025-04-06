# === IMPORTS ===
import requests
import pandas as pd
import time
import json
import os
import threading
from datetime import datetime, timedelta
import schedule
import ta
import ccxt

# === CONFIGURATION ===
TELEGRAM_TOKEN = "8050078976:AAEu6HHh7UtnSgVvzy0zUIa_TprcuT4IP10"
TELEGRAM_CHAT_ID = "-1002516223605"
SYMBOLS = ["BTC/USDT", "ETH/USDT"]
SCAN_INTERVAL = 60
exchange = ccxt.binance()
active_trades = {}
trade_history = []

# === TELEGRAM ===
def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        print("Message Telegram envoyé.")
    except Exception as e:
        print("Erreur Telegram:", e)

# === UTILS ===
def fetch_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

def calculate_tp_sl(entry, direction, rr=2.0):
    delta = entry * 0.003
    if direction == "Achat":
        sl = entry - delta
        tp = entry + (entry - sl) * rr
    else:
        sl = entry + delta
        tp = entry - (sl - entry) * rr
    return round(tp, 2), round(sl, 2)

def log_trade(symbol, direction, entry, tp, sl, result, pips, elapsed):
    trade = {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "result": result,
        "pips": pips,
        "elapsed": elapsed,
        "timestamp": datetime.now().isoformat()
    }
    trade_history.append(trade)

# === ALERTES ===
def send_alert(symbol, data):
    message = (
        f"{data['confiance']}\n"
        f"*Crypto* : {symbol}\n"
        f"*Signal* : {data['signal']}\n"
        f"*Entrée* : {data['entrée']}\n"
        f"*TP* : {data['tp']}\n"
        f"*SL* : {data['sl']}\n"
        f"*RR* : {data['rr']}\n"
        f"*Horodatage* : {data['horodatage']}"
    )
    send_telegram_message(message)

# === STRATEGIE CLASSIQUE ===
def detect_signal_classique(symbol):
    try:
        df = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=100)
        df = pd.DataFrame(df, columns=["time", "open", "high", "low", "close", "volume"])
        close = df["close"]
        ema50 = ta.trend.ema_indicator(close, window=50).ema_indicator()
        ema200 = ta.trend.ema_indicator(close, window=200).ema_indicator()
        rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
        macd = ta.trend.macd_diff(close)

        latest = -1
        score = 0
        if ema50[latest] > ema200[latest]: score += 1
        if rsi[latest] > 50: score += 1
        if macd[latest] > 0: score += 1

        if score >= 2:
            direction = "Achat" if ema50[latest] > ema200[latest] else "Vente"
            entry = float(close[latest])
            rr = 2.5 if score == 3 else 2.0
            tp, sl = calculate_tp_sl(entry, direction, rr)
            confiance = "🔒 Signal très fiable" if score == 3 else "⚠️ Signal modéré"

            send_alert(symbol, {
                "confiance": confiance,
                "signal": direction,
                "entrée": entry,
                "tp": tp,
                "sl": sl,
                "rr": round(abs(tp - entry) / abs(entry - sl), 2),
                "horodatage": datetime.now().isoformat()
            })
            active_trades[symbol] = {
                "direction": direction,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "start": datetime.now()
            }
    except Exception as e:
        print(f"Erreur classique sur {symbol}:", e)

# === STRATEGIE SCALPING ===
def detect_signal_scalping(symbol):
    try:
        timeframes = ["1m", "5m"]
        valid = 0
        for tf in timeframes:
            df = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=50)
            df = pd.DataFrame(df, columns=["time", "open", "high", "low", "close", "volume"])
            close = df["close"]
            ema = ta.trend.ema_indicator(close, window=20).ema_indicator()
            macd = ta.trend.macd_diff(close)
            rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
            if ema.iloc[-1] > close.iloc[-1] and macd.iloc[-1] < 0 and rsi.iloc[-1] < 50:
                valid += 1
        if valid >= 2:
            entry = fetch_price(symbol)
            direction = "Vente"
            tp, sl = calculate_tp_sl(entry, direction, rr=1.5)
            send_alert(symbol, {
                "confiance": "🔦 Signal Scalping",
                "signal": direction,
                "entrée": entry,
                "tp": tp,
                "sl": sl,
                "rr": round(abs(tp - entry) / abs(entry - sl), 2),
                "horodatage": datetime.now().isoformat()
            })
            active_trades[symbol] = {
                "direction": direction,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "start": datetime.now()
            }
    except Exception as e:
        print(f"Erreur scalping {symbol}:", e)

# === VERIFICATION TP/SL ===
def check_active_trades():
    to_remove = []
    for symbol, trade in active_trades.items():
        try:
            price = fetch_price(symbol)
            direction = trade['direction']
            tp = trade['tp']
            sl = trade['sl']
            entry = trade['entry']
            start = trade['start']
            elapsed = datetime.now() - start
            minutes = int(elapsed.total_seconds() / 60)
            time_str = f"({minutes} minutes)"

            if direction == "Achat":
                if price >= tp:
                    pips = round((tp - entry) * 10000)
                    msg = f"📈 TP atteint sur {symbol} ! +{pips} pips\n{time_str}"
                    send_telegram_message(msg)
                    log_trade(symbol, direction, entry, tp, sl, "TP", pips, minutes)
                    to_remove.append(symbol)
                elif price <= sl:
                    pips = round((entry - sl) * 10000)
                    msg = f"❌ SL touché sur {symbol} ! -{pips} pips\n{time_str}"
                    send_telegram_message(msg)
                    log_trade(symbol, direction, entry, tp, sl, "SL", -pips, minutes)
                    to_remove.append(symbol)
            else:
                if price <= tp:
                    pips = round((entry - tp) * 10000)
                    msg = f"📈 TP atteint sur {symbol} ! +{pips} pips\n{time_str}"
                    send_telegram_message(msg)
                    log_trade(symbol, direction, entry, tp, sl, "TP", pips, minutes)
                    to_remove.append(symbol)
                elif price >= sl:
                    pips = round((sl - entry) * 10000)
                    msg = f"❌ SL touché sur {symbol} ! -{pips} pips\n{time_str}"
                    send_telegram_message(msg)
                    log_trade(symbol, direction, entry, tp, sl, "SL", -pips, minutes)
                    to_remove.append(symbol)
        except:
            continue
    for s in to_remove:
        del active_trades[s]

# === RECAP HEBDOMADAIRE ===
last_recap = None

def schedule_recap():
    global last_recap
    now = datetime.now()
    if now.weekday() == 6 and now.hour == 22:
        if last_recap != now.date():
            total = len(trade_history)
            wins = len([t for t in trade_history if t['result'] == "TP"])
            losses = len([t for t in trade_history if t['result'] == "SL"])
            winrate = round((wins / total) * 100, 2) if total > 0 else 0
            best = max(trade_history, key=lambda x: x['pips'], default=None)
            worst = min(trade_history, key=lambda x: x['pips'], default=None)

            message = f"\n*\ud83d\udcca Récapitulatif de la semaine*\n"
            message += f"\n*Signaux envoyés* : {total}"
            message += f"\n*TP atteints* : {wins}"
            message += f"\n*SL touchés* : {losses}"
            message += f"\n*Taux de victoire* : {winrate}%"
            if best:
                message += f"\n*Meilleur trade* : {best['symbol']} +{best['pips']} pips"
            if worst:
                message += f"\n*Pire trade* : {worst['symbol']} {worst['pips']} pips"
            send_telegram_message(message)
            last_recap = now.date()

# === BOUCLE PRINCIPALE ===
def run_bot():
    schedule.every(1).minutes.do(schedule_recap)
    send_telegram_message("\ud83d\udcc5 Bot d'alerte lancé avec succès.")
    while True:
        check_active_trades()
        for s in SYMBOLS:
            detect_signal_classique(s)
            detect_signal_scalping(s)
        schedule.run_pending()
        time.sleep(SCAN_INTERVAL)

# === EXECUTION ===
if __name__ == "__main__":
    run_bot()


