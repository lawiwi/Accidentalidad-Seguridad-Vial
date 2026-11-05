from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os
import json

app = Flask(__name__)


# Almacenamiento temporal en memoria
reportes_temp = []

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/reportar", methods=["POST"])
def reportar():
    try:
        data = request.get_json()
        
        reporte = {
            "tipo": data["tipo"],
            "descripcion": data["descripcion"],
            "latitud": float(data["latitud"]),
            "longitud": float(data["longitud"]),
            "fecha_hora": datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p"),
            "municipio": "Sabana Centro"  # Temporal
        }
        
        reportes_temp.append(reporte)
        return jsonify({"mensaje": "Reporte guardado con éxito ✅", "municipio": "Sabana Centro"})
    
    except Exception as e:
        print(f"Error en reportar: {e}")
        return jsonify({"error": "Error al guardar el reporte"}), 500

@app.route("/obtener_reportes")
def obtener_reportes():
    return jsonify(reportes_temp)

@app.route("/lista")
def lista():
    return render_template("lista.html", reportes=reportes_temp)

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)