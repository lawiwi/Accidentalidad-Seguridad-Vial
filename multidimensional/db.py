"""
Conexión al modelo estrella (SQLAlchemy Core).

Por defecto la aplicación consulta la réplica SQLite del modelo estrella:
    modelo_multidimensional/dw/dw_accidentalidad_vial.sqlite
Esa réplica se genera con modelo_multidimensional/etl/construir_dw.py y contiene las
mismas tablas, columnas y reglas que DW_AccidentalidadVial en SQL Server.

Para consultar directamente SQL Server, defina la variable de entorno DW_DATABASE_URL, p. ej.:
    DW_DATABASE_URL=mssql+pyodbc://@localhost\\SQL2025/DW_AccidentalidadVial?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
(requiere `pip install pyodbc` y el controlador ODBC de Microsoft).

Las consultas del módulo cubo.py usan SQL estándar (SELECT/JOIN/WHERE/GROUP BY/SUM/COUNT),
compatible con ambos motores.
"""
import os
import sqlite3
from functools import lru_cache
from urllib.request import pathname2url

from sqlalchemy import create_engine, text

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_SQLITE = os.path.join(RAIZ, "modelo_multidimensional", "dw", "dw_accidentalidad_vial.sqlite")


def url_modelo():
    url = os.getenv("DW_DATABASE_URL", "").strip()
    if url:
        return url
    return "sqlite:///" + RUTA_SQLITE.replace("\\", "/")


@lru_cache(maxsize=1)
def motor():
    url = url_modelo()
    if url.startswith("sqlite:///"):
        ruta = url.replace("sqlite:///", "", 1)
        if not os.path.exists(ruta):
            raise FileNotFoundError(
                "No se encontró la base del modelo estrella en " + ruta +
                ". Ejecute: python modelo_multidimensional/etl/construir_dw.py")
        # Solo lectura: la aplicación nunca modifica el modelo. pathname2url codifica
        # espacios y unidades de Windows (C:\...) para que la URI de SQLite sea válida.
        uri = "file:" + pathname2url(os.path.abspath(ruta)) + "?mode=ro"
        return create_engine("sqlite://", creator=lambda: sqlite3.connect(uri, uri=True, check_same_thread=False))
    return create_engine(url, pool_pre_ping=True)


def consultar(sql, parametros=None):
    """Ejecuta una consulta de lectura y devuelve una lista de diccionarios."""
    with motor().connect() as cn:
        resultado = cn.execute(text(sql), parametros or {})
        columnas = list(resultado.keys())
        return [dict(zip(columnas, fila)) for fila in resultado.fetchall()]


def motor_disponible():
    try:
        consultar("SELECT COUNT(*) AS n FROM DimGravedad")
        return True, None
    except Exception as exc:  # noqa: BLE001 - se informa en la página
        return False, str(exc)


def metadatos():
    try:
        return {f["Clave"]: f["Valor"] for f in consultar("SELECT Clave, Valor FROM MetadatosModelo")}
    except Exception:  # noqa: BLE001 - la tabla no existe en SQL Server
        return {}
