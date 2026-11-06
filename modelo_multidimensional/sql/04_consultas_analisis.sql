/* =====================================================================================
   04_consultas_analisis.sql  ·  Consultas de las 4 preguntas, de las 5 operaciones
                                 multidimensionales y de la evidencia de los 8 conocimientos
   -------------------------------------------------------------------------------------
   Base: DW_AccidentalidadVial (scripts 01, 02 y 03 ejecutados).
   Los valores esperados en los comentarios se obtuvieron con los datos tratados de la
   Etapa 3 (406.540 vehículos) en la réplica SQLite que consulta Flask; al ejecutar en
   SQL Server deben coincidir. Si alguno difiere, revisar 05_validaciones.sql.

   Regla de cálculo: las consultas suman SOLO medidas aditivas (CantidadVehiculos,
   VehiculoAccidenteConMuertos, EdadAlAccidente) y calculan porcentajes y promedios
   después de agrupar, para que se recalculen en cada nivel.
   ===================================================================================== */
USE DW_AccidentalidadVial;
GO

/* =====================================================================================
   A. CONSULTAS BASE DE LAS CUATRO PREGUNTAS
   ===================================================================================== */

-- P1 · Tiempo × Ubicación × Autoridad: vehículos por año y región
SELECT t.Anio, u.RegionNatural,
       SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.CantidadVehiculos) / SUM(SUM(f.CantidadVehiculos)) OVER (PARTITION BY t.Anio) AS DECIMAL(6,2)) AS PctDelAnio
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTiempo    t ON t.SK_Tiempo    = f.SK_Tiempo
JOIN dbo.DimUbicacion u ON u.SK_Ubicacion = f.SK_Ubicacion
GROUP BY t.Anio, u.RegionNatural
ORDER BY t.Anio, Vehiculos DESC;
-- Esperado: 2022 = 114.478 · 2023 = 111.609 · 2024 = 120.342 · 2025 = 57.867 · 2026 = 2.244

-- P2 · Tipo de vehículo × Gravedad × Ubicación: % con muertos por categoría y región
SELECT tv.CategoriaVehiculo, u.RegionNatural,
       SUM(f.CantidadVehiculos)            AS Vehiculos,
       SUM(f.VehiculoAccidenteConMuertos)  AS VehiculosConMuertos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
JOIN dbo.DimUbicacion    u  ON u.SK_Ubicacion     = f.SK_Ubicacion
GROUP BY tv.OrdenCategoria, tv.CategoriaVehiculo, u.RegionNatural
ORDER BY tv.OrdenCategoria, u.RegionNatural;

-- P3 · Antigüedad × Tipo de vehículo × Gravedad
SELECT an.OrdenGrupo, an.GrupoEdad, tv.CategoriaVehiculo,
       SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.CantidadVehiculos) / SUM(SUM(f.CantidadVehiculos)) OVER (PARTITION BY tv.CategoriaVehiculo) AS DECIMAL(6,2)) AS PctDeLaCategoria,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos,
       CAST(1.0 * SUM(f.EdadAlAccidente) / COUNT(f.EdadAlAccidente) AS DECIMAL(6,2)) AS EdadPromedio
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimAntiguedad   an ON an.SK_Antiguedad   = f.SK_Antiguedad
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
GROUP BY an.OrdenGrupo, an.GrupoEdad, tv.CategoriaVehiculo
ORDER BY tv.CategoriaVehiculo, an.OrdenGrupo;

-- P4 · Marca × Tipo de vehículo × Ubicación × Gravedad: concentración de marcas por categoría
SELECT tv.CategoriaVehiculo, m.GrupoMarca,
       SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.CantidadVehiculos) / SUM(SUM(f.CantidadVehiculos)) OVER (PARTITION BY tv.CategoriaVehiculo) AS DECIMAL(6,2)) AS PctDeLaCategoria,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
JOIN dbo.DimMarca        m  ON m.SK_Marca         = f.SK_Marca
GROUP BY tv.CategoriaVehiculo, m.GrupoMarca
ORDER BY tv.CategoriaVehiculo, m.GrupoMarca;
GO

/* =====================================================================================
   B. LAS CINCO OPERACIONES MULTIDIMENSIONALES (un ejemplo de cada una)
   ===================================================================================== */

-- B1 · DRILL-DOWN (Tiempo): de Año a Mes dentro de 2024. Cambia el GROUP BY a un nivel inferior.
--      Nivel Año:  2024 = 120.342
SELECT t.Anio, SUM(f.CantidadVehiculos) AS Vehiculos
FROM dbo.FactVehiculoAccidente f JOIN dbo.DimTiempo t ON t.SK_Tiempo = f.SK_Tiempo
WHERE t.Anio = 2024
GROUP BY t.Anio;
--      Nivel Mes: la suma de los 12 meses vuelve a dar 120.342; julio = 28.794 (23,93 % del año)
SELECT t.AnioMes, SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.CantidadVehiculos) / SUM(SUM(f.CantidadVehiculos)) OVER () AS DECIMAL(6,2)) AS PctDelAnio
FROM dbo.FactVehiculoAccidente f JOIN dbo.DimTiempo t ON t.SK_Tiempo = f.SK_Tiempo
WHERE t.Anio = 2024
GROUP BY t.AnioMes
ORDER BY t.AnioMes;
--      Drill-down en Ubicación sobre el miembro julio 2024 -> Antioquia -> municipios
SELECT u.Municipio, SUM(f.CantidadVehiculos) AS Vehiculos
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTiempo t    ON t.SK_Tiempo    = f.SK_Tiempo
JOIN dbo.DimUbicacion u ON u.SK_Ubicacion = f.SK_Ubicacion
WHERE t.AnioMes = '2024-07' AND u.Departamento = N'Antioquia'
GROUP BY u.Municipio
ORDER BY Vehiculos DESC;   -- Medellín = 22.667

-- B2 · ROLL-UP (Tipo de vehículo): de Tipo a Categoría; el % se RECALCULA con las sumas, no se suma.
SELECT tv.CategoriaVehiculo, tv.TipoVehiculo,
       SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos
FROM dbo.FactVehiculoAccidente f JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
WHERE tv.CategoriaVehiculo = N'Vehículo de carga'
GROUP BY tv.CategoriaVehiculo, tv.TipoVehiculo;
SELECT tv.CategoriaVehiculo,
       SUM(f.CantidadVehiculos) AS Vehiculos,                          -- 17.875
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos  -- 21,10
FROM dbo.FactVehiculoAccidente f JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
WHERE tv.CategoriaVehiculo = N'Vehículo de carga'
GROUP BY tv.CategoriaVehiculo;
--      Variante con ROLLUP de SQL Server: subtotales por categoría y total general en una sola consulta
SELECT ISNULL(tv.CategoriaVehiculo, N'TOTAL') AS Categoria, ISNULL(tv.TipoVehiculo, N'(subtotal)') AS Tipo,
       SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos
FROM dbo.FactVehiculoAccidente f JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
GROUP BY ROLLUP (tv.CategoriaVehiculo, tv.TipoVehiculo)
ORDER BY GROUPING(tv.CategoriaVehiculo), tv.CategoriaVehiculo, GROUPING(tv.TipoVehiculo), Vehiculos DESC;

-- B3 · SLICE: Tipo de vehículo = Motocicleta (un valor de una dimensión) y comparación de marcas
SELECT TOP (10) m.Marca,
       SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.CantidadVehiculos) / SUM(SUM(f.CantidadVehiculos)) OVER () AS DECIMAL(6,2)) AS PctDeLasMotos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
JOIN dbo.DimMarca        m  ON m.SK_Marca         = f.SK_Marca
WHERE tv.TipoVehiculo = N'Motocicleta'
GROUP BY m.Marca
ORDER BY Vehiculos DESC;   -- Bajaj 52.779 (23,03 %; 5,49 % con muertos)

-- B4 · DICE: Categoría = Motocicletas y similares  Y  Gravedad = Con Muertos (dos dimensiones)
SELECT an.OrdenRango, an.RangoEdad, SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.CantidadVehiculos) / SUM(SUM(f.CantidadVehiculos)) OVER () AS DECIMAL(6,2)) AS PctDelSubconjunto
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
JOIN dbo.DimGravedad     g  ON g.SK_Gravedad      = f.SK_Gravedad
JOIN dbo.DimAntiguedad   an ON an.SK_Antiguedad   = f.SK_Antiguedad
WHERE tv.CategoriaVehiculo = N'Motocicletas y similares'
  AND g.NivelSeveridad = 2
GROUP BY an.OrdenRango, an.RangoEdad
ORDER BY an.OrdenRango;    -- total del subconjunto: 11.157 motos en accidentes con muertos

-- B5 · PIVOT: Nivel territorial de la autoridad × Año, y la disposición inversa (Año × Nivel)
SELECT NivelTerritorial, [2022], [2023], [2024], [2025], [2026]
FROM (SELECT a.NivelTerritorial, t.Anio, f.CantidadVehiculos
      FROM dbo.FactVehiculoAccidente f
      JOIN dbo.DimTiempo t            ON t.SK_Tiempo    = f.SK_Tiempo
      JOIN dbo.DimAutoridadTransito a ON a.SK_Autoridad = f.SK_Autoridad) AS s
PIVOT (SUM(CantidadVehiculos) FOR Anio IN ([2022], [2023], [2024], [2025], [2026])) AS p
ORDER BY NivelTerritorial;

SELECT Anio, [Municipal], [Distrital], [Nacional], [Departamental]
FROM (SELECT a.NivelTerritorial, t.Anio, f.CantidadVehiculos
      FROM dbo.FactVehiculoAccidente f
      JOIN dbo.DimTiempo t            ON t.SK_Tiempo    = f.SK_Tiempo
      JOIN dbo.DimAutoridadTransito a ON a.SK_Autoridad = f.SK_Autoridad) AS s
PIVOT (SUM(CantidadVehiculos) FOR NivelTerritorial IN ([Municipal], [Distrital], [Nacional], [Departamental])) AS p
ORDER BY Anio;
GO

/* =====================================================================================
   C. EVIDENCIA DE LOS OCHO CONOCIMIENTOS
   ===================================================================================== */

-- P1-C1 · Pico de julio de 2024 por autoridad (esperado: total 28.794; Medellín 22.667 = 78,72 %)
SELECT a.Autoridad, SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.CantidadVehiculos) / SUM(SUM(f.CantidadVehiculos)) OVER () AS DECIMAL(6,2)) AS PctDelMes
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTiempo t            ON t.SK_Tiempo    = f.SK_Tiempo
JOIN dbo.DimAutoridadTransito a ON a.SK_Autoridad = f.SK_Autoridad
WHERE t.AnioMes = '2024-07'
GROUP BY a.Autoridad
ORDER BY Vehiculos DESC;
--        Promedio mensual de esa autoridad ene-jun 2024 (esperado: 2.448,5)
SELECT AVG(1.0 * Vehiculos) AS PromedioEneJun2024
FROM (SELECT t.AnioMes, SUM(f.CantidadVehiculos) AS Vehiculos
      FROM dbo.FactVehiculoAccidente f
      JOIN dbo.DimTiempo t            ON t.SK_Tiempo    = f.SK_Tiempo
      JOIN dbo.DimAutoridadTransito a ON a.SK_Autoridad = f.SK_Autoridad
      WHERE a.Autoridad = N'STRIA DE TTOYTTE MEDELLIN' AND t.Anio = 2024 AND t.NumeroMes BETWEEN 1 AND 6
      GROUP BY t.AnioMes) AS x;

-- P1-C2 · Caída de 2025 y composición por nivel territorial (esperado: Medellín 44.092 -> 5; 70,57 % de la caída)
SELECT t.Anio, a.NivelTerritorial,
       SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.CantidadVehiculos) / SUM(SUM(f.CantidadVehiculos)) OVER (PARTITION BY t.Anio) AS DECIMAL(6,2)) AS PesoEnElAnio,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTiempo t            ON t.SK_Tiempo    = f.SK_Tiempo
JOIN dbo.DimAutoridadTransito a ON a.SK_Autoridad = f.SK_Autoridad
WHERE t.Anio IN (2024, 2025)
GROUP BY t.Anio, a.NivelTerritorial
ORDER BY t.Anio, Vehiculos DESC;   -- Nacional: 22,44 % (2024) y 22,04 % (2025); peso 8,48 % -> 19,09 %
SELECT t.Anio, SUM(f.CantidadVehiculos) AS VehiculosMedellin
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTiempo t            ON t.SK_Tiempo    = f.SK_Tiempo
JOIN dbo.DimAutoridadTransito a ON a.SK_Autoridad = f.SK_Autoridad
WHERE a.Autoridad = N'STRIA DE TTOYTTE MEDELLIN'
GROUP BY t.Anio ORDER BY t.Anio;

-- P2-C1 · % con muertos por tipo (esperado: tractocamión 28,86; volqueta 19,38; camión 17,77; motocicleta 4,84)
SELECT tv.CategoriaVehiculo, tv.TipoVehiculo, SUM(f.CantidadVehiculos) AS Vehiculos,
       SUM(f.VehiculoAccidenteConMuertos) AS ConMuertos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(SUM(f.VehiculoAccidenteConMuertos)) OVER () AS DECIMAL(6,2)) AS PctDeLosConMuertos
FROM dbo.FactVehiculoAccidente f JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
GROUP BY tv.CategoriaVehiculo, tv.TipoVehiculo
ORDER BY PctConMuertos DESC;

-- P2-C2 · Dice motos × región (esperado: Andina 3,54; Caribe 11,62; Orinoquía 11,89; Amazonía 19,33)
SELECT u.RegionNatural, SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
JOIN dbo.DimUbicacion    u  ON u.SK_Ubicacion     = f.SK_Ubicacion
WHERE tv.CategoriaVehiculo = N'Motocicletas y similares'
GROUP BY u.RegionNatural ORDER BY PctConMuertos;

-- P3-C1 · % con muertos por grupo de antigüedad, total y dentro de motos y livianos
--         (esperado total: 4,63 / 5,02 / 7,04; motos 4,54 -> 6,91; livianos 3,00 -> 4,13)
SELECT ISNULL(tv.CategoriaVehiculo, N'TOTAL') AS Categoria, an.GrupoEdad,
       SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimAntiguedad   an ON an.SK_Antiguedad   = f.SK_Antiguedad
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
GROUP BY GROUPING SETS ((an.OrdenGrupo, an.GrupoEdad), (tv.CategoriaVehiculo, an.OrdenGrupo, an.GrupoEdad))
ORDER BY Categoria, an.OrdenGrupo;

-- P3-C2 · Edad mediana por categoría (esperado: motos 4; livianos 9; pasajeros 9; carga 11; total 6)
SELECT DISTINCT tv.CategoriaVehiculo,
       PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY f.EdadAlAccidente) OVER (PARTITION BY tv.CategoriaVehiculo) AS EdadMediana
FROM dbo.FactVehiculoAccidente f JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo;
SELECT DISTINCT PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY EdadAlAccidente) OVER () AS EdadMedianaTotal
FROM dbo.FactVehiculoAccidente;

-- P4-C1 · Participación de las 10 marcas principales por categoría y por región
--         (esperado: total 73,83; motos 83,39; livianos 69,28; pasajeros 39,67; carga 29,86)
SELECT tv.CategoriaVehiculo,
       CAST(100.0 * SUM(CASE WHEN m.GrupoMarca = N'10 marcas principales' THEN f.CantidadVehiculos ELSE 0 END)
            / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctTop10
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
JOIN dbo.DimMarca        m  ON m.SK_Marca         = f.SK_Marca
GROUP BY tv.CategoriaVehiculo ORDER BY PctTop10 DESC;
SELECT u.RegionNatural, SUM(f.CantidadVehiculos) AS Vehiculos,
       CAST(100.0 * SUM(CASE WHEN m.GrupoMarca = N'10 marcas principales' THEN f.CantidadVehiculos ELSE 0 END)
            / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctTop10
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimUbicacion u ON u.SK_Ubicacion = f.SK_Ubicacion
JOIN dbo.DimMarca     m ON m.SK_Marca     = f.SK_Marca
GROUP BY u.RegionNatural ORDER BY PctTop10;

-- P4-C2 · Slice Motocicleta: participación en motos y en motos con muertos
--         (esperado: Bajaj 23,03 % / 26,11 %; Yamaha 22,29 % / 19,04 %; Kymco 1,68 % con muertos)
SELECT TOP (12) m.Marca,
       CAST(100.0 * SUM(f.CantidadVehiculos) / SUM(SUM(f.CantidadVehiculos)) OVER () AS DECIMAL(6,2)) AS PctDeLasMotos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(SUM(f.VehiculoAccidenteConMuertos)) OVER () AS DECIMAL(6,2)) AS PctDeMotosConMuertos,
       CAST(100.0 * SUM(f.VehiculoAccidenteConMuertos) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctConMuertos
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
JOIN dbo.DimMarca        m  ON m.SK_Marca         = f.SK_Marca
WHERE tv.TipoVehiculo = N'Motocicleta'
GROUP BY m.Marca
ORDER BY SUM(f.CantidadVehiculos) DESC;
GO
