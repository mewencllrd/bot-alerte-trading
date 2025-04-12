import requests
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_signal_alert(type_signal="long", niveau="fiable", mode="classique", price=None, atr=None):
    emoji = "🔒" if niveau == "fiable" else "⚠️" if niveau == "modéré" else "❓"
    direction = "📈 Achat (Long)" if type_signal == "long" else "📉 Vente (Short)"
    mode_txt = "Mode scalping 🧠" if mode == "scalping" else "Mode classique 🧘"

    if price and atr:
        sl = price - atr if type_signal == "long" else price + atr
        tp = price + (atr * 1.8) if type_signal == "long" else price - (atr * 1.8)
        tp = round(tp, 2)
        sl = round(sl, 2)
        price = round(price, 2)
        message = f"""{emoji} *Signal détecté*

{direction}
Confiance : *{niveau.upper()}*
{mode_txt}

🎯 Entrée : {price} $
🟢 TP : {tp} $
🔴 SL : {sl} $
"""
    else:
        message = f"""{emoji} *Signal détecté*

{direction}
Confiance : *{niveau.upper()}*
{mode_txt}

🔁 TP et SL calculés automatiquement.
"""

    send_telegram_message(message)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print("❌ Erreur envoi Telegram :", response.text)
    except Exception as e:
        print("❌ Exception envoi Telegram :", str(e))
