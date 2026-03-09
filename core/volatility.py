import pandas as pd
from ta.volatility import AverageTrueRange

def calcular_atr(df, window=200, factor=0.8):
    """
    Calcula el ATR (Average True Range) y lo agrega al DataFrame.
    Si el histórico es más corto que el window, ajusta automáticamente.
    """
    if len(df) < window:
        window = max(5, len(df) // 2)  # usa la mitad de velas disponibles, mínimo 5

    atr = AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=window
    )
    df["ATR"] = atr.average_true_range() * factor
    return df

def calcular_sl_targets(last_row, tp_multipliers=[3,6,9]):
    """
    Calcula Stop Loss y Targets a partir del último cruce y ATR.
    Retorna: trend, entry, stop_loss, targets
    """
    entry = last_row["close"]
    atr_val = last_row["ATR"]

    if last_row["EMA10"] > last_row["EMA55"]:  # Cruce alcista
        trend = "bullish"
        stop_loss = last_row["low"] - atr_val
        targets = [entry + atr_val * m for m in tp_multipliers]
    else:  # Cruce bajista
        trend = "bearish"
        stop_loss = last_row["high"] + atr_val
        targets = [entry - atr_val * m for m in tp_multipliers]

    return trend, entry, stop_loss, targets

def validar_trade(df, last_cross_idx, trend, entry, stop_loss, targets):
    """
    Valida si los TPs o SL fueron alcanzados después del cruce.
    Retorna un diccionario con el estado de cada TP y del SL.
    """
    future_df = df.iloc[last_cross_idx+1:]
    status = {f"TP{i}": "" for i in range(1, len(targets)+1)}
    status["SL"] = ""

    tp_reached = False
    trade_over = False

    for _, row in future_df.iterrows():
        high, low = row["high"], row["low"]

        if trend == "bullish":
            for i, t in enumerate(targets, start=1):
                if high >= t and status[f"TP{i}"] == "":
                    status[f"TP{i}"] = "✅"
                    tp_reached = True
            if low <= stop_loss:
                status["SL"] = "❌" if not tp_reached else "❌ (ignorado)"
                trade_over = True

        else:  # bearish
            for i, t in enumerate(targets, start=1):
                if low <= t and status[f"TP{i}"] == "":
                    status[f"TP{i}"] = "✅"
                    tp_reached = True
            if high >= stop_loss:
                status["SL"] = "❌" if not tp_reached else "❌ (ignorado)"
                trade_over = True

        if trade_over:
            break

    return status
