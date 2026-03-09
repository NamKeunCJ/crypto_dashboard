import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.support_resistance import get_support_resistance_levels
import numpy as np

def graficar_plotly(df, symbol, interval="15m", length=20, multiplier=1.0, 
                    ultimo_cruce=None, tipo_cruce=None, validado=None, 
                    precio_objetivo=None, objetivo_alcanzado=None,
                    last_cross_idx=None, trend=None, entry=None,
                    stop_loss=None, targets=None, status=None):
    """
    Grafica velas japonesas, EMAs, volumen, cruces, soportes/resistencias,
    más ATR con líneas de Entry, SL y Targets.
    """

    # === Volumen promedio y colores ===
    df["vol_sma"] = df["volume"].rolling(window=length).mean()
    colors = []
    for i in range(len(df)):
        esAlcista = df["close"].iloc[i] > df["open"].iloc[i]
        esBajista = df["close"].iloc[i] < df["open"].iloc[i]
        volumenGrande = df["volume"].iloc[i] > df["vol_sma"].iloc[i] * multiplier

        if volumenGrande and esAlcista:
            colors.append("yellow")
        elif volumenGrande and esBajista:
            colors.append("purple")
        else:
            colors.append("gray")

    # === Subplots ===
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{symbol} {interval} - Velas y EMAs", "Volumen", "ADX/DI")
    )


    # === Velas ===
    fig.add_trace(go.Candlestick(
        x=df["open_time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Velas"
    ), row=1, col=1)

    # === EMAs ===
    fig.add_trace(go.Scatter(
        x=df["open_time"], y=df["EMA10"],
        line=dict(color="blue", width=1.5),
        name="EMA10"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["open_time"], y=df["EMA55"],
        line=dict(color="orange", width=1.5),
        name="EMA55"
    ), row=1, col=1)

    # === Volumen ===
    fig.add_trace(go.Bar(
        x=df["open_time"], y=df["volume"],
        name="Volumen",
        marker_color=colors
    ), row=2, col=1)

    # === Línea promedio volumen ===
    fig.add_trace(go.Scatter(
        x=df["open_time"], y=df["vol_sma"],
        line=dict(color="white", width=2),
        name="Volumen Promedio"
    ), row=2, col=1)

    # === Cruce vertical ===
    if ultimo_cruce is not None:
        color = "lime" if tipo_cruce == "up" else "red"
        estilo = "solid" if validado else "dot"

        #
        fig.add_vline(
            x=ultimo_cruce,
            line=dict(color=color, dash=estilo, width=2),
            row=1, col=1
        )


    # === Objetivo clásico ===
    if precio_objetivo is not None:
        color_obj = "white" if objetivo_alcanzado else "yellow"
        texto_obj = "🎯 Objetivo alcanzado ✅" if objetivo_alcanzado else "🎯 Objetivo pendiente ⏳"
        fig.add_hline(
            y=precio_objetivo,
            line=dict(color=color_obj, dash="dot", width=2),
            row=1, col=1
        )
        fig.add_annotation(
            x=df["open_time"].iloc[-1],
            y=precio_objetivo,
            text=f"{texto_obj}: {precio_objetivo:.2f}",
            showarrow=False,
            xanchor="left",
            font=dict(color=color_obj, size=12)
        )

    # === Soportes y resistencias ===
    levels = get_support_resistance_levels(df)
    last_close = df["close"].iloc[-1]
    for lvl in levels:
        color = "green" if last_close >= lvl else "red"
        fig.add_hline(
            y=lvl,
            line=dict(color=color, width=1, dash="dot"),
            annotation_text=f"{lvl:.2f}",
            annotation_position="right",
            annotation_font=dict(color=color, size=10)
        )

    # === ATR: Entry, SL y Targets ===
    if last_cross_idx is not None and entry is not None and stop_loss is not None and targets is not None:
        x_start = df["open_time"].iloc[last_cross_idx]
        x_end = df["open_time"].iloc[min(last_cross_idx+20, len(df)-1)]#### linea de tps sl y en a 20 velas  despues del cruce

        def add_line_with_label(y, color, name):
            fig.add_trace(go.Scatter(
                x=[x_start, x_end], y=[y, y],
                mode="lines",
                line=dict(color=color, width=2, dash="dot"),
                name=name
            ))
            fig.add_annotation(
                x=x_end, y=y,
                text=f"{name}: {y:.2f} {status.get(name,'') if status else ''}",
                showarrow=False,
                font=dict(color=color, size=12),
                align="left", xanchor="left"
            )

        # Entry
        add_line_with_label(entry, "blue", "BE")
        # Stop Loss
        add_line_with_label(stop_loss, "red", "SL")
        # Targets
        target_colors = ["lightgreen", "orange", "deepskyblue"]
        for i, t in enumerate(targets, start=1):
            add_line_with_label(t, target_colors[i-1], f"TP{i}")

# ===============================
# # === ADX y DI ===
# ===============================    
    
    # === ADX y DI dinámicos ===
    if "adx" in df and "plus_di" in df and "minus_di" in df:
        adx_normal, adx_yellow, adx_violet = [], [], []

        for i in range(len(df)):
            adx_val = df["adx"].iloc[i]
            plus_di = df["plus_di"].iloc[i]
            minus_di = df["minus_di"].iloc[i]

            if adx_val >= 23 and plus_di > adx_val:
                adx_yellow.append(adx_val)
                adx_violet.append(None)
                adx_normal.append(None)
            elif adx_val >= 23 and minus_di > adx_val:
                adx_violet.append(adx_val)
                adx_yellow.append(None)
                adx_normal.append(None)
            else:
                adx_normal.append(adx_val)
                adx_yellow.append(None)
                adx_violet.append(None)

        # Graficar series de ADX
        fig.add_trace(go.Scatter(
            x=df["open_time"], y=adx_normal,
            line=dict(color="blue", width=2),
            name="ADX"
        ), row=3, col=1)

        fig.add_trace(go.Scatter(
            x=df["open_time"], y=adx_yellow,
            line=dict(color="yellow", width=2),
            name="ADX Alcista fuerte"
        ), row=3, col=1)

        fig.add_trace(go.Scatter(
            x=df["open_time"], y=adx_violet,
            line=dict(color="violet", width=2),
            name="ADX Bajista fuerte"
        ), row=3, col=1)

        # Graficar DI+ y DI-
        fig.add_trace(go.Scatter(
            x=df["open_time"], y=df["plus_di"],
            line=dict(color="green", width=1.5),
            name="+DI"
        ), row=3, col=1)

        fig.add_trace(go.Scatter(
            x=df["open_time"], y=df["minus_di"],
            line=dict(color="red", width=1.5),
            name="-DI"
        ), row=3, col=1)

        # Línea horizontal en ADX = 23
        fig.add_hline(
            y=23,
            line=dict(color="white", dash="dot", width=1),
            row=3, col=1
        )

        # === Último valor y cuadro dinámico ===
        last_time = df["open_time"].iloc[-1]
        last_adx = df["adx"].iloc[-1]
        last_plus = df["plus_di"].iloc[-1]
        last_minus = df["minus_di"].iloc[-1]

        # Color del texto
        if np.isnan(last_adx):
            adx_text_color = "white"
        elif last_adx >= 23:
            adx_text_color = "yellow"
        elif 15 <= last_adx < 23:
            adx_text_color = "lightskyblue"
        else:
            adx_text_color = "white"

        # Color del fondo
        if np.isnan(last_adx) or np.isnan(last_plus) or np.isnan(last_minus):
            adx_bg_color = "rgba(30,30,30,0.9)"
        elif last_adx >= 23:
            if last_plus > last_minus:
                adx_bg_color = "rgba(0,128,0,0.7)" if last_plus >= last_adx else "rgba(144,238,144,0.7)"
            elif last_minus > last_plus:
                adx_bg_color = "rgba(255,0,0,0.7)" if last_minus >= last_adx else "rgba(255,182,193,0.7)"
            else:
                adx_bg_color = "rgba(128,128,128,0.9)"
        else:
            adx_bg_color = "black"

        # Anotación del último valor ADX
        fig.add_annotation(
            x=last_time,
            y=last_adx,
            text=f"{last_adx:.2f}",
            showarrow=True,
            arrowhead=2,
            ax=40, ay=-30,
            font=dict(color="white", size=12),
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor="white",
            row=3, col=1
        )

        # Cuadro flotante
        fig.add_annotation(
            xref="paper", yref="paper",
            x=1, y=0.17,# Cordenada posicion del cuadro ADX
            text=f"<b>ADX: {last_adx:.2f}</b>",
            showarrow=False,
            font=dict(size=14, color=adx_text_color),
            align="left",
            bgcolor=adx_bg_color,
            bordercolor="white",
            borderwidth=1,
            borderpad=6
        )


#============================
    # === Layout ===
    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=1100,  # más alto para meter ADX
        title=f"{symbol} {interval} - Velas, EMAs, Volumen, SR, ATR y ADX/DI"
    )


    return fig
