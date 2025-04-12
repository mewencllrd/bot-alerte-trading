import requests
import os

# 🧠 Variables d'environnement pour garder ton token et chat_id secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_signal_alert(type_signal="long", niveau="fiable", mode="classique"):
    """
    Envoie une alerte Telegram avec type de signal (long/short),
    niveau (fiable/modéré/pré-signal) et mode (classique/scalping)
    """
    emoji = "🔒" if niveau == "fiable" else "⚠️" if niveau == "modéré" else "🕵️"
    direction = "📈 Achat (Long)" if type_signal == "long" else "📉 Vente (Short)"
    mode_txt = "Mode scalping" if mode == "scalping" else "Mode classique"

    message = f"""{emoji} *Signal détecté*

{direction}
Confiance : *{niveau.upper()}*
{mode_txt}

🎯 TP et SL calculés automatiquement.
"""

    send_telegram_message(message)

def send_telegram_message(message):
    """
    Envoie un message brut au groupe Telegram via l'API Bot
    """
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
