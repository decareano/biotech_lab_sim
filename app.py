#!/usr/bin/env python3
"""
Convertidor CBOT a Pesos Argentinos + Referencia A3 Rosario
CORREGIDO - Error de tipo (string vs number)
"""

from flask import Flask, current_app, render_template_string, request, redirect, url_for
from datetime import datetime
import os
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================
# INICIALIZAR CONFIGURACIÓN
# ============================================
app.config["PRECIO_CBOT"] = 12.0625
app.config["FECHA_CBOT"] = "No actualizado"
app.config["PRECIO_A3"] = 430000
app.config["FECHA_A3"] = "No actualizado"
app.config["DOLAR_BLUE_VENTA"] = 1400
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


@app.route("/actualizar-dolar", methods=["POST"])
def actualizar_dolar():
    try:
        nuevo_dolar = int(request.form.get("dolar_blue", 0))
        if nuevo_dolar > 0:
            current_app.config["DOLAR_BLUE_VENTA"] = nuevo_dolar
            current_app.config["DOLAR_BLUE_FECHA"] = datetime.now().strftime("%Y-%m-%d")
    except:
        pass
    return redirect(url_for("index"))


@app.route("/", methods=["GET"])
def index():
    # Obtener valores como números, no strings
    precio_cbot = float(current_app.config["PRECIO_CBOT"])
    precio_a3 = int(current_app.config["PRECIO_A3"])
    dolar_blue = int(current_app.config["DOLAR_BLUE_VENTA"])

    # Calcular conversiones (todas como números)
    cbot_usd_tn = precio_a_tonelada(precio_cbot)
    cbot_ars_tn = cbot_usd_tn * dolar_blue
    productor = precio_argentina(cbot_usd_tn, dolar_blue)

    brecha_ars = cbot_ars_tn - precio_a3
    brecha_porcentaje = (
        round((brecha_ars / cbot_ars_tn) * 100, 1) if cbot_ars_tn > 0 else 0
    )
    brecha_abs = abs(brecha_ars)

    if brecha_ars > 0:
        brecha_signo = "POSITIVA +"
        brecha_texto = "por DEBAJO"
        brecha_clase = "positivo"
    elif brecha_ars < 0:
        brecha_signo = "NEGATIVA"
        brecha_texto = "por ENCIMA"
        brecha_clase = "negativo"
    else:
        brecha_signo = ""
        brecha_texto = "en línea con"
        brecha_clase = "neutral"

    # Formatear precio CBOT para mostrar
    precio_cbot_formateado = f"{precio_cbot:.4f}".rstrip("0").rstrip(".")

    return render_template_string(
        HTML_TEMPLATE,
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
        brecha_ars=brecha_ars,
        brecha_abs=brecha_abs,
        brecha_signo=brecha_signo,
        brecha_porcentaje=brecha_porcentaje,
        brecha_texto=brecha_texto,
        brecha_clase=brecha_clase,
        dolar_blue=dolar_blue,
        dolar_fecha=current_app.config["DOLAR_BLUE_FECHA"],
    )


# ============================================
# HTML TEMPLATE
# ============================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soja: CBOT vs A3 Rosario</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; padding: 30px 20px; }
        .container { max-width: 750px; margin: 0 auto; background: white; border-radius: 32px; padding: 32px; box-shadow: 0 25px 50px rgba(0,0,0,0.25); }
        h1 { font-size: 28px; margin-bottom: 4px; }
        .sub { color: #666; font-size: 14px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #e9ecef; }
        .button-group { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
        .btn-primary { flex: 1; padding: 12px; background: #0f172a; color: white; border: none; border-radius: 40px; font-weight: 600; cursor: pointer; }
        .precio-card { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; border-radius: 24px; padding: 24px; text-align: center; margin-bottom: 24px; }
        .precio-label { font-size: 13px; opacity: 0.8; }
        .precio-valor { font-size: 48px; font-weight: 800; margin: 8px 0; }
        .precio-valor small { font-size: 18px; font-weight: normal; }
        .fecha { font-size: 11px; opacity: 0.6; margin-top: 6px; }
        .grid-2 { display: flex; gap: 20px; margin-bottom: 24px; flex-wrap: wrap; }
        .referencia-card { flex: 1; background: #f8fafc; padding: 20px; border-radius: 20px; text-align: center; border-left: 4px solid #2e7d32; }
        .referencia-precio { font-size: 28px; font-weight: 800; color: #0f172a; }
        .brecha-card { background: #fff8e1; padding: 20px; border-radius: 20px; text-align: center; margin-bottom: 24px; border-left: 4px solid #ff9800; }
        .positivo { color: #15803d; font-weight: bold; }
        .negativo { color: #b91c1c; font-weight: bold; }
        .brecha-numero { font-size: 32px; font-weight: 800; margin: 10px 0; }
        .detalle-card { background: #f1f5f9; padding: 20px; border-radius: 20px; margin-bottom: 24px; }
        .detalle-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e2e8f0; }
        .admin-panel { background: #f1f5f9; padding: 16px; border-radius: 16px; margin: 16px 0; border: 1px solid #cbd5e1; }
        .admin-input { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; align-items: center; }
        .admin-input input { padding: 8px 12px; border-radius: 40px; border: 1px solid #cbd5e1; flex: 1; }
        .admin-input button { background: #475569; padding: 8px 20px; border: none; border-radius: 40px; color: white; cursor: pointer; }
        .footer { font-size: 11px; color: #94a3b8; text-align: center; margin-top: 20px; padding-top: 16px; border-top: 1px solid #e2e8f0; }
        details { cursor: pointer; }
        summary { font-weight: 600; color: #475569; }
    </style>
</head>
<body>
<div class="container">
    <h1>🌱 Soja Argentina</h1>
    <div class="sub">CBOT Julio (ZSN26) vs A3 Rosario · Dólar Blue</div>
    
    <div class="button-group">
        <form method="POST" action="/auto-fetch-cbot" style="flex:1">
            <button type="submit" class="btn-primary">🔍 Auto-Fetch CBOT</button>
        </form>
    </div>
    
    <div class="precio-card">
        <div class="precio-label">📊 CBOT SOJA - CONTRATO JULIO 2026 (ZSN26)</div>
        <div class="precio-valor">$ {{ precio_cbot_formateado }} <small>USD/bushel</small></div>
        <div class="fecha">Actualizado: {{ fecha_cbot }}</div>
    </div>
    
    <div class="grid-2">
        <div class="referencia-card">
            <div>🇺🇸 CBOT convertido</div>
            <div class="referencia-precio">USD {{ "{:,.2f}".format(cbot_usd_tn) }} <small>/TN</small></div>
            <div style="font-size:12px">🇦🇷 $ {{ "{:,.0f}".format(cbot_ars_tn) }} ARS</div>
        </div>
        <div class="referencia-card" style="border-left-color:#e65100">
            <div>🇦🇷 A3 Rosario</div>
            <div class="referencia-precio">$ {{ "{:,.0f}".format(precio_a3) }} <small>ARS/TN</small></div>
        </div>
    </div>
    
    <div class="brecha-card">
        <div style="font-weight:600">📉 BRECHA CBOT vs PRECIO LOCAL</div>
        <div class="brecha-numero {{ brecha_clase }}">
            {{ brecha_signo }} $ {{ "{:,.0f}".format(brecha_abs) }} ARS/TN
        </div>
        <div>El precio local está <strong>{{ brecha_texto }}</strong> del valor teórico</div>
        <div style="font-size:13px">({{ "%.1f"|format(brecha_porcentaje) }}% por {{ brecha_texto }})</div>
    </div>
    
    <div class="detalle-card">
        <div class="detalle-item"><span>📊 Precio CBOT (USD/TN FOB)</span><strong>USD {{ "{:,.2f}".format(cbot_usd_tn) }}</strong></div>
        <div class="detalle-item"><span>📉 Retenciones ({{ productor_retencion }}%)</span><strong class="negativo">-USD {{ "{:,.2f}".format(cbot_usd_tn * 0.33) }}</strong></div>
        <div class="detalle-item"><span>🚛 Fletes + comisiones</span><strong class="negativo">-USD 25.00</strong></div>
        <div class="detalle-item" style="border-top:2px solid #cbd5e1;margin-top:8px;padding-top:12px"><span>🚜 Precio al productor (USD)</span><strong>USD {{ "{:,.2f}".format(productor_usd) }}</strong></div>
        <div class="detalle-item"><span>🇦🇷 Dólar Blue</span><strong>$ {{ dolar_blue }} ARS</strong></div>
        <div class="detalle-item" style="background:#e8f5e9;border-radius:12px"><span>💰 Precio al productor (ARS)</span><strong class="positivo" style="font-size:18px">$ {{ "{:,.0f}".format(productor_ars) }} ARS/TN</strong></div>
    </div>
    
    <div class="admin-panel">
        <details>
            <summary>⚙️ Admin: Actualizar precios</summary>
            
            <div style="margin-top:15px">
                <strong>🟡 Actualizar CBOT (formato CME ej: 1206'2)</strong>
                <form method="POST" action="/actualizar-cbot-manual" class="admin-input">
                    <input type="text" name="precio_cbot" placeholder="Ej: 1206'2 o 12.0625">
                    <button type="submit">Guardar CBOT</button>
                </form>
            </div>
            
            <div style="margin-top:15px">
                <strong>🟡 Actualizar A3 Rosario (ARS/TN)</strong>
                <form method="POST" action="/actualizar-a3" class="admin-input">
                    <input type="number" name="precio_a3" value="{{ precio_a3 }}" step="1000">
                    <button type="submit">Guardar A3</button>
                </form>
            </div>
            
            <div style="margin-top:15px">
                <strong>💵 Actualizar Dólar Blue (ARS)</strong>
                <form method="POST" action="/actualizar-dolar" class="admin-input">
                    <input type="number" name="dolar_blue" value="{{ dolar_blue }}" step="10">
                    <button type="submit">Guardar Dólar</button>
                </form>
            </div>
        </details>
    </div>
    
    <div class="footer">
        Dólar blue: ${{ dolar_blue }} ARS · Contrato CBOT ZSN26 · Retención soja 33% · Costos USD 25/TN
    </div>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
