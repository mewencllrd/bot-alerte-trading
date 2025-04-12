import time
from indicators import detect_classic_signal, detect_scalping_signal
from telegram_bot import send_signal_alert

def launch_price_check_loop():
    print("🔍 Lancement de la surveillance des prix...")

    last_signal_sent = None

    while True:
        # --- Simule les données des indicateurs (à remplacer plus tard par vraies valeurs) ---
        classic_data = {
            "ssl_hybrid": True,
            "macd_mtf": True,
            "price_action": True,
        }

        scalping_data = {
            "qqe": True,
            "stoch_rsi": False,
            "volume_oscillator": True,
        }

        # --- Analyse des signaux ---
        classic_signal = detect_classic_signal(classic_data)
        scalping_signal = detect_scalping_signal(scalping_data)

        # --- Envoi Telegram si un nouveau signal détecté ---
        if classic_signal and last_signal_sent != classic_signal:
            send_signal_alert(
                type_signal="long",
                niveau=classic_signal,
                mode="classique"
            )
            last_signal_sent = classic_signal

        elif scalping_signal and last_signal_sent != scalping_signal:
            send_signal_alert(
                type_signal="short",
                niveau=scalping_signal,
                mode="scalping"
            )
            last_signal_sent = scalping_signal

        time.sleep(60)  # scan toutes les 60 secondes
