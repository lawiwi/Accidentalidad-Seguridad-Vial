from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os
from flask import session

from flask import Flask, render_template, request, jsonify, session, redirect
import json
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import pandas as pd
from utils.excel_db import guardar_reporte, cargar_usuarios, verificar_login, registrar_usuario, cargar_reportes

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTES_PATH = os.path.join(ROOT_DIR, "reportes.xlsx")
# Cargar variables de entorno
load_dotenv()
from utils.excel_db import registrar_usuario

def crear_admin_por_defecto():
    df = cargar_usuarios()
    if not ((df["Correo"] == "nicolas72lol@gmail.com") & (df["Rol"] == "admin")).any():
        registrar_usuario("Nicolás", "nicolas72lol@gmail.com", "admin", rol="admin")
        print("✅ Usuario administrador creado por defecto")

crear_admin_por_defecto()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "clave-segura")
# Variable global para el GeoJSON
sabana_geojson = None

def cargar_geojson():
    global sabana_geojson
    try:
        geojson_path = 'static/sabana_centro.geojson'
        if not os.path.exists(geojson_path) or os.path.getsize(geojson_path) == 0:
            print(f"⚠️ Archivo {geojson_path} no válido")
            return False
        with open(geojson_path, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
            if not contenido:
                print(f"⚠️ Archivo {geojson_path} vacío")
                return False
            sabana_geojson = json.loads(contenido)
            print(f"✅ GeoJSON cargado con {len(sabana_geojson['features'])} municipios")
            return True
    except Exception as e:
        print(f"❌ Error cargando GeoJSON: {e}")
        return False

def obtener_municipio(lat, lng):
    if not sabana_geojson:
        return "Sabana Centro"
    try:
        coords_municipios = {
            'Chía': {'min_lat': 4.8, 'max_lat': 5.0, 'min_lng': -74.1, 'max_lng': -73.9},
            'Cajicá': {'min_lat': 4.9, 'max_lat': 5.0, 'min_lng': -74.1, 'max_lng': -73.9},
            'Zipaquirá': {'min_lat': 5.0, 'max_lat': 5.2, 'min_lng': -74.1, 'max_lng': -73.9},
            'Tabio': {'min_lat': 4.9, 'max_lat': 5.0, 'min_lng': -74.2, 'max_lng': -74.0},
            'Tenjo': {'min_lat': 4.8, 'max_lat': 5.0, 'min_lng': -74.2, 'max_lng': -74.0},
            'Cota': {'min_lat': 4.8, 'max_lat': 5.0, 'min_lng': -74.1, 'max_lng': -74.0},
            'Funza': {'min_lat': 4.7, 'max_lat': 4.8, 'min_lng': -74.2, 'max_lng': -74.1},
            'Mosquera': {'min_lat': 4.7, 'max_lat': 4.8, 'min_lng': -74.2, 'max_lng': -74.1},
            'Madrid': {'min_lat': 4.7, 'max_lat': 4.8, 'min_lng': -74.3, 'max_lng': -74.2},
            'El Rosal': {'min_lat': 4.8, 'max_lat': 5.0, 'min_lng': -74.3, 'max_lng': -74.2},
            'Subachoque': {'min_lat': 4.9, 'max_lat': 5.0, 'min_lng': -74.2, 'max_lng': -74.1},
            'Bojacá': {'min_lat': 4.7, 'max_lat': 4.9, 'min_lng': -74.3, 'max_lng': -74.2}
        }
        for municipio, bbox in coords_municipios.items():
            if bbox['min_lat'] <= lat <= bbox['max_lat'] and bbox['min_lng'] <= lng <= bbox['max_lng']:
                return municipio
        return "Sabana Centro"
    except Exception as e:
        print(f"Error determinando municipio: {e}")
        return "Sabana Centro"

cargar_geojson()

os.makedirs('logs', exist_ok=True)
handler = RotatingFileHandler('logs/app.log', maxBytes=1024*1024, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

@app.route("/")
def home():
    nombre = session.get("usuario")
    rol = session.get("rol")
    return render_template("index.html", nombre=nombre, rol=rol)

@app.route("/reportar", methods=["GET", "POST"])
def reportar():
    if "usuario" not in session:
        return redirect("/login")
    if request.method == "GET":
        return render_template("reportar.html")
    try:
        data = request.get_json()
        nombre = session.get("usuario")
        df_usuarios = cargar_usuarios()
        usuario_id = df_usuarios[df_usuarios["Nombre"] == nombre]["Usuario_ID"].values[0]

        guardar_reporte(data["tipo"], data["descripcion"], float(data["latitud"]), float(data["longitud"]), usuario_id=usuario_id)

        municipio = obtener_municipio(float(data["latitud"]), float(data["longitud"]))
        return jsonify({"mensaje": "Reporte guardado con éxito ✅", "municipio": municipio})
    except Exception as e:
        print(f"Error en reportar: {e}")
        return jsonify({"error": "Error al guardar el reporte"}), 500

@app.route("/lista")
def lista():
    try:
        df = pd.read_excel("reportes.xlsx")
        # Convertir la columna 'Fecha' al formato esperado por el template
        df["Fecha y hora"] = pd.to_datetime(df["Fecha"]).dt.strftime("%d/%m/%Y, %I:%M:%S %p")
        reportes = df.rename(columns={
            "Tipo": "tipo",
            "Descripción": "descripcion",
            "Latitud": "latitud",
            "Longitud": "longitud",
            "Fecha y hora": "fecha_hora"
        }).to_dict(orient="records")
        return render_template("lista.html", reportes=reportes)
    except Exception as e:
        print(f"Error cargando lista: {e}")
        return render_template("lista.html", reportes=[])

@app.route("/login", methods=["GET", "POST"])
def login_view():
    if request.method == "POST":
        correo = request.form.get("email")
        clave = request.form.get("password")
        usuario = verificar_login(correo, clave)
        if usuario:
            session["usuario"] = usuario["Nombre"]
            session["rol"] = usuario["Rol"]
            if usuario["Rol"] == "admin":
                return redirect("/admin/dashboard")
            else:
                return redirect("/dashboard")
        else:
            return render_template("login.html", error="Credenciales inválidas")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register_view():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        correo = request.form.get("email")
        clave = request.form.get("password")
        registrar_usuario(nombre, correo, clave, rol="usuario")
        return render_template("login.html", mensaje="Usuario registrado con éxito")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# =========================
# ETAPA 1 - MINERÍA DE DATOS
# =========================

@app.route("/Etapa1")
def Etapa1():
    return render_template("Etapa1/menu.html")


@app.route("/Etapa1/problema")
def Etapa1_problema():
    return render_template("Etapa1/problema.html")


@app.route("/Etapa1/preguntas")
def Etapa1_preguntas():
    return render_template("Etapa1/preguntas.html")


@app.route("/Etapa1/necesidades")
def Etapa1_necesidades():
    return render_template("Etapa1/necesidades.html")


@app.route("/Etapa1/fuentes")
def Etapa1_fuentes():
    return render_template("Etapa1/fuentes.html")


@app.route("/Etapa1/dataset")
def dataset():
    import pandas as pd

    try:
        ruta = "data/vehiculos_accidentes.csv"
        df = pd.read_csv(ruta)

        # Información general
        registros = len(df)
        variables = len(df.columns)

        # Tamaño aproximado
        tamano_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)

        # Columnas
        columnas = list(df.columns)

        # Primeros registros
        muestra = df.head(10).to_dict(orient="records")

        # Valores faltantes
        faltantes = int(df.isnull().sum().sum())

        # Duplicados
        duplicados = int(df.duplicated().sum())

        # Fechas
        df["fecha_accidente"] = pd.to_datetime(
            df["fecha_accidente"],
            errors="coerce"
        )

        fecha_inicio = df["fecha_accidente"].min()
        fecha_fin = df["fecha_accidente"].max()

        return render_template(
            "Etapa1/dataset.html",
            registros=registros,
            variables=variables,
            tamano_mb=tamano_mb,
            columnas=columnas,
            muestra=muestra,
            faltantes=faltantes,
            duplicados=duplicados,
            fecha_inicio=fecha_inicio.strftime("%Y-%m-%d") if pd.notna(fecha_inicio) else "N/D",
            fecha_fin=fecha_fin.strftime("%Y-%m-%d") if pd.notna(fecha_fin) else "N/D"
        )

    except Exception as e:
        return f"Error al cargar el dataset: {e}", 500


@app.route("/Etapa1/diccionario")
def Etapa1_diccionario():
    return render_template("Etapa1/diccionario.html")


@app.route("/Etapa1/calidad")
def Etapa1_calidad():
    return render_template("Etapa1/calidad.html")


@app.route("/Etapa1/limitaciones")
def Etapa1_limitaciones():
    return render_template("Etapa1/limitaciones.html")

@app.route("/dashboard")
def dashboard_view():
    if "usuario" not in session:
        return redirect("/login")
    nombre = session["usuario"]
    df_usuarios = cargar_usuarios()
    df_reportes = cargar_reportes()

    # Obtener el ID del usuario actual
    usuario_id = df_usuarios[df_usuarios["Nombre"] == nombre]["Usuario_ID"].values[0]

    # Filtrar los reportes del usuario
    df_mios = df_reportes[df_reportes["Usuario_ID"] == usuario_id]

    total = len(df_mios)
    ultimos = df_mios.sort_values("Fecha", ascending=False).head(5)
    tipos = df_mios["Tipo"].value_counts().to_dict()

    return render_template("dashboard.html",
        nombre=nombre,
        total=total,
        ultimos=ultimos,
        tipos=tipos,
        todos=df_mios
    )

@app.route("/admin/dashboard")
def admin_dashboard_view():
    df_usuarios = cargar_usuarios()
    df_reportes = cargar_reportes()

    total_usuarios = len(df_usuarios)
    total_reportes = len(df_reportes)

    # Unir reportes con nombres
    df_merged = pd.merge(df_reportes, df_usuarios[["Usuario_ID", "Nombre"]], on="Usuario_ID", how="left")
    df_merged["Fecha"] = pd.to_datetime(df_merged["Fecha"]).dt.strftime("%d/%m/%Y %H:%M")
    ultimos = df_merged.sort_values("Fecha", ascending=False).head(10)

    return render_template("admin_dashboard.html",
        total_usuarios=total_usuarios,
        total_reportes=total_reportes,
        ultimos=ultimos
    )

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.errorhandler(500)
def internal_error(e):
    app.logger.exception("Internal server error")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)