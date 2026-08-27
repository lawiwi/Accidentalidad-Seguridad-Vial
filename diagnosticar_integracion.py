import pandas as pd
import os

# ============================================================
# CONFIGURACIÓN
# ============================================================

SINIESTROS_PATH = "data/siniestros_viales.csv"
VEHICULOS_PATH = "data/vehiculos_accidentes.csv"


def encabezado(titulo):
    print("\n" + "=" * 70)
    print(titulo)
    print("=" * 70)


# ============================================================
# CARGAR DATASETS
# ============================================================

encabezado("🚦 DIAGNÓSTICO DE INTEGRACIÓN DE DATASETS")

print("\n📁 Cargando archivos...")

if not os.path.exists(SINIESTROS_PATH):
    print(f"❌ No existe: {SINIESTROS_PATH}")
    exit()

if not os.path.exists(VEHICULOS_PATH):
    print(f"❌ No existe: {VEHICULOS_PATH}")
    exit()

siniestros = pd.read_csv(SINIESTROS_PATH)
vehiculos = pd.read_csv(VEHICULOS_PATH)

print(f"✅ Siniestros: {len(siniestros):,} registros")
print(f"✅ Vehículos:  {len(vehiculos):,} registros")


# ============================================================
# FECHAS
# ============================================================

encabezado("📅 COBERTURA TEMPORAL")

siniestros["fecha_hech"] = pd.to_datetime(
    siniestros["fecha_hech"],
    errors="coerce"
)

vehiculos["fecha_accidente"] = pd.to_datetime(
    vehiculos["fecha_accidente"],
    errors="coerce"
)

print("\nSiniestros:")
print(f"  Inicio: {siniestros['fecha_hech'].min()}")
print(f"  Final:  {siniestros['fecha_hech'].max()}")

print("\nVehículos:")
print(f"  Inicio: {vehiculos['fecha_accidente'].min()}")
print(f"  Final:  {vehiculos['fecha_accidente'].max()}")


# ============================================================
# NORMALIZACIÓN DE TEXTO
# ============================================================

encabezado("🧹 PREPARANDO CAMPOS PARA COMPARACIÓN")

def normalizar_texto(serie):
    return (
        serie
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
    )


# Departamento
siniestros["departamento_normalizado"] = normalizar_texto(
    siniestros["depto_hech"]
)

vehiculos["departamento_normalizado"] = normalizar_texto(
    vehiculos["departamento_accidente"]
)

# Municipio
siniestros["municipio_normalizado"] = normalizar_texto(
    siniestros["municipio_"]
)

vehiculos["municipio_normalizado"] = normalizar_texto(
    vehiculos["municipio_accidente"]
)

# Fecha solamente
siniestros["fecha"] = siniestros["fecha_hech"].dt.date
vehiculos["fecha"] = vehiculos["fecha_accidente"].dt.date


# ============================================================
# COMPARACIÓN DE DEPARTAMENTOS
# ============================================================

encabezado("🗺️ COMPARACIÓN DE DEPARTAMENTOS")

deps_siniestros = set(
    siniestros["departamento_normalizado"].unique()
)

deps_vehiculos = set(
    vehiculos["departamento_normalizado"].unique()
)

deps_comunes = deps_siniestros.intersection(deps_vehiculos)

print(f"\nDepartamentos en siniestros: {len(deps_siniestros)}")
print(f"Departamentos en vehículos:  {len(deps_vehiculos)}")
print(f"Departamentos comunes:       {len(deps_comunes)}")

print("\nDepartamentos comunes:")

for departamento in sorted(deps_comunes):
    print(f"  • {departamento}")


# ============================================================
# COMPARACIÓN DE MUNICIPIOS
# ============================================================

encabezado("📍 COMPARACIÓN DE MUNICIPIOS")

mun_siniestros = set(
    siniestros["municipio_normalizado"].unique()
)

mun_vehiculos = set(
    vehiculos["municipio_normalizado"].unique()
)

mun_comunes = mun_siniestros.intersection(mun_vehiculos)

print(f"\nMunicipios en siniestros: {len(mun_siniestros)}")
print(f"Municipios en vehículos:  {len(mun_vehiculos)}")
print(f"Municipios comunes:       {len(mun_comunes)}")

print("\nPrimeros 30 municipios comunes:")

for municipio in sorted(mun_comunes)[:30]:
    print(f"  • {municipio}")


# ============================================================
# COMPARACIÓN DE FECHAS
# ============================================================

encabezado("📅 COMPARACIÓN DE FECHAS")

fechas_siniestros = set(
    siniestros["fecha"].dropna()
)

fechas_vehiculos = set(
    vehiculos["fecha"].dropna()
)

fechas_comunes = fechas_siniestros.intersection(
    fechas_vehiculos
)

print(f"\nFechas en siniestros: {len(fechas_siniestros)}")
print(f"Fechas en vehículos:  {len(fechas_vehiculos)}")
print(f"Fechas comunes:       {len(fechas_comunes)}")


# ============================================================
# INTERSECCIÓN FECHA + DEPARTAMENTO
# ============================================================

encabezado("🔗 INTERSECCIÓN: FECHA + DEPARTAMENTO")

claves_siniestros = siniestros[
    ["fecha", "departamento_normalizado"]
].drop_duplicates()

claves_vehiculos = vehiculos[
    ["fecha", "departamento_normalizado"]
].drop_duplicates()

cruce_fecha_depto = pd.merge(
    claves_siniestros,
    claves_vehiculos,
    on=["fecha", "departamento_normalizado"],
    how="inner"
)

print(
    f"\nCombinaciones comunes "
    f"fecha + departamento: {len(cruce_fecha_depto):,}"
)


# ============================================================
# INTERSECCIÓN FECHA + MUNICIPIO
# ============================================================

encabezado("🔗 INTERSECCIÓN: FECHA + MUNICIPIO")

claves_siniestros_mun = siniestros[
    ["fecha", "municipio_normalizado"]
].drop_duplicates()

claves_vehiculos_mun = vehiculos[
    ["fecha", "municipio_normalizado"]
].drop_duplicates()

cruce_fecha_municipio = pd.merge(
    claves_siniestros_mun,
    claves_vehiculos_mun,
    on=["fecha", "municipio_normalizado"],
    how="inner"
)

print(
    f"\nCombinaciones comunes "
    f"fecha + municipio: {len(cruce_fecha_municipio):,}"
)


# ============================================================
# INTERSECCIÓN FECHA + DEPARTAMENTO + MUNICIPIO
# ============================================================

encabezado(
    "🔗 INTERSECCIÓN: FECHA + DEPARTAMENTO + MUNICIPIO"
)

claves_siniestros_completas = siniestros[
    [
        "fecha",
        "departamento_normalizado",
        "municipio_normalizado"
    ]
].drop_duplicates()

claves_vehiculos_completas = vehiculos[
    [
        "fecha",
        "departamento_normalizado",
        "municipio_normalizado"
    ]
].drop_duplicates()

cruce_completo = pd.merge(
    claves_siniestros_completas,
    claves_vehiculos_completas,
    on=[
        "fecha",
        "departamento_normalizado",
        "municipio_normalizado"
    ],
    how="inner"
)

print(
    f"\nCombinaciones comunes "
    f"fecha + departamento + municipio:"
    f" {len(cruce_completo):,}"
)


# ============================================================
# EJEMPLOS
# ============================================================

encabezado("🔎 EJEMPLOS DE COINCIDENCIAS")

if len(cruce_completo) > 0:

    print("\nPrimeras 20 coincidencias:\n")

    print(
        cruce_completo.head(20).to_string(
            index=False
        )
    )

else:

    print("\n⚠️ No se encontraron coincidencias completas.")


# ============================================================
# COBERTURA COMÚN POR AÑO
# ============================================================

encabezado("📊 COBERTURA COMÚN POR AÑO")

siniestros["año"] = siniestros["fecha_hech"].dt.year
vehiculos["año"] = vehiculos["fecha_accidente"].dt.year

años_siniestros = set(
    siniestros["año"].dropna().astype(int)
)

años_vehiculos = set(
    vehiculos["año"].dropna().astype(int)
)

años_comunes = sorted(
    años_siniestros.intersection(años_vehiculos)
)

print("\nAños comunes:")

if años_comunes:
    for año in años_comunes:
        print(f"  • {año}")
else:
    print("  ❌ No existen años comunes.")


# ============================================================
# RESUMEN
# ============================================================

encabezado("🎯 RESUMEN DEL DIAGNÓSTICO")

print(f"""
Dataset de siniestros:
    Registros: {len(siniestros):,}
    Variables: {len(siniestros.columns)}

Dataset de vehículos:
    Registros: {len(vehiculos):,}
    Variables: {len(vehiculos.columns)}

Coincidencias:
    Departamentos: {len(deps_comunes)}
    Municipios: {len(mun_comunes)}
    Fechas: {len(fechas_comunes)}
    Fecha + departamento: {len(cruce_fecha_depto):,}
    Fecha + municipio: {len(cruce_fecha_municipio):,}
    Fecha + departamento + municipio: {len(cruce_completo):,}

Años comunes:
    {años_comunes}
""")


# ============================================================
# RECOMENDACIÓN
# ============================================================

print("=" * 70)
print("💡 RECOMENDACIÓN")
print("=" * 70)

if len(cruce_completo) > 0:

    print("""
✅ Existen coincidencias mediante:

   FECHA + DEPARTAMENTO + MUNICIPIO

Sin embargo, esto NO significa que cada coincidencia
represente necesariamente el mismo accidente.

Antes de hacer un merge de registros se debe analizar
la granularidad de ambas fuentes.

👉 Se recomienda conservar ambos datasets originales
   y documentar la estrategia de integración.
""")

else:

    print("""
⚠️ No existen suficientes coincidencias para realizar
una integración directa mediante fecha + departamento
+ municipio.

👉 Se recomienda utilizar ambas fuentes como datasets
   complementarios y no realizar un merge registro a registro.
""")

print("=" * 70)