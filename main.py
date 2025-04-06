import requests
import time
import threading
import json
import os
from datetime import datetime, timedelta
import schedule
import ta
import ccxt

# === CONFIGURATION ===
TELEGRAM_TOKEN = "8050078976:AAEu6HHh7UtnSgVvzy0zUIa_TprcuT4IP10"
TELEGRAM_CHAT_ID = "-1002516223605"
SYMBOLS = ["BTC/USDT", "ETH/USDT"]
SCAN_INTERVAL = 60  # secondes

exchange = ccxt.binance()
active_trades = {}
trade_history = []
LOG_FILE = "trade_log.json"
last_recap = None

# === ENVOI TELEGRAM ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=data)
        print("Message envoyé ", response.text)
    except Exception as e:
        print("Erreur Telegram:", e)

# === CALCUL RR ===
def calculate_rr(tp, entry, sl):
    return round(abs(tp - entry) / abs(entry - sl), 2)

# === FETCH PRIX ===
def fetch_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return ticker['close']

# === ALERT TELEGRAM ===
def send_alert(symbol, data):
    try:
        message = (
            f"{data['confiance']}\n"
            f"*Crypto* : {symbol}\n"
            f"*Direction* : {data['signal']}\n"
            f"🎯 *Entrée* : {data['entrée']}\n"
            f"🎯 *TP* : {data['tp']}\n"
            f"🛑 *SL* : {data['sl']}\n"
            f"📊 *RR* : {data['rr']}\n"
            f"🕰 Horodatage : {data['horodatage']}"
        )
        send_telegram_message(message)
    except Exception as e:
        print("Erreur lors de l'envoi d'alerte:", e)

# === DETECTION CLASSIQUE ===
def detect_signal_classique(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        closes = [c[4] for c in ohlcv]

        ema50 = ta.trend.ema_indicator(pd.Series(closes), window=50).iloc[-1]
        ema200 = ta.trend.ema_indicator(pd.Series(closes), window=200).iloc[-1]
        rsi = ta.momentum.rsi(pd.Series(closes), window=14).iloc[-1]

        macd = ta.trend.macd_diff(pd.Series(closes)).iloc[-1]
        price = closes[-1]

        conditions = {
            "ema": ema50 > ema200,
            "rsi": rsi > 50,
            "macd": macd > 0
        }

        score = sum(conditions.values())

        if score == 3:
            niveau = "🔒 Signal très fiable"
            rr = 2.5
        elif score == 2:
            niveau = "⚠️ Signal modéré"
            rr = 2.0
        else:
            return

        direction = "Achat" if conditions["ema"] and conditions["macd"] else "Vente"

        if direction == "Achat":
            sl = price - (price * 0.01)
            tp = price + (abs(price - sl) * rr)
        else:
            sl = price + (price * 0.01)
            tp = price - (abs(sl - price) * rr)

        rr_calc = calculate_rr(tp, price, sl)

        send_alert(symbol, {
            "confiance": niveau,
            "signal": direction,
            "entrée": round(price, 2),
            "tp": round(tp, 2),
            "sl": round(sl, 2),
            "rr": rr_calc,
            "horodatage": datetime.now().isoformat()
        })

        active_trades[symbol] = {
            "direction": direction,
            "tp": tp,
            "sl": sl,
            "entrée": price,
            "temps": datetime.now()
        }

    except Exception as e:
        print("Erreur classique:", e)

# === DETECTION SCALPING ===
def detect_signal_scalping(symbol):
    try:
        timeframes = ['1m', '5m', '15m']
        confirmations = 0

        for tf in timeframes:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=50)
            closes = [c[4] for c in ohlcv]
            ema = ta.trend.ema_indicator(pd.Series(closes), window=20).iloc[-1]
            price = closes[-1]
            if price > ema:
                confirmations += 1

        if confirmations >= 2:
            direction = "Achat"
            rr = 1.5
            sl = price - (price * 0.003)
            tp = price + (abs(price - sl) * rr)
        elif confirmations <= 1:
            direction = "Vente"
            rr = 1.5
            sl = price + (price * 0.003)
            tp = price - (abs(sl - price) * rr)
        else:
            return

        rr_calc = calculate_rr(tp, price, sl)

        send_alert(symbol, {
            "confiance": "⚡ Signal Scalping",
            "signal": direction,
            "entrée": round(price, 2),
            "tp": round(tp, 2),
            "sl": round(sl, 2),
            "rr": rr_calc,
            "horodatage": datetime.now().isoformat()
        })

        active_trades[symbol] = {
            "direction": direction,
            "tp": tp,
            "sl": sl,
            "entrée": price,
            "temps": datetime.now()
        }

    except Exception as e:
        print("Erreur scalping:", e)

# === CHECK TP/SL ===
def check_active_trades():
    for symbol, trade in list(active_trades.items()):
        try:
            current = fetch_price(symbol)
            direction = trade['direction']
            tp = trade['tp']
            sl = trade['sl']
            entry = trade['entrée']
            time_open = trade['temps']
            elapsed = datetime.now() - time_open
            minutes = int(elapsed.total_seconds() / 60)

            if direction == "Achat" and current >= tp:
                pips = round((tp - entry) * 10000)
                msg = f"✅ TP atteint sur {symbol} !\n+{pips} pips\n(⏱ {minutes} minutes)"
                send_telegram_message(msg)
                del active_trades[symbol]

            elif direction == "Achat" and current <= sl:
                pips = round((entry - sl) * 10000)
                msg = f"❌ SL touché sur {symbol} !\n-{pips} pips\n(⏱ {minutes} minutes)"
                send_telegram_message(msg)
                del active_trades[symbol]

            elif direction == "Vente" and current <= tp:
                pips = round((entry - tp) * 10000)
                msg = f"✅ TP atteint sur {symbol} !\n+{pips} pips\n(⏱ {minutes} minutes)"
                send_telegram_message(msg)
                del active_trades[symbol]

            elif direction == "Vente" and current >= sl:
                pips = round((sl - entry) * 10000)
                msg = f"❌ SL touché sur {symbol} !\n-{pips} pips\n(⏱ {minutes} minutes)"
                send_telegram_message(msg)
                del active_trades[symbol]

        except Exception as e:
            print(f"Erreur TP/SL {symbol}:", e)

# === RECAP HEBDOMADAIRE ===
def schedule_recap():
    global last_recap
    if datetime.now().weekday() == 6 and datetime.now().hour == 22:
        if not os.path.exists(LOG_FILE):
            return
        with open(LOG_FILE, 'r') as f:
            data = json.load(f)
        this_week = [t for t in data if datetime.fromisoformat(t['horodatage']) >= datetime.now() - timedelta(days=7)]
        if not this_week:
            return

        wins = [t for t in this_week if t['résultat'] == 'TP']
        losses = [t for t in this_week if t['résultat'] == 'SL']
        winrate = round(len(wins) / len(this_week) * 100, 2)
        best = max(this_week, key=lambda x: x['pips'])
        worst = min(this_week, key=lambda x: x['pips'])

        msg = f"📊 *Récap de la semaine*\n\n"
        msg += f"📈 TP : {len(wins)}\n"
        msg += f"📉 SL : {len(losses)}\n"
        msg += f"🏆 Winrate : {winrate}%\n"
        msg += f"💚 Best : {best['symbole']} +{best['pips']} pips\n"
        msg += f"💔 Worst : {worst['symbole']} -{abs(worst['pips'])} pips"

        send_telegram_message(msg)
        last_recap = datetime.now().date()

# === LANCEMENT ===
def run_bot():
    threading.Thread(target=schedule_recap, daemon=True).start()
    send_telegram_message("✅ Bot d'alerte lancé avec succès.")
    while True:
        check_market()
        check_active_trades()
        time.sleep(SCAN_INTERVAL)

def check_market():
    for symbol in SYMBOLS:
        detect_signal_classique(symbol)
        detect_signal_scalping(symbol)

if __name__ == '__main__':
    run_bot()

