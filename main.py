import requests
import time
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta
import json
import os

# Configuration de base
TOKEN = "8050078976:AAEu6HHh7UtnSgVvzy0zUIa_TprcuT4IP10"
CHAT_ID = "-1002516223605"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT"]
INTERVAL = "15m"
LIMIT = 100
LOG_FILE = "trade_log.json"

sent_alerts = {}
active_trades = {}

# Fonction d'envoi de message Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=data)
    print("Message envoyé ! Réponse :", response.text)

# Fonction pour calculer TP/SL selon RR
def calculate_tp_sl(entry, sl, rr=2.0):
    risk = abs(entry - sl)
    if entry > sl:
        tp = round(entry + (risk * rr), 4)
    else:
        tp = round(entry - (risk * rr), 4)
    return tp, sl

# Fonction de détection de signal et de confiance
def detect_signal(df):
    close = df["close"]
    ema50 = EMAIndicator(close, window=50).ema_indicator()
    ema200 = EMAIndicator(close, window=200).ema_indicator()
    rsi = RSIIndicator(close, window=14).rsi()
    macd = MACD(close).macd_diff()

    indicators = {
        "ema": ema50.iloc[-1] > ema200.iloc[-1],
        "rsi": rsi.iloc[-1] > 50,
        "macd": macd.iloc[-1] > 0,
        "price_action": close.iloc[-1] > close.iloc[-2]
    }

    score = sum(indicators.values())
    if score == 4:
        level = "🔒 Signal très fiable"
        rr = 2.5
    elif score == 3:
        level = "⚠️ Signal modéré"
        rr = 2.0
    else:
        return None, None, None, None, None, None, None

    direction = "Long" if indicators["ema"] and indicators["macd"] else "Short"
    entry = close.iloc[-1]

    if direction == "Long":
        sl = df["low"].iloc[-5:-1].min()
    else:
        sl = df["high"].iloc[-5:-1].max()

    tp, sl = calculate_tp_sl(entry, sl, rr)
    return level, direction, entry, tp, sl, rr, datetime.now()

# Fonction pour enregistrer un trade dans le fichier log
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
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
    else:
        data = []
    data.append(trade)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Vérifie si un trade actif a atteint TP ou SL
def check_active_trades():
    for symbol, trade in list(active_trades.items()):
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url)
            price = float(response.json()["price"])
            direction = trade['direction']
            tp = trade['tp']
            sl = trade['sl']
            entry = trade['entry']
            time_opened = trade['time']

            now = datetime.now()
            elapsed = now - time_opened
            minutes = int(elapsed.total_seconds() // 60)
            hours = minutes // 60
            mins = minutes % 60
            time_str = f"⏱ Temps écoulé : {hours}h{mins:02}min" if hours else f"⏱ Temps écoulé : {mins} minutes"

            if direction == "Long" and price >= tp:
                pips = round((tp - entry) * 10000)
                msg = f"✅ TP atteint sur {symbol} !\n+{pips} pips\n\n{time_str}"
                send_telegram_message(msg)
                log_trade(symbol, direction, entry, tp, sl, "TP", pips, time_str)
                del active_trades[symbol]
            elif direction == "Long" and price <= sl:
                pips = round((entry - sl) * 10000)
                msg = f"❌ SL touché sur {symbol}\n-{pips} pips\n\n{time_str}"
                send_telegram_message(msg)
                log_trade(symbol, direction, entry, tp, sl, "SL", -pips, time_str)
                del active_trades[symbol]
            elif direction == "Short" and price <= tp:
                pips = round((entry - tp) * 10000)
                msg = f"✅ TP atteint sur {symbol} !\n+{pips} pips\n\n{time_str}"
                send_telegram_message(msg)
                log_trade(symbol, direction, entry, tp, sl, "TP", pips, time_str)
                del active_trades[symbol]
            elif direction == "Short" and price >= sl:
                pips = round((sl - entry) * 10000)
                msg = f"❌ SL touché sur {symbol}\n-{pips} pips\n\n{time_str}"
                send_telegram_message(msg)
                log_trade(symbol, direction, entry, tp, sl, "SL", -pips, time_str)
                del active_trades[symbol]

        except Exception as e:
            print(f"Erreur de vérification du TP/SL pour {symbol} :", e)

# Récap hebdomadaire
last_recap = None

def weekly_recap():
    global last_recap
    now = datetime.now()
    if now.weekday() == 6 and now.hour == 22 and (not last_recap or last_recap.date() != now.date()):
        if not os.path.exists(LOG_FILE):
            return
        with open(LOG_FILE, "r") as f:
            data = json.load(f)

        this_week = [t for t in data if datetime.fromisoformat(t["timestamp"]) >= now - timedelta(days=7)]
        if not this_week:
            return

        total = len(this_week)
        wins = len([t for t in this_week if t["result"] == "TP"])
        losses = len([t for t in this_week if t["result"] == "SL"])
        winrate = round((wins / total) * 100, 2)

        best = max(this_week, key=lambda x: x["pips"])
        worst = min(this_week, key=lambda x: x["pips"])

        message = f"📊 *Récapitulatif de la semaine* :\n\n"
        message += f"✅ Signaux envoyés : {total}\n"
        message += f"📈 TP atteints : {wins}\n"
        message += f"📉 SL touchés : {losses}\n"
        message += f"🏆 Win Rate : {winrate}%\n"
        message += f"🔔 Meilleur trade : {best['symbol']} {best['pips']} pips\n"
        message += f"💥 Pire trade : {worst['symbol']} {worst['pips']} pips"

        send_telegram_message(message)
        last_recap = now

# Fonction principale
print("\nBot de détection de signaux lancé...")

def check_market():
    base_url = "https://api.binance.com/api/v3/klines"
    for symbol in SYMBOLS:
        try:
            params = {"symbol": symbol, "interval": INTERVAL, "limit": LIMIT}
            response = requests.get(base_url, params=params)
            if response.status_code != 200:
                print(f"Erreur API pour {symbol}")
                continue

            data = response.json()
            df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume",
                                              "close_time", "quote_asset_volume", "num_trades",
                                              "taker_buy_base", "taker_buy_quote", "ignore"])
            df["close"] = df["close"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)

            level, direction, entry, tp, sl, rr, timestamp = detect_signal(df)

            if level:
                alert_id = f"{symbol}_{direction}_{round(entry, 2)}"
                if alert_id in sent_alerts:
                    print(f"Signal déjà envoyé pour {symbol} ({direction})")
                    continue
                sent_alerts[alert_id] = True

                message = (
                    f"{level}\n\n"
                    f"💰 *Crypto* : {symbol}\n"
                    f"📈 Direction : {direction}\n"
                    f"💵 Prix d'entrée : {entry}\n"
                    f"🎯 TP : {tp}\n"
                    f"🛡 SL : {sl}\n"
                    f"📏 RR : {round(abs(tp - entry) / abs(entry - sl), 2)}"
                )
                send_telegram_message(message)

                active_trades[symbol] = {
                    "direction": direction,
                    "entry": entry,
                    "tp": tp,
                    "sl": sl,
                    "time": timestamp
                }
            else:
                print(f"Aucun signal valide pour {symbol}")

        except Exception as e:
            print(f"Erreur analyse {symbol} :", e)

# Boucle infinie
send_telegram_message("✅ Test manuel depuis Render !")
while True:
    check_market()
    check_active_trades()
    weekly_recap()
    time.sleep(60)
    # 🔧 TEST MANUEL - à retirer après
send_alert("BTCUSDT", {
    "confidence": "🔒 Signal très fiable",
    "signal": "Achat",
    "entry": 83000,
    "tp": 84600,
    "sl": 82100,
    "timeframe": "M15"
})

