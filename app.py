#!/usr/bin/env python3
"""
Convertidor CBOT a Pesos Argentinos (Dólar Blue)
Sin la complejidad del agente - solo conversión directa
"""

from flask import Flask, request, render_template_string
from datetime import date
from typing import Dict, Optional

app = Flask(__name__)

# ============================================
# CONVERSIONES DE GRANOS
# ============================================

FACTORES = {
    "maiz": 0.0254,
    "maíz": 0.0254,
    "trigo": 0.0272155,
    "soja": 0.0272155,
    "sorgo": 0.0254,
}


def bushels_a_toneladas(bushels: float, grano: str) -> Optional[float]:
    """Convierte bushels a toneladas métricas"""
    grano = grano.lower().replace("á", "a")
    factor = FACTORES.get(grano)
    if factor:
        return round(bushels * factor, 2)
    return None


def precio_a_tonelada(precio_por_bushel: float, grano: str) -> Optional[float]:
    """Convierte precio USD/bushel a USD/tonelada"""
    grano = grano.lower().replace("á", "a")
    factor = FACTORES.get(grano)
    if factor:
        return round(precio_por_bushel / factor, 2)
    return None


# ============================================
# DÓLAR BLUE (simulado - luego conectás API real)
# ============================================


def obtener_dolar_blue() -> Dict:
    """
    Versión simplificada - en producción usar:
    https://api.bluelytics.com.ar/v2/latest
    """
    # Datos actualizados al 1 de mayo 2026
    return {"compra": 1380, "venta": 1400, "fecha": "2026-05-01"}


def usd_a_ars(precio_usd: float, dolar_blue: Dict) -> float:
    """Convierte USD a ARS usando dólar blue venta"""
    return round(precio_usd * dolar_blue["venta"], 2)


# ============================================
# FRONT END (HTML minimalista)
# ============================================

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CBOT a Pesos 🇦🇷 | Dólar Blue</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 550px;
            width: 100%;
            background: white;
            border-radius: 28px;
            padding: 32px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            font-size: 28px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sub {
            color: #666;
            font-size: 14px;
            margin-bottom: 28px;
            padding-bottom: 16px;
            border-bottom: 1px solid #eee;
        }
        .dolar-card {
            background: #f5f7fa;
            border-radius: 16px;
            padding: 14px 18px;
            margin-bottom: 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .dolar-label {
            font-weight: 600;
            color: #2c3e66;
        }
        .dolar-value {
            font-size: 22px;
            font-weight: 700;
            color: #1a1a2e;
        }
        .dolar-value small { font-size: 12px; font-weight: normal; color: #666; }
        input, select {
            width: 100%;
            padding: 14px 16px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 14px;
            margin-bottom: 14px;
            font-family: inherit;
        }
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
            transition: background 0.2s;
        }
        button:hover { background: #1b5e20; }
        .resultado {
            margin-top: 28px;
            padding: 20px;
            background: #e8f5e9;
            border-radius: 20px;
            border-left: 5px solid #2e7d32;
        }
        .resultado p {
            margin: 8px 0;
            font-size: 18px;
        }
        .resultado .usd { font-size: 24px; font-weight: 700; color: #1a1a2e; }
        .resultado .ars { font-size: 28px; font-weight: 800; color: #2e7d32; }
        .footer {
            margin-top: 24px;
            font-size: 11px;
            color: #999;
            text-align: center;
        }
        .error {
            background: #ffebee;
            border-left-color: #c62828;
            color: #c62828;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌽 CBOT → Pesos 🇦🇷</h1>
        <div class="sub">Precios de Chicago convertidos a toneladas + dólar blue</div>
        
        <div class="dolar-card">
            <span class="dolar-label">💵 Dólar Blue (venta)</span>
            <span class="dolar-value">${{ dolar_blue.venta }} <small>ARS</small></span>
        </div>
        
        <form method="POST">
            <input type="number" step="0.01" name="precio" placeholder="Precio en USD / bushel" value="{{ precio_input or '' }}" required>
            <select name="grano">
                <option value="maiz" {{ 'selected' if grano_selected == 'maiz' else '' }}>🌽 Maíz</option>
                <option value="trigo" {{ 'selected' if grano_selected == 'trigo' else '' }}>🌾 Trigo</option>
                <option value="soja" {{ 'selected' if grano_selected == 'soja' else '' }}>🫘 Soja</option>
                <option value="sorgo" {{ 'selected' if grano_selected == 'sorgo' else '' }}>🌾 Sorgo</option>
            </select>
            <button type="submit">Convertir →</button>
        </form>
        
        {% if resultado %}
        <div class="resultado">
            <p>📊 <strong>{{ grano_nombre }}</strong> ({{ precio_input }} USD/bushel)</p>
            <p class="usd">🇺🇸 <strong>{{ precio_tn_usd }} USD</strong> / tonelada</p>
            <p class="ars">🇦🇷 <strong>$ {{ precio_tn_ars }} ARS</strong> / tonelada</p>
            <p style="font-size: 12px; margin-top: 12px;">💡 Dólar blue: ${{ dolar_blue.venta }} ARS ({{ dolar_blue.fecha }})</p>
        </div>
        {% endif %}
        
        <div class="footer">
            Precios de referencia del CBOT (Chicago). El valor local puede diferir.
        </div>
    </div>
</body>
</html>
"""

# ============================================
# RUTAS DE LA APP
# ============================================


@app.route("/", methods=["GET", "POST"])
def index():
    dolar = obtener_dolar_blue()
    resultado = None
    precio_input = ""
    grano_selected = "maiz"

    if request.method == "POST":
        try:
            precio = float(request.form.get("precio", 0))
            grano = request.form.get("grano", "maiz")
            grano_selected = grano

            # Mapeo para mostrar nombre lindo
            nombres = {
                "maiz": "Maíz",
                "trigo": "Trigo",
                "soja": "Soja",
                "sorgo": "Sorgo",
            }
            grano_nombre = nombres.get(grano, grano)

            # Calcular precio por tonelada en USD
            precio_tn_usd = precio_a_tonelada(precio, grano)

            if precio_tn_usd:
                # Convertir a ARS
                precio_tn_ars = usd_a_ars(precio_tn_usd, dolar)
                precio_input = f"{precio:.2f}"

                resultado = {
                    "grano_nombre": grano_nombre,
                    "precio_tn_usd": f"{precio_tn_usd:,.2f}",
                    "precio_tn_ars": f"{precio_tn_ars:,.0f}",
                }
            else:
                resultado = {
                    "error": f"❌ No reconozco '{grano}'. Usá maíz, trigo, soja o sorgo."
                }
        except:
            resultado = {"error": "❌ Ingresá un precio válido (ej: 5.50)"}

    return render_template_string(
        HTML,
        dolar_blue=dolar,
        resultado=resultado,
        precio_input=precio_input,
        grano_selected=grano_selected,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
