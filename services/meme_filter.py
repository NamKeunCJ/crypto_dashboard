import requests
import pandas as pd

LIMIT = 20
MIN_VOLUME = 50_000_000

def get_active_symbols():
    """Obtiene lista de símbolos activos en Binance Futures."""
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    data = requests.get(url).json()
    activos = [s["symbol"] for s in data["symbols"] if s["status"] == "TRADING"]
    return set(activos)

def get_top_symbols(limit=LIMIT, min_volume=MIN_VOLUME):
    """
    Obtiene los símbolos más volátiles en 24h con volumen mínimo y que estén activos.
    Filtra solo pares con USDT, volumen alto y con histórico suficiente.
    """
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    data = requests.get(url).json()
    df = pd.DataFrame([data])

    # Conversión de tipos
    df["priceChangePercent"] = df["priceChangePercent"].astype(float)
    df["quoteVolume"] = df["quoteVolume"].astype(float)

    # Lista de activos válidos
    activos = get_active_symbols()

    # Filtrar: solo USDT, con volumen alto y activos
    df = df[(df["symbol"].str.endswith("USDT")) &
            (df["quoteVolume"] > min_volume) &
            (df["symbol"].isin(activos))]

    # ⚡ Extra: descartar monedas sospechosamente nuevas (sin trades reales)
    df = df[df["count"].astype(int) > 1000]  # requiere al menos 1000 trades en 24h

    # Ordenar por % cambio en 24h
    top = df.sort_values("priceChangePercent", ascending=False).head(limit)
    return top["symbol"].tolist()
