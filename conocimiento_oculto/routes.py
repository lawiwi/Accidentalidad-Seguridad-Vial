"""
Etapa 6 · Sección «Conocimiento Oculto».

    /conocimiento-oculto/           síntesis de hallazgos (supervisado, clustering, YouTube) + informe + video
    /conocimiento-oculto/informe    abre o descarga el informe técnico en PDF

Las cifras NO se escriben a mano en la plantilla: se leen de data/conocimiento_oculto/resultados_etapa6.json,
que el equipo actualiza con los resultados finales de Orange y del análisis de comentarios.
El enlace del video se toma de la variable de entorno VIDEO_ETAPA6_URL o del JSON.
"""
import json
import os

from flask import Blueprint, abort, render_template, send_from_directory

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_RESULTADOS = os.path.join(RAIZ, "data", "conocimiento_oculto", "resultados_etapa6.json")
CARPETA_DOCS = os.path.join(RAIZ, "static", "docs")
INFORME = "Informe_Etapa6.pdf"

bp_conocimiento_oculto = Blueprint("conocimiento_oculto", __name__, url_prefix="/conocimiento-oculto")


def cargar_resultados():
    with open(RUTA_RESULTADOS, encoding="utf-8") as f:
        return json.load(f)


def embed_youtube(url):
    """Convierte https://www.youtube.com/watch?v=ID o https://youtu.be/ID en la URL de inserción."""
    if not url:
        return ""
    if "youtu.be/" in url:
        vid = url.split("youtu.be/")[1].split("?")[0]
    elif "v=" in url:
        vid = url.split("v=")[1].split("&")[0]
    else:
        return ""
    return f"https://www.youtube-nocookie.com/embed/{vid}"


@bp_conocimiento_oculto.route("/")
def inicio():
    try:
        R = cargar_resultados()
    except (OSError, ValueError) as exc:
        return render_template("ConocimientoOculto/menu.html", R=None, error=str(exc))
    video = os.getenv("VIDEO_ETAPA6_URL", "") or R.get("enlaces", {}).get("video", "")
    return render_template("ConocimientoOculto/menu.html", R=R, error=None,
                           video_url=video, video_embed=embed_youtube(video),
                           hay_informe=os.path.exists(os.path.join(CARPETA_DOCS, INFORME)))


@bp_conocimiento_oculto.route("/informe")
def informe():
    if not os.path.exists(os.path.join(CARPETA_DOCS, INFORME)):
        abort(404)
    return send_from_directory(CARPETA_DOCS, INFORME, mimetype="application/pdf")
