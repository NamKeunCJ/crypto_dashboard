# core/adx.py
import pandas as pd
import numpy as np
from typing import Tuple

def wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """
    Suavizado al estilo Wilder usando ewm alpha=1/period (mismo enfoque que TradingView).
    """
    return series.ewm(alpha=1/period, adjust=False).mean()

def calculate_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Recibe un DataFrame con columnas 'high','low','close' y devuelve (plus_di, minus_di, adx)
    como pd.Series alineadas con df.index.
    """
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    up_move = high.diff()
    down_move = low.shift() - low

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # evitar división por cero
    atr = wilder_smooth(tr, period).replace(0, np.nan)

    plus_di = 100 * (wilder_smooth(plus_dm, period) / atr)
    minus_di = 100 * (wilder_smooth(minus_dm, period) / atr)

    dx = ( (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) ) * 100
    adx = wilder_smooth(dx.fillna(0), period)

    # devolver series sin NaN molestos (las primeras filas pueden ser 0)
    return plus_di.fillna(0), minus_di.fillna(0), adx.fillna(0)
