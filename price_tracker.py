import time
from indicators import detect_classic_signal, detect_scalping_signal
from telegram_bot import send_signal_alert

def launch_price_check_loop():
    print("🔵 Lancement de la surveillance des prix...")

    last_signal_sent = None

    while True:
        # --- Données simulées des indicateurs (à remplacer plus tard par les vraies valeurs) ---

        classic_data = {
            "ssl_hybrid": True,
            "macd_mtf": True,
            "price_action": True
        }

        scalping_data = {
            "stoch_rsi": True,
            "vwap": True,
            "supertrend": True
        }

        # --- Analyse des signaux ---
        classic_signal = detect_classic_signal(classic_data)
        scalping_signal = detect_scalping_signal(scalping_data)

        print("🔍 Signal classique :", classic_signal)
        print("⚡ Signal scalping :", scalping_signal)

        # --- Envoi Telegram si un nouveau signal détecté ---
        if classic_signal != last_signal_sent and classic_signal is not None:
            send_signal_alert(
                type_signal="long" if classic_signal == "fiable" else "short",
                niveau=classic_signal,
                mode="classique"
            )
            last_signal_sent = classic_signal

        elif scalping_signal != last_signal_sent and scalping_signal is not None:
            send_signal_alert(
                type_signal="long" if scalping_signal == "fiable" else "short",
                niveau=scalping_signal,
                mode="scalping"
            )
            last_signal_sent = scalping_signal

        time.sleep(60)  # Scan toutes les 60 secondes

