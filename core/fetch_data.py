import requests
import pandas as pd

def get_binance_futures_klines(symbol="BTCUSDT", interval="1h", limit=150):
    """
    Obtiene velas de Binance Futuros Perpetuos USDT-M y ajusta hora a zona local.
    Devuelve un DataFrame con columnas estándar (open_time, open, high, low, close, volume, etc.)
    """
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    data = requests.get(url, params=params).json()

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades",
        "taker_base_vol", "taker_quote_vol", "ignore"
    ])
    
    # Conversión de tipos numéricos
    df = df.astype(float, errors="ignore")

    # Conversión a hora local (Colombia)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_convert("America/Bogota")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True).dt.tz_convert("America/Bogota")

    return df
