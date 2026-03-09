import pandas as pd

def ema(series, period):
    """
    Calcula la Media Móvil Exponencial (EMA).
    """
    return series.ewm(span=period, adjust=False).mean()

def sma(series, period):
    """
    Calcula la Media Móvil Simple (SMA).
    """
    return series.rolling(window=period).mean()
