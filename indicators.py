import ccxt
import pandas as pd
import merci

# === MODE CLASSIQUE ===
def detect_classic_signal(df):
    """
    Détection de signaux pour le mode classique (SSL Hybrid, MACD, Price Action...)
    Délais utilisés : M15, M30, H1
    """
    df['ema_50'] = merci.tendance.ema_indicator(df['close'], window=50)
    df['ema_200'] = merci.tendance.ema_indicator(df['close'], window=200)

    macd = merci.tendance.macd_diff(df['close'])
    df['macd_hist'] = macd

    signal_long = (
        df['close'].iloc[-1] > df['ema_50'].iloc[-1] > df['ema_200'].iloc[-1] and
        df['macd_hist'].iloc[-1] > 0
    )

    signal_short = (
        df['close'].iloc[-1] < df['ema_50'].iloc[-1] < df['ema_200'].iloc[-1] and
        df['macd_hist'].iloc[-1] < 0
    )

    if signal_long:
        return "long"
    elif signal_short:
        return "short"
    else:
        return "none"

# === MODE SCALPING RAPIDE ===
def detect_scalping_signal(df):
    """
    Détection de signaux pour le scalping rapide
    Indicateurs : Supertend, VWAP, Stoch RSI
    Délais utilisés : M1, M5, M10
    """
    # Stoch RSI
    stoch_k = merci.élan.stochrsi_k(df['close'])
    stoch_d = merci.élan.stochrsi_d(df['close'])

    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d

    # VWAP approximation avec cumulation volume
    df['VWAP'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()

    # Supertendance
    high = df['high']
    low = df['low']
    close = df['close']
    supertrend = merci.tendance.STC(close=close, fillna=True)
    df['Supertrend'] = supertrend

    signal_long = (
        df['close'].iloc[-1] > df['VWAP'].iloc[-1] and
        df['stoch_k'].iloc[-1] > df['stoch_d'].iloc[-1] and
        df['Supertrend'].iloc[-1] > df['Supertrend'].iloc[-2]
    )

    signal_short = (
        df['close'].iloc[-1] < df['VWAP'].iloc[-1] and
        df['stoch_k'].iloc[-1] < df['stoch_d'].iloc[-1] and
        df['Supertrend'].iloc[-1] < df['Supertrend'].iloc[-2]
    )

    if signal_long:
        return "long"
    elif signal_short:
        return "short"
    else:
        return "none"
