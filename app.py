#!/usr/bin/env python3
"""
Convertidor CBOT a Pesos Argentinos + Referencia A3 Rosario + Dólar BNA
VERSIÓN MANUAL - Sin scraping, sin APIs pagas
"""

from flask import Flask, current_app, render_template, request, redirect, url_for
from datetime import datetime
import os
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================
# INICIALIZAR CONFIGURACIÓN (valores manuales)
# ============================================
app.config["PRECIO_CBOT"] = 12.0625  # Contrato ZSN26
app.config["FECHA_CBOT"] = "No actualizado"
app.config["PRECIO_A3"] = 439800  # Pizarra Rosario (actualizado 08/05)
app.config["FECHA_A3"] = "2026-05-08"
app.config["DOLAR_BLUE_VENTA"] = 1400  # Dólar blue (paralelo)
app.config["DOLAR_BNA_COMPRADOR"] = 1384  # Dólar BNA comprador (exportadores)
app.config["FECHA_DOLAR_BNA"] = "2026-05-08"
app.config["DOLAR_BLUE_FECHA"] = "2026-05-01"

# ============================================
# CONSTANTES
# ============================================
FACTOR_SOJA = 0.0272155
RETENCION_SOJA = 0.33
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


def precio_argentina(precio_usd_tn: float, dolar_blue_venta: float) -> dict:
    """Calcula precio al productor (Argentina) usando dólar blue"""
    valor_post_retencion = precio_usd_tn * (1 - RETENCION_SOJA)
    valor_en_puerto_usd = valor_post_retencion - COSTOS_FIJOS_USD
    valor_en_puerto_ars = valor_en_puerto_usd * dolar_blue_venta
    return {
        "retencion_pct": int(RETENCION_SOJA * 100),
        "precio_usd_puerto": round(valor_en_puerto_usd, 2),
        "precio_ars_puerto": round(valor_en_puerto_ars, 0),
    }


def auto_fetch_cbot_price() -> float:
    try:
        ticker = yf.Ticker("ZSN26.F")
        data = ticker.history(period="2d")
        if not data.empty:
            return round(data["Close"].iloc[-1], 4)
    except Exception as e:
        print(f"Auto-fetch error: {e}")
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


@app.route("/actualizar-dolar-blue", methods=["POST"])
def actualizar_dolar_blue():
    try:
        nuevo_dolar = int(request.form.get("dolar_blue", 0))
        if nuevo_dolar > 0:
            current_app.config["DOLAR_BLUE_VENTA"] = nuevo_dolar
            current_app.config["DOLAR_BLUE_FECHA"] = datetime.now().strftime("%Y-%m-%d")
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


@app.route("/", methods=["GET"])
def index():
    # Obtener valores como números
    precio_cbot = float(current_app.config["PRECIO_CBOT"])
    precio_a3 = int(current_app.config["PRECIO_A3"])
    dolar_blue = int(current_app.config["DOLAR_BLUE_VENTA"])
    dolar_bna = int(current_app.config["DOLAR_BNA_COMPRADOR"])

    # Calcular conversiones CBOT
    cbot_usd_tn = precio_a_tonelada(precio_cbot)
    cbot_ars_tn_blue = cbot_usd_tn * dolar_blue
    cbot_ars_tn_bna = cbot_usd_tn * dolar_bna

    # Precio al productor con dólar blue
    productor = precio_argentina(cbot_usd_tn, dolar_blue)

    # Brechas
    brecha_a3_blue = cbot_ars_tn_blue - precio_a3
    brecha_a3_bna = cbot_ars_tn_bna - precio_a3

    brecha_porcentaje = (
        round((brecha_a3_blue / cbot_ars_tn_blue) * 100, 1)
        if cbot_ars_tn_blue > 0
        else 0
    )

    if brecha_a3_blue > 0:
        brecha_signo = "POSITIVA +"
        brecha_texto = "por DEBAJO"
        brecha_clase = "positivo"
    elif brecha_a3_blue < 0:
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
        cbot_ars_tn_blue=cbot_ars_tn_blue,
        cbot_ars_tn_bna=cbot_ars_tn_bna,
        precio_a3=precio_a3,
        fecha_a3=current_app.config["FECHA_A3"],
        productor_retencion=productor["retencion_pct"],
        productor_usd=productor["precio_usd_puerto"],
        productor_ars=productor["precio_ars_puerto"],
        brecha_ars=brecha_a3_blue,
        brecha_abs=abs(brecha_a3_blue),
        brecha_signo=brecha_signo,
        brecha_porcentaje=brecha_porcentaje,
        brecha_texto=brecha_texto,
        brecha_clase=brecha_clase,
        dolar_blue=dolar_blue,
        dolar_bna=dolar_bna,
        fecha_dolar_blue=current_app.config["DOLAR_BLUE_FECHA"],
        fecha_dolar_bna=current_app.config["FECHA_DOLAR_BNA"],
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
