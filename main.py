import ccxt
import time
import requests
import threading
import schedule
from datetime import datetime, timedelta

# === CONFIGURATION ===
TELEGRAM_TOKEN = "8050078976:AAEu6HHh7UtnSgVvzy0zUIa_TprcuT4IP10"
TELEGRAM_CHAT_ID = -1002516223605
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
SCAN_INTERVAL = 60

exchange = ccxt.binance()
active_trades = {}
trade_history = []

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Erreur Telegram:", e)

def fetch_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

def calculate_tp_sl(entry, direction, rr=2.0):
    if direction == "Achat":
        sl = entry - (entry * 0.003)
        tp = entry + ((entry - sl) * rr)
    else:
        sl = entry + (entry * 0.003)
        tp = entry - ((sl - entry) * rr)
    return round(tp), round(sl)

def send_alert(symbol, data):
    now = datetime.now()
    message = f"""ALERTE {symbol}
Confiance : {data['confiance']}
Signal : {data['signal']}
Entree : {data['entrée']}
TP : {data['tp']}
SL : {data['sl']}
RR : {data['rr']}
Timeframe : {data.get('timeframe', 'Inconnu')}
Horodatage : {now.isoformat()}"""
    send_telegram_message(message)

def detect_signal_classique(symbol):
    signals = ["Achat", "Vente"]
    direction = "Achat" if signals.count("Achat") >= 2 else "Vente" if signals.count("Vente") >= 2 else None
    if not direction:
        return
    entry = fetch_price(symbol)
    tp, sl = calculate_tp_sl(entry, direction)
    rr = round(abs(tp - entry) / abs(entry - sl), 2)
    send_alert(symbol, {
        "confiance": "Signal très fiable",
        "signal": direction,
        "entrée": entry,
        "tp": tp,
        "sl": sl,
        "rr": rr,
        "timeframe": "M15/M30/H1"
    })
    active_trades[symbol] = {
        "direction": direction,
        "entrée": entry,
        "tp": tp,
        "sl": sl,
        "time": datetime.now()
    }

def detect_signal_scalping(symbol):
    signals = ["Vente", "Vente"]
    direction = "Achat" if signals.count("Achat") >= 2 else "Vente" if signals.count("Vente") >= 2 else None
    if not direction:
        return
    entry = fetch_price(symbol)
    tp, sl = calculate_tp_sl(entry, direction, rr=1.5)
    rr = round(abs(tp - entry) / abs(entry - sl), 2)
    send_alert(symbol, {
        "confiance": "Scalping de signal",
        "signal": direction,
        "entrée": entry,
        "tp": tp,
        "sl": sl,
        "rr": rr,
        "timeframe": "M1/M5/M10"
    })
    active_trades[symbol + "_scalp"] = {
        "direction": direction,
        "entrée": entry,
        "tp": tp,
        "sl": sl,
        "time": datetime.now()
    }

def check_active_trades():
    now = datetime.now()
    for key in list(active_trades.keys()):
        trade = active_trades[key]
        symbol = key.replace("_scalp", "")
        price = fetch_price(symbol)
        hit = None
        if trade["direction"] == "Achat":
            if price >= trade["tp"]:
                hit = "TP"
            elif price <= trade["sl"]:
                hit = "SL"
        else:
            if price <= trade["tp"]:
                hit = "TP"
            elif price >= trade["sl"]:
                hit = "SL"
        if hit:
            duration = now - trade["time"]
            pips = abs(price - trade["entrée"])
            send_telegram_message(f"{hit} touché sur {symbol} — {pips} pips — {int(duration.total_seconds() / 60)} min")
            trade_history.append({"hit": hit, "symbol": symbol})
            del active_trades[key]

def weekly_recap():
    if not trade_history:
        send_telegram_message("Récapitulatif : Aucun trade cette semaine.")
        return
    total = len(trade_history)
    tp = sum(1 for t in trade_history if t["hit"] == "TP")
    sl = sum(1 for t in trade_history if t["hit"] == "SL")
    winrate = round((tp / total) * 100) if total else 0
    send_telegram_message(f"""Récapitulatif Hebdo
TP atteints : {tp}
SL touchés : {sl}
Taux de victoire : {winrate}%""")
    trade_history.clear()

def run_bot():
    schedule.every().sunday.at("22:00").do(weekly_recap)
    send_telegram_message("Bot d'alerte lancé avec succès.")
    while True:
        check_active_trades()
        for symbol in SYMBOLS:
            detect_signal_classique(symbol)
            detect_signal_scalping(symbol)
        schedule.run_pending()
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run_bot()


