import pandas as pd

def calcular_volumen(df, length=20, multiplier=1.0):
    """
    Calcula volumen promedio y clasifica colores según tendencia.
    Devuelve el DataFrame con columnas extra: vol_sma, color.
    """
    df = df.copy()
    df["vol_sma"] = df["volume"].rolling(length).mean()
    df["esAlcista"] = df["close"] > df["open"]
    df["esBajista"] = df["close"] < df["open"]
    df["volumenGrande"] = df["volume"] > (df["vol_sma"] * multiplier)

    def color_barras(row):
        if row["volumenGrande"] and row["esAlcista"]:
            return "yellow"
        elif row["volumenGrande"] and row["esBajista"]:
            return "purple"
        else:
            return "gray"

    df["color"] = df.apply(color_barras, axis=1)
    return df
