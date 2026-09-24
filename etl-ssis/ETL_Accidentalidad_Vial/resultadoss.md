# Iteración 1 — Data Flow de Extracción y Transformación (Persona 3)

## Conteos
- Registros originales (CSV): 406.540
- Cargados a StagingVehiculos: 406.540
- Con edad faltante (Data Conversion error output): 20
- Después de eliminar duplicados exactos (Sort): 258.945
- Duplicados eliminados: 147.575
- Aceptados (VehiculosLimpios): 250.299
- Enviados a revisión (VehiculosRevision): 8.666 (8.646 por edad atípica/modelo inconsistente + 20 por edad faltante)

## Reglas aplicadas
- Marca vacía = "NO REGISTRADA"
- Edad faltante  = conservada como nula, registro enviado a revisión
- Fecha convertida de texto a tipo fecha
- Edad > 50 años = marcada como atípica, enviada a revisión
- Modelo del vehículo posterior al año del accidente 0 marcado como inconsistente, enviado a revisión
- Texto normalizado (mayúsculas, sin espacios) en marca, tipo, departamento, municipio, autoridad
- Duplicados completos eliminados con Sort

## Cómo ejecutar el paquete
1. Requiere SQL Server 2025 (o compatible) con la base `IntegracionSiniestrosVehiculos` restaurada.
2. Ejecutar `create_tables.sql` primero para crear las tablas si no existen.
3. Abrir `ETL_Accidentalidad_Vial.dtproj` en Visual Studio con extensión SSIS instalada.
4. Ajustar el Connection Manager al servidor local si es necesario.
5. Ejecutar el paquete completo (F5) desde Control Flow — trunca las tablas y recarga todo desde cero.
