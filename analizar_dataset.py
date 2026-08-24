import pandas as pd
import os


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO = "data/siniestros_viales.csv"


# ============================================================
# CARGAR DATASET
# ============================================================

if not os.path.exists(ARCHIVO):
    print(f"❌ No se encontró el archivo: {ARCHIVO}")
    exit()

print("=" * 70)
print("🚦 DIAGNÓSTICO DATASET — SINIESTROS VIALES ANSV")
print("=" * 70)

df = pd.read_csv(ARCHIVO)

print(f"\n📁 Archivo: {ARCHIVO}")
print(f"📊 Registros: {len(df):,}")
print(f"📊 Variables: {len(df.columns)}")


# ============================================================
# CONVERTIR FECHA
# ============================================================

if "fecha_hech" in df.columns:

    df["fecha_hech"] = pd.to_datetime(
        df["fecha_hech"],
        errors="coerce"
    )


# ============================================================
# INFORMACIÓN GENERAL
# ============================================================

print("\n")
print("=" * 70)
print("📋 VARIABLES")
print("=" * 70)

for columna in df.columns:

    print(
        f"{columna:<20} "
        f"Tipo: {str(df[columna].dtype):<12} "
        f"Únicos: {df[columna].nunique():,} "
        f"Faltantes: {df[columna].isna().sum():,}"
    )


# ============================================================
# COBERTURA TEMPORAL
# ============================================================

print("\n")
print("=" * 70)
print("📅 COBERTURA TEMPORAL")
print("=" * 70)

if "fecha_hech" in df.columns:

    fecha_min = df["fecha_hech"].min()
    fecha_max = df["fecha_hech"].max()

    print(f"Fecha inicial: {fecha_min}")
    print(f"Fecha final:   {fecha_max}")

    print(
        f"Cantidad de años: "
        f"{df['fecha_hech'].dt.year.nunique()}"
    )

    print("\nAccidentes por año:")

    accidentes_anio = (
        df["fecha_hech"]
        .dt.year
        .value_counts()
        .sort_index()
    )

    print(accidentes_anio.to_string())


# ============================================================
# MESES
# ============================================================

print("\n")
print("=" * 70)
print("📆 ACCIDENTALIDAD POR MES")
print("=" * 70)

if "mes_largo" in df.columns:

    accidentes_mes = (
        df["mes_largo"]
        .value_counts()
    )

    print(accidentes_mes.to_string())


# ============================================================
# DEPARTAMENTOS
# ============================================================

print("\n")
print("=" * 70)
print("🗺️ DEPARTAMENTOS")
print("=" * 70)

if "depto_hech" in df.columns:

    print(
        f"Departamentos registrados: "
        f"{df['depto_hech'].nunique()}"
    )

    print("\nTop 20 departamentos:")

    print(
        df["depto_hech"]
        .value_counts()
        .head(20)
        .to_string()
    )


# ============================================================
# MUNICIPIOS
# ============================================================

print("\n")
print("=" * 70)
print("📍 MUNICIPIOS")
print("=" * 70)

if "municipio_" in df.columns:

    print(
        f"Municipios registrados: "
        f"{df['municipio_'].nunique()}"
    )

    print("\nTop 20 municipios:")

    print(
        df["municipio_"]
        .value_counts()
        .head(20)
        .to_string()
    )


# ============================================================
# CLASIFICACIÓN
# ============================================================

print("\n")
print("=" * 70)
print("🚨 CLASIFICACIÓN DE SINIESTROS")
print("=" * 70)

if "sievi_clas" in df.columns:

    print(
        df["sievi_clas"]
        .value_counts()
        .to_string()
    )


# ============================================================
# HIPÓTESIS
# ============================================================

print("\n")
print("=" * 70)
print("⚠️ HIPÓTESIS / CAUSAS")
print("=" * 70)

if "hipotesis_" in df.columns:

    print(
        df["hipotesis_"]
        .value_counts()
        .head(20)
        .to_string()
    )


# ============================================================
# MEDIO INVOLUCRADO
# ============================================================

print("\n")
print("=" * 70)
print("🚗 MEDIO INVOLUCRADO")
print("=" * 70)

if "medio_cono" in df.columns:

    print(
        df["medio_cono"]
        .value_counts()
        .to_string()
    )


# ============================================================
# LUGAR
# ============================================================

print("\n")
print("=" * 70)
print("📍 LUGAR DEL SINIESTRO")
print("=" * 70)

if "lugaro" in df.columns:

    print(
        df["lugaro"]
        .value_counts()
        .head(20)
        .to_string()
    )


# ============================================================
# VÍCTIMAS
# ============================================================

print("\n")
print("=" * 70)
print("👥 VÍCTIMAS")
print("=" * 70)

columnas_numericas = [
    "smuertos",
    "slesionado",
    "tvictimas"
]

for columna in columnas_numericas:

    if columna in df.columns:

        print(f"\n{columna}:")

        print(
            df[columna]
            .describe()
            .to_string()
        )


# ============================================================
# DUPLICADOS
# ============================================================

print("\n")
print("=" * 70)
print("🔁 DUPLICADOS")
print("=" * 70)

duplicados = df.duplicated().sum()

print(f"Registros duplicados completos: {duplicados:,}")

if "hechos_id" in df.columns:

    duplicados_hecho = df["hechos_id"].duplicated().sum()

    print(
        f"hechos_id duplicados: "
        f"{duplicados_hecho:,}"
    )


# ============================================================
# VALORES FALTANTES
# ============================================================

print("\n")
print("=" * 70)
print("❓ VALORES FALTANTES")
print("=" * 70)

faltantes = df.isna().sum()

faltantes = faltantes[
    faltantes > 0
].sort_values(ascending=False)

if len(faltantes) == 0:

    print("✅ No existen valores faltantes.")

else:

    print(faltantes.to_string())


# ============================================================
# COORDENADAS
# ============================================================

print("\n")
print("=" * 70)
print("🌎 COORDENADAS")
print("=" * 70)

if "latitud" in df.columns and "longitud" in df.columns:

    lat_invalidas = (
        (df["latitud"] < -90) |
        (df["latitud"] > 90)
    ).sum()

    lon_invalidas = (
        (df["longitud"] < -180) |
        (df["longitud"] > 180)
    ).sum()

    print(
        f"Latitudes fuera de rango: {lat_invalidas:,}"
    )

    print(
        f"Longitudes fuera de rango: {lon_invalidas:,}"
    )

    print("\nRango de latitud:")

    print(
        f"Min: {df['latitud'].min()}"
        f" | Max: {df['latitud'].max()}"
    )

    print("\nRango de longitud:")

    print(
        f"Min: {df['longitud'].min()}"
        f" | Max: {df['longitud'].max()}"
    )


# ============================================================
# RESUMEN FINAL
# ============================================================

print("\n")
print("=" * 70)
print("🎯 RESUMEN PARA LA ACTIVIDAD")
print("=" * 70)

print(f"""
Registros:              {len(df):,}
Variables:              {len(df.columns)}
Valores faltantes:      {df.isna().sum().sum():,}
Duplicados completos:   {duplicados:,}
Departamentos:          {df['depto_hech'].nunique() if 'depto_hech' in df.columns else 'N/A'}
Municipios:             {df['municipio_'].nunique() if 'municipio_' in df.columns else 'N/A'}
""")

if "fecha_hech" in df.columns:

    print(
        f"Periodo:                "
        f"{df['fecha_hech'].min().date()} → "
        f"{df['fecha_hech'].max().date()}"
    )

print("\n")
print("✅ Diagnóstico terminado.")
print("=" * 70)