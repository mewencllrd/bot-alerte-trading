def detect_classic_signal(data):
    """
    Détection des signaux de trading en mode classique
    avec les indicateurs : SSL Hybrid, MACD MTF, Price Action.
    """
    ssl_hybrid = data.get("ssl_hybrid")
    macd_mtf = data.get("macd_mtf")
    price_action = data.get("price_action")

    # Comptage des signaux alignés
    score = 0
    if ssl_hybrid: score += 1
    if macd_mtf: score += 1
    if price_action: score += 1

    if score == 3:
        return "très_fiable"
    elif score == 2:
        return "modéré"
    elif score == 1:
        return "pré_signal"
    else:
        return None


def detect_scalping_signal(data):
    """
    Détection de signaux en mode scalping sur M1, M5, M10
    avec : QQE Mod, Stochastic RSI, Volume Oscillator.
    """
    qqe = data.get("qqe")
    stoch_rsi = data.get("stoch_rsi")
    volume = data.get("volume_oscillator")

    score = 0
    if qqe: score += 1
    if stoch_rsi: score += 1
    if volume: score += 1

    if score >= 2:
        return "scalping"
    else:
        return None
