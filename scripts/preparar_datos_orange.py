"""
Etapa 6 · Prepara los archivos que usan los flujos de Orange a partir del modelo estrella (Etapa 5).

Origen : modelo_multidimensional/dw/dw_accidentalidad_vial.sqlite  (réplica del DW de la Etapa 5)
Salidas: data/orange/
    vehiculos_gravedad_completo.tab          406.540 filas (todas)
    vehiculos_gravedad_muestra100k.tab       100.000 filas, muestra estratificada por Gravedad (semilla 42)
    vehiculos_entrenamiento_2022_2024.tab    parte de la muestra con años 2022-2024 (validación temporal)
    vehiculos_prueba_2025_2026.tab           parte de la muestra con años 2025-feb 2026
    perfil_municipios.tab                    248 municipios con ≥ 50 vehículos registrados (clustering)

Transformaciones adicionales a las de etapas anteriores (documentadas en el informe):
  T1. Se unen el hecho y las dimensiones en una sola tabla plana (Orange no hace JOIN).
  T2. Tipos de vehículo con menos de 800 registros (maquinaria, cuadriciclos…) → «Otro (maquinaria/especial)».
  T3. Marca: 15 marcas más frecuentes + «Otras marcas» (de 361 categorías a 16).
  T4. Variables redundantes o que no deben predecir quedan como META (visibles, pero no entran al modelo):
      CategoriaVehiculo (deriva de TipoVehiculo), GrupoEdad (deriva de EdadVehiculo), Region (deriva de
      Departamento), Trimestre (deriva de Mes), Anio (solo sirve para la partición temporal), IdRegistro, Municipio.
  T5. Se excluye VehiculoAccidenteConMuertos: es la misma variable objetivo codificada como 0/1 (fuga de información).
  T6. Archivos .tab con 3 filas de encabezado: nombre, tipo (d = discreta, c = continua, s = texto) y rol
      (class / meta), para que Orange reconozca la variable objetivo sin configuración manual.
  T7. Perfil municipal: porcentajes por municipio calculados SIN usar la gravedad; PctConMuertos se guarda solo
      como META para caracterizar los grupos después de formarlos.

Uso (desde la raíz del repositorio):
    python scripts/preparar_datos_orange.py
"""
import os
import sqlite3

import numpy as np
import pandas as pd

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))   # scripts/ → raíz del repositorio
DW = os.path.join(RAIZ, "modelo_multidimensional", "dw", "dw_accidentalidad_vial.sqlite")
DESTINO = os.path.join(RAIZ, "data", "orange")

CONSULTA = """
SELECT f.IdRegistroOrigen, f.EdadAlAccidente, f.ModeloPosteriorAlAccidente,
       t.Anio, t.NumeroMes, t.Trimestre,
       u.RegionNatural, u.Departamento, u.Municipio, u.AmbitoProyecto,
       tv.TipoVehiculo, tv.CategoriaVehiculo, m.Marca, g.Gravedad,
       a.TipoEntidad, a.NivelTerritorial, an.GrupoEdad
FROM FactVehiculoAccidente f
JOIN DimTiempo t USING (SK_Tiempo)            JOIN DimUbicacion u USING (SK_Ubicacion)
JOIN DimTipoVehiculo tv USING (SK_TipoVehiculo) JOIN DimMarca m USING (SK_Marca)
JOIN DimGravedad g USING (SK_Gravedad)        JOIN DimAutoridadTransito a USING (SK_Autoridad)
JOIN DimAntiguedad an USING (SK_Antiguedad)
"""


def escribir_tab(df, ruta, tipos, roles):
    """Formato nativo de Orange: fila 1 nombres, fila 2 tipos, fila 3 roles."""
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write("\t".join(df.columns) + "\n")
        f.write("\t".join(tipos.get(c, "d") for c in df.columns) + "\n")
        f.write("\t".join(roles.get(c, "") for c in df.columns) + "\n")
        df.to_csv(f, sep="\t", header=False, index=False, lineterminator="\n")
    print(f"  {os.path.relpath(ruta, RAIZ):<55} {len(df):>8,} filas")


def main():
    os.makedirs(DESTINO, exist_ok=True)
    with sqlite3.connect(DW) as cn:
        df = pd.read_sql(CONSULTA, cn)
    print(f"Registros leídos del modelo estrella: {len(df):,}")

    # ---------------- Dataset supervisado ----------------
    frec_tipo = df.TipoVehiculo.value_counts()
    df["TipoVehiculoAgr"] = np.where(df.TipoVehiculo.isin(frec_tipo[frec_tipo >= 800].index),
                                     df.TipoVehiculo, "Otro (maquinaria/especial)")                       # T2
    top_marcas = df.Marca.value_counts().head(15).index
    df["MarcaAgr"] = np.where(df.Marca.isin(top_marcas), df.Marca, "Otras marcas")                        # T3
    sup = pd.DataFrame({
        "Gravedad": df.Gravedad, "CategoriaVehiculo": df.CategoriaVehiculo, "TipoVehiculo": df.TipoVehiculoAgr,
        "EdadVehiculo": df.EdadAlAccidente, "GrupoEdad": df.GrupoEdad, "Marca": df.MarcaAgr,
        "Region": df.RegionNatural, "Departamento": df.Departamento, "NivelAutoridad": df.NivelTerritorial,
        "TipoEntidad": df.TipoEntidad, "Anio": df.Anio.astype(str), "Mes": df.NumeroMes,
        "Trimestre": "T" + df.Trimestre.astype(str), "ModeloPosterior": df.ModeloPosteriorAlAccidente.map({0: "No", 1: "Sí"}),
        "IdRegistro": df.IdRegistroOrigen, "Municipio": df.Municipio,
    })
    tipos = {"EdadVehiculo": "c", "Mes": "c", "IdRegistro": "s", "Municipio": "s"}
    roles = {"Gravedad": "class", **{c: "meta" for c in
             ["CategoriaVehiculo", "GrupoEdad", "Region", "Trimestre", "Anio", "IdRegistro", "Municipio"]}}  # T4
    escribir_tab(sup, os.path.join(DESTINO, "vehiculos_gravedad_completo.tab"), tipos, roles)
    muestra = sup.groupby("Gravedad").sample(frac=100_000 / len(sup), random_state=42).sample(frac=1, random_state=42)
    escribir_tab(muestra, os.path.join(DESTINO, "vehiculos_gravedad_muestra100k.tab"), tipos, roles)
    escribir_tab(muestra[muestra.Anio.isin(["2022", "2023", "2024"])],
                 os.path.join(DESTINO, "vehiculos_entrenamiento_2022_2024.tab"), tipos, roles)
    escribir_tab(muestra[muestra.Anio.isin(["2025", "2026"])],
                 os.path.join(DESTINO, "vehiculos_prueba_2025_2026.tab"), tipos, roles)

    # ---------------- Perfil municipal para clustering ----------------
    df["MunDep"] = df.Municipio + " (" + df.Departamento + ")"
    g = df.groupby("MunDep")
    pct = lambda col, valor: g[col].apply(lambda s: (s == valor).mean() * 100)
    P = pd.DataFrame({
        "Departamento": g.Departamento.first(), "Region": g.RegionNatural.first(), "Ambito": g.AmbitoProyecto.first(),
        "Registros": g.size(),
        "PctMotos": pct("CategoriaVehiculo", "Motocicletas y similares"), "PctLivianos": pct("CategoriaVehiculo", "Vehículo liviano"),
        "PctPasajeros": pct("CategoriaVehiculo", "Transporte de pasajeros"), "PctCarga": pct("CategoriaVehiculo", "Vehículo de carga"),
        "EdadMediana": g.EdadAlAccidente.median(), "PctMas15Anios": g.EdadAlAccidente.apply(lambda s: (s > 15).mean() * 100),
        "PctPoliciaNacional": pct("NivelTerritorial", "Nacional"),
        "PctConMuertos": pct("Gravedad", "Con Muertos"),                                                  # T7 (solo meta)
    })
    P = P[P.Registros >= 50].copy()
    P["LogRegistros"] = np.log10(P.Registros)
    P = P.reset_index().rename(columns={"MunDep": "Municipio"}).round(3)
    cols = ["Municipio", "Departamento", "Region", "Ambito", "Registros", "LogRegistros", "PctMotos", "PctLivianos",
            "PctPasajeros", "PctCarga", "EdadMediana", "PctMas15Anios", "PctPoliciaNacional", "PctConMuertos"]
    activas = ["PctMotos", "PctCarga", "EdadMediana", "PctPoliciaNacional"]
    tipos = {c: "c" for c in cols} | {"Municipio": "s", "Departamento": "d", "Region": "d", "Ambito": "d"}
    roles = {c: "meta" for c in cols if c not in activas}
    escribir_tab(P[cols], os.path.join(DESTINO, "perfil_municipios.tab"), tipos, roles)


if __name__ == "__main__":
    main()
