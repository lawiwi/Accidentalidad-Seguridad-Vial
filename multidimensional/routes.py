"""
Rutas de la sección «Análisis multidimensional».

Vistas HTML:
    /analisis-multidimensional                 página principal (mapa de secciones y preguntas)
    /analisis-multidimensional/seccion/<slug>  ocho secciones del recorrido (contexto … conclusiones)
    /analisis-multidimensional/pregunta/1..4   cuatro vistas independientes

API JSON (la usan las vistas para filtros, drill-down, roll-up, slice, dice y pivot):
    POST /analisis-multidimensional/api/pregunta/<n>   cuerpo: estado de la vista
    GET  /analisis-multidimensional/api/salud          estado de la conexión al modelo
"""
import json
import os
from functools import lru_cache

from flask import Blueprint, abort, jsonify, render_template, request

from . import conocimientos as K
from . import cubo as C
from . import db
from . import preguntas as P

bp_multidimensional = Blueprint("multidimensional", __name__, url_prefix="/analisis-multidimensional")

PLANTILLAS = {1: "Multidimensional/pregunta1.html", 2: "Multidimensional/pregunta2.html",
              3: "Multidimensional/pregunta3.html", 4: "Multidimensional/pregunta4.html"}

# Secciones del recorrido (página principal en forma de mapa, como la Etapa 3).
# El orden de la lista es el orden de lectura sugerido; cada sección es una página propia.
SECCIONES = [
    {"slug": "contexto", "titulo": "Contexto y alcance",
     "resumen": "Propósito, unidad de análisis, granularidad y relación con la Etapa 4."},
    {"slug": "modelo", "titulo": "Modelo estrella",
     "resumen": "Tabla de hechos, siete dimensiones y diagrama del modelo."},
    {"slug": "dimensiones", "titulo": "Dimensiones y jerarquías",
     "resumen": "Qué responde cada dimensión, sus atributos, niveles y número de filas."},
    {"slug": "medidas", "titulo": "Medidas",
     "resumen": "Cómo se calcula y agrega cada medida y cuáles se pueden sumar."},
    {"slug": "operaciones", "titulo": "Operaciones OLAP",
     "resumen": "Drill-down, roll-up, slice, dice y pivot, con ejemplos y dónde probarlos."},
    {"slug": "validacion", "titulo": "Validación de la carga",
     "resumen": "Comparación del modelo con los datos tratados de la Etapa 3."},
    {"slug": "conocimientos", "titulo": "Conocimientos",
     "resumen": "Los ocho hallazgos multidimensionales calculados sobre el modelo."},
    {"slug": "conclusiones", "titulo": "Limitaciones y conclusiones",
     "resumen": "Lo que el modelo no permite afirmar, lo que aporta y el origen de los datos."},
]
SECCIONES_POR_SLUG = {s["slug"]: dict(s, numero=i) for i, s in enumerate(SECCIONES, start=1)}


@lru_cache(maxsize=1)
def _cobertura():
    """Periodo y volumen leídos del modelo (no escritos a mano)."""
    tot, _ = C.total()
    periodo = db.consultar(
        "SELECT MIN(AnioMes) AS desde, MAX(AnioMes) AS hasta, "
        "COUNT(DISTINCT AnioMes) AS n_meses "
        "FROM DimTiempo WHERE SK_Tiempo <> -1 AND AnioMes IS NOT NULL AND AnioMes <> 'Sin dato'"
    )[0]
    ubicacion = db.consultar(
        "SELECT COUNT(DISTINCT Departamento) AS departamentos, "
        "COUNT(DISTINCT MunicipioDepartamento) AS municipios "
        "FROM DimUbicacion WHERE SK_Ubicacion <> -1 "
        "AND Departamento IS NOT NULL AND Departamento <> 'Sin dato' "
        "AND MunicipioDepartamento IS NOT NULL AND MunicipioDepartamento <> 'Sin dato'"
    )[0]
    marcas = db.consultar(
        "SELECT COUNT(DISTINCT Marca) AS marcas FROM DimMarca "
        "WHERE SK_Marca <> -1 AND Marca IS NOT NULL AND Marca NOT LIKE 'Sin dato%'"
    )[0]["marcas"]
    return {"vehiculos": tot["n"], "con_muertos": tot["m"], "pct_con_muertos": tot["pct_con_muertos"],
            "desde": periodo["desde"], "hasta": periodo["hasta"], "n_meses": periodo["n_meses"],
            "departamentos": ubicacion["departamentos"], "municipios": ubicacion["municipios"],
            "marcas": marcas}


def _conteos():
    tablas = ["DimTiempo", "DimUbicacion", "DimTipoVehiculo", "DimMarca", "DimGravedad",
              "DimAutoridadTransito", "DimAntiguedad", "FactVehiculoAccidente"]
    return {t: db.consultar(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"] for t in tablas}


def _validacion():
    """Reporte generado por el ETL (modelo_multidimensional/dw/validacion_etl.json)."""
    ruta = os.path.join(db.RAIZ, "modelo_multidimensional", "dw", "validacion_etl.json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


@bp_multidimensional.route("/")
def inicio():
    ok, error = db.motor_disponible()
    secciones = [SECCIONES_POR_SLUG[s["slug"]] for s in SECCIONES]
    if not ok:
        return render_template("Multidimensional/menu.html", error=error, preguntas=P.PREGUNTAS,
                               dimensiones=C.DIMENSIONES, secciones=secciones, cobertura=None), 503
    return render_template("Multidimensional/menu.html", error=None, preguntas=P.PREGUNTAS,
                           dimensiones=C.DIMENSIONES, secciones=secciones, cobertura=_cobertura())


@bp_multidimensional.route("/seccion/<slug>")
def seccion(slug):
    """Una sección del recorrido; solo se consulta lo que esa sección muestra."""
    actual = SECCIONES_POR_SLUG.get(slug)
    if actual is None:
        abort(404)
    secciones = [SECCIONES_POR_SLUG[s["slug"]] for s in SECCIONES]
    i = actual["numero"] - 1
    nav = {"anterior": secciones[i - 1] if i > 0 else None,
           "siguiente": secciones[i + 1] if i + 1 < len(secciones) else None}
    ok, error = db.motor_disponible()
    datos = {"error": error, "seccion": actual, "secciones": secciones, "nav": nav,
             "preguntas": P.PREGUNTAS, "dimensiones": C.DIMENSIONES, "medidas": C.MEDIDAS,
             "cobertura": None, "conteos": {}, "conocimientos": [], "validacion": None, "meta": {}}
    if not ok:
        return render_template("Multidimensional/seccion.html", **datos), 503
    datos["cobertura"] = _cobertura()
    if slug == "dimensiones":
        datos["conteos"] = _conteos()
    elif slug == "validacion":
        datos["validacion"] = _validacion()
    elif slug == "conocimientos":
        datos["conocimientos"] = K.calcular()
    elif slug == "conclusiones":
        datos["meta"] = db.metadatos()
    return render_template("Multidimensional/seccion.html", **datos)


@bp_multidimensional.route("/pregunta/<int:numero>")
def pregunta(numero):
    if numero not in P.PREGUNTAS:
        abort(404)
    ok, error = db.motor_disponible()
    cfg = P.PREGUNTAS[numero]
    if not ok:
        return render_template(PLANTILLAS[numero], error=error, numero=numero, cfg=cfg, filtros=[],
                               conocimientos=[], dimensiones=C.DIMENSIONES, medidas=C.MEDIDAS, cobertura=None), 503
    return render_template(PLANTILLAS[numero], error=None, numero=numero, cfg=cfg,
                           filtros=P.opciones_filtros(numero), conocimientos=[],
                           dimensiones=C.DIMENSIONES, medidas=C.MEDIDAS, cobertura=_cobertura())


@bp_multidimensional.route("/api/pregunta/<int:numero>", methods=["POST"])
def api_pregunta(numero):
    estado = request.get_json(silent=True) or {}
    try:
        return jsonify(P.resolver(numero, estado))
    except C.ErrorConsulta as exc:
        return jsonify({"error": str(exc)}), 400


@bp_multidimensional.route("/api/pregunta/<int:numero>/conocimientos")
def api_conocimientos(numero):
    if numero not in P.PREGUNTAS:
        abort(404)
    return render_template("Multidimensional/_conocimientos.html",
                           conocimientos=K.por_pregunta(numero))


@bp_multidimensional.route("/api/salud")
def api_salud():
    ok, error = db.motor_disponible()
    return jsonify({"modelo_disponible": ok, "error": error,
                    "motor": db.url_modelo().split(":")[0]}), (200 if ok else 503)
