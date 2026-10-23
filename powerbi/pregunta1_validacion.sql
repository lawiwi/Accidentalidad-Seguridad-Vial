/* =====================================================================
   Pregunta 1 · Composición y distribución de la población
   Consultas para validar en SQL Server los valores del tablero de Power BI
   Base: IntegracionSiniestrosVehiculos
   ===================================================================== */
   USE IntegracionSiniestrosVehiculos_Equipo;
GO

-- 1. Total de vehículos involucrados (debe coincidir con [Total Vehiculos])
SELECT COUNT(*) AS TotalVehiculos FROM dbo.Vehiculo;

-- 2. Composición por tipo de vehículo, con % sobre el total
SELECT  t.NombreTipoVehiculo,
        COUNT(*) AS Vehiculos,
        CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS DECIMAL(6,2)) AS Porcentaje
FROM dbo.Vehiculo v
LEFT JOIN dbo.TipoVehiculo t ON t.IdTipoVehiculo = v.IdTipoVehiculo
GROUP BY t.NombreTipoVehiculo
ORDER BY Vehiculos DESC;

-- 3. Diez marcas principales, con % y % acumulado
WITH M AS (
    SELECT  ISNULL(m.NombreMarca, 'Sin dato') AS Marca, COUNT(*) AS Vehiculos
    FROM dbo.Vehiculo v
    LEFT JOIN dbo.Marca m ON m.IdMarca = v.IdMarca
    GROUP BY m.NombreMarca
)
SELECT TOP 10 Marca, Vehiculos,
       CAST(100.0 * Vehiculos / SUM(Vehiculos) OVER () AS DECIMAL(6,2)) AS Porcentaje,
       CAST(100.0 * SUM(Vehiculos) OVER (ORDER BY Vehiculos DESC ROWS UNBOUNDED PRECEDING)
            / SUM(Vehiculos) OVER () AS DECIMAL(6,2)) AS PorcentajeAcumulado
FROM M
ORDER BY Vehiculos DESC;

-- 4. Edad al accidente (año del accidente - año del modelo, mínimo 0) por rango
WITH E AS (
    SELECT CASE WHEN f.Anio - v.AnioModelo < 0 THEN 0 ELSE f.Anio - v.AnioModelo END AS Edad
    FROM dbo.Vehiculo v
    JOIN dbo.Fecha f ON f.IdFecha = v.IdFechaAccidente
)
SELECT  CASE WHEN Edad IS NULL THEN '7 Sin dato'
             WHEN Edad <= 2  THEN '1 0-2 años'
             WHEN Edad <= 5  THEN '2 3-5 años'
             WHEN Edad <= 10 THEN '3 6-10 años'
             WHEN Edad <= 15 THEN '4 11-15 años'
             WHEN Edad <= 20 THEN '5 16-20 años'
             ELSE '6 Más de 20 años' END AS RangoEdad,
        COUNT(*) AS Vehiculos,
        CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS DECIMAL(6,2)) AS Porcentaje
FROM E
GROUP BY CASE WHEN Edad IS NULL THEN '7 Sin dato'
              WHEN Edad <= 2  THEN '1 0-2 años'
              WHEN Edad <= 5  THEN '2 3-5 años'
              WHEN Edad <= 10 THEN '3 6-10 años'
              WHEN Edad <= 15 THEN '4 11-15 años'
              WHEN Edad <= 20 THEN '5 16-20 años'
              ELSE '6 Más de 20 años' END
ORDER BY RangoEdad;

-- 5. Mediana de la edad al accidente (debe dar 6)
SELECT DISTINCT
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY
           CASE WHEN f.Anio - v.AnioModelo < 0 THEN 0 ELSE f.Anio - v.AnioModelo END) OVER () AS EdadMediana
FROM dbo.Vehiculo v
JOIN dbo.Fecha f ON f.IdFecha = v.IdFechaAccidente;

-- 6. Calidad: registros sin marca y sin año de modelo (faltantes, no ceros)
SELECT SUM(CASE WHEN IdMarca IS NULL THEN 1 ELSE 0 END)    AS SinMarca,
       SUM(CASE WHEN AnioModelo IS NULL THEN 1 ELSE 0 END) AS SinAnioModelo,
       SUM(CASE WHEN EdadVehiculo IS NULL THEN 1 ELSE 0 END) AS SinEdadOriginal
FROM dbo.Vehiculo;
