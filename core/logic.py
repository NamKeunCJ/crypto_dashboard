import pandas as pd

# ===============================
# Detectar último cruce EMA10 vs EMA55
# ===============================
def detectar_cruce(df):
    """
    Busca el último cruce entre EMA10 y EMA55.
    Retorna: (time, tipo, precio_entrada, idx)
    """
    df["cruce_up"] = (df["EMA10"].shift(1) < df["EMA55"].shift(1)) & (df["EMA10"] >= df["EMA55"])
    df["cruce_down"] = (df["EMA10"].shift(1) > df["EMA55"].shift(1)) & (df["EMA10"] <= df["EMA55"])

    ultimo_cruce, tipo_cruce, precio_entrada, idx = None, None, None, None
    for i in range(len(df)-1, -1, -1):
        if df.loc[i, "cruce_up"]:
            return df.loc[i, "open_time"], "up", df.loc[i, "EMA10"], i
        elif df.loc[i, "cruce_down"]:
            return df.loc[i, "open_time"], "down", df.loc[i, "EMA10"], i

    return ultimo_cruce, tipo_cruce, precio_entrada, idx

# ===============================
# Validar cruce y calcular objetivo
# ===============================
def calcular_objetivo(df, idx, tipo, threshold, entry_price):
    """
    Valida si el precio alcanzó el objetivo tras el cruce.
    Retorna: (validado, precio_objetivo, objetivo_alcanzado)
    """
    if idx is None:
        return None, None, None

    posteriores = df.iloc[idx+1:]
    if tipo == "up":
        precio_objetivo = entry_price * (1 + threshold)
        validado = (posteriores["close"] >= precio_objetivo).any()
        objetivo_alcanzado = validado
    else:
        precio_objetivo = entry_price * (1 - threshold)
        validado = (posteriores["close"] <= precio_objetivo).any()
        objetivo_alcanzado = validado

    return validado, precio_objetivo, objetivo_alcanzado

# ===============================
# Calcular métricas adicionales
# ===============================
def calcular_metricas(df, idx):
    """
    Calcula volatilidad 24h, cercanía en velas desde el último cruce y diferencia EMA10/EMA55 en %.
    """
    # Volatilidad 24h = (max - min) / min * 100
    volatilidad_24h = ((df["high"].max() - df["low"].min()) / df["low"].min()) * 100

    # Cercanía en velas desde último cruce
    cercania_velas = (len(df) - 1 - idx) if idx is not None else None

    # Diferencia EMA10 vs EMA55 en %
    ema_diff = abs(df["EMA10"].iloc[-1] - df["EMA55"].iloc[-1]) / df["EMA55"].iloc[-1] * 100

    return volatilidad_24h, cercania_velas, ema_diff
