#!/usr/bin/env python3
"""
Convertidor CBOT a Pesos Argentinos (Dólar Blue)
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


def precio_a_tonelada(precio_por_bushel: float, grano: str) -> Optional[float]:
    """Convierte precio USD/bushel a USD/tonelada"""
    grano = grano.lower().replace("á", "a")
    factor = FACTORES.get(grano)
    if factor:
        return round(precio_por_bushel / factor, 2)
    return None


# ============================================
# DÓLAR BLUE
# ============================================


def obtener_dolar_blue() -> Dict:
    """Versión simplificada - reemplazar con API real después"""
    return {"compra": 1380, "venta": 1400, "fecha": "2026-05-01"}


def usd_a_ars(precio_usd: float, dolar_blue: Dict) -> float:
    """Convierte USD a ARS usando dólar blue venta"""
    return round(precio_usd * dolar_blue["venta"], 2)


# ============================================
# FRONT END (Versión corregida)
# ============================================

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CBOT a Pesos 🇦🇷</title>
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
        .debug {
            background: #fff3e0;
            border-left-color: #ff9800;
            font-family: monospace;
            font-size: 12px;
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
        
        <!-- IMPORTANTE: method="POST" sin action (envía a la misma URL) -->
        <form method="POST">
            <input type="number" step="any" name="precio" placeholder="Precio en USD / bushel" value="{{ precio_input or '' }}" required>
            <select name="grano">
                <option value="maiz" {{ 'selected' if grano_selected == 'maiz' else '' }}>🌽 Maíz</option>
                <option value="trigo" {{ 'selected' if grano_selected == 'trigo' else '' }}>🌾 Trigo</option>
                <option value="soja" {{ 'selected' if grano_selected == 'soja' else '' }}>🫘 Soja</option>
                <option value="sorgo" {{ 'selected' if grano_selected == 'sorgo' else '' }}>🌾 Sorgo</option>
            </select>
            <button type="submit">Convertir →</button>
        </form>
        
        <!-- SECCIÓN DE RESULTADOS -->
        {% if resultado %}
            {% if resultado.error %}
                <div class="resultado error">
                    <p>{{ resultado.error }}</p>
                </div>
            {% else %}
                <div class="resultado">
                    <p>📊 <strong>{{ resultado.grano_nombre }}</strong> ({{ resultado.precio_input }} USD/bushel)</p>
                    <p class="usd">🇺🇸 <strong>{{ resultado.precio_tn_usd }} USD</strong> / tonelada</p>
                    <p class="ars">🇦🇷 <strong>$ {{ resultado.precio_tn_ars }} ARS</strong> / tonelada</p>
                    <p style="font-size: 12px; margin-top: 12px;">💡 Dólar blue: ${{ dolar_blue.venta }} ARS ({{ dolar_blue.fecha }})</p>
                </div>
            {% endif %}
        {% endif %}
        
        <div class="footer">
            Precios de referencia del CBOT (Chicago). El valor local puede diferir.
        </div>
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    dolar = obtener_dolar_blue()
    resultado = None
    precio_input = ""
    grano_selected = "maiz"

    # Verificar si es una solicitud POST (el usuario envió el formulario)
    if request.method == "POST":
        try:
            # Extraer datos del formulario
            precio_str = request.form.get("precio", "")
            grano = request.form.get("grano", "maiz")
            grano_selected = grano

            print(
                f"🔍 DEBUG: precio_str = '{precio_str}', grano = '{grano}'"
            )  # Esto aparece en logs de Render

            if not precio_str:
                resultado = {"error": "❌ Ingresá un precio válido (ej: 5.50)"}
            else:
                precio = float(precio_str)

                # Mapeo para mostrar nombre lindo
                nombres = {
                    "maiz": "🌽 Maíz",
                    "trigo": "🌾 Trigo",
                    "soja": "🫘 Soja",
                    "sorgo": "🌾 Sorgo",
                }
                grano_nombre = nombres.get(grano, grano)

                # Calcular precio por tonelada en USD
                precio_tn_usd = precio_a_tonelada(precio, grano)

                if precio_tn_usd:
                    # Convertir a ARS
                    precio_tn_ars = usd_a_ars(precio_tn_usd, dolar)

                    resultado = {
                        "grano_nombre": grano_nombre,
                        "precio_input": f"{precio:.2f}",
                        "precio_tn_usd": f"{precio_tn_usd:,.2f}",
                        "precio_tn_ars": f"{precio_tn_ars:,.0f}",
                    }
                    precio_input = f"{precio:.2f}"
                else:
                    resultado = {
                        "error": f"❌ No reconozco '{grano}'. Usá maíz, trigo, soja o sorgo."
                    }

        except ValueError as e:
            print(f"❌ Error de conversión: {e}")
            resultado = {"error": "❌ Ingresá un número válido (ej: 5.50)"}
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            resultado = {"error": f"❌ Error: {str(e)}"}

    return render_template_string(
        HTML,
        dolar_blue=dolar,
        resultado=resultado,
        precio_input=precio_input,
        grano_selected=grano_selected,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
