import pandas as pd

def pivot_high(series, left, right):
    res = [None] * len(series)
    for i in range(left, len(series) - right):
        if series[i] == max(series[i-left:i+right+1]):
            res[i] = series[i]
    return res

def pivot_low(series, left, right):
    res = [None] * len(series)
    for i in range(left, len(series) - right):
        if series[i] == min(series[i-left:i+right+1]):
            res[i] = series[i]
    return res

def get_support_resistance_levels(df, left=20, right=10, quick_right=3, max_levels=6, gap=0.01, window_pct=0.15):
    """
    Calcula niveles de soporte/resistencia importantes.
    - gap: mínima distancia entre niveles (ej. 0.01 = 1%)
    - window_pct: rango relativo al precio actual donde buscar niveles
    - max_levels: máximo de niveles a mostrar
    """
    df = df.copy()
    df["pivot_high"] = pivot_high(df["high"], left, right)
    df["pivot_low"]  = pivot_low(df["low"], left, right)
    df["quick_pivot_high"] = pivot_high(df["high"], left, quick_right)
    df["quick_pivot_low"]  = pivot_low(df["low"], left, quick_right)

    # Extraer niveles
    levels = []
    for col in ["quick_pivot_high","quick_pivot_low","pivot_high","pivot_low"]:
        vals = df[col].dropna().tolist()
        levels.extend(vals)

    last_close = df["close"].iloc[-1]

    # Ordenar y limpiar duplicados cercanos
    levels = sorted(set(levels))
    filtered = []
    for lvl in levels:
        if not filtered or abs(lvl - filtered[-1]) / filtered[-1] > gap:
            filtered.append(lvl)

    # Solo niveles cercanos al precio actual
    filtered = [lvl for lvl in filtered if abs(lvl - last_close)/last_close < window_pct]

    # Tomar los más cercanos
    important = sorted(filtered, key=lambda x: abs(x-last_close))[:max_levels]

    return important
