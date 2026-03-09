from core.fetch_data import get_binance_futures_klines
from core.indicators import ema
from core.logic import detectar_cruce, calcular_objetivo, calcular_metricas
from core.volatility import calcular_atr, calcular_sl_targets, validar_trade
from visuals.plot import graficar_plotly
from core.adx import calculate_adx


# Validaciones por timeframe
VALIDATION_THRESHOLDS = {
    "15m": 0.01,   # 1%
    "1h": 0.02,    # 2%
    "4h": 0.04,    # 4%
    "1d": 0.07     # 7%
}

# Lista de símbolos a analizar
SYMBOLS = ["BTCUSDT","XRPUSDT","SOLUSDT","DOGEUSDT","SUIUSDT"]

# === Análisis de un par ===
def analizar_par(symbol, interval="15m"):
    threshold = VALIDATION_THRESHOLDS[interval]
    df = get_binance_futures_klines(symbol=symbol, interval=interval, limit=300)

    # Calcular EMAs
    df["EMA10"] = ema(df["close"], 10)
    df["EMA55"] = ema(df["close"], 55)

    # Detectar cruce
    ultimo_cruce, tipo_cruce, precio_entrada, idx = detectar_cruce(df)

    # Validar cruce y calcular objetivo
    validado, precio_objetivo, objetivo_alcanzado = calcular_objetivo(
        df, idx, tipo_cruce, threshold, precio_entrada
    )

    # Calcular métricas adicionales
    volatilidad_24h, cercania_velas, ema_diff = calcular_metricas(df, idx)

    # === Nuevo: ADX / +DI / -DI ===
    df["plus_di"], df["minus_di"], df["adx"] = calculate_adx(df, period=14)
    adx_last = float(df["adx"].iloc[-1]) if not df["adx"].empty else None
    plus_last = float(df["plus_di"].iloc[-1]) if not df["plus_di"].empty else None
    minus_last = float(df["minus_di"].iloc[-1]) if not df["minus_di"].empty else None


    # Calcular ATR + SL + Targets
    df = calcular_atr(df, window=200, factor=0.8)
    trend, entry, stop_loss, targets = None, None, None, None
    status = {}
    if idx is not None:
        last_row = df.loc[idx]
        trend, entry, stop_loss, targets = calcular_sl_targets(last_row)
        status = validar_trade(df, idx, trend, entry, stop_loss, targets)
      

    return (
        df,
        ultimo_cruce,
        tipo_cruce,
        validado,
        precio_objetivo,
        objetivo_alcanzado,
        volatilidad_24h,
        cercania_velas,
        ema_diff,
        idx,
        trend,
        entry,
        stop_loss,
        targets,
        status,
        adx_last,
        plus_last,
        minus_last
    )

# === Modo script ===
if __name__ == "__main__":
    interval = "15m"

    for symbol in SYMBOLS:
        print(f"\n=== Analizando {symbol} {interval} ===")
        resultados = analizar_par(symbol, interval)
        (
            df, ultimo_cruce, tipo_cruce, validado,
            precio_objetivo, objetivo_alcanzado,
            volatilidad_24h, cercania_velas, ema_diff,
            idx, trend, entry, stop_loss, targets, status,
            adx_val, plus_di_val, minus_di_val
            
        ) = resultados

        if ultimo_cruce is not None:
            # Gráfico normal
                fig = graficar_plotly(
                    df, symbol, interval=interval,
                    ultimo_cruce=ultimo_cruce, tipo_cruce=tipo_cruce,
                    validado=validado, precio_objetivo=precio_objetivo,
                    objetivo_alcanzado=objetivo_alcanzado,
                    last_cross_idx=idx, trend=trend, entry=entry,
                    stop_loss=stop_loss, targets=targets, status=status
                )
                fig.show()

