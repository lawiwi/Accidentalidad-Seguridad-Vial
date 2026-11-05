"""
Motor de consultas multidimensionales sobre el modelo estrella.

Conceptos:
  - Una DIMENSIÓN tiene NIVELES (columnas de la tabla de dimensión) y una JERARQUÍA
    (lista ordenada de niveles de lo general a lo particular).
  - Un EJE es (dimension, nivel): las agrupaciones del GROUP BY.
  - Un FILTRO es {(dimension, nivel): [valores]}: el WHERE.

Operaciones multidimensionales (todas cambian la consulta SQL, no solo la gráfica):
  - drill_down / roll_up : cambian el nivel del eje dentro de la jerarquía.
  - slice                : filtro con un solo valor en una dimensión.
  - dice                 : filtros sobre dos o más dimensiones.
  - pivot                : intercambia las dimensiones de filas y columnas de la matriz.

Medidas: la consulta devuelve SOLO componentes aditivos (sumas y conteos):
    n  = SUM(CantidadVehiculos)            -> vehículos (aditiva)
    m  = SUM(VehiculoAccidenteConMuertos)  -> vehículos en accidentes con muertos (aditiva)
    se = SUM(EdadAlAccidente), ce = COUNT(EdadAlAccidente)
Los porcentajes y promedios se calculan DESPUÉS de agregar (m/n, se/ce, n/N), por eso
se recalculan correctamente en cualquier nivel y nunca se suman porcentajes.
"""
import json
from functools import lru_cache

from . import db

# ---------------------------------------------------------------------------
# Catálogo de dimensiones (lista blanca: nada del usuario se concatena al SQL)
# ---------------------------------------------------------------------------
DIMENSIONES = {
    "tiempo": {
        "nombre": "Tiempo", "tabla": "DimTiempo", "alias": "t", "clave": "SK_Tiempo",
        "jerarquia": ["anio", "semestre", "trimestre", "mes"],
        "niveles": {
            "anio": ("Año", "t.Anio", "t.Anio"),
            "semestre": ("Semestre", "t.AnioSemestre", "t.AnioSemestre"),
            "trimestre": ("Trimestre", "t.AnioTrimestre", "t.AnioTrimestre"),
            "mes": ("Mes", "t.AnioMes", "t.AnioMes"),
            "mes_calendario": ("Mes del año", "t.NombreMesCorto", "t.NumeroMes"),
            "cobertura": ("Cobertura del año", "t.CoberturaAnio", "t.CoberturaAnio"),
        },
    },
    "ubicacion": {
        "nombre": "Ubicación", "tabla": "DimUbicacion", "alias": "u", "clave": "SK_Ubicacion",
        "jerarquia": ["region", "departamento", "municipio"],
        "niveles": {
            "region": ("Región natural", "u.RegionNatural", "u.RegionNatural"),
            "departamento": ("Departamento", "u.Departamento", "u.Departamento"),
            "municipio": ("Municipio", "u.MunicipioDepartamento", "u.MunicipioDepartamento"),
            "ambito": ("Ámbito del proyecto", "u.AmbitoProyecto", "u.AmbitoProyecto"),
        },
    },
    "tipo": {
        "nombre": "Tipo de vehículo", "tabla": "DimTipoVehiculo", "alias": "tv", "clave": "SK_TipoVehiculo",
        "jerarquia": ["categoria", "tipo"],
        "niveles": {
            "categoria": ("Categoría", "tv.CategoriaVehiculo", "tv.OrdenCategoria"),
            "tipo": ("Tipo de vehículo", "tv.TipoVehiculo", "tv.TipoVehiculo"),
        },
    },
    "marca": {
        "nombre": "Marca", "tabla": "DimMarca", "alias": "m", "clave": "SK_Marca",
        "jerarquia": ["grupo", "marca"],
        "niveles": {
            "grupo": ("Grupo de marca", "m.GrupoMarca", "m.GrupoMarca"),
            "marca": ("Marca", "m.Marca", "m.Marca"),
            "calidad": ("Calidad del dato de marca", "m.CalidadDato", "m.CalidadDato"),
        },
    },
    "gravedad": {
        "nombre": "Gravedad", "tabla": "DimGravedad", "alias": "g", "clave": "SK_Gravedad",
        "jerarquia": ["gravedad"],
        "niveles": {"gravedad": ("Gravedad", "g.Gravedad", "g.NivelSeveridad")},
    },
    "autoridad": {
        "nombre": "Autoridad de tránsito", "tabla": "DimAutoridadTransito", "alias": "a", "clave": "SK_Autoridad",
        "jerarquia": ["nivel", "autoridad"],
        "niveles": {
            "nivel": ("Nivel territorial", "a.NivelTerritorial", "a.NivelTerritorial"),
            "tipo_entidad": ("Tipo de entidad", "a.TipoEntidad", "a.TipoEntidad"),
            "autoridad": ("Autoridad", "a.Autoridad", "a.Autoridad"),
        },
    },
    "antiguedad": {
        "nombre": "Antigüedad", "tabla": "DimAntiguedad", "alias": "an", "clave": "SK_Antiguedad",
        "jerarquia": ["grupo", "rango", "edad"],
        "niveles": {
            "grupo": ("Grupo de antigüedad", "an.GrupoEdad", "an.OrdenGrupo"),
            "rango": ("Rango de antigüedad", "an.RangoEdad", "an.OrdenRango"),
            "edad": ("Años de antigüedad", "an.EdadAnios", "an.EdadAnios"),
        },
    },
}

MEDIDAS = {
    "vehiculos": {"nombre": "Vehículos involucrados", "unidad": "vehículos",
                  "formula": "SUM(CantidadVehiculos)", "agregacion": "Suma (aditiva)"},
    "con_muertos": {"nombre": "Vehículos en accidentes con muertos", "unidad": "vehículos",
                    "formula": "SUM(VehiculoAccidenteConMuertos)", "agregacion": "Suma (aditiva)"},
    "pct_con_muertos": {"nombre": "% en accidentes con muertos", "unidad": "%",
                        "formula": "SUM(VehiculoAccidenteConMuertos) / SUM(CantidadVehiculos)",
                        "agregacion": "Razón recalculada en cada nivel (no se suma)"},
    "participacion": {"nombre": "Participación", "unidad": "%",
                      "formula": "SUM(CantidadVehiculos) del grupo / SUM(CantidadVehiculos) de la selección",
                      "agregacion": "Razón recalculada; denominador = total de la selección activa"},
    "edad_promedio": {"nombre": "Edad promedio al accidente", "unidad": "años",
                      "formula": "SUM(EdadAlAccidente) / COUNT(EdadAlAccidente)",
                      "agregacion": "Promedio ponderado recalculado (no se promedian promedios)"},
}


class ErrorConsulta(ValueError):
    """Parámetro de consulta no permitido (dimensión o nivel inexistente)."""


def nivel_def(dim, nivel):
    try:
        d = DIMENSIONES[dim]
        return d, d["niveles"][nivel]
    except KeyError as exc:
        raise ErrorConsulta(f"Dimensión o nivel no válido: {dim}.{nivel}") from exc


def nivel_inferior(dim, nivel):
    j = DIMENSIONES[dim]["jerarquia"]
    return j[j.index(nivel) + 1] if nivel in j and j.index(nivel) < len(j) - 1 else None


def nivel_superior(dim, nivel):
    j = DIMENSIONES[dim]["jerarquia"]
    return j[j.index(nivel) - 1] if nivel in j and j.index(nivel) > 0 else None


# ---------------------------------------------------------------------------
# Construcción de la consulta
# ---------------------------------------------------------------------------
def construir_sql(ejes, filtros):
    """ejes: lista de (dim, nivel). filtros: dict {(dim, nivel): [valores]}.
    Devuelve (sql, parametros). Solo se unen las dimensiones necesarias."""
    usadas, select, group, order, where, params = [], [], [], [], [], {}
    for i, (dim, nivel) in enumerate(ejes):
        d, (_, etiqueta, orden) = nivel_def(dim, nivel)
        usadas.append(dim)
        select += [f"{etiqueta} AS e{i}", f"{orden} AS o{i}"]
        group += [etiqueta, orden] if etiqueta != orden else [etiqueta]
        order.append(f"o{i}")
    k = 0
    for (dim, nivel), valores in sorted(filtros.items()):
        if not valores:
            continue
        d, (_, etiqueta, _) = nivel_def(dim, nivel)
        usadas.append(dim)
        marcas = []
        for v in valores:
            params[f"p{k}"] = v
            marcas.append(f":p{k}")
            k += 1
        where.append(f"{etiqueta} IN ({', '.join(marcas)})")
    joins = []
    for dim in dict.fromkeys(usadas):
        d = DIMENSIONES[dim]
        joins.append(f"JOIN {d['tabla']} {d['alias']} ON {d['alias']}.{d['clave']} = f.{d['clave']}")
    medidas = ("SUM(f.CantidadVehiculos) AS n, SUM(f.VehiculoAccidenteConMuertos) AS m, "
               "SUM(f.EdadAlAccidente) AS se, COUNT(f.EdadAlAccidente) AS ce")
    sql = "SELECT " + ", ".join(select + [medidas]) + "\nFROM FactVehiculoAccidente f"
    if joins:
        sql += "\n" + "\n".join(joins)
    if where:
        sql += "\nWHERE " + "\n  AND ".join(where)
    if group:
        sql += "\nGROUP BY " + ", ".join(group)
        sql += "\nORDER BY " + ", ".join(order)
    return sql, params


def sql_legible(sql, params):
    """Sustituye los parámetros para mostrar la consulta en la página (solo visualización)."""
    out = sql
    for k in sorted(params, key=lambda x: -len(x)):
        v = params[k]
        out = out.replace(":" + k, str(v) if isinstance(v, (int, float)) else "'" + str(v).replace("'", "''") + "'")
    return out


@lru_cache(maxsize=512)
def _agregar_cache(clave):
    ejes, filtros = json.loads(clave)
    filtros = {tuple(k.split("|")): v for k, v in filtros.items()}
    sql, params = construir_sql([tuple(e) for e in ejes], filtros)
    filas = db.consultar(sql, params)
    return sql, params, filas


def agregar(ejes, filtros=None):
    """Ejecuta la agregación y devuelve (filas, sql_legible). Cada fila trae:
    claves (tupla de etiquetas), n, m, se, ce y las medidas derivadas."""
    filtros = {k: list(v) for k, v in (filtros or {}).items() if v}
    clave = json.dumps([[list(e) for e in ejes], {"|".join(k): v for k, v in sorted(filtros.items())}],
                       ensure_ascii=False, default=str)
    sql, params, filas = _agregar_cache(clave)
    resultado = []
    for f in filas:
        claves = tuple(f[f"e{i}"] for i in range(len(ejes)))
        resultado.append(derivar(claves, f["n"], f["m"], f["se"], f["ce"]))
    return resultado, sql_legible(sql, params)


def derivar(claves, n, m, se, ce):
    n, m, se, ce = int(n or 0), int(m or 0), float(se or 0), int(ce or 0)
    return {
        "claves": claves, "n": n, "m": m, "se": se, "ce": ce,
        "pct_con_muertos": (m / n) if n else None,
        "edad_promedio": (se / ce) if ce else None,
    }


def total(filtros=None):
    filas, sql = agregar([], filtros)
    return (filas[0] if filas else derivar((), 0, 0, 0, 0)), sql


def mediana_edad(filtros=None):
    """Mediana de EdadAlAccidente a partir del histograma por edad (portable entre motores)."""
    filas, _ = agregar([("antiguedad", "edad")], filtros)
    filas = [f for f in filas if f["claves"][0] is not None and f["claves"][0] >= 0]
    tot = sum(f["n"] for f in filas)
    if not tot:
        return None
    acumulado, mitad = 0, tot / 2
    for f in filas:
        acumulado += f["n"]
        if acumulado >= mitad:
            return f["claves"][0]
    return None


def miembros(dim, nivel, filtros=None):
    """Valores de un nivel con datos (para llenar los filtros), en el orden de la dimensión."""
    filas, _ = agregar([(dim, nivel)], filtros)
    return [f["claves"][0] for f in filas]


def pivotar(filas, eje_filas, eje_columnas):
    """Arma una matriz {fila: {columna: celda}} desde una agregación de dos ejes.
    eje_filas / eje_columnas son índices (0 o 1) dentro de 'claves'; pivotar = intercambiarlos."""
    orden_f, orden_c, celdas = [], [], {}
    for f in filas:
        kf, kc = f["claves"][eje_filas], f["claves"][eje_columnas]
        if kf not in orden_f:
            orden_f.append(kf)
        if kc not in orden_c:
            orden_c.append(kc)
        celdas.setdefault(kf, {})[kc] = f
    return orden_f, orden_c, celdas
