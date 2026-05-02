#!/usr/bin/env python3
"""
Convertidor CBOT a Pesos Argentinos (Dólar Blue)
CON AUTO-FETCH + ENTRADA MANUAL OPCIONAL
"""

from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime
import os
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================
# CONVERSIONES DE GRANOS
# ============================================

FACTORES = {
    "soja": 0.0272155,  # 60 lb/bu
}


def precio_a_tonelada(precio_por_bushel: float) -> float:
    """Convierte precio USD/bushel a USD/tonelada para soja"""
    return round(precio_por_bushel / FACTORES["soja"], 2)


# ============================================
# COSTOS ARGENTINOS (Soja)
# ============================================

RETENCION_SOJA = 0.33  # 33%
COSTOS_FIJOS_USD = 25  # USD/TN (flete + comisiones)


def precio_argentina(precio_usd_tn: float, dolar_blue: float) -> dict:
    """Calcula precio real que recibe el productor en Argentina"""
    valor_post_retencion = precio_usd_tn * (1 - RETENCION_SOJA)
    valor_en_puerto_usd = valor_post_retencion - COSTOS_FIJOS_USD
    valor_en_puerto_ars = valor_en_puerto_usd * dolar_blue
    return {
        "retencion_pct": int(RETENCION_SOJA * 100),
        "precio_usd_puerto": round(valor_en_puerto_usd, 2),
        "precio_ars_puerto": round(valor_en_puerto_ars, 0),
    }


# ============================================
# DÓLAR BLUE
# ============================================


def obtener_dolar_blue() -> dict:
    """Dólar blue actual - actualizar manualmente cuando cambie"""
    return {"compra": 1380, "venta": 1400, "fecha": "2026-05-01"}


# ============================================
# AUTO-FETCH PRICE
# ============================================


def auto_fetch_price():
    """Obtiene el precio de Yahoo Finance (último cierre)"""
    try:
        ticker = yf.Ticker("ZSN26.F")
        data = ticker.history(period="2d")
        if not data.empty:
            latest_close = data["Close"].iloc[-1]
            return round(latest_close, 2)
    except Exception as e:
        print(f"Auto-fetch error: {e}")
    return None


# ============================================
# FRONT END
# ============================================

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CBOT a Pesos | Soja Argentina</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            width: 100%;
            background: white;
            border-radius: 28px;
            padding: 32px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { font-size: 28px; margin-bottom: 4px; }
        .sub { color: #666; font-size: 13px; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #eee; }
        
        .precio-card {
            background: #1a1a2e;
            color: white;
            border-radius: 20px;
            padding: 24px;
            text-align: center;
            margin-bottom: 24px;
        }
        .precio-label { font-size: 13px; opacity: 0.8; margin-bottom: 8px; }
        .precio-valor { font-size: 48px; font-weight: 800; }
        .precio-valor small { font-size: 18px; font-weight: normal; }
        .fecha { font-size: 11px; opacity: 0.7; margin-top: 8px; }
        
        .button-group {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
        }
        .btn-auto {
            flex: 1;
            padding: 14px;
            background: #1565C0;
            color: white;
            border: none;
            border-radius: 14px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-auto:hover { background: #0D47A1; }
        
        .divider {
            text-align: center;
            color: #999;
            font-size: 12px;
            margin: 16px 0;
            position: relative;
        }
        .divider::before, .divider::after {
            content: "";
            position: absolute;
            top: 50%;
            width: 45%;
            height: 1px;
            background: #ddd;
        }
        .divider::before { left: 0; }
        .divider::after { right: 0; }
        
        .input-group {
            margin-bottom: 16px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
            font-size: 14px;
        }
        input {
            width: 100%;
            padding: 14px 16px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 14px;
            font-family: inherit;
        }
        .btn-manual {
            width: 100%;
            padding: 14px;
            background: #2e7d32;
            color: white;
            border: none;
            border-radius: 14px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-manual:hover { background: #1b5e20; }
        
        .resultado {
            margin-top: 28px;
            padding: 20px;
            background: #e8f5e9;
            border-radius: 20px;
            border-left: 5px solid #2e7d32;
        }
        .usd { font-size: 20px; font-weight: 700; color: #1a1a2e; }
        .ars { font-size: 24px; font-weight: 800; color: #2e7d32; }
        .ars-real { font-size: 28px; font-weight: 800; color: #e65100; }
        .footer {
            margin-top: 24px;
            font-size: 11px;
            color: #999;
            text-align: center;
        }
        .info {
            font-size: 12px;
            color: #666;
            margin-top: 12px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌽 CBOT → Argentina 🇦🇷</h1>
        <div class="sub">Soja · Contrato Julio (ZSN26) · Dólar Blue</div>
        
        <div class="precio-card">
            <div class="precio-label">📊 Precio CBOT Soja</div>
            <div class="precio-valor">${{ precio_bushel }} <small>USD/bushel</small></div>
            <div class="fecha">Actualizado: {{ fecha_actualizacion }}</div>
        </div>
        
        <div class="button-group">
            <form method="POST" action="/auto-fetch" style="flex: 1;">
                <button type="submit" class="btn-auto">🔍 Obtener último precio</button>
            </form>
        </div>
        
        <div class="divider">o ingresar manualmente</div>
        
        <form method="POST">
            <div class="input-group">
                <label>✏️ Ingresar precio manual</label>
                <input type="number" step="any" name="precio_bushel" placeholder="Ej: 12.00" value="">
            </div>
            <button type="submit" name="action" value="manual" class="btn-manual">Actualizar Precio</button>
        </form>
        
        <div class="resultado">
            <p><strong>📊 Conversión a tonelada métrica</strong></p>
            <p class="usd">🇺🇸 <strong>{{ precio_tn_usd }} USD</strong> / tonelada (FOB)</p>
            <p class="ars">🇦🇷 <strong>$ {{ precio_teorico_ars }} ARS</strong> / tonelada (valor exportación)</p>
            
            <hr style="margin: 16px 0; border: none; border-top: 1px dashed #ccc;">
            
            <p><strong>🚜 PRECIO ESTIMADO AL PRODUCTOR</strong></p>
            <p>📉 Retención: {{ retencion_pct }}%</p>
            <p>🚛 Fletes + comisiones: USD {{ costos_fijos }}/TN</p>
            <p class="ars-real">🇦🇷 <strong>$ {{ precio_productor_ars }} ARS</strong> / tonelada</p>
            <p style="font-size: 11px; margin-top: 10px;">(Precio en puerto Rosario)</p>
        </div>
        
        <div class="footer">
            Dólar blue: ${{ dolar_blue_venta }} ARS · Retención soja 33%
        </div>
    </div>
</body>
</html>
"""

# ============================================
# VALORES GLOBALES
# ============================================

precio_bushel_actual = 12.00
fecha_actualizacion = datetime.now().strftime("%Y-%m-%d %H:%M")

# ============================================
# RUTAS DE LA APP
# ============================================


@app.route("/auto-fetch", methods=["POST"])
def auto_fetch():
    global precio_bushel_actual, fecha_actualizacion
    fetched_price = auto_fetch_price()
    if fetched_price:
        precio_bushel_actual = fetched_price
        fecha_actualizacion = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} (auto)"
    return redirect(url_for("index"))


@app.route("/", methods=["GET", "POST"])
def index():
    global precio_bushel_actual, fecha_actualizacion

    if request.method == "POST":
        action = request.form.get("action")

        if action == "manual":
            try:
                nuevo_precio = float(request.form.get("precio_bushel", 0))
                if nuevo_precio > 0:
                    precio_bushel_actual = nuevo_precio
                    fecha_actualizacion = datetime.now().strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass

    # Obtener dólar blue
    dolar = obtener_dolar_blue()
    dolar_venta = dolar["venta"]

    # Calcular conversiones con el precio actual
    precio_tn_usd = precio_a_tonelada(precio_bushel_actual)
    precio_teorico_ars = round(precio_tn_usd * dolar_venta, 0)

    # Calcular precio productor Argentina
    productor = precio_argentina(precio_tn_usd, dolar_venta)

    return render_template_string(
        HTML,
        precio_bushel=f"{precio_bushel_actual:.2f}",
        fecha_actualizacion=fecha_actualizacion,
        precio_tn_usd=f"{precio_tn_usd:,.2f}",
        precio_teorico_ars=f"{precio_teorico_ars:,.0f}",
        retencion_pct=productor["retencion_pct"],
        costos_fijos=COSTOS_FIJOS_USD,
        precio_productor_ars=f"{productor['precio_ars_puerto']:,.0f}",
        dolar_blue_venta=dolar_venta,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
