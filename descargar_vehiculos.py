import requests
import pandas as pd
import os
import time


# ============================================================
# CONFIGURACIÓN
# ============================================================

DATASET_ID = "6jmc-vaxk"

API_URL = f"https://www.datos.gov.co/resource/{DATASET_ID}.json"

OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "vehiculos_accidentes.csv"
)

BATCH_SIZE = 5000


# ============================================================
# ENCABEZADO
# ============================================================

print("=" * 70)
print("🚗 DESCARGA DATASET — VEHÍCULOS INVOLUCRADOS EN ACCIDENTES")
print("=" * 70)

print("\n🌐 Fuente:")
print(API_URL)

print(f"\n📦 Dataset ID: {DATASET_ID}")


# ============================================================
# FUNCIÓN PARA CONSULTAR
# ============================================================

def consultar_api(offset=0, limit=5000):

    parametros = {
        "$limit": limit,
        "$offset": offset
    }

    respuesta = requests.get(
        API_URL,
        params=parametros,
        timeout=120
    )

    respuesta.raise_for_status()

    return respuesta.json()


# ============================================================
# OBTENER CANTIDAD DE REGISTROS
# ============================================================

print("\n🔎 Consultando cantidad total de registros...")

try:

    url_count = API_URL

    parametros_count = {
        "$select": "count(*) as total"
    }

    respuesta = requests.get(
        url_count,
        params=parametros_count,
        timeout=120
    )

    respuesta.raise_for_status()

    resultado = respuesta.json()

    total = int(resultado[0]["total"])

except Exception as e:

    print("\n❌ Error consultando cantidad de registros:")
    print(e)

    exit()


print(f"📊 Registros encontrados: {total:,}")


# ============================================================
# VERIFICACIÓN DEL REQUISITO
# ============================================================

print("\n🎓 Verificación del requisito:")

if total >= 10000:

    print(
        "   ✅ El dataset supera los 10.000 registros requeridos."
    )

else:

    print(
        "   ⚠️ El dataset NO alcanza los 10.000 registros requeridos."
    )


# ============================================================
# CREAR CARPETA
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# DESCARGA POR LOTES
# ============================================================

todos_los_registros = []

print("\n")
print("=" * 70)
print("⬇️ INICIANDO DESCARGA")
print("=" * 70)


for offset in range(0, total, BATCH_SIZE):

    limite_real = min(
        BATCH_SIZE,
        total - offset
    )

    inicio = offset + 1
    fin = offset + limite_real

    print(
        f"\n⬇️ Descargando registros "
        f"{inicio:,} - {fin:,} de {total:,}..."
    )

    try:

        registros = consultar_api(
            offset=offset,
            limit=limite_real
        )

        if not registros:

            print("   ⚠️ La API no devolvió registros.")
            break

        todos_los_registros.extend(registros)

        print(
            f"   ✅ Lote descargado: "
            f"{len(registros):,} registros"
        )

        # Evitar saturar la API
        time.sleep(0.3)

    except Exception as e:

        print("\n❌ Error descargando lote:")
        print(e)

        print(
            f"\n⚠️ La descarga se detuvo en "
            f"{inicio:,} - {fin:,}"
        )

        break


# ============================================================
# VERIFICACIÓN DE DESCARGA
# ============================================================

print("\n")
print("=" * 70)
print("📊 RESUMEN DE DESCARGA")
print("=" * 70)

print(
    f"Registros descargados: "
    f"{len(todos_los_registros):,}"
)

print(
    f"Registros esperados:   "
    f"{total:,}"
)


if len(todos_los_registros) != total:

    print(
        "\n⚠️ ADVERTENCIA:"
    )

    print(
        "La cantidad descargada no coincide "
        "con la cantidad reportada por la API."
    )


# ============================================================
# DATAFRAME
# ============================================================

if not todos_los_registros:

    print("\n❌ No se descargaron registros.")
    exit()


print("\n📦 Construyendo DataFrame...")

df = pd.DataFrame(
    todos_los_registros
)

print(
    f"📐 Filas:    {df.shape[0]:,}"
)

print(
    f"📐 Columnas: {df.shape[1]}"
)


# ============================================================
# LISTADO DE VARIABLES
# ============================================================

print("\n")
print("=" * 70)
print("📋 VARIABLES ENCONTRADAS")
print("=" * 70)

for columna in df.columns:

    print(
        f"  • {columna:<35} "
        f"Tipo: {str(df[columna].dtype):<12} "
        f"Faltantes: {df[columna].isna().sum():,}"
    )


# ============================================================
# CONVERSIÓN DE FECHA
# ============================================================

if "fecha_accidente" in df.columns:

    print(
        "\n📅 Procesando columna "
        "fecha_accidente..."
    )

    df["fecha_accidente"] = pd.to_datetime(
        df["fecha_accidente"],
        errors="coerce"
    )

    fechas_invalidas = (
        df["fecha_accidente"].isna().sum()
    )

    print(
        f"   Fechas no convertibles: "
        f"{fechas_invalidas:,}"
    )


# ============================================================
# DIAGNÓSTICO DE DUPLICADOS
# ============================================================

print("\n")
print("=" * 70)
print("🔁 DUPLICADOS")
print("=" * 70)

duplicados = df.duplicated().sum()

print(
    f"Registros duplicados completos: "
    f"{duplicados:,}"
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
].sort_values(
    ascending=False
)

if len(faltantes) == 0:

    print(
        "✅ No existen valores faltantes."
    )

else:

    print(
        faltantes.to_string()
    )


# ============================================================
# COBERTURA TEMPORAL
# ============================================================

print("\n")
print("=" * 70)
print("📅 COBERTURA TEMPORAL")
print("=" * 70)

if "fecha_accidente" in df.columns:

    fecha_min = df["fecha_accidente"].min()

    fecha_max = df["fecha_accidente"].max()

    print(
        f"Fecha inicial: {fecha_min}"
    )

    print(
        f"Fecha final:   {fecha_max}"
    )

    print(
        f"Años registrados: "
        f"{df['fecha_accidente'].dt.year.nunique()}"
    )

    print("\nRegistros por año:")

    print(
        df["fecha_accidente"]
        .dt.year
        .value_counts()
        .sort_index()
        .to_string()
    )


# ============================================================
# DEPARTAMENTOS
# ============================================================

print("\n")
print("=" * 70)
print("🗺️ DEPARTAMENTOS")
print("=" * 70)

if "departamento_accidente" in df.columns:

    print(
        f"Departamentos registrados: "
        f"{df['departamento_accidente'].nunique()}"
    )

    print("\nTop 20:")

    print(
        df["departamento_accidente"]
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

if "municipio_accidente" in df.columns:

    print(
        f"Municipios registrados: "
        f"{df['municipio_accidente'].nunique()}"
    )

    print("\nTop 20:")

    print(
        df["municipio_accidente"]
        .value_counts()
        .head(20)
        .to_string()
    )


# ============================================================
# GRAVEDAD
# ============================================================

print("\n")
print("=" * 70)
print("🚨 GRAVEDAD DE LOS ACCIDENTES")
print("=" * 70)

if "gravedad_accidente" in df.columns:

    print(
        df["gravedad_accidente"]
        .value_counts()
        .to_string()
    )


# ============================================================
# TIPO DE VEHÍCULO
# ============================================================

print("\n")
print("=" * 70)
print("🚗 TIPO DE VEHÍCULO")
print("=" * 70)

if "tipo_vehiculo" in df.columns:

    print(
        df["tipo_vehiculo"]
        .value_counts()
        .head(30)
        .to_string()
    )


# ============================================================
# MARCA
# ============================================================

print("\n")
print("=" * 70)
print("🏭 MARCAS")
print("=" * 70)

if "marca_vehiculo" in df.columns:

    print(
        df["marca_vehiculo"]
        .value_counts()
        .head(20)
        .to_string()
    )


# ============================================================
# AUTORIDAD DE TRÁNSITO
# ============================================================

print("\n")
print("=" * 70)
print("👮 AUTORIDAD DE TRÁNSITO")
print("=" * 70)

if "autoridad_de_transito" in df.columns:

    print(
        df["autoridad_de_transito"]
        .value_counts()
        .head(20)
        .to_string()
    )


# ============================================================
# EDAD DEL VEHÍCULO
# ============================================================

print("\n")
print("=" * 70)
print("🚙 EDAD DEL VEHÍCULO")
print("=" * 70)

if "edad_vehiculo" in df.columns:

    edad = pd.to_numeric(
        df["edad_vehiculo"],
        errors="coerce"
    )

    print(
        edad.describe().to_string()
    )


# ============================================================
# MODELO DEL VEHÍCULO
# ============================================================

print("\n")
print("=" * 70)
print("📆 MODELO DEL VEHÍCULO")
print("=" * 70)

if "modelo_vehiculo" in df.columns:

    modelo = pd.to_numeric(
        df["modelo_vehiculo"],
        errors="coerce"
    )

    print(
        modelo.describe().to_string()
    )


# ============================================================
# GUARDAR CSV
# ============================================================

print("\n")
print("=" * 70)
print("💾 GUARDANDO DATASET")
print("=" * 70)

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print(
    f"\n✅ Dataset guardado correctamente:"
)

print(
    f"   {OUTPUT_FILE}"
)


# ============================================================
# RESUMEN FINAL
# ============================================================

print("\n")
print("=" * 70)
print("🎯 RESUMEN FINAL")
print("=" * 70)

print(
    f"""
Registros:              {len(df):,}
Variables:              {len(df.columns)}
Valores faltantes:      {df.isna().sum().sum():,}
Duplicados completos:   {duplicados:,}
"""
)

if "fecha_accidente" in df.columns:

    print(
        f"Periodo:                "
        f"{df['fecha_accidente'].min().date()} → "
        f"{df['fecha_accidente'].max().date()}"
    )

if "departamento_accidente" in df.columns:

    print(
        f"Departamentos:          "
        f"{df['departamento_accidente'].nunique():,}"
    )

if "municipio_accidente" in df.columns:

    print(
        f"Municipios:             "
        f"{df['municipio_accidente'].nunique():,}"
    )

print("\n")
print("🎉 PROCESO TERMINADO")
print("=" * 70)

print(
    "\n📁 Archivo generado:"
)

print(
    f"   {OUTPUT_FILE}"
)

print(
    "\n👉 No se realizó limpieza ni eliminación "
    "de registros."
)

print(
    "👉 El archivo conserva los datos obtenidos "
    "desde la API."
)