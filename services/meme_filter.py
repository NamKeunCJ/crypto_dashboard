import requests
import pandas as pd

LIMIT = 20
MIN_VOLUME = 50_000_000

def get_active_symbols():
    """Obtiene lista de símbolos activos en Binance Futures."""
    url = "https://api.binance.com/api/v3/exchangeInfo"
    data = requests.get(url).json()
    activos = [s["symbol"] for s in data["symbols"] if s["status"] == "TRADING"]
    return set(activos)

def get_top_symbols(limit=LIMIT, min_volume=MIN_VOLUME):
    """
    Obtiene los símbolos más volátiles en 24h con volumen mínimo y que estén activos.
    Filtra solo pares con USDT, volumen alto y con histórico suficiente.
    """
    url = "https://api.binance.com/api/v3/ticker/24hr"
    response = requests.get(url, timeout=10)
    data = response.json()
    
    # validar respuesta de la API
    if not isinstance(data, list):
        print("Binance API error:", data)
        return []
    
    df = pd.DataFrame(data)

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
