"""
Reglas de transformación del modelo multidimensional (Etapa 5).

Este módulo concentra TODAS las reglas que convierten los datos tratados de la
Etapa 3 (base IntegracionSiniestrosVehiculos, tabla dbo.Vehiculo y sus catálogos)
en atributos del modelo estrella. Las mismas reglas están escritas en T-SQL en
modelo_multidimensional/sql/02_carga_dimensiones.sql y 03_carga_hechos.sql;
si se cambia una regla aquí, debe cambiarse también allí.

Todas las comparaciones de texto se hacen sin tildes y en mayúsculas para que el
resultado no dependa de la codificación del archivo ni de la intercalación
(collation) del servidor.
"""
import unicodedata


def normalizar(texto):
    """Mayúsculas y sin tildes. 'Bogotá D.C.' -> 'BOGOTA D.C.'; 'Nariño' -> 'NARINO'."""
    if texto is None:
        return ""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    )
    return sin_tildes.upper().strip()


# ---------------------------------------------------------------------------
# DimTiempo
# ---------------------------------------------------------------------------
NOMBRES_MES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
               "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
NOMBRES_MES_CORTO = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago",
                     "Sep", "Oct", "Nov", "Dic"]


# ---------------------------------------------------------------------------
# DimUbicacion: región natural de Colombia por departamento
# (asignación convencional; un departamento pertenece a una sola región)
# ---------------------------------------------------------------------------
REGIONES = {
    "Caribe": ["ATLANTICO", "BOLIVAR", "CESAR", "CORDOBA", "LA GUAJIRA", "MAGDALENA", "SUCRE"],
    "Pacífica": ["CHOCO", "CAUCA", "NARINO", "VALLE DEL CAUCA"],
    "Orinoquía": ["ARAUCA", "CASANARE", "META", "VICHADA"],
    "Amazonía": ["AMAZONAS", "CAQUETA", "GUAINIA", "GUAVIARE", "PUTUMAYO", "VAUPES"],
    "Andina": ["ANTIOQUIA", "BOGOTA D.C.", "BOYACA", "CALDAS", "CUNDINAMARCA", "HUILA",
               "NORTE DE SANTANDER", "QUINDIO", "RISARALDA", "SANTANDER", "TOLIMA"],
}


def region_natural(departamento):
    d = normalizar(departamento)
    if d.startswith("ARCHIPIELAGO") or d.startswith("SAN ANDRES"):
        return "Insular"
    for region, deptos in REGIONES.items():
        if d in deptos:
            return region
    return "Sin clasificar"


# Provincia de Sabana Centro (Cundinamarca): 11 municipios.
# Es el territorio que da nombre al proyecto; se usa como atributo de ámbito.
SABANA_CENTRO = ["CAJICA", "CHIA", "COGUA", "COTA", "GACHANCIPA", "NEMOCON",
                 "SOPO", "TABIO", "TENJO", "TOCANCIPA", "ZIPAQUIRA"]


def ambito_proyecto(departamento, municipio):
    if normalizar(departamento) == "CUNDINAMARCA":
        if normalizar(municipio) in SABANA_CENTRO:
            return "Sabana Centro"
        return "Resto de Cundinamarca"
    return "Otros departamentos"


# ---------------------------------------------------------------------------
# DimTipoVehiculo: categoría (nivel superior de la jerarquía Categoría > Tipo)
# ---------------------------------------------------------------------------
CATEGORIAS = {
    "Motocicletas y similares": ["MOTOCICLETA", "MOTOCARRO", "CICLOMOTOR", "CUATRIMOTO", "CUADRICICLO"],
    "Vehículo liviano": ["AUTOMOVIL", "CAMIONETA", "CAMPERO"],
    "Transporte de pasajeros": ["BUS", "BUSETA", "MICROBUS"],
    "Vehículo de carga": ["CAMION", "TRACTOCAMION", "VOLQUETA", "REMOLQUE", "SEMIREMOLQUE"],
}
ORDEN_CATEGORIA = {"Motocicletas y similares": 1, "Vehículo liviano": 2, "Transporte de pasajeros": 3,
                   "Vehículo de carga": 4, "Maquinaria agrícola e industrial": 5, "Sin dato": 9}


def categoria_vehiculo(tipo):
    t = normalizar(tipo)
    for categoria, tipos in CATEGORIAS.items():
        if t in tipos:
            return categoria
    return "Maquinaria agrícola e industrial"


# ---------------------------------------------------------------------------
# DimMarca
# ---------------------------------------------------------------------------
# Las 10 marcas con más vehículos en el conjunto completo (conocimiento evidente C2
# de la Etapa 4: reúnen el 73,8 % de los registros). La lista se calcula en el ETL
# a partir de los datos; no se escribe a mano.
TOP_MARCAS = 10


def calidad_marca(nombre_marca, id_marca):
    if id_marca is None:
        return "Faltante (nulo en la fuente)"
    if normalizar(nombre_marca) in ("SIN MARCA", "NO REGISTRADA", ""):
        return "Categoría «Sin marca» declarada en la fuente"
    return "Marca informada"


# ---------------------------------------------------------------------------
# DimAutoridadTransito: tipo de entidad y nivel territorial deducidos del nombre
# ---------------------------------------------------------------------------
def _empieza(n, prefijos):
    return any(n.startswith(p) for p in prefijos)


def _contiene(n, partes):
    return any(p in n for p in partes)


def tipo_entidad(nombre):
    n = normalizar(nombre)
    if _contiene(n, ["POLICIA NACIONAL", "DITRA"]):
        return "Policía Nacional (DITRA)"
    if _empieza(n, ["STRIA", "SECRETAR", "SRIA", "STARIA", "SDT", "SUB"]):
        return "Secretaría de tránsito y movilidad"
    if _empieza(n, ["INSP", "INPS", "INS "]):
        return "Inspección de tránsito"
    if _empieza(n, ["INST", "ITBOY"]):
        return "Instituto de tránsito y transporte"
    if _empieza(n, ["DIR", "DPTO", "DEPTO"]):
        return "Dirección o departamento administrativo"
    if _empieza(n, ["UND ", "UNIDAD", "U TEC"]):
        return "Unidad de tránsito"
    return "Otra entidad (alcaldía, fondo o agencia)"


def nivel_territorial(nombre):
    n = normalizar(nombre)
    if _contiene(n, ["POLICIA NACIONAL", "DITRA"]):
        return "Nacional"
    if (_contiene(n, ["DPTAL", "CUND/", "ATLANTICO/", "HUILA/", "ARAUCA/", "DTAL NARINO"])
            or _empieza(n, ["ITBOY", "UND TTO CALDAS/", "UNIDAD TTO CALDAS/",
                            "AGENCIA DE SEGURIDAD VIAL ANTIOQUIA", "STRIA GOB"])):
        return "Departamental"
    if _contiene(n, ["DISTRITAL", "DIST CARTAGENA", "DTAL TTO BARRANQUILLA", "SANTA MARTA"]):
        return "Distrital"
    return "Municipal"


# ---------------------------------------------------------------------------
# DimGravedad
# ---------------------------------------------------------------------------
def nivel_severidad(nombre):
    n = normalizar(nombre)
    if "MUERT" in n:
        return 2
    if "HERID" in n:
        return 1
    return 0


# ---------------------------------------------------------------------------
# DimAntiguedad y medida EdadAlAccidente
# ---------------------------------------------------------------------------
def edad_al_accidente(anio_accidente, anio_modelo):
    """Regla de la Etapa 4: año del accidente - año del modelo, con mínimo 0.

    La columna EdadVehiculo de la fuente está calculada frente a 2026, no frente
    al año del accidente; por eso se recalcula. Un modelo posterior al año del
    accidente (p. ej. moto modelo 2025 accidentada en 2024) queda con edad 0.
    """
    if anio_accidente is None or anio_modelo is None:
        return None
    return max(0, int(anio_accidente) - int(anio_modelo))


def rango_edad(edad):
    """Rangos usados en la Etapa 4 (orden, etiqueta)."""
    if edad is None or edad < 0:
        return 7, "Sin dato"
    if edad <= 2:
        return 1, "0-2 años"
    if edad <= 5:
        return 2, "3-5 años"
    if edad <= 10:
        return 3, "6-10 años"
    if edad <= 15:
        return 4, "11-15 años"
    if edad <= 20:
        return 5, "16-20 años"
    return 6, "Más de 20 años"


def grupo_edad(edad):
    """Nivel superior de la jerarquía Grupo > Rango > Edad (agrupa rangos completos)."""
    if edad is None or edad < 0:
        return 9, "Sin dato"
    if edad <= 5:
        return 1, "Hasta 5 años"
    if edad <= 15:
        return 2, "De 6 a 15 años"
    return 3, "Más de 15 años"
