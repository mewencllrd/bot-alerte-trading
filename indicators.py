import ccxt
import pandas as pd
import ta

# === MODE CLASSIQUE ===
def detect_classic_signal(df):
    """
    Détection de signaux pour le mode classique (SSL Hybrid, MACD, Price Action...)
    Timeframes utilisés : M15, M30, H1
    """
    df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['ema_200'] = ta.trend.ema_indicator(df['close'], window=200)

    macd = ta.trend.macd_diff(df['close'])
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
        return None


# === MODE SCALPING RAPIDE ===
def detect_scalping_signal(df):
    """
    Détection de signaux pour le scalping rapide
    Indicateurs : Supertrend, VWAP, Stoch RSI
    Timeframes utilisés : M1, M5, M10
    """
    # Stoch RSI
    stoch = ta.momentum.stochrsi_k(df['close'])
    stoch_d = ta.momentum.stochrsi_d(df['close'])

    df['stoch_k'] = stoch
    df['stoch_d'] = stoch_d

    # VWAP (approximation avec rolling VWAP sur la journée)
    df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()

    # Supertrend
    high = df['high']
    low = df['low']
    close = df['close']
    supertrend = ta.trend.stc(close=close, fillna=True)  # Approximation ST via STC
    df['supertrend'] = supertrend

    signal_long = (
        df['close'].iloc[-1] > df['vwap'].iloc[-1] and
        df['stoch_k'].iloc[-1] > df['stoch_d'].iloc[-1] and
        df['supertrend'].iloc[-1] > df['supertrend'].iloc[-2]
    )

    signal_short = (
        df['close'].iloc[-1] < df['vwap'].iloc[-1] and
        df['stoch_k'].iloc[-1] < df['stoch_d'].iloc[-1] and
        df['supertrend'].iloc[-1] < df['supertrend'].iloc[-2]
    )

    if signal_long:
        return "long"
    elif signal_short:
        return "short"
    else:
        return None
