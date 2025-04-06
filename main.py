# === IMPORTATIONS ===
import ccxt
import time
import pandas as pd
import requests
import ta
from datetime import datetime
import schedule
import threading

# === CONFIGURATION ===
TELEGRAM_TOKEN = "TON_TOKEN"
TELEGRAM_CHAT_ID = -1002516223605
SYMBOLS = ["BTC/USDT", "ETH/USDT"]
SCAN_INTERVAL = 60

exchange = ccxt.binance()
active_trades = {}
trade_history = []

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
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, data=data)
        print("📤 Envoi Telegram...")  # ← Affiche que ça tente l'envoi
        print("📨 Contenu :", data)  # ← Vérifie bien le message et le chat ID
        print("🧾 Réponse Telegram :", response.text)  # ← Réponse complète JSON
        return response.json()
    except Exception as e:
        print("❌ Erreur lors de l'envoi Telegram :", e)
        return None
    response = requests.post(url, data=data)
    print("Réponse Telegram :", response.text)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=data)
    print("🔧 Réponse Telegram :", response.status_code, response.text)

def send_alert(symbol, data):
    message = f"{data['confidence']}\n"
    message += f"💰 *Crypto* : {symbol}\n"
    message += f"📈 *Direction* : {data['signal']}\n"
    message += f"🎯 *Prix d\'entrée* : {round(data['entry'], 2)}\n"
    message += f"🎯 TP : {round(data['tp'], 2)}\n"
    message += f"🛡️ SL : {round(data['sl'], 2)}\n"
    message += f"🕓 Timeframe : {data['timeframe']}"
    send_telegram_message(message)
    active_trades[symbol] = {
        "entry": data['entry'], "tp": data['tp'], "sl": data['sl'],
        "direction": data['signal'], "start_time": datetime.now()
    }

# === SUIVI TP / SL ===
def check_active_trades():
    to_remove = []
    for symbol, trade in active_trades.items():
        price = fetch_price(symbol)
        if trade['direction'] == "Achat":
            if price >= trade['tp']:
                duration = datetime.now() - trade['start_time']
                send_telegram_message(f"✅ TP atteint sur {symbol} (+{round(trade['tp'] - trade['entry'], 2)} pts)\n⏱️ Durée : {duration}")
                to_remove.append(symbol)
                trade_history.append("TP")
            elif price <= trade['sl']:
                duration = datetime.now() - trade['start_time']
                send_telegram_message(f"❌ SL touché sur {symbol} (-{round(trade['entry'] - trade['sl'], 2)} pts)\n⏱️ Durée : {duration}")
                to_remove.append(symbol)
                trade_history.append("SL")
        else:
            if price <= trade['tp']:
                duration = datetime.now() - trade['start_time']
                send_telegram_message(f"✅ TP atteint sur {symbol} (+{round(trade['entry'] - trade['tp'], 2)} pts)\n⏱️ Durée : {duration}")
                to_remove.append(symbol)
                trade_history.append("TP")
            elif price >= trade['sl']:
                duration = datetime.now() - trade['start_time']
                send_telegram_message(f"❌ SL touché sur {symbol} (-{round(trade['sl'] - trade['entry'], 2)} pts)\n⏱️ Durée : {duration}")
                to_remove.append(symbol)
                trade_history.append("SL")
    for symbol in to_remove:
        del active_trades[symbol]

# === RECAP HEBDOMADAIRE ===
def weekly_recap():
    total = len(trade_history)
    tp = trade_history.count("TP")
    sl = trade_history.count("SL")
    wr = round((tp / total) * 100, 2) if total > 0 else 0
    recap = f"📊 *Récapitulatif Hebdomadaire*\nTotal trades : {total}\n✅ TP : {tp}\n❌ SL : {sl}\n🎯 Winrate : {wr}%"
    send_telegram_message(recap)

def schedule_recap():
    schedule.every().sunday.at("22:00").do(weekly_recap)
    while True:
        schedule.run_pending()
        time.sleep(30)

# === BOT CLASSIQUE ===
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

# === SCALPING ===
def compute_scalping_indicators(df):
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['stoch_rsi'] = (df['rsi'] - df['rsi'].rolling(14).min()) / (df['rsi'].rolling(14).max() - df['rsi'].rolling(14).min())
    df['supertrend'] = (df['high'] + df['low']) / 2
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

# === MAIN ===
def run_bot():
    threading.Thread(target=schedule_recap, daemon=True).start()
    send_telegram_message("✅ Bot d'alerte lancé avec succès.")
    while True:
        check_market()
        check_active_trades()
        for symbol in SYMBOLS:
            detect_signal_scalping(symbol)
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    print("🚀 Test d'envoi manuel...")
    send_telegram_message("✅ Test depuis Render - si tu lis ça, c’est que le bot fonctionne.")
    run_bot()
try:
    response = send_telegram_message("📢 Test Telegram depuis Render !")
    print("✅ Réponse Telegram :", response)
except Exception as e:
    print("❌ Erreur lors de l’envoi :", e)

