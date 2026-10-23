# Pregunta 1 · Composición y distribución de la población

Página **«1 · Composición»** del informe de Power BI de la Etapa 4 (Conocimiento evidente).

| Elemento | Ubicación |
|---|---|
| Archivo PBIX | `powerbi/Etapa4_ConocimientoEvidente.pbix` (si supera 100 MB, ver enlace de descarga abajo) |
| Medidas DAX | `powerbi/pregunta1_medidas_dax.md` |
| Textos del tablero | `powerbi/pregunta1_textos_tablero.md` |
| Consultas de validación | `powerbi/pregunta1_validacion.sql` |
| Tema de colores | `powerbi/tema_accidentalidad.json` |
| Plano de la página | `powerbi/referencia_pagina1_composicion.png` |
| Plano de la página | `powerbi/referencia_pagina1_composicion.png` |
| Vista web | `templates/Etapa4/integrante1.html` → ruta `/Etapa4/integrante1` |

**URL del informe publicado:** _(pegar aquí)_
**URL de la aplicación publicada:** _(pegar aquí)_/Etapa4/integrante1
**Enlace de descarga del PBIX (si no cabe en GitHub):** _(pegar aquí)_

## Datos utilizados

- Base SQL Server `IntegracionSiniestrosVehiculos` (modelo final del ETL de la Etapa 3), restaurada localmente como `IntegracionSiniestrosVehiculos_Equipo`.
- Tablas: `Vehiculo` (hechos, 406.540 filas), `TipoVehiculo`, `Marca`, `GravedadAccidente`, `Fecha`.
- Fuente original: Datos Abiertos Colombia, «Vehículos involucrados en un accidente de tránsito» (6jmc-vaxk).
- Periodo: enero 2022 – febrero 2026 (fecha registrada por mes).
- Alternativa sin SQL Server: `vehiculos_limpio.csv` exportado de la tabla `Vehiculo` (mismas 406.540 filas).

### Cómo obtener la base

El archivo `.bak` contiene **tres respaldos**; el completo es el **tercero** (`FILE = 3`). Los dos primeros tienen la tabla `Vehiculo` vacía.

1. Copiar el `.bak` a la carpeta `Backup` de la instancia (por ejemplo `C:\Program Files\Microsoft SQL Server\MSSQL17.SQL2025M\MSSQL\Backup\`).
2. En SSMS ejecutar (ajustando rutas e instancia):

```sql
USE master;
GO
RESTORE DATABASE [IntegracionSiniestrosVehiculos_Equipo]
FROM DISK = N'C:\Program Files\Microsoft SQL Server\MSSQL17.SQL2025M\MSSQL\Backup\IntegracionSiniestrosVehiculos_Equipo.bak'
WITH FILE = 3,
     MOVE N'IntegracionSiniestrosVehiculos'     TO N'C:\Program Files\Microsoft SQL Server\MSSQL17.SQL2025M\MSSQL\DATA\IntegracionSiniestrosVehiculos_Equipo.mdf',
     MOVE N'IntegracionSiniestrosVehiculos_log' TO N'C:\Program Files\Microsoft SQL Server\MSSQL17.SQL2025M\MSSQL\DATA\IntegracionSiniestrosVehiculos_Equipo_log.ldf',
     RECOVERY, STATS = 10;
GO
SELECT COUNT(*) AS Vehiculos FROM IntegracionSiniestrosVehiculos_Equipo.dbo.Vehiculo;  -- debe dar 406540
```

3. Ejecutar `pregunta1_validacion.sql` y comparar con los valores esperados de `pregunta1_medidas_dax.md`.

## Cómo abrir el informe

1. Instalar Power BI Desktop (Microsoft Store).
2. Restaurar la base (ver arriba) y comprobar que el servicio de SQL Server está iniciado.
3. Abrir `Etapa4_ConocimientoEvidente.pbix`.
4. Si el servidor es distinto, ir a **Transformar datos → Configuración de origen de datos → Cambiar origen** y escribir el servidor propio (en el equipo de desarrollo: `localhost\SQL2025M`, base `IntegracionSiniestrosVehiculos_Equipo`). La conexión es local y sin cifrado (desmarcar «Usar conexión cifrada»).

## Diseño de la página

`referencia_pagina1_composicion.png` muestra la ubicación (X, Y, ancho, alto) de cada elemento de la página «1. Composición» (lienzo 1280 × 1800).

## Cómo actualizar el informe

1. Si cambian los datos en SQL Server, en Power BI Desktop pulsar **Inicio → Actualizar**.
2. Ejecutar `pregunta1_validacion.sql` en SSMS y comparar con la tabla «Valores esperados» de `pregunta1_medidas_dax.md`.
3. Si los valores cambian, actualizar los textos de interpretación y conocimientos (las tarjetas con medidas se actualizan solas).
4. Guardar, y **Inicio → Publicar** al área de trabajo del equipo. El enlace de inserción no cambia al volver a publicar.
