#!/usr/bin/env python3
"""
Convertidor CBOT a Pesos Argentinos (Dólar Blue)
CON ENTRADA MANUAL DE PRECIO - Sin scraping, sin APIs externas
"""

from flask import Flask, request, render_template_string, session
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Necesario para session

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
# DÓLAR BLUE (Hardcodeado - editable manualmente)
# ============================================


def obtener_dolar_blue() -> dict:
    """Dólar blue actual - se puede actualizar manualmente desde la interfaz"""
    # Valores por defecto (actualizar según corresponda)
    return {"compra": 1380, "venta": 1400, "fecha": "2026-05-01"}


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
        
        .input-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
        }
        input, select {
            width: 100%;
            padding: 14px 16px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 14px;
            font-family: inherit;
        }
        .precio-actual {
            background: #1a1a2e;
            color: white;
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            margin-bottom: 24px;
        }
        .precio-label { font-size: 13px; opacity: 0.8; }
        .precio-valor { font-size: 42px; font-weight: 800; }
        .precio-valor small { font-size: 16px; font-weight: normal; }
        .fecha { font-size: 11px; opacity: 0.7; margin-top: 6px; }
        
        button {
            width: 100%;
            padding: 14px;
            background: #2e7d32;
            color: white;
            border: none;
            border-radius: 14px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 8px;
        }
        button:hover { background: #1b5e20; }
        
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
        
        <div class="precio-actual">
            <div class="precio-label">📊 Precio CBOT actual (ingresado manualmente)</div>
            <div class="precio-valor">${{ precio_bushel }} <small>USD/bushel</small></div>
            <div class="fecha">Última actualización: {{ fecha_actualizacion }}</div>
        </div>
        
        <form method="POST">
            <div class="input-group">
                <label>✏️ Actualizar precio CBOT (Soja Julio ZSN26)</label>
                <input type="number" step="any" name="precio_bushel" placeholder="Ej: 12.00" value="{{ precio_input }}" required>
            </div>
            <button type="submit" name="action" value="update_price">⟳ Actualizar Precio</button>
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
            <p style="font-size: 11px; margin-top: 10px;">(Precio en puerto Rosario, antes de impuestos internos)</p>
        </div>
        
        <div class="info">
            💡 <strong>Cómo usar:</strong> Ingresá el precio de cierre del contrato Julio (ZSN26) que ves en Bloomberg, Reuters o tu broker, y presioná "Actualizar Precio".
        </div>
        
        <div class="footer">
            Dólar blue: ${{ dolar_blue_venta }} ARS (venta) · Retención soja 33%
        </div>
    </div>
</body>
</html>
"""

# ============================================
# RUTAS DE LA APP
# ============================================

# Valores por defecto
precio_bushel_actual = 12.00
fecha_actualizacion = datetime.now().strftime("%Y-%m-%d %H:%M")


@app.route("/", methods=["GET", "POST"])
def index():
    global precio_bushel_actual, fecha_actualizacion

    precio_input = ""

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_price":
            try:
                nuevo_precio = float(request.form.get("precio_bushel", 0))
                if nuevo_precio > 0:
                    precio_bushel_actual = nuevo_precio
                    fecha_actualizacion = datetime.now().strftime("%Y-%m-%d %H:%M")
                    precio_input = f"{nuevo_precio:.2f}"
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
        precio_input=precio_input,
        precio_tn_usd=f"{precio_tn_usd:,.2f}",
        precio_teorico_ars=f"{precio_teorico_ars:,.0f}",
        retencion_pct=productor["retencion_pct"],
        costos_fijos=COSTOS_FIJOS_USD,
        precio_productor_ars=f"{productor['precio_ars_puerto']:,.0f}",
        dolar_blue_venta=dolar_venta,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
