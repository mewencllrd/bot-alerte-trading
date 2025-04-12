from indicators import get_bitget_ohlcv, detect_classic_signal, detect_scalping_signal
from telegram_bot import send_signal_alert
import time

def launch_price_check_loop():
    print("🔍 Lancement de la surveillance des prix...")
    last_signal = None

    while True:
        df = get_bitget_ohlcv()
        signal_classic = detect_classic_signal(df)
        signal_scalping = detect_scalping_signal(df)

        last_price = df["close"].iloc[-1]
        atr = df["atr"].iloc[-1] if "atr" in df.columns else None

        if signal_classic and signal_classic != last_signal:
            send_signal_alert(type_signal=signal_classic, niveau="fiable", mode="classique", price=last_price, atr=atr)
            last_signal = signal_classic

        if signal_scalping and signal_scalping != last_signal:
            send_signal_alert(type_signal=signal_scalping, niveau="fiable", mode="scalping", price=last_price, atr=atr)
            last_signal = signal_scalping

        time.sleep(60)


