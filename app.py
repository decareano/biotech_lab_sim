#!/usr/bin/env python3
"""
Convertidor CBOT a Pesos Argentinos + Referencia A3 Rosario + Dólar BNA
VERSIÓN SIMPLIFICADA - Solo dólar BNA (exportadores)
"""

from flask import Flask, current_app, render_template, request, redirect, url_for
from datetime import datetime
import os
import yfinance as yf
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================
# INICIALIZAR CONFIGURACIÓN (valores manuales)
# ============================================
app.config["PRECIO_CBOT"] = 12.0625  # Contrato "ZSX26.F"
app.config["FECHA_CBOT"] = "No actualizado"
app.config["PRECIO_A3"] = 482000  # Pizarra Rosario
app.config["FECHA_A3"] = "2026-05-08"
app.config["DOLAR_BNA_COMPRADOR"] = 1384  # Dólar BNA comprador (exportadores)
app.config["FECHA_DOLAR_BNA"] = "2026-05-08"

# ============================================
# CONSTANTES
# ============================================
FACTOR_SOJA = 0.0272155
RETENCION_SOJA = 0.24
COSTOS_FIJOS_USD = 25


def convertir_precio_cme_a_decimal(precio_str: str) -> float:
    """Convierte '1206'2' a 12.0625"""
    if not precio_str or "'" not in precio_str:
        return float(precio_str)

    partes = precio_str.split("'")
    dolares_centavos = partes[0]
    fraccion = partes[1] if len(partes) > 1 else "0"

    if "/" in fraccion:
        fraccion = fraccion.split("/")[0]

    try:
        fraccion_int = int(fraccion)
    except:
        fraccion_int = 0

    dolares = int(dolares_centavos) // 100
    centavos = int(dolares_centavos) % 100
    fraccion_decimal = fraccion_int / 8 * 0.01

    return round(dolares + (centavos / 100) + fraccion_decimal, 5)


def precio_a_tonelada(precio_bushel: float) -> float:
    return round(precio_bushel / FACTOR_SOJA, 2)


def precio_argentina(precio_usd_tn: float, dolar_bna: float) -> dict:
    """Calcula precio al productor (Argentina) usando dólar BNA comprador"""
    valor_post_retencion = precio_usd_tn * (1 - RETENCION_SOJA)
    valor_en_puerto_usd = valor_post_retencion - COSTOS_FIJOS_USD
    valor_en_puerto_ars = valor_en_puerto_usd * dolar_bna
    return {
        "retencion_pct": int(RETENCION_SOJA * 100),
        "precio_usd_puerto": round(valor_en_puerto_usd, 2),
        "precio_ars_puerto": round(valor_en_puerto_ars, 0),
    }


def auto_fetch_cbot_price():
    try:
        session = cffi_requests.Session(impersonate="safari15_5")
        ticker = yf.Ticker("ZSX26.CBT", session=session)
        data = ticker.history(period="2d")
        if data is None or data.empty:
            print("Auto-fetch: no hay datos")
            return None

        latest_close_cents = data["Close"].iloc[-1]
        latest_close_dollars = latest_close_cents / 100

        if not isinstance(latest_close_dollars, (int, float)):
            print("Auto-fetch: latest_close no es un numero")
            return None
        print(f"Auto-fetch exitoso: {round(latest_close_dollars, 4)}")
        return round(latest_close_dollars, 4)

    except Exception as e:
        print(f"auto-fetch error: {e}")
        return None


def auto_fetch_bna_price() -> int | None:
    try:
        url = "https://dolarapi.com/v1/dolares/oficial"
        session = cffi_requests.Session(impersonate="safari15_5")
        response = session.get(url)
        if response.status_code != 200:
            print("request failed")
            return None
        data = response.json()
        valor_raw = data.get("compra")
        if valor_raw is None:
            print("bna: clave compra no se encontró")
            return None
        valor_float = float(valor_raw)
        valor_int = int(valor_float)
        if valor_int <= 0:
            print("bna: valor invalido")
            return None
        return valor_int
    except Exception as e:
        print(f"bna error: {e}")
        return None


def obtener_historial_cbot(dias: int) -> list:
    ticker = yf.Ticker("ZS=F")
    hist = ticker.history(period=f"{dias+20}d")
    precios = hist["Close"]
    precios = precios.tolist()
    return precios


def calcular_medias(precios: list, dias_ema1: int = 9, dias_ema2: int = 26):
    if len(precios) < dias_ema2:
        return (None, None)

    # Valor inicial de la EMA 9 y EMA 26 (SMA de los primeros N precios)
    ema1 = sum(precios[:dias_ema1]) / dias_ema1
    ema2 = sum(precios[:dias_ema2]) / dias_ema2

    k1 = 2 / (dias_ema1 + 1)
    k2 = 2 / (dias_ema2 + 1)

    # Iterar sobre todos los precios desde el día 'dias_ema2' hasta el final
    for precio_actual in precios[dias_ema2:]:
        ema1 = (precio_actual * k1) + (ema1 * (1 - k1))
        ema2 = (precio_actual * k2) + (ema2 * (1 - k2))

    return (ema1, ema2)


def obtener_precio_pizarra() -> float | None:
    try:
        url = "https://matbarofex.primary.ventures/security/rx_DDA_SOJ_ROS_P_DISPO"
        response = requests.get(url)

        # Después de response = requests.get(url)
        print(f"HTML length: {len(response.text)}")
        print(response.text[:5000])  # primeros 1000 caracteres

        if response.status_code != 200:
            print(f"Error al obtener pizarra: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        precio_elemento = soup.find("div", class_="PriceCell-content")

        if not precio_elemento:
            print("No se encontró el elemento con el precio")
            return None

        precio_texto = precio_elemento.text.strip()  # "510.000"
        precio = float(precio_texto.replace(".", ""))  # 510000.0

        print(f"Precio pizarra obtenido: {precio}")
        return precio

    except Exception as e:
        print(f"Error en obtener_precio_pizarra: {e}")
        return None


# ============================================
# RUTAS
# ============================================
@app.route("/auto-fetch-cbot", methods=["POST"])
def auto_fetch_cbot():
    precio = auto_fetch_cbot_price()
    if precio and precio > 0:
        current_app.config["PRECIO_CBOT"] = precio
        current_app.config["FECHA_CBOT"] = (
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')} (auto)"
        )
    return redirect(url_for("index"))


@app.route("/actualizar-cbot-manual", methods=["POST"])
def actualizar_cbot_manual():
    try:
        precio_input = request.form.get("precio_cbot", "")
        if "'" in precio_input:
            precio_decimal = convertir_precio_cme_a_decimal(precio_input)
        else:
            precio_decimal = float(precio_input)

        if precio_decimal > 0:
            current_app.config["PRECIO_CBOT"] = precio_decimal
            current_app.config["FECHA_CBOT"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"Error: {e}")
    return redirect(url_for("index"))


@app.route("/actualizar-a3", methods=["POST"])
def actualizar_a3():
    try:
        nuevo_precio = int(request.form.get("precio_a3", 0))
        if nuevo_precio > 0:
            current_app.config["PRECIO_A3"] = nuevo_precio
            current_app.config["FECHA_A3"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    except:
        pass
    return redirect(url_for("index"))


@app.route("/actualizar-dolar-bna", methods=["POST"])
def actualizar_dolar_bna():
    """Actualiza el dólar BNA comprador (usado por exportadores)"""
    try:
        nuevo_dolar = int(request.form.get("dolar_bna", 0))
        if nuevo_dolar > 0:
            current_app.config["DOLAR_BNA_COMPRADOR"] = nuevo_dolar
            current_app.config["FECHA_DOLAR_BNA"] = datetime.now().strftime("%Y-%m-%d")
    except:
        pass
    return redirect(url_for("index"))


@app.route("/auto-fetch-bna", methods=["POST"])
def auto_fetch_bna():
    precio = auto_fetch_bna_price()
    if precio and precio > 0:
        current_app.config["DOLAR_BNA_COMPRADOR"] = precio
        current_app.config["FECHA_DOLAR_BNA"] = datetime.now().strftime("%Y-%m-%d")
    return redirect(url_for("index"))


@app.route("/auto-fetch-pizarra", methods=["POST"])
def auto_fetch_pizarra():
    try:
        precio = obtener_precio_pizarra()
        if precio is not None and precio > 0:
            current_app.config["PRECIO_A3"] = precio
            current_app.config["FECHA_A3"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"Error en auto_fetch_pizarra: {e}")

    return redirect(url_for("index"))


def analizar_tecnico(precio_centavos: float) -> str:
    soporte = 1176.6
    resistencia = 1194.4
    if precio_centavos > resistencia:
        return "🟢 SEÑAL ALCISTA"
    elif precio_centavos < soporte:
        return "🔴 SEÑAL BAJISTA"
    else:
        return "🟡 ZONA DE DECISIÓN"


@app.route("/tradingView")
def tradingView():
    return render_template("tradingView.html")


@app.route("/", methods=["GET"])
def index():

    # Obtener valores como números
    precio_cbot = float(current_app.config["PRECIO_CBOT"])
    precio_cbot_centavos = precio_cbot * 100
    senal_tecnica = analizar_tecnico(precio_cbot_centavos)
    precio_a3 = int(current_app.config["PRECIO_A3"])
    dolar_bna = int(current_app.config["DOLAR_BNA_COMPRADOR"])

    precio_automatico = obtener_precio_pizarra()
    if precio_automatico is not None and precio_automatico > 0:
        current_app.config["PRECIO_A3"] = precio_automatico
        current_app.config["FECHA_A3"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        precio_a3 = precio_automatico

    # 2. Obtener historial de precios
    historial = obtener_historial_cbot(200)
    ema_9, ema_26 = calcular_medias(historial)
    print(
        f"📊 EMA 9: {ema_9}, EMA 26: {ema_26}"
    )  # 👈 Esto te dice qué están devolviendo

    ema_9, ema_26 = calcular_medias(historial)
    if ema_9 is None:
        ema_9 = 0
    if ema_26 is None:
        ema_26 = 0

    # 👇 ACÁ VA EL CÓDIGO DE LA SEÑAL DE CRUCE
    if ema_9 > ema_26:
        cruce_signal = "🟢 CRUCE ALCISTA (EMA 9 > EMA 26)"
    elif ema_9 < ema_26:
        cruce_signal = "🔴 CRUCE BAJISTA (EMA 9 < EMA 26)"
    else:
        cruce_signal = "⚪ SIN CRUCE"

    try:
        with open("A3_rofexNov26X.txt", "r") as f:
            a3_usd = float(f.read().strip())
    except:
        a3_usd = None

    if a3_usd is not None and a3_usd > 0:
        a3_ars_desde_usd = a3_usd * dolar_bna
    else:
        a3_ars_desde_usd = None
        # Calcular brecha entre Rofex y Pizarra
    if a3_ars_desde_usd is not None and precio_a3 is not None:
        brecha_rofex_pizarra = a3_ars_desde_usd - precio_a3
    else:
        brecha_rofex_pizarra = None

    # Calcular conversiones CBOT
    cbot_usd_tn = precio_a_tonelada(precio_cbot)
    cbot_ars_tn = cbot_usd_tn * dolar_bna

    # Precio al productor con dólar BNA
    productor = precio_argentina(cbot_usd_tn, dolar_bna)

    # Brecha entre CBOT (convertido) y A3 real
    brecha = cbot_ars_tn - precio_a3
    brecha_abs = abs(brecha)
    brecha_porcentaje = round((brecha / cbot_ars_tn) * 100, 1) if cbot_ars_tn > 0 else 0

    if brecha > 0:
        brecha_signo = "POSITIVA +"
        brecha_texto = "por DEBAJO"
        brecha_clase = "positivo"
    elif brecha < 0:
        brecha_signo = "NEGATIVA"
        brecha_texto = "por ENCIMA"
        brecha_clase = "negativo"
    else:
        brecha_signo = ""
        brecha_texto = "en línea con"
        brecha_clase = "neutral"

    precio_cbot_formateado = f"{precio_cbot:.4f}".rstrip("0").rstrip(".")

    return render_template(
        "index.html",
        precio_cbot=precio_cbot,
        precio_cbot_formateado=precio_cbot_formateado,
        fecha_cbot=current_app.config["FECHA_CBOT"],
        cbot_usd_tn=cbot_usd_tn,
        cbot_ars_tn=cbot_ars_tn,
        precio_a3=precio_a3,
        fecha_a3=current_app.config["FECHA_A3"],
        productor_retencion=productor["retencion_pct"],
        productor_usd=productor["precio_usd_puerto"],
        productor_ars=productor["precio_ars_puerto"],
        brecha_ars=brecha,
        brecha_abs=brecha_abs,
        brecha_signo=brecha_signo,
        brecha_porcentaje=brecha_porcentaje,
        brecha_texto=brecha_texto,
        brecha_clase=brecha_clase,
        dolar_bna=dolar_bna,
        fecha_dolar_bna=current_app.config["FECHA_DOLAR_BNA"],
        a3_ars_desde_usd=a3_ars_desde_usd,
        brecha_rofex_pizarra=brecha_rofex_pizarra,
        senal_tecnica=senal_tecnica,
        cruce_signal=cruce_signal,
        ema_9=ema_9,
        ema_26=ema_26,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
