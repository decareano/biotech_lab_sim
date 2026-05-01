from flask import Flask, request, render_template_string
import re

app = Flask(__name__)

# --- PASTE YOUR ENTIRE EXISTING AGENT CODE HERE ---
# (Your ConvertidorGranos and AgenteGranos classes)
# Make sure they are exactly as you have them working now.
# --- ---

# Simple HTML Front End (You can expand this later)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Convertidor de Granos Argentina</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; text-align: center; }
        input, button { padding: 10px; margin: 5px; width: 80%; }
        .result { background: #f0f0f0; padding: 20px; border-radius: 10px; margin-top: 20px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h1>🌽 CBOT a Toneladas y Pesos 🇦🇷</h1>
    <form method="POST">
        <input type="text" name="query" placeholder="Ej: 5000 bushels de maíz a toneladas" required>
        <button type="submit">Convertir</button>
    </form>
    {% if result %}
    <div class="result">{{ result }}</div>
    {% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        query = request.form["query"]
        agent = AgenteGranos()  # Instantiate your agent class
        parsed = agent.parsear_consulta(query)
        if parsed:
            result = agent.ejecutar(parsed)
        else:
            result = "❌ No entendí tu consulta. Probá con '5000 bushels de maíz a toneladas'"
    return render_template_string(HTML_TEMPLATE, result=result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
