#!/usr/bin/env python3
"""
Convertidor CBOT a Pesos Argentinos + Referencia A3 Rosario (Manual)
"""

from flask import Flask, request, render_template_string, redirect, url_for, session
from datetime import datetime
import os
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================
# 1. LOGICA DE CONVERSION (CBOT)
# ============================================
FACTOR_SOJA = 0.0272155  # 60 lb/bu
RETENCION_SOJA = 0.33
COSTOS_FIJOS_USD = 25


def precio_a_tonelada(precio_bushel):
    return round(precio_bushel / FACTOR_SOJA, 2)


def precio_argentina(precio_usd_tn, dolar_blue_venta):
    precio_con_retencion = precio_usd_tn * (1 - RETENCION_SOJA)
    precio_final_usd = precio_con_retencion - COSTOS_FIJOS_USD
    precio_final_ars = precio_final_usd * dolar_blue_venta
    return {
        "retencion_pct": int(RETENCION_SOJA * 100),
        "precio_usd_puerto": round(precio_final_usd, 2),
        "precio_ars_puerto": round(precio_final_ars, 0),
    }


# ============================================
# 2. OBTENCION DE PRECIOS
# ============================================
def obtener_precio_cbot():
    """Auto-fetch desde Yahoo Finance (contrato ZSN26)"""
    try:
        ticker = yf.Ticker("ZSN26.F")
        data = ticker.history(period="1d")
        if not data.empty:
            return round(data["Close"].iloc[-1], 2)
    except Exception as e:
        print(f"Error fetching CBOT: {e}")
    return None


def obtener_dolar_blue():
    return {"venta": 1400, "compra": 1380, "fecha": "2026-05-01"}  # Placeholder


# ============================================
# 3. VARIABLES GLOBALES (Datos)
# ============================================
precio_bushel_cbot = 12.00  # Valor inicial por defecto
precio_tn_a3 = 430000  # <--- PRECIO DE ROSARIO (Actualizar manualmente)
fecha_actualizacion_cbot = "No actualizado"
fecha_actualizacion_a3 = "No actualizado"

# ============================================
# 4. FRONT END (HTML)
# ============================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Soja: CBOT vs A3 Rosario</title>
    <style>
        body { font-family: sans-serif; background: #1a1a2e; display: flex; justify-content: center; padding: 2rem; }
        .card { max-width: 700px; background: white; border-radius: 2rem; padding: 2rem; box-shadow: 0 20px 35px rgba(0,0,0,0.2); }
        h1 { margin: 0 0 0.5rem 0; }
        .precio-box { background: #0f172a; color: white; border-radius: 1.5rem; padding: 1.5rem; text-align: center; margin: 1.5rem 0; }
        .precio-grande { font-size: 2.5rem; font-weight: bold; }
        .grid-2 { display: flex; gap: 1.5rem; margin: 1.5rem 0; flex-wrap: wrap; }
        .referencia { flex: 1; background: #f8fafc; padding: 1rem; border-radius: 1rem; text-align: center; border-left: 5px solid #2e7d32; }
        .brecha { background: #fff3e0; padding: 1rem; border-radius: 1rem; text-align: center; margin: 1rem 0; }
        .positivo { color: #15803d; }
        .negativo { color: #b91c1c; }
        button { background: #2563eb; color: white; border: none; padding: 0.7rem 1.2rem; border-radius: 2rem; cursor: pointer; margin-top: 1rem; width: 100%; font-weight: bold; }
        .footer { font-size: 0.7rem; text-align: center; margin-top: 1.5rem; color: #64748b; }
        .admin-panel { background: #f1f5f9; padding: 1rem; border-radius: 1rem; margin: 1rem 0; font-size: 0.8rem; border: 1px solid #cbd5e1; }
        input { padding: 0.4rem; border-radius: 0.5rem; border: 1px solid #cbd5e1; width: 120px; }
        small { color: #475569; }
    </style>
</head>
<body>
<div class="card">
    <h1>🌱 Soja Argentina</h1>
    <p>CBOT Julio (ZSN26) vs A3 Rosario</p>

    <!-- Botón de Auto-Fetch CBOT -->
    <form method="POST" action="/auto-fetch-cbot">
        <button type="submit" style="background: #0f172a;">🔍 Actualizar Precio CBOT</button>
    </form>

    <!-- Panel de Precios -->
    <div class="precio-box">
        📊 <strong>Precio CBOT (soja)</strong><br>
        <span class="precio-grande">USD {{ "%.2f"|format(precio_cbot) }} / bushel</span><br>
        <small>Actualizado: {{ fecha_cbot }}</small>
    </div>

    <div class="grid-2">
        <div class="referencia">
            <strong>🇺🇸 CBOT (convertido)</strong><br>
            <span class="precio-grande" style="font-size: 1.8rem;">USD {{ cbot_usd_tn }} / TN</span><br>
            <span>🇦🇷 $ {{ cbot_ars_tn }} ARS</span>
        </div>
        <div class="referencia">
            <strong>🇦🇷 A3 Rosario (Referencia)</strong><br>
            <span class="precio-grande" style="font-size: 1.8rem;">$ {{ a3_ars_tn }} ARS / TN</span>
        </div>
    </div>

    <!-- Brecha de Precios -->
    <div class="brecha">
        <strong>📉 Brecha CBOT vs Precio Local (Rosario)</strong><br>
        <span class="{% if brecha_ars > 0 %}positivo{% else %}negativo{% endif %}" style="font-weight: bold;">
            {% if brecha_ars > 0 %}Positiva (+){% else %}Negativa{% endif %} 
            $ {{ "%0.f"|format(brecha_ars|abs) }} ARS/TN
        </span><br>
        <small>El precio local está 
            {% if brecha_ars > 0 %}por DEBAJO{% else %}por ENCIMA{% endif %} 
            del valor teórico de exportación.
        </small>
    </div>

    <!-- Panel de Configuración (Solo para administradores) -->
    <div class="admin-panel">
        <details>
            <summary>⚙️ Admin: Actualizar precio A3 Rosario</summary>
            <form method="POST" action="/actualizar-a3" style="margin-top: 1rem;">
                <label>Precio A3 Soja (ARS/TN): </label>
                <input type="number" name="precio_a3" value="{{ a3_ars_tn }}" step="1000">
                <button type="submit" style="display: inline-block; width: auto; margin-top: 0; padding: 0.4rem 1rem;">Guardar</button>
                <p><small>⚠️ Solo actualizar con el precio de cierre del contrato líder en Rosario</small></p>
            </form>
        </details>
    </div>

    <div class="footer">
        Dólar Blue: ${{ dolar_blue }} ARS | Contrato CBOT ZSN26 | Retención Soja 33% + Costos Fijos
    </div>
</div>
</body>
</html>
"""


# ============================================
# 5. RUTAS DE LA APLICACIÓN
# ============================================
@app.route("/auto-fetch-cbot", methods=["POST"])
def auto_fetch_cbot():
    global precio_bushel_cbot, fecha_actualizacion_cbot
    precio = obtener_precio_cbot()
    if precio:
        precio_bushel_cbot = precio
        fecha_actualizacion_cbot = datetime.now().strftime("%Y-%m-%d %H:%M")
    return redirect(url_for("index"))


@app.route("/actualizar-a3", methods=["POST"])
def actualizar_a3():
    global precio_tn_a3, fecha_actualizacion_a3
    try:
        nuevo_precio = int(request.form.get("precio_a3", 0))
        if nuevo_precio > 0:
            precio_tn_a3 = nuevo_precio
            fecha_actualizacion_a3 = datetime.now().strftime("%Y-%m-%d %H:%M")
    except:
        pass
    return redirect(url_for("index"))


@app.route("/", methods=["GET"])
def index():
    # 1. Obtener valores actuales
    global precio_bushel_cbot, fecha_actualizacion_cbot, precio_tn_a3, fecha_actualizacion_a3
    dolar = obtener_dolar_blue()
    dolar_venta = dolar["venta"]

    # 2. Calcular conversiones
    cbot_usd_tn = precio_a_tonelada(precio_bushel_cbot)
    cbot_ars_tn = cbot_usd_tn * dolar_venta

    # 3. Calcular Brecha (CBOT vs A3)
    brecha_ars = cbot_ars_tn - precio_tn_a3

    return render_template_string(
        HTML_TEMPLATE,
        precio_cbot=precio_bushel_cbot,
        fecha_cbot=fecha_actualizacion_cbot,
        cbot_usd_tn=f"{cbot_usd_tn:,.2f}",
        cbot_ars_tn=f"{cbot_ars_tn:,.0f}",
        a3_ars_tn=f"{precio_tn_a3:,}",
        brecha_ars=brecha_ars,
        dolar_blue=dolar_venta,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
