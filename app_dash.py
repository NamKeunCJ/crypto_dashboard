# app_dash.py
import dash
from dash import Dash, dcc, html, dash_table, Output, Input, State
import dash_bootstrap_components as dbc
from main import analizar_par
from services.meme_filter import get_top_symbols
from visuals.plot import graficar_plotly
import requests
from dash.dash_table import FormatTemplate  # ayuda a realizar el dinamismo de ema y cambio 24h
from dash.dash_table.Format import Format, Scheme # filtra decimales en cambio 24h y ema
import base64
from concurrent.futures import ThreadPoolExecutor

# =============================== 7552415670:AAHDu8kkbycqToiQa4OLdqnDNKS9hmMvBhw
# Telegram
# =============================== 2145970238

TELEGRAM_TOKEN = "7552415670:AAHDu8kkbycqToiQa4OLdqnDNKS9hmMvBhw"
CHAT_ID = "-1002630358496"#Id Grupo #"2145970238"id bot independiente

def enviar_telegram(imagen_bytes, caption="📊 Señal detectada"):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {"photo": ("chart.png", imagen_bytes)}
    data = {"chat_id": CHAT_ID, "caption": caption}
    requests.post(url, files=files, data=data)


def obtener_cambios_24h():### Obtiene datos de las 24 horas
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    try:
        data = requests.get(url).json()
        return {item["symbol"]: float(item["priceChangePercent"]) 
                for item in data if item["symbol"].endswith("USDT")}
    except Exception as e:
        print(f"Error obteniendo cambios 24h: {e}")
        return {}

# ===============================
# Configuración
# ===============================
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

REFRESH_INTERVAL = 15
INTERVALS = ["15m", "1h", "4h", "1d"]

# ===============================
# Lista oficial de top coins (sin duplicados)
# ===============================
TOP_COINS = list(dict.fromkeys([
    "BTCUSDT","ETHUSDT","FARTCOINUSDT","XRPUSDT",
    "SUIUSDT","DOGEUSDT","SOLUSDT","LTCUSDT","BNBUSDT"
]))

# ===============================
# Lista dinámica de meme coins filtrada
# ===============================
MEME_COINS = get_top_symbols(limit=30)    #=======================================================

# 1. Quitar duplicados
# 2. Evitar que un top coin aparezca en esta lista
MEME_COINS = [
    s for s in dict.fromkeys(MEME_COINS)
    if s not in TOP_COINS
]

# ===============================
# Lista combinada sin repetidos
# ===============================
ALL_SYMBOLS = list(dict.fromkeys(TOP_COINS + MEME_COINS))
# ===============================
# Layout principal
# ===============================

app.layout = dbc.Container([
    html.H1("📊 Crypto Dashboard - Dash", className="mt-3 mb-3 text-center"),

    # Dropdown intervalo
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id="interval",
                options=[{"label": i, "value": i} for i in INTERVALS],
                value="15m",
                clearable=False,
                style={"color": "black"}
            )
        ], width=3)
    ], justify="center"),

    # Tabs
    dcc.Tabs(id="tabs", value="top", children=[
        dcc.Tab(label="🏦 Top Market Cap", value="top"),
        dcc.Tab(label="💩 Meme Coins", value="meme"),
    ], className="mt-3"),

    # Tabla (ya declarada desde el inicio)
    dash_table.DataTable(
    id="tabla-datos",
        columns=[
            {"name": "Moneda", "id": "Moneda"},
            {"name": "Último Cruce", "id": "Último Cruce"},
            {"name": "Tipo", "id": "Tipo"},
            {"name": "Validado", "id": "Validado"},
            {"name": "Objetivo", "id": "Objetivo"},
            {"name": "Alcanzado", "id": "Alcanzado"},
             # para poder dinamizar la letra 
            {"name": "Cambio 24h", "id": "Cambio 24h", "type": "numeric","format": Format(precision=2, scheme=Scheme.fixed, nully="—").group(False) },
            {"name": "Velas", "id": "Velas"},
            # para poder dinamizar la letra 
            {"name": "EMA Δ", "id": "EMA Δ", "type": "numeric","format": Format(precision=2, scheme=Scheme.fixed, nully="—").group(False) },
            {"name": "Acción", "id": "Acción"}
        ],
        data=[],
        cell_selectable=True,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "color": "white", "backgroundColor": "black"},
        style_header={"backgroundColor": "#222", "fontWeight": "bold", "color": "white"},
        style_data_conditional=[
            {"if": {"filter_query": "{Cambio 24h} >= 0", "column_id": "Cambio 24h"},
            "color": "lime", "fontWeight": "bold"},
            {"if": {"filter_query": "{Cambio 24h} < 0", "column_id": "Cambio 24h"},
            "color": "red", "fontWeight": "bold"},
            {"if": {"filter_query": "{Velas} < 5", "column_id": "Velas"},
            "color": "#FFD700", "fontWeight": "bold"},
            {"if": {"filter_query": "{EMA Δ} <= 0.5", "column_id": "EMA Δ"},
            "color": "#FFD700", "fontWeight": "bold"},
            {"if": {"filter_query": "{EMA Δ} > 0.5 && {EMA Δ} <= 1.0", "column_id": "EMA Δ"},
            "color": "#00BFFF", "fontWeight": "bold"},
            {"if": {"filter_query": "{EMA Δ} > 1.0", "column_id": "EMA Δ"},
            "color": "white", "fontWeight": "bold"}
        ]   
    ),

    # Auto-refresh
    dcc.Interval(
        id="auto-refresh",
        interval=REFRESH_INTERVAL * 1000,
        n_intervals=0
    ),

    # Store símbolo seleccionado
    dcc.Store(id="selected-symbol"),
    # Store para la imagen capturada en base64
    dcc.Store(id="chart-image"),
    # Modal con gráfico
    # Store para símbolos que necesitan captura
    dcc.Store(id="symbols-to-capture"),
    # Gráfico oculto (no visible en UI)
    dcc.Graph(id="hidden-graph", style={"display": "none"}),
    # Store para lista de símbolos ya enviados (evita repeticiones)
    dcc.Store(id="symbols-sent", data=[]),


    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),

            dbc.ModalBody([ 
                    dcc.Loading(dcc.Graph(id="grafico"), type="circle"),
                    html.Br(),
                    dash_table.DataTable(
                        id="tabla-detalle",
                        columns=[
                            {"name": "Nivel", "id": "Nivel"},
                            {"name": "Precio", "id": "Precio"},
                            {"name": "Estado", "id": "Estado"}
                        ],
                        data=[],
                        style_cell={"textAlign": "center", "color": "white", "backgroundColor": "black"},
                        style_header={"backgroundColor": "#222", "fontWeight": "bold", "color": "white"},
                        style_table={"marginTop": "10px"}
                    ),
                    # Imagen de preview (oculta por defecto)
                    html.Img(id="chart-image-preview", style={"display": "none"})
            ]),
            
            dbc.ModalFooter([
               #dbc.Button("📸 Capturar PNG", id="capture-btn", color="primary", className="me-2"),
                dbc.Button("Cerrar", id="close-modal", className="ms-auto", color="danger")
            ]),

        ],
        id="modal",
        size="xl",
        is_open=False,
        backdrop="static",
        centered=True,
    )
], fluid=True)

app.clientside_callback(
    """
    function(symbols){
        if (!symbols || symbols.length === 0){
            return null;
        }
        const graphDiv = document.querySelector('#hidden-graph .js-plotly-plot');
        if (!graphDiv){
            console.warn("No se encontró el gráfico oculto todavía");
            return window.dash_clientside.no_update;
        }
        // ⚠️ Evitar PNG en blanco: aseguramos que ya tenga trazas
        if (!graphDiv.data || graphDiv.data.length === 0){
            console.warn("El gráfico oculto aún no tiene data");
            return window.dash_clientside.no_update;
        }
        return Plotly.toImage(graphDiv, {
            format: 'png',
            height: 900,
            width: 1600,
            scale: 1
        });
    }
    """,
    Output("chart-image", "data"),
    Input("symbols-to-capture", "data")
)


# ===============================
# Callback: actualizar tabla
# ===============================
ya_enviados = set()  # control anti-spam

@app.callback(
    [Output("tabla-datos", "data"),
     Output("tabla-datos", "columns"),
     Output("symbols-to-capture", "data")],   # NUEVO monedas en cruce
    Input("tabs", "value"),
    Input("interval", "value"),
    Input("auto-refresh", "n_intervals"),
    State("symbols-sent", "data")   # <<< NUEVO
)
def actualizar_tabla(tab, interval, n, enviados):
    # ✅ Ahora siempre procesamos todos los símbolos
    symbols = ALL_SYMBOLS
    filas = []
    cambios_24h = obtener_cambios_24h()
    symbols_to_capture = []

    if enviados is None:
        enviados = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(analizar_par, s, interval): s for s in symbols}

    for future in futures:
        s = futures[future]
        try:
            (
                _,
                ultimo_cruce,
                tipo_cruce,
                validado,
                precio_objetivo,
                objetivo_alcanzado,
                _,
                cercania_velas,
                ema_diff,
                *_   # resto se descarta
            ) = future.result()

            cambio_24h = cambios_24h.get(s)

            filas.append({
                "Moneda": s,
                "Último Cruce": ultimo_cruce.strftime("%Y-%m-%d %H:%M") if ultimo_cruce else "N/A",
                "Tipo": "📈🟢" if tipo_cruce=="up" else "📉🔴" if tipo_cruce=="down" else "—",
                "Validado": "✅" if validado else "❌" if validado is not None else "—",
                "Objetivo": f"{precio_objetivo:.2f}" if precio_objetivo else "—",
                "Alcanzado": "🎯" if objetivo_alcanzado else "⏳" if objetivo_alcanzado is not None else "—",
                "Cambio 24h": cambio_24h if cambio_24h is not None else None,
                "Velas": cercania_velas if cercania_velas is not None else "—",
                "EMA Δ": round(ema_diff, 2) if ema_diff is not None else None,
                "Acción": "📊 Ver gráfico"
            })

            # --- lógica de envío a Telegram (igual que antes) ---
            print(f"DEBUG {s} -> validado={validado}, cercania_velas(raw)={cercania_velas}")
            try:
                velas = int(cercania_velas)
            except (TypeError, ValueError):
                velas = None

            if velas is not None and 0 <= velas <= 3 and s not in enviados:# ( filtro por velas)
                print(f"✅ Enviando a captura (cruce detectado): {s} con {velas} velas")
                symbols_to_capture.append(s)
            else:
                print(f"⏭️  No cumple condiciones: {s} (cercania_velas={cercania_velas})")

        except Exception as e:
            print(f"⚠️ Error analizando {s}: {e}")
            
            filas.append({
                "Moneda": s,
                "Último Cruce": "❌ Error",
                "Tipo": "—",
                "Validado": "—",
                "Objetivo": "—",
                "Alcanzado": "—",
                "Cambio 24h": None,
                "Velas": "—",       
                "EMA Δ": None,
                "Acción": "—"
            })


    # ✅ Filtrar lo que se muestra en la tabla según la pestaña
    if tab == "top":
        filas = [f for f in filas if f["Moneda"] in TOP_COINS]
    elif tab == "meme":
        filas = [f for f in filas if f["Moneda"] in MEME_COINS]

    # Ordenar por velas
    #nunca va faltar velas 
    filas = sorted(
        filas,
        key=lambda x: x.get("Velas", float("inf")) if isinstance(x.get("Velas"), (int, float)) else float("inf")
    )

    for fila in filas:
        if fila["Velas"] == float("inf"):
            fila["Velas"] = "—"

    columnas = [{"name": i, "id": i} for i in filas[0].keys()] if filas else []
    return filas, columnas, symbols_to_capture

# ===============================
# Callback: manejar modal
# ===============================
@app.callback(
    [Output("selected-symbol", "data"),
     Output("modal", "is_open"),
     Output("modal-title", "children")],
    [Input("tabla-datos", "active_cell"),
     Input("close-modal", "n_clicks")],
    [State("tabla-datos", "data"),
     State("modal", "is_open")],
    prevent_initial_call=True
)
def manejar_modal(active_cell, n_clicks, data, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, is_open, dash.no_update

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Abrir modal al hacer clic en la columna Acción
    if trigger_id == "tabla-datos" and active_cell:
        row = active_cell["row"]
        col = active_cell["column_id"]
        if col == "Acción" and data:
            symbol = data[row]["Moneda"]
            return symbol, True, f"📈 {symbol} - Gráfico"

    # Cerrar modal
    if trigger_id == "close-modal" and n_clicks:
        return dash.no_update, False, dash.no_update

    return dash.no_update, is_open, dash.no_update

def format_price(value):
    if value is None:
        return "—"
    return f"{value:.2f}" if value >= 1 else f"{value:.6f}"

# ===============================
# Callback: mostrar gráfico dentro del modal
# ===============================
@app.callback(
    [Output("grafico", "figure"),
     Output("tabla-detalle", "data")],
    Input("selected-symbol", "data"),
    State("interval", "value")
)

def mostrar_grafico(symbol, interval):
    if not symbol:
        return {}, []

    (
        df,
        ultimo_cruce,
        tipo_cruce,
        validado,
        precio_objetivo,
        objetivo_alcanzado,
        _,
        cercania_velas,
        ema_diff,
        idx,
        trend,
        entry,
        stop_loss,
        targets,
        status,
        adx_val,
        plus_di_val,
        minus_di_val
    ) = analizar_par(symbol, interval)

    fig = graficar_plotly(
        df, symbol, interval,
        ultimo_cruce=ultimo_cruce,
        tipo_cruce=tipo_cruce,
        validado=validado,
        precio_objetivo=precio_objetivo,
        objetivo_alcanzado=objetivo_alcanzado,
        last_cross_idx=idx,
        trend=trend,
        entry=entry,
        stop_loss=stop_loss,
        targets=targets,
        status=status
    )

    # ✅ Crear datos para la tabla
    detalle = []
    if entry is not None:
        detalle.append({"Nivel": "BE", "Precio": format_price(entry), "Estado": status.get("BE", "")})
    if stop_loss is not None:
        detalle.append({"Nivel": "SL", "Precio": format_price(stop_loss), "Estado": status.get("SL", "")})
    if targets:
        for i, t in enumerate(targets, start=1):
            detalle.append({"Nivel": f"TP{i}", "Precio": format_price(t), "Estado": status.get(f"TP{i}", "")})

    return fig, detalle

# ===============================
# Mostrar el preview en el modal   ### borrables
# ===============================

@app.callback(
    [Output("chart-image-preview", "src"),
     Output("chart-image-preview", "style")],
    Input("chart-image", "data")
)
def mostrar_preview(data_url):
    if data_url:
        return data_url, {
            "width": "100%",
            "marginTop": "10px",
            "border": "1px solid #333",
            "borderRadius": "8px"
        }
    return dash.no_update, {"display": "none"}

import base64


# ===============================
# RunTelegram 
# ===============================
@app.callback(
    [Output("symbols-to-capture", "data", allow_duplicate=True),  # cola
     Output("symbols-sent", "data", allow_duplicate=True)],       # enviados
    Input("chart-image", "data"),
    State("symbols-to-capture", "data"),
    State("symbols-sent", "data"),
    State("interval", "value"),
    prevent_initial_call=True
)
def enviar_a_telegram(img_data, symbols, enviados, interval):
    if not img_data or not symbols or len(symbols) == 0:
        return dash.no_update, dash.no_update

    if enviados is None:
        enviados = []

    symbol = symbols[0]  # el primero en la cola

    clave = f"{symbol}_{interval}"
    if clave in ya_enviados:
        print(f"⏭️  Ya enviado antes: {clave}")
        return symbols[1:], enviados

    # Decodificar base64
    header, encoded = img_data.split(",", 1)
    imagen_bytes = base64.b64decode(encoded)

    # Enviar a Telegram
    enviar_telegram(imagen_bytes, caption=f"📈 {symbol} en cruce ({interval})")

    ya_enviados.add(clave)
    print(f"📤 Enviado a Telegram: {symbol}")

    # Actualizar stores:
    #   - quitar símbolo de la cola
    #   - agregarlo a enviados
    return symbols[1:], enviados + [symbol]


# ===============================
# Callback para renderizar el gráfico oculto
# ===============================
@app.callback(
    Output("hidden-graph", "figure"),
    Input("symbols-to-capture", "data"),
    State("interval", "value")
)
def render_hidden_graph(symbols, interval):
    if not symbols or len(symbols) == 0:
        return {}

    # Tomar el primero de la cola
    symbol = symbols[0]

    (
        df,
        ultimo_cruce,
        tipo_cruce,
        validado,
        precio_objetivo,
        objetivo_alcanzado,
        _,
        cercania_velas,
        ema_diff,
        idx,
        trend,
        entry,
        stop_loss,
        targets,
        status,
        adx_val,
        plus_di_val,
        minus_di_val
    ) = analizar_par(symbol, interval)

    fig = graficar_plotly(
        df, symbol, interval,
        ultimo_cruce=ultimo_cruce,
        tipo_cruce=tipo_cruce,
        validado=validado,
        precio_objetivo=precio_objetivo,
        objetivo_alcanzado=objetivo_alcanzado,
        last_cross_idx=idx,
        trend=trend,
        entry=entry,
        stop_loss=stop_loss,
        targets=targets,
        status=status
    )
    return fig


#==================================================================================================================================
# ===============================
# Run
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
