import requests
import pandas as pd
import os
import time


# ============================================================
# CONFIGURACIÓN
# ============================================================

URL = (
    "https://srvansvargweb.ansv.gov.co/server/rest/services/"
    "Hosted/Datos_siniestros/FeatureServer/0/query"
)

# Cantidad máxima permitida por consulta según el servicio
TAMANO_LOTE = 2000

# Carpeta donde guardaremos el dataset
CARPETA_SALIDA = "data"

# Nombre del archivo final
ARCHIVO_SALIDA = os.path.join(
    CARPETA_SALIDA,
    "siniestros_viales.csv"
)


# ============================================================
# CREAR CARPETA
# ============================================================

os.makedirs(CARPETA_SALIDA, exist_ok=True)


# ============================================================
# OBTENER CANTIDAD TOTAL DE REGISTROS
# ============================================================

def obtener_total_registros():

    print("🔎 Consultando cantidad total de registros...")

    parametros = {
        "where": "1=1",
        "returnCountOnly": "true",
        "f": "json"
    }

    respuesta = requests.get(
        URL,
        params=parametros,
        timeout=60
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    if "count" not in datos:
        print("❌ No se pudo obtener la cantidad de registros.")
        print(datos)
        return None

    total = datos["count"]

    print(f"📊 Registros encontrados: {total:,}")

    return total


# ============================================================
# DESCARGAR REGISTROS
# ============================================================

def descargar_registros(total):

    registros = []

    offset = 0

    while offset < total:

        print(
            f"\n⬇️ Descargando registros "
            f"{offset + 1:,} - "
            f"{min(offset + TAMANO_LOTE, total):,} "
            f"de {total:,}..."
        )

        parametros = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "resultOffset": offset,
            "resultRecordCount": TAMANO_LOTE,
            "orderByFields": "fid ASC",
            "f": "json"
        }

        respuesta = requests.get(
            URL,
            params=parametros,
            timeout=120
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

        # Verificar errores de ArcGIS
        if "error" in datos:

            print("❌ ArcGIS devolvió un error:")
            print(datos["error"])

            break

        features = datos.get("features", [])

        if not features:
            print("⚠️ No se recibieron más registros.")
            break

        for feature in features:

            atributos = feature.get("attributes", {})

            registros.append(atributos)

        print(
            f"   ✅ Lote descargado: "
            f"{len(features):,} registros"
        )

        offset += len(features)

        # Evitar realizar demasiadas solicitudes consecutivas
        time.sleep(0.5)

    return registros


# ============================================================
# GUARDAR CSV
# ============================================================

def guardar_csv(registros):

    if not registros:

        print("❌ No hay registros para guardar.")
        return False

    print("\n💾 Construyendo DataFrame...")

    df = pd.DataFrame(registros)

    print(f"📐 Filas: {len(df):,}")
    print(f"📐 Columnas: {len(df.columns)}")

    # Convertir fecha
    if "fecha_hech" in df.columns:

        print("📅 Procesando columna fecha_hech...")

        df["fecha_hech"] = pd.to_datetime(
            df["fecha_hech"],
            unit="ms",
            errors="coerce"
        )

    # Guardar CSV
    df.to_csv(
        ARCHIVO_SALIDA,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"\n✅ Dataset guardado correctamente:"
        f"\n   {ARCHIVO_SALIDA}"
    )

    return True


# ============================================================
# RESUMEN DEL DATASET
# ============================================================

def mostrar_resumen(registros):

    if not registros:
        return

    df = pd.DataFrame(registros)

    print("\n")
    print("=" * 60)
    print("📊 RESUMEN DEL DATASET")
    print("=" * 60)

    print(f"Registros: {len(df):,}")
    print(f"Variables: {len(df.columns)}")

    print("\n📋 VARIABLES:")

    for columna in df.columns:

        tipo = df[columna].dtype

        faltantes = df[columna].isna().sum()

        print(
            f"  • {columna:<20} "
            f"Tipo: {str(tipo):<12} "
            f"Faltantes: {faltantes:,}"
        )

    print("\n")
    print("=" * 60)


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print("=" * 60)
    print("🚦 DESCARGA DATASET — SINIESTROS VIALES ANSV")
    print("=" * 60)

    print("\n🌐 Fuente:")
    print(URL)

    # --------------------------------------------------------
    # 1. Obtener cantidad total
    # --------------------------------------------------------

    total = obtener_total_registros()

    if total is None:
        return

    if total == 0:

        print("⚠️ El servicio no devolvió registros.")
        return

    # --------------------------------------------------------
    # 2. Verificar requisito académico
    # --------------------------------------------------------

    print("\n🎓 Verificación del requisito:")

    if total >= 10000:

        print(
            "   ✅ El dataset supera los 10.000 registros "
            "requeridos."
        )

    else:

        print(
            "   ⚠️ El dataset NO alcanza los 10.000 registros."
        )

        respuesta = input(
            "\n¿Deseas descargarlo de todas formas? (s/n): "
        )

        if respuesta.lower() != "s":

            print("❌ Descarga cancelada.")
            return

    # --------------------------------------------------------
    # 3. Descargar todos los registros
    # --------------------------------------------------------

    registros = descargar_registros(total)

    # --------------------------------------------------------
    # 4. Mostrar resumen
    # --------------------------------------------------------

    mostrar_resumen(registros)

    # --------------------------------------------------------
    # 5. Guardar
    # --------------------------------------------------------

    guardar_csv(registros)

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("🎉 PROCESO TERMINADO")
    print("=" * 60)

    print(
        f"\n📁 Archivo generado:"
        f"\n   {ARCHIVO_SALIDA}"
    )

    print(
        "\n👉 Ahora podemos analizar el dataset "
        "para la Etapa 1."
    )


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":
    main()