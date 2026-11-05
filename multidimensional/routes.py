"""
Rutas de la sección «Análisis multidimensional».

Vistas HTML:
    /analisis-multidimensional                 página principal de la sección
    /analisis-multidimensional/pregunta/1..4   cuatro vistas independientes

API JSON (la usan las vistas para filtros, drill-down, roll-up, slice, dice y pivot):
    POST /analisis-multidimensional/api/pregunta/<n>   cuerpo: estado de la vista
    GET  /analisis-multidimensional/api/salud          estado de la conexión al modelo
"""
import json
import os

from flask import Blueprint, abort, jsonify, render_template, request

from . import conocimientos as K
from . import cubo as C
from . import db
from . import preguntas as P

bp_multidimensional = Blueprint("multidimensional", __name__, url_prefix="/analisis-multidimensional")

PLANTILLAS = {1: "Multidimensional/pregunta1.html", 2: "Multidimensional/pregunta2.html",
              3: "Multidimensional/pregunta3.html", 4: "Multidimensional/pregunta4.html"}


def _cobertura():
    """Periodo y volumen leídos del modelo (no escritos a mano)."""
    tot, _ = C.total()
    meses = C.miembros("tiempo", "mes")
    meses = [m for m in meses if m and m != "Sin dato"]
    return {"vehiculos": tot["n"], "con_muertos": tot["m"], "pct_con_muertos": tot["pct_con_muertos"],
            "desde": meses[0] if meses else None, "hasta": meses[-1] if meses else None,
            "n_meses": len(meses), "departamentos": len([d for d in C.miembros("ubicacion", "departamento") if d != "Sin dato"]),
            "municipios": len([m for m in C.miembros("ubicacion", "municipio") if m != "Sin dato"]),
            "marcas": len([m for m in C.miembros("marca", "marca") if not str(m).startswith("Sin dato")])}


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
    if not ok:
        return render_template("Multidimensional/menu.html", error=error, preguntas=P.PREGUNTAS,
                               dimensiones=C.DIMENSIONES, medidas=C.MEDIDAS, conocimientos=[], cobertura=None,
                               meta={}, conteos={}, validacion=None), 503
    return render_template("Multidimensional/menu.html", error=None, preguntas=P.PREGUNTAS,
                           dimensiones=C.DIMENSIONES, medidas=C.MEDIDAS, conocimientos=K.calcular(),
                           cobertura=_cobertura(), meta=db.metadatos(), conteos=_conteos(),
                           validacion=_validacion())


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
                           filtros=P.opciones_filtros(numero), conocimientos=K.por_pregunta(numero),
                           dimensiones=C.DIMENSIONES, medidas=C.MEDIDAS, cobertura=_cobertura())


@bp_multidimensional.route("/api/pregunta/<int:numero>", methods=["POST"])
def api_pregunta(numero):
    estado = request.get_json(silent=True) or {}
    try:
        return jsonify(P.resolver(numero, estado))
    except C.ErrorConsulta as exc:
        return jsonify({"error": str(exc)}), 400


@bp_multidimensional.route("/api/salud")
def api_salud():
    ok, error = db.motor_disponible()
    return jsonify({"modelo_disponible": ok, "error": error,
                    "motor": db.url_modelo().split(":")[0]}), (200 if ok else 503)
