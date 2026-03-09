import time
import os
import requests
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import plotly.graph_objects as go

from playwright.sync_api import sync_playwright

from main import analizar_par
from services.meme_filter import get_top_symbols
from visuals.plot import graficar_plotly



# ============================
# CONFIG TELEGRAM
# ============================
TELEGRAM_TOKEN = "7552415670:AAHDu8kkbycqToiQa4OLdqnDNKS9hmMvBhw"
CHAT_ID = "-1002630358496"

# Topics del grupo
TOPICS = {
    "15m": 824,
    "1h": 825,
    "4h": 826,
    "1d": 827
}


def enviar_telegram_png(png_bytes, caption, interval):
    """
    Envía la imagen al topic correcto según el timeframe.
    Si no hay topic, lo envía al GENERAL.
    """

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {"photo": ("chart.png", png_bytes)}

    data = {
        "chat_id": CHAT_ID,
        "caption": caption
    }

    # Asignar topic si existe
    if interval in TOPICS:
        data["message_thread_id"] = TOPICS[interval]

    try:
        requests.post(url, files=files, data=data)
        print(f"📤 Imagen enviada a Telegram → Topic {interval}")
    except Exception as e:
        print("⚠️ Error enviando a Telegram:", e)



# ============================
#  CAPTURA REAL CON PLAYWRIGHT
# ============================
def convertir_figura_a_png(fig, output_png="chart.png"):
    """
    Convierte figura Plotly a PNG EXACTO usando Chromium headless.
    REMUEVE BORDES, MÁRGENES Y AJUSTA A PANTALLA COMPLETA.
    """
    html = f"""
    <html>
    <head>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: black;
        }}
        #chart {{
            width: 100vw;
            height: 100vh;
            margin: 0;
            padding: 0;
        }}
    </style>
    </head>
    <body>
        <div id="chart">
            {fig.to_html(include_plotlyjs="cdn", full_html=False)}
        </div>
    </body>
    </html>
    """

    temp_html = "temp_plot.html"
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200})

        page.goto(f"file:///{os.path.abspath(temp_html)}", wait_until="networkidle")

        page.add_style_tag(content="""
            body {
                margin: 0 !important;
                padding: 0 !important;
                background: black !important;
            }
        """)

        page.screenshot(path=output_png, full_page=False)
        browser.close()

    with open(output_png, "rb") as f:
        png_bytes = f.read()

    try:
        os.remove(temp_html)
        os.remove(output_png)
    except:
        pass

    return png_bytes



# ============================
# CONFIG
# ============================
INTERVALS = ["15m", "1h", "4h", "1d"]

TOP_COINS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT",
    "FARTCOINUSDT","SUIUSDT","LTCUSDT","BNBUSDT"
]

MEME_COINS = get_top_symbols(limit=20)
SYMBOLS = list(dict.fromkeys(TOP_COINS + MEME_COINS))

YA_MOSTRADOS = set()
cola_capturas = Queue()

print("🔍 Worker iniciado — Capturas reales con PLAYWRIGHT...\n")



# ============================================================
#     FUNCION EN THREADS → SOLO DETECTA CRUCE
# ============================================================
def detectar_cruce(symbol, interval):

    try:
        (
            df, ultimo_cruce, tipo_cruce, validado,
            precio_objetivo, objetivo_alcanzado,
            volatilidad_24h, velas, ema_diff,
            idx, trend, entry, stop_loss,
            targets, status,
            adx, plus_di, minus_di
        ) = analizar_par(symbol, interval)

        if velas is None or velas > 3:
            return

        clave = f"{symbol}_{interval}"
        if clave in YA_MOSTRADOS:
            return

        YA_MOSTRADOS.add(clave)

        print(f"📈 NUEVO CRUCE → {symbol} [{interval}] | velas={velas}")

        cola_capturas.put({
            "symbol": symbol,
            "interval": interval,
            "df": df,
            "ultimo_cruce": ultimo_cruce,
            "tipo_cruce": tipo_cruce,
            "validado": validado,
            "precio_objetivo": precio_objetivo,
            "objetivo_alcanzado": objetivo_alcanzado,
            "idx": idx,
            "trend": trend,
            "entry": entry,
            "stop_loss": stop_loss,
            "targets": targets,
            "status": status,
            "ema_diff": ema_diff,
            "velas": velas
        })

    except Exception as e:
        print(f"⚠️ Error detectando {symbol} [{interval}]: {e}")



# ============================================================
#                 LOOP PRINCIPAL
# ============================================================
if __name__ == "__main__":

    while True:

        print("\n==============================")
        print("⏳ Escaneando nuevos cruces...")
        print("==============================\n")

        with ThreadPoolExecutor(max_workers=10) as exe:
            for s in SYMBOLS:
                for tf in INTERVALS:
                    exe.submit(detectar_cruce, s, tf)

        while not cola_capturas.empty():

            data = cola_capturas.get()

            fig = graficar_plotly(
                data["df"],
                data["symbol"],
                data["interval"],
                ultimo_cruce=data["ultimo_cruce"],
                tipo_cruce=data["tipo_cruce"],
                validado=data["validado"],
                precio_objetivo=data["precio_objetivo"],
                objetivo_alcanzado=data["objetivo_alcanzado"],
                last_cross_idx=data["idx"],
                trend=data["trend"],
                entry=data["entry"],
                stop_loss=data["stop_loss"],
                targets=data["targets"],
                status=data["status"]
            )

            png_bytes = convertir_figura_a_png(
                fig,
                f"capture_{data['symbol']}_{data['interval']}.png"
            )

            caption = (
                f"📈 {data['symbol']} [{data['interval']}]\n"
                f"Velas: {data['velas']}\n"
                f"Tipo: {data['tipo_cruce']}\n"
                f"EMAΔ: {data['ema_diff']:.3f}\n"
                f"Trend: {data['trend']}"
            )

            # Ahora sí → se envía a la temporalidad correcta
            enviar_telegram_png(png_bytes, caption, data["interval"])

        print("\n⏳ Esperando siguiente ciclo...\n")
        time.sleep(30)
