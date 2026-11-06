# Modelo multidimensional · Etapa 5

Modelo estrella de **vehículos involucrados en accidentes de tránsito con víctimas** (Colombia, ene. 2022 – feb. 2026), construido a partir de los datos tratados de la Etapa 3. Solo se usa la fuente de vehículos (`dbo.Vehiculo`); la fuente de siniestros no se mezcla.

## Granularidad

Una fila de `FactVehiculoAccidente` = un registro de `dbo.Vehiculo`: un vehículo, en un mes, en un municipio, reportado por un organismo de tránsito. No es un accidente, ni un vehículo único (no hay placa), ni una persona.

## Contenido

| Carpeta / archivo | Qué es |
|---|---|
| `sql/01_creacion_modelo_estrella.sql` | Crea `DW_AccidentalidadVial`, los sinónimos `src.*` hacia la base tratada y las 8 tablas con PK, FK, CHECK e índices. |
| `sql/02_carga_dimensiones.sql` | Transforma y carga las 7 dimensiones (incluye el miembro −1 «Sin dato»). |
| `sql/03_carga_hechos.sql` | Carga el hecho resolviendo las claves; crea la vista `vw_CuboVehiculos`. |
| `sql/04_consultas_analisis.sql` | Consultas de las 4 preguntas, ejemplos de las 5 operaciones y evidencia de los 8 conocimientos. |
| `sql/05_validaciones.sql` | Unicidad, integridad, duplicados, faltantes y 6 comparaciones con el origen. |
| `sql/consultas_prueba_sqlite.sql` | Pruebas rápidas sobre la réplica SQLite (`etl/probar_consultas.py`). |
| `etl/reglas.py` | Reglas de transformación (mismas que en T-SQL). |
| `etl/construir_dw.py` | ETL reproducible: origen tratado → réplica SQLite + `dw/validacion_etl.json`. |
| `origen_tratado/*.csv.gz` | Exportación de `dbo.Vehiculo` y sus catálogos (respaldo FILE = 3). |
| `dw/dw_accidentalidad_vial.sqlite` | Réplica del modelo estrella que consulta Flask. |
| `diagrama/modelo_estrella.svg` / `.png` | Diagrama del modelo. |

## Orden de ejecución

**SQL Server (SSMS):** restaurar el `.bak` con `WITH FILE = 3` → `01` → `02` → `03` → `05` → `04`.

**Réplica SQLite:**

```bash
python modelo_multidimensional/etl/construir_dw.py              # desde origen_tratado/
python modelo_multidimensional/etl/construir_dw.py --origen sqlserver \
  --url "mssql+pyodbc://@localhost\SQL2025/IntegracionSiniestrosVehiculos?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
python modelo_multidimensional/etl/probar_consultas.py
```

## Regenerar `origen_tratado/` desde SQL Server (opcional)

Con `construir_dw.py --origen sqlserver` no hace falta. Si se quieren actualizar los CSV, exportar con SSMS (*Tareas → Exportar datos*) o `bcp` las consultas de `SQL_EXTRACCION` en `etl/construir_dw.py` a `NombreTabla.csv` con encabezado y UTF-8; el ETL acepta `.csv` y `.csv.gz`.

## Resultados esperados

DimTiempo 51 · DimUbicacion 556 · DimTipoVehiculo 29 · DimMarca 361 · DimGravedad 3 · DimAutoridadTransito 233 · DimAntiguedad 89 · FactVehiculoAccidente 406.540 (filas con el miembro −1 incluido). Comparaciones con el origen: diferencia 0.
