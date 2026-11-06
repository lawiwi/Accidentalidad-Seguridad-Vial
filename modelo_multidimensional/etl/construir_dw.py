"""
ETL del modelo estrella de vehículos accidentados -> base SQLite consultada por Flask.

Uso (desde la raíz del repositorio):

    # 1) Desde los datos tratados exportados de SQL Server (incluidos en el repo)
    python modelo_multidimensional/etl/construir_dw.py

    # 2) Leyendo directamente la base tratada de la Etapa 3 en SQL Server
    #    (requiere: pip install pyodbc  y el ODBC Driver 17/18 for SQL Server)
    python modelo_multidimensional/etl/construir_dw.py --origen sqlserver ^
        --url "mssql+pyodbc://@localhost\\SQL2025/IntegracionSiniestrosVehiculos?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

Resultado: modelo_multidimensional/dw/dw_accidentalidad_vial.sqlite y
           modelo_multidimensional/dw/validacion_etl.json

Fuente: únicamente dbo.Vehiculo y sus catálogos (no se lee dbo.Siniestro).
El proceso es idempotente: borra y reconstruye el archivo en cada ejecución.
Las mismas reglas están implementadas en T-SQL en modelo_multidimensional/sql/.
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import reglas as R  # noqa: E402

RAIZ_MODELO = os.path.dirname(AQUI)
ORIGEN_CSV = os.path.join(RAIZ_MODELO, "origen_tratado")
SALIDA = os.path.join(RAIZ_MODELO, "dw", "dw_accidentalidad_vial.sqlite")
REPORTE = os.path.join(RAIZ_MODELO, "dw", "validacion_etl.json")

TABLAS_ORIGEN = ["Vehiculo", "Fecha", "DepartamentoMunicipio", "Departamento", "Municipio",
                 "Marca", "TipoVehiculo", "GravedadAccidente", "AutoridadTransito"]

# Consultas de extracción para el modo SQL Server: SOLO la fuente de vehículos.
SQL_EXTRACCION = {
    "Vehiculo": "SELECT IdVehiculo, AnioModelo, EdadVehiculo, IdFechaAccidente, IdDepartamentoMunicipio, "
                "IdMarca, IdTipoVehiculo, IdGravedadAccidente, IdAutoridadTransito, FilaOrigen FROM dbo.Vehiculo",
    "Fecha": "SELECT f.IdFecha, f.FechaCompleta, f.Anio, f.Trimestre, f.NumeroMes, f.NombreMes, f.NumeroDia, "
             "f.DiaSemana, f.NombreDiaSemana FROM dbo.Fecha f "
             "WHERE f.IdFecha IN (SELECT IdFechaAccidente FROM dbo.Vehiculo)",
    "DepartamentoMunicipio": "SELECT IdDepartamentoMunicipio, IdDepartamento, IdMunicipio FROM dbo.DepartamentoMunicipio "
                             "WHERE IdDepartamentoMunicipio IN (SELECT IdDepartamentoMunicipio FROM dbo.Vehiculo)",
    "Departamento": "SELECT IdDepartamento, NombreDepartamento FROM dbo.Departamento",
    "Municipio": "SELECT IdMunicipio, NombreMunicipio FROM dbo.Municipio",
    "Marca": "SELECT IdMarca, NombreMarca FROM dbo.Marca",
    "TipoVehiculo": "SELECT IdTipoVehiculo, NombreTipoVehiculo FROM dbo.TipoVehiculo",
    "GravedadAccidente": "SELECT IdGravedadAccidente, NombreGravedad FROM dbo.GravedadAccidente",
    "AutoridadTransito": "SELECT IdAutoridadTransito, NombreAutoridad FROM dbo.AutoridadTransito",
}

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE DimTiempo (
    SK_Tiempo        INTEGER PRIMARY KEY,           -- AAAAMM (-1 = sin dato)
    FechaInicioMes   TEXT,
    Anio             INTEGER NOT NULL,
    Semestre         INTEGER NOT NULL,
    AnioSemestre     TEXT    NOT NULL,
    Trimestre        INTEGER NOT NULL,
    AnioTrimestre    TEXT    NOT NULL,
    NumeroMes        INTEGER NOT NULL,
    NombreMes        TEXT    NOT NULL,
    NombreMesCorto   TEXT    NOT NULL,
    AnioMes          TEXT    NOT NULL,
    MesesConDatosAnio INTEGER NOT NULL,
    CoberturaAnio    TEXT    NOT NULL
);

CREATE TABLE DimUbicacion (
    SK_Ubicacion            INTEGER PRIMARY KEY,
    IdDepartamentoMunicipio INTEGER NOT NULL UNIQUE,
    RegionNatural           TEXT NOT NULL,
    Departamento            TEXT NOT NULL,
    Municipio               TEXT NOT NULL,
    MunicipioDepartamento   TEXT NOT NULL,
    AmbitoProyecto          TEXT NOT NULL
);

CREATE TABLE DimTipoVehiculo (
    SK_TipoVehiculo    INTEGER PRIMARY KEY,
    IdTipoVehiculo     INTEGER NOT NULL UNIQUE,
    TipoVehiculo       TEXT NOT NULL,
    CategoriaVehiculo  TEXT NOT NULL,
    OrdenCategoria     INTEGER NOT NULL
);

CREATE TABLE DimMarca (
    SK_Marca       INTEGER PRIMARY KEY,
    IdMarca        INTEGER NOT NULL UNIQUE,              -- -1 = marca nula en la fuente
    Marca          TEXT NOT NULL,
    GrupoMarca     TEXT NOT NULL,
    PosicionMarca  INTEGER,
    CalidadDato    TEXT NOT NULL
);

CREATE TABLE DimGravedad (
    SK_Gravedad          INTEGER PRIMARY KEY,
    IdGravedadAccidente  INTEGER NOT NULL UNIQUE,
    Gravedad             TEXT NOT NULL,
    NivelSeveridad       INTEGER NOT NULL,
    DescripcionGravedad  TEXT NOT NULL
);

CREATE TABLE DimAutoridadTransito (
    SK_Autoridad         INTEGER PRIMARY KEY,
    IdAutoridadTransito  INTEGER NOT NULL UNIQUE,
    Autoridad            TEXT NOT NULL,
    TipoEntidad          TEXT NOT NULL,
    NivelTerritorial     TEXT NOT NULL
);

CREATE TABLE DimAntiguedad (
    SK_Antiguedad   INTEGER PRIMARY KEY,                 -- años de antigüedad (-1 = sin dato)
    EdadAnios       INTEGER NOT NULL,
    RangoEdad       TEXT NOT NULL,
    OrdenRango      INTEGER NOT NULL,
    GrupoEdad       TEXT NOT NULL,
    OrdenGrupo      INTEGER NOT NULL
);

CREATE TABLE FactVehiculoAccidente (
    IdRegistroOrigen             INTEGER PRIMARY KEY,   -- dbo.Vehiculo.IdVehiculo (dimensión degenerada)
    FilaOrigen                   INTEGER NOT NULL,      -- unicidad comprobada en la validación
    SK_Tiempo                    INTEGER NOT NULL REFERENCES DimTiempo(SK_Tiempo),
    SK_Ubicacion                 INTEGER NOT NULL REFERENCES DimUbicacion(SK_Ubicacion),
    SK_TipoVehiculo              INTEGER NOT NULL REFERENCES DimTipoVehiculo(SK_TipoVehiculo),
    SK_Marca                     INTEGER NOT NULL REFERENCES DimMarca(SK_Marca),
    SK_Gravedad                  INTEGER NOT NULL REFERENCES DimGravedad(SK_Gravedad),
    SK_Autoridad                 INTEGER NOT NULL REFERENCES DimAutoridadTransito(SK_Autoridad),
    SK_Antiguedad                INTEGER NOT NULL REFERENCES DimAntiguedad(SK_Antiguedad),
    AnioModelo                   INTEGER,
    CantidadVehiculos            INTEGER NOT NULL DEFAULT 1 CHECK (CantidadVehiculos = 1),
    VehiculoAccidenteConMuertos  INTEGER NOT NULL CHECK (VehiculoAccidenteConMuertos IN (0, 1)),
    EdadAlAccidente              INTEGER CHECK (EdadAlAccidente IS NULL OR EdadAlAccidente >= 0),
    ModeloPosteriorAlAccidente   INTEGER NOT NULL CHECK (ModeloPosteriorAlAccidente IN (0, 1))
);

CREATE INDEX IX_Fact_Tiempo       ON FactVehiculoAccidente (SK_Tiempo);
CREATE INDEX IX_Fact_Ubicacion    ON FactVehiculoAccidente (SK_Ubicacion);
CREATE INDEX IX_Fact_TipoVehiculo ON FactVehiculoAccidente (SK_TipoVehiculo);
-- En SQLite solo se indexan las tres claves más usadas en filtros (slice/dice) para
-- mantener el archivo por debajo de ~30 MB; en SQL Server se indexan las siete.

CREATE TABLE MetadatosModelo (Clave TEXT PRIMARY KEY, Valor TEXT NOT NULL);
"""


# ---------------------------------------------------------------------------
# Extracción
# ---------------------------------------------------------------------------
def extraer_csv(carpeta):
    datos = {}
    for t in TABLAS_ORIGEN:
        ruta = os.path.join(carpeta, f"{t}.csv.gz")
        if not os.path.exists(ruta):
            ruta = os.path.join(carpeta, f"{t}.csv")
        datos[t] = pd.read_csv(ruta, encoding="utf-8")
    return datos


def extraer_sqlserver(url):
    from sqlalchemy import create_engine  # importación diferida: solo en este modo
    motor = create_engine(url)
    with motor.connect() as cn:
        return {t: pd.read_sql(sql, cn) for t, sql in SQL_EXTRACCION.items()}


def a_int(valor):
    return None if pd.isna(valor) else int(valor)


# ---------------------------------------------------------------------------
# Transformación
# ---------------------------------------------------------------------------
def transformar(o):
    v = o["Vehiculo"].copy()
    fecha = o["Fecha"].copy()
    fecha["FechaCompleta"] = pd.to_datetime(fecha["FechaCompleta"])

    # --- DimTiempo (mensual: la fuente registra el accidente por mes, día 1) ----------
    fv = v.merge(fecha[["IdFecha", "FechaCompleta"]], left_on="IdFechaAccidente",
                 right_on="IdFecha", how="left")
    meses = pd.period_range(fv["FechaCompleta"].min().to_period("M"),
                            fv["FechaCompleta"].max().to_period("M"), freq="M")
    meses_por_anio = pd.Series([p.year for p in meses]).value_counts().to_dict()
    filas = [dict(SK_Tiempo=-1, FechaInicioMes=None, Anio=0, Semestre=0, AnioSemestre="Sin dato",
                  Trimestre=0, AnioTrimestre="Sin dato", NumeroMes=0, NombreMes="Sin dato",
                  NombreMesCorto="N/D", AnioMes="Sin dato", MesesConDatosAnio=0, CoberturaAnio="Sin dato")]
    for p in meses:
        sem = 1 if p.month <= 6 else 2
        tri = (p.month - 1) // 3 + 1
        n_meses = meses_por_anio[p.year]
        filas.append(dict(
            SK_Tiempo=p.year * 100 + p.month, FechaInicioMes=f"{p.year}-{p.month:02d}-01",
            Anio=p.year, Semestre=sem, AnioSemestre=f"{p.year}-S{sem}", Trimestre=tri,
            AnioTrimestre=f"{p.year}-T{tri}", NumeroMes=p.month, NombreMes=R.NOMBRES_MES[p.month - 1],
            NombreMesCorto=R.NOMBRES_MES_CORTO[p.month - 1], AnioMes=f"{p.year}-{p.month:02d}",
            MesesConDatosAnio=n_meses,
            CoberturaAnio="Año completo" if n_meses == 12 else f"Parcial ({n_meses} meses)"))
    dim_tiempo = pd.DataFrame(filas)

    # --- DimUbicacion (solo combinaciones usadas por vehículos) ------------------------
    dm = o["DepartamentoMunicipio"].merge(o["Departamento"], on="IdDepartamento", how="left") \
                                   .merge(o["Municipio"], on="IdMunicipio", how="left")
    dm = dm[dm["IdDepartamentoMunicipio"].isin(v["IdDepartamentoMunicipio"].dropna())]
    dm = dm.sort_values("IdDepartamentoMunicipio").reset_index(drop=True)
    dim_ubic = pd.DataFrame({
        "SK_Ubicacion": range(1, len(dm) + 1),
        "IdDepartamentoMunicipio": dm["IdDepartamentoMunicipio"].astype(int),
        "RegionNatural": dm["NombreDepartamento"].map(R.region_natural),
        "Departamento": dm["NombreDepartamento"].fillna("Sin dato"),
        "Municipio": dm["NombreMunicipio"].fillna("Sin dato"),
    })
    dim_ubic["MunicipioDepartamento"] = dim_ubic["Municipio"] + " (" + dim_ubic["Departamento"] + ")"
    dim_ubic["AmbitoProyecto"] = [R.ambito_proyecto(d, m) for d, m in
                                  zip(dim_ubic["Departamento"], dim_ubic["Municipio"])]
    dim_ubic = pd.concat([pd.DataFrame([dict(SK_Ubicacion=-1, IdDepartamentoMunicipio=-1,
                                             RegionNatural="Sin dato", Departamento="Sin dato",
                                             Municipio="Sin dato", MunicipioDepartamento="Sin dato",
                                             AmbitoProyecto="Sin dato")]), dim_ubic], ignore_index=True)

    # --- DimTipoVehiculo ---------------------------------------------------------------
    tv = o["TipoVehiculo"].sort_values("IdTipoVehiculo").reset_index(drop=True)
    dim_tipo = pd.DataFrame({
        "SK_TipoVehiculo": range(1, len(tv) + 1),
        "IdTipoVehiculo": tv["IdTipoVehiculo"].astype(int),
        "TipoVehiculo": tv["NombreTipoVehiculo"].fillna("Sin dato"),
    })
    dim_tipo["CategoriaVehiculo"] = dim_tipo["TipoVehiculo"].map(R.categoria_vehiculo)
    dim_tipo["OrdenCategoria"] = dim_tipo["CategoriaVehiculo"].map(R.ORDEN_CATEGORIA)
    dim_tipo = pd.concat([pd.DataFrame([dict(SK_TipoVehiculo=-1, IdTipoVehiculo=-1, TipoVehiculo="Sin dato",
                                             CategoriaVehiculo="Sin dato", OrdenCategoria=9)]), dim_tipo],
                         ignore_index=True)

    # --- DimMarca (Top 10 calculado sobre el conjunto completo) ------------------------
    conteo = v["IdMarca"].value_counts()               # excluye nulos
    mc = o["Marca"].copy()
    mc["n"] = mc["IdMarca"].map(conteo).fillna(0).astype(int)
    mc = mc.sort_values(["n", "NombreMarca"], ascending=[False, True]).reset_index(drop=True)
    mc["PosicionMarca"] = range(1, len(mc) + 1)
    mc = mc.sort_values("IdMarca").reset_index(drop=True)
    dim_marca = pd.DataFrame({
        "SK_Marca": range(1, len(mc) + 1),
        "IdMarca": mc["IdMarca"].astype(int),
        "Marca": mc["NombreMarca"].fillna("Sin dato"),
        "GrupoMarca": ["10 marcas principales" if p <= R.TOP_MARCAS else "Resto de marcas"
                       for p in mc["PosicionMarca"]],
        "PosicionMarca": mc["PosicionMarca"],
        "CalidadDato": [R.calidad_marca(n, i) for n, i in zip(mc["NombreMarca"], mc["IdMarca"])],
    })
    dim_marca = pd.concat([pd.DataFrame([dict(SK_Marca=-1, IdMarca=-1, Marca="Sin dato (nulo)",
                                              GrupoMarca="Sin dato", PosicionMarca=None,
                                              CalidadDato=R.calidad_marca(None, None))]), dim_marca],
                          ignore_index=True)

    # --- DimGravedad -------------------------------------------------------------------
    g = o["GravedadAccidente"].sort_values("IdGravedadAccidente").reset_index(drop=True)
    dim_grav = pd.DataFrame({
        "SK_Gravedad": range(1, len(g) + 1),
        "IdGravedadAccidente": g["IdGravedadAccidente"].astype(int),
        "Gravedad": g["NombreGravedad"].fillna("Sin dato"),
    })
    dim_grav["NivelSeveridad"] = dim_grav["Gravedad"].map(R.nivel_severidad)
    dim_grav["DescripcionGravedad"] = dim_grav["NivelSeveridad"].map({
        2: "Accidente con al menos una persona fallecida",
        1: "Accidente con personas lesionadas y sin fallecidos",
        0: "Gravedad no clasificada"})
    dim_grav = pd.concat([pd.DataFrame([dict(SK_Gravedad=-1, IdGravedadAccidente=-1, Gravedad="Sin dato",
                                             NivelSeveridad=0, DescripcionGravedad="Gravedad no reportada")]),
                          dim_grav], ignore_index=True)

    # --- DimAutoridadTransito ----------------------------------------------------------
    au = o["AutoridadTransito"].sort_values("IdAutoridadTransito").reset_index(drop=True)
    dim_aut = pd.DataFrame({
        "SK_Autoridad": range(1, len(au) + 1),
        "IdAutoridadTransito": au["IdAutoridadTransito"].astype(int),
        "Autoridad": au["NombreAutoridad"].fillna("Sin dato"),
    })
    dim_aut["TipoEntidad"] = dim_aut["Autoridad"].map(R.tipo_entidad)
    dim_aut["NivelTerritorial"] = dim_aut["Autoridad"].map(R.nivel_territorial)
    dim_aut = pd.concat([pd.DataFrame([dict(SK_Autoridad=-1, IdAutoridadTransito=-1, Autoridad="Sin dato",
                                            TipoEntidad="Sin dato", NivelTerritorial="Sin dato")]), dim_aut],
                        ignore_index=True)

    # --- Medida EdadAlAccidente y DimAntiguedad ---------------------------------------
    fv["AnioAccidente"] = fv["FechaCompleta"].dt.year
    fv["EdadAlAccidente"] = [R.edad_al_accidente(a_int(a), a_int(m))
                             for a, m in zip(fv["AnioAccidente"], fv["AnioModelo"])]
    edad_max = int(pd.Series([e for e in fv["EdadAlAccidente"] if e is not None]).max())
    filas = [dict(SK_Antiguedad=-1, EdadAnios=-1, RangoEdad="Sin dato", OrdenRango=7,
                  GrupoEdad="Sin dato", OrdenGrupo=9)]
    for e in range(0, edad_max + 1):
        orng, rng = R.rango_edad(e)
        ogrp, grp = R.grupo_edad(e)
        filas.append(dict(SK_Antiguedad=e, EdadAnios=e, RangoEdad=rng, OrdenRango=orng,
                          GrupoEdad=grp, OrdenGrupo=ogrp))
    dim_ant = pd.DataFrame(filas)

    # --- Tabla de hechos: búsqueda de claves sustitutas (lookup) ----------------------
    f = fv.copy()
    f["SK_Tiempo"] = (f["FechaCompleta"].dt.year * 100 + f["FechaCompleta"].dt.month)
    f["SK_Tiempo"] = f["SK_Tiempo"].where(f["SK_Tiempo"].isin(dim_tiempo["SK_Tiempo"]), -1).fillna(-1)
    f = f.merge(dim_ubic[["IdDepartamentoMunicipio", "SK_Ubicacion"]], on="IdDepartamentoMunicipio", how="left")
    f = f.merge(dim_tipo[["IdTipoVehiculo", "SK_TipoVehiculo"]], on="IdTipoVehiculo", how="left")
    f["IdMarcaBK"] = f["IdMarca"].fillna(-1).astype(int)
    f = f.merge(dim_marca[["IdMarca", "SK_Marca"]].rename(columns={"IdMarca": "IdMarcaBK"}),
                on="IdMarcaBK", how="left")
    f = f.merge(dim_grav[["IdGravedadAccidente", "SK_Gravedad", "NivelSeveridad"]],
                on="IdGravedadAccidente", how="left")
    f = f.merge(dim_aut[["IdAutoridadTransito", "SK_Autoridad"]], on="IdAutoridadTransito", how="left")
    for c in ["SK_Ubicacion", "SK_TipoVehiculo", "SK_Marca", "SK_Gravedad", "SK_Autoridad"]:
        f[c] = f[c].fillna(-1).astype(int)
    f["SK_Antiguedad"] = [e if e is not None else -1 for e in f["EdadAlAccidente"]]
    f["ModeloPosteriorAlAccidente"] = (f["AnioModelo"] > f["AnioAccidente"]).astype(int)
    hechos = pd.DataFrame({
        "IdRegistroOrigen": f["IdVehiculo"].astype(int),
        "FilaOrigen": f["FilaOrigen"].astype(int),
        "SK_Tiempo": f["SK_Tiempo"].astype(int),
        "SK_Ubicacion": f["SK_Ubicacion"], "SK_TipoVehiculo": f["SK_TipoVehiculo"],
        "SK_Marca": f["SK_Marca"], "SK_Gravedad": f["SK_Gravedad"],
        "SK_Autoridad": f["SK_Autoridad"], "SK_Antiguedad": f["SK_Antiguedad"].astype(int),
        "AnioModelo": f["AnioModelo"].astype("Int64"),
        "CantidadVehiculos": 1,
        "VehiculoAccidenteConMuertos": (f["NivelSeveridad"] == 2).astype(int),
        "EdadAlAccidente": pd.array(f["EdadAlAccidente"], dtype="Int64"),
        "ModeloPosteriorAlAccidente": f["ModeloPosteriorAlAccidente"],
    }).sort_values("IdRegistroOrigen")

    return dict(DimTiempo=dim_tiempo, DimUbicacion=dim_ubic, DimTipoVehiculo=dim_tipo,
                DimMarca=dim_marca, DimGravedad=dim_grav, DimAutoridadTransito=dim_aut,
                DimAntiguedad=dim_ant, FactVehiculoAccidente=hechos)


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------
def cargar(modelo, ruta, origen):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    if os.path.exists(ruta):
        os.remove(ruta)                                    # reejecución limpia
    cn = sqlite3.connect(ruta)
    cn.executescript(DDL)
    orden = ["DimTiempo", "DimUbicacion", "DimTipoVehiculo", "DimMarca", "DimGravedad",
             "DimAutoridadTransito", "DimAntiguedad", "FactVehiculoAccidente"]
    for t in orden:
        df = modelo[t].astype(object).where(pd.notna(modelo[t]), None)
        cols = list(df.columns)
        cn.executemany(f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                       df.itertuples(index=False, name=None))
    meta = {
        "fuente": "Datos Abiertos Colombia - Vehículos involucrados en un accidente de tránsito (6jmc-vaxk)",
        "url_fuente": "https://www.datos.gov.co/Transporte/VEHICULOS-INVOLUCRADOS-EN-UN-ACCIDENTE-DE-TRANSITO/6jmc-vaxk/about_data",
        "origen_tratado": "IntegracionSiniestrosVehiculos.dbo.Vehiculo (Etapa 3, respaldo FILE = 3)",
        "modo_extraccion": origen,
        "fecha_construccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "granularidad": "Un registro de vehículo involucrado en un accidente de tránsito con víctimas",
    }
    cn.executemany("INSERT INTO MetadatosModelo VALUES (?, ?)", meta.items())
    cn.commit()
    cn.execute("ANALYZE")
    cn.execute("VACUUM")
    cn.close()


# ---------------------------------------------------------------------------
# Validaciones (las mismas de 05_validaciones.sql)
# ---------------------------------------------------------------------------
def validar(ruta, origen):
    cn = sqlite3.connect(ruta)
    q = lambda sql: cn.execute(sql).fetchall()
    v = origen["Vehiculo"]
    r = {}
    r["filas_por_tabla"] = {t: q(f"SELECT COUNT(*) FROM {t}")[0][0] for t in
                            ["DimTiempo", "DimUbicacion", "DimTipoVehiculo", "DimMarca", "DimGravedad",
                             "DimAutoridadTransito", "DimAntiguedad", "FactVehiculoAccidente"]}
    # 1. Unicidad de claves de dimensión
    unicidad = {}
    for t, k, bk in [("DimTiempo", "SK_Tiempo", "AnioMes"), ("DimUbicacion", "SK_Ubicacion", "IdDepartamentoMunicipio"),
                     ("DimTipoVehiculo", "SK_TipoVehiculo", "IdTipoVehiculo"), ("DimMarca", "SK_Marca", "IdMarca"),
                     ("DimGravedad", "SK_Gravedad", "IdGravedadAccidente"),
                     ("DimAutoridadTransito", "SK_Autoridad", "IdAutoridadTransito"),
                     ("DimAntiguedad", "SK_Antiguedad", "EdadAnios")]:
        n, nk, nbk = q(f"SELECT COUNT(*), COUNT(DISTINCT {k}), COUNT(DISTINCT {bk}) FROM {t}")[0]
        unicidad[t] = dict(filas=n, claves_distintas=nk, claves_negocio_distintas=nbk, ok=(n == nk == nbk))
    r["unicidad_dimensiones"] = unicidad
    # 2. Integridad referencial (huérfanos)
    huerf = {}
    for k, t in [("SK_Tiempo", "DimTiempo"), ("SK_Ubicacion", "DimUbicacion"), ("SK_TipoVehiculo", "DimTipoVehiculo"),
                 ("SK_Marca", "DimMarca"), ("SK_Gravedad", "DimGravedad"), ("SK_Autoridad", "DimAutoridadTransito"),
                 ("SK_Antiguedad", "DimAntiguedad")]:
        huerf[k] = q(f"SELECT COUNT(*) FROM FactVehiculoAccidente f LEFT JOIN {t} d ON d.{k} = f.{k} "
                     f"WHERE d.{k} IS NULL")[0][0]
    r["hechos_huerfanos"] = huerf
    r["hechos_en_miembro_desconocido"] = {k: q(f"SELECT COUNT(*) FROM FactVehiculoAccidente WHERE {k} = -1")[0][0]
                                          for k in huerf}
    # 3. Duplicaciones indebidas en el hecho
    r["duplicados_clave_origen"] = q("SELECT COUNT(*) - COUNT(DISTINCT IdRegistroOrigen) FROM FactVehiculoAccidente")[0][0]
    r["duplicados_fila_origen"] = q("SELECT COUNT(*) - COUNT(DISTINCT FilaOrigen) FROM FactVehiculoAccidente")[0][0]
    # Filas con el mismo contenido en las 9 columnas de negocio del origen (sin IdVehiculo ni FilaOrigen).
    # Se conservan por decisión de la Etapa 4: sin placa y con fecha mensual pueden ser vehículos distintos.
    negocio = ["AnioModelo", "EdadVehiculo", "IdFechaAccidente", "IdDepartamentoMunicipio", "IdMarca",
               "IdTipoVehiculo", "IdGravedadAccidente", "IdAutoridadTransito"]
    r["filas_con_contenido_repetido_en_origen"] = int(v.duplicated(subset=negocio).sum())
    # 4. Comparaciones con el origen tratado
    comp = []
    tot = q("SELECT SUM(CantidadVehiculos) FROM FactVehiculoAccidente")[0][0]
    comp.append(dict(prueba="C1 Total de vehículos", origen=int(len(v)), modelo=int(tot), diferencia=int(len(v) - tot)))
    fecha = origen["Fecha"].copy(); fecha["Anio"] = pd.to_datetime(fecha["FechaCompleta"]).dt.year
    o_anio = v.merge(fecha[["IdFecha", "Anio"]], left_on="IdFechaAccidente", right_on="IdFecha").groupby("Anio").size()
    m_anio = dict(q("SELECT t.Anio, SUM(f.CantidadVehiculos) FROM FactVehiculoAccidente f JOIN DimTiempo t "
                    "ON t.SK_Tiempo = f.SK_Tiempo GROUP BY t.Anio"))
    comp.append(dict(prueba="C2 Vehículos por año", origen={int(k): int(x) for k, x in o_anio.items()},
                     modelo={int(k): int(x) for k, x in m_anio.items()},
                     diferencia=sum(abs(int(o_anio[k]) - int(m_anio.get(k, 0))) for k in o_anio.index)))
    g = origen["GravedadAccidente"]
    o_m = int(v.merge(g, on="IdGravedadAccidente")["NombreGravedad"].map(R.nivel_severidad).eq(2).sum())
    m_m = q("SELECT SUM(VehiculoAccidenteConMuertos) FROM FactVehiculoAccidente")[0][0]
    comp.append(dict(prueba="C3 Vehículos en accidentes con muertos", origen=o_m, modelo=int(m_m), diferencia=o_m - int(m_m)))
    tv = origen["TipoVehiculo"]
    o_t = v.merge(tv, on="IdTipoVehiculo").groupby("NombreTipoVehiculo").size()
    m_t = dict(q("SELECT d.TipoVehiculo, SUM(f.CantidadVehiculos) FROM FactVehiculoAccidente f JOIN DimTipoVehiculo d "
                 "ON d.SK_TipoVehiculo = f.SK_TipoVehiculo GROUP BY d.TipoVehiculo"))
    comp.append(dict(prueba="C4 Vehículos por tipo (28 tipos)", origen=len(o_t), modelo=len(m_t),
                     diferencia=sum(abs(int(o_t[k]) - int(m_t.get(k, 0))) for k in o_t.index)))
    dmo = origen["DepartamentoMunicipio"].merge(origen["Departamento"], on="IdDepartamento")
    o_d = v.merge(dmo, on="IdDepartamentoMunicipio").groupby("NombreDepartamento").size()
    m_d = dict(q("SELECT d.Departamento, SUM(f.CantidadVehiculos) FROM FactVehiculoAccidente f JOIN DimUbicacion d "
                 "ON d.SK_Ubicacion = f.SK_Ubicacion GROUP BY d.Departamento"))
    comp.append(dict(prueba="C5 Vehículos por departamento", origen=len(o_d), modelo=len(m_d),
                     diferencia=sum(abs(int(o_d[k]) - int(m_d.get(k, 0))) for k in o_d.index)))
    o_sinmarca = int(v["IdMarca"].isna().sum())
    m_sinmarca = q("SELECT COUNT(*) FROM FactVehiculoAccidente WHERE SK_Marca = -1")[0][0]
    comp.append(dict(prueba="C6 Marca nula -> miembro desconocido", origen=o_sinmarca, modelo=m_sinmarca,
                     diferencia=o_sinmarca - m_sinmarca))
    r["comparaciones_origen"] = comp
    # 5. Coherencia de agregaciones (roll-up): suma de meses = suma de años = total
    s_mes = q("SELECT SUM(n) FROM (SELECT t.AnioMes, SUM(f.CantidadVehiculos) n FROM FactVehiculoAccidente f "
              "JOIN DimTiempo t ON t.SK_Tiempo = f.SK_Tiempo GROUP BY t.AnioMes)")[0][0]
    s_mun = q("SELECT SUM(n) FROM (SELECT u.SK_Ubicacion, SUM(f.CantidadVehiculos) n FROM FactVehiculoAccidente f "
              "JOIN DimUbicacion u ON u.SK_Ubicacion = f.SK_Ubicacion GROUP BY u.SK_Ubicacion)")[0][0]
    r["coherencia_rollup"] = dict(total=tot, suma_meses=s_mes, suma_municipios=s_mun, ok=(tot == s_mes == s_mun))
    r["calidad"] = dict(
        marca_nula=o_sinmarca,
        categoria_sin_marca=q("SELECT COUNT(*) FROM FactVehiculoAccidente f JOIN DimMarca m ON m.SK_Marca = f.SK_Marca "
                              "WHERE m.CalidadDato LIKE 'Categor%'")[0][0],
        edad_original_nula=int(v["EdadVehiculo"].isna().sum()),
        edad_al_accidente_nula=q("SELECT COUNT(*) FROM FactVehiculoAccidente WHERE EdadAlAccidente IS NULL")[0][0],
        modelo_posterior_al_accidente=q("SELECT SUM(ModeloPosteriorAlAccidente) FROM FactVehiculoAccidente")[0][0],
        edad_mayor_40=q("SELECT COUNT(*) FROM FactVehiculoAccidente WHERE EdadAlAccidente > 40")[0][0],
    )
    cn.close()
    r["todas_ok"] = (all(u["ok"] for u in unicidad.values()) and not any(huerf.values())
                     and r["duplicados_clave_origen"] == 0 and all(c["diferencia"] == 0 for c in comp)
                     and r["coherencia_rollup"]["ok"])
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origen", choices=["csv", "sqlserver"], default="csv")
    ap.add_argument("--carpeta", default=ORIGEN_CSV, help="Carpeta con los CSV del origen tratado")
    ap.add_argument("--url", help="URL SQLAlchemy de IntegracionSiniestrosVehiculos (modo sqlserver)")
    ap.add_argument("--salida", default=SALIDA)
    a = ap.parse_args()

    print("1/4 Extracción desde", a.origen)
    origen = extraer_csv(a.carpeta) if a.origen == "csv" else extraer_sqlserver(a.url)
    print("    dbo.Vehiculo:", len(origen["Vehiculo"]), "filas")
    print("2/4 Transformación")
    modelo = transformar(origen)
    print("3/4 Carga en", a.salida)
    cargar(modelo, a.salida, a.origen)
    print("4/4 Validación")
    rep = validar(a.salida, origen)
    with open(REPORTE, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2, default=str)
    for t, n in rep["filas_por_tabla"].items():
        print(f"    {t:<24}{n:>10,}".replace(",", "."))
    for c in rep["comparaciones_origen"]:
        print(f"    {c['prueba']:<45} diferencia = {c['diferencia']}")
    print("    Resultado global:", "OK" if rep["todas_ok"] else "REVISAR")
    sys.exit(0 if rep["todas_ok"] else 1)


if __name__ == "__main__":
    main()
