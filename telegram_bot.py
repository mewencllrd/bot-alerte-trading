import requests
import os

# 🌺 Variables d’environnement
TELEGRAM_TOKEN = os.getenv("8508078976:AAEu6HHh7UtnSgVvzy0zUIa_TrpcuT4IP10")
TELEGRAM_CHAT_ID = os.getenv("-1002516223605")


def send_signal_alert(type_signal="long", niveau="fiable", mode="classique"):
    """
    Envoie une alerte Telegram avec type de signal (long/short),
    niveau (fiable/modéré/pré-signal) et mode (classique/scalping)
    """
    emoji = "🔒" if niveau == "fiable" else "⚠️" if niveau == "modéré" else "🟠"
    direction = "🟦 Achat (Long)" if type_signal == "long" else "🟥 Vente (Short)"
    mode_txt = "Mode scalping" if mode == "scalping" else "Mode classique"

    message = f"""**{emoji} Signal détecté**

{direction}
Confiance : *{niveau.upper()}*
{mode_txt}

🎯 TP et SL calculés automatiquement.
"""
    send_telegram_message(message)


def send_telegram_message(message):
    """
    Envoie un message brut au groupe Telegram via l’API Bot
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

def start_bot():
    print("🤖 Bot Telegram en cours de démarrage...")

    from price_tracker import launch_price_check_loop
    launch_price_check_loop()
