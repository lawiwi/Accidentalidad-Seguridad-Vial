/* =====================================================================================
   05_validaciones.sql  ·  Comprobaciones del modelo estrella contra los datos tratados
   -------------------------------------------------------------------------------------
   Ejecutar después de 03. Cada bloque devuelve una columna "Resultado" = 'OK' o 'REVISAR'.
   Valores esperados = los obtenidos por el ETL de la réplica SQLite
   (modelo_multidimensional/dw/validacion_etl.json).
   ===================================================================================== */
USE DW_AccidentalidadVial;
GO

/* V1 · Filas por tabla ---------------------------------------------------------------- */
SELECT Tabla, Filas, Esperado, CASE WHEN Filas = Esperado THEN 'OK' ELSE 'REVISAR' END AS Resultado
FROM (VALUES
    ('DimTiempo',            (SELECT COUNT(*) FROM dbo.DimTiempo),            51),
    ('DimUbicacion',         (SELECT COUNT(*) FROM dbo.DimUbicacion),         556),
    ('DimTipoVehiculo',      (SELECT COUNT(*) FROM dbo.DimTipoVehiculo),      29),
    ('DimMarca',             (SELECT COUNT(*) FROM dbo.DimMarca),             361),
    ('DimGravedad',          (SELECT COUNT(*) FROM dbo.DimGravedad),          3),
    ('DimAutoridadTransito', (SELECT COUNT(*) FROM dbo.DimAutoridadTransito), 233),
    ('DimAntiguedad',        (SELECT COUNT(*) FROM dbo.DimAntiguedad),        89),
    ('FactVehiculoAccidente',(SELECT COUNT(*) FROM dbo.FactVehiculoAccidente),406540)
) AS x(Tabla, Filas, Esperado);

/* V2 · Unicidad de claves de las dimensiones (clave sustituta y clave de negocio) ------ */
SELECT 'DimTiempo' AS Dimension, COUNT(*) AS Filas, COUNT(DISTINCT SK_Tiempo) AS ClavesSK, COUNT(DISTINCT AnioMes) AS ClavesNegocio FROM dbo.DimTiempo
UNION ALL SELECT 'DimUbicacion', COUNT(*), COUNT(DISTINCT SK_Ubicacion), COUNT(DISTINCT IdDepartamentoMunicipio) FROM dbo.DimUbicacion
UNION ALL SELECT 'DimTipoVehiculo', COUNT(*), COUNT(DISTINCT SK_TipoVehiculo), COUNT(DISTINCT IdTipoVehiculo) FROM dbo.DimTipoVehiculo
UNION ALL SELECT 'DimMarca', COUNT(*), COUNT(DISTINCT SK_Marca), COUNT(DISTINCT IdMarca) FROM dbo.DimMarca
UNION ALL SELECT 'DimGravedad', COUNT(*), COUNT(DISTINCT SK_Gravedad), COUNT(DISTINCT IdGravedadAccidente) FROM dbo.DimGravedad
UNION ALL SELECT 'DimAutoridadTransito', COUNT(*), COUNT(DISTINCT SK_Autoridad), COUNT(DISTINCT IdAutoridadTransito) FROM dbo.DimAutoridadTransito
UNION ALL SELECT 'DimAntiguedad', COUNT(*), COUNT(DISTINCT SK_Antiguedad), COUNT(DISTINCT EdadAnios) FROM dbo.DimAntiguedad;
-- Resultado esperado: Filas = ClavesSK = ClavesNegocio en las 7 filas.

/* V3 · Integridad referencial: hechos sin dimensión (debe ser 0 en todas) --------------- */
SELECT
  (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente f WHERE NOT EXISTS (SELECT 1 FROM dbo.DimTiempo d WHERE d.SK_Tiempo = f.SK_Tiempo))                AS SinTiempo,
  (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente f WHERE NOT EXISTS (SELECT 1 FROM dbo.DimUbicacion d WHERE d.SK_Ubicacion = f.SK_Ubicacion))       AS SinUbicacion,
  (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente f WHERE NOT EXISTS (SELECT 1 FROM dbo.DimTipoVehiculo d WHERE d.SK_TipoVehiculo = f.SK_TipoVehiculo)) AS SinTipo,
  (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente f WHERE NOT EXISTS (SELECT 1 FROM dbo.DimMarca d WHERE d.SK_Marca = f.SK_Marca))                   AS SinMarca,
  (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente f WHERE NOT EXISTS (SELECT 1 FROM dbo.DimGravedad d WHERE d.SK_Gravedad = f.SK_Gravedad))          AS SinGravedad,
  (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente f WHERE NOT EXISTS (SELECT 1 FROM dbo.DimAutoridadTransito d WHERE d.SK_Autoridad = f.SK_Autoridad)) AS SinAutoridad,
  (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente f WHERE NOT EXISTS (SELECT 1 FROM dbo.DimAntiguedad d WHERE d.SK_Antiguedad = f.SK_Antiguedad))    AS SinAntiguedad;
-- Además, las llaves foráneas declaradas en 01 impiden cargar hechos huérfanos.

/* V4 · Duplicaciones indebidas en el hecho (0 = OK) ----------------------------------- */
SELECT COUNT(*) - COUNT(DISTINCT IdRegistroOrigen) AS DuplicadosClaveOrigen,   -- esperado 0
       COUNT(*) - COUNT(DISTINCT FilaOrigen)       AS DuplicadosFilaOrigen     -- esperado 0
FROM dbo.FactVehiculoAccidente;
--     Filas con contenido repetido en el ORIGEN (se conservan por decisión de la Etapa 4): esperado 147.580
SELECT SUM(Repeticiones - 1) AS FilasRepetidasEnOrigen
FROM (SELECT COUNT(*) AS Repeticiones
      FROM src.Vehiculo
      GROUP BY AnioModelo, EdadVehiculo, IdFechaAccidente, IdDepartamentoMunicipio, IdMarca,
               IdTipoVehiculo, IdGravedadAccidente, IdAutoridadTransito) AS g;

/* V5 · Valores faltantes y categorías desconocidas ------------------------------------ */
SELECT 'Marca nula en la fuente -> miembro -1'        AS Caso, (SELECT COUNT(*) FROM src.Vehiculo WHERE IdMarca IS NULL) AS Origen,
       (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente WHERE SK_Marca = -1) AS Modelo                        -- 44 / 44
UNION ALL
SELECT 'Categoría «Sin Marca» declarada en la fuente', (SELECT COUNT(*) FROM src.Vehiculo v JOIN src.Marca m ON m.IdMarca = v.IdMarca WHERE m.NombreMarca = N'Sin Marca'),
       (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente f JOIN dbo.DimMarca m ON m.SK_Marca = f.SK_Marca WHERE m.CalidadDato LIKE N'Categor%')  -- 97 / 97
UNION ALL
SELECT 'Edad original nula (no se usa; se recalcula)', (SELECT COUNT(*) FROM src.Vehiculo WHERE EdadVehiculo IS NULL),
       (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente WHERE EdadAlAccidente IS NULL)                    -- 78 / 0
UNION ALL
SELECT 'Modelo posterior al año del accidente (edad = 0)', NULL,
       (SELECT SUM(CAST(ModeloPosteriorAlAccidente AS INT)) FROM dbo.FactVehiculoAccidente)            -- 14.233
UNION ALL
SELECT 'Hechos en miembro -1 de Tiempo/Ubicación/Tipo/Gravedad/Autoridad/Antigüedad', NULL,
       (SELECT COUNT(*) FROM dbo.FactVehiculoAccidente
        WHERE SK_Tiempo = -1 OR SK_Ubicacion = -1 OR SK_TipoVehiculo = -1
           OR SK_Gravedad = -1 OR SK_Autoridad = -1 OR SK_Antiguedad = -1);                         -- 0

/* V6 · COMPARACIONES CON LOS DATOS TRATADOS (al menos tres; aquí seis) ---------------- */
-- C1 Total de vehículos
SELECT 'C1 Total de vehículos' AS Comprobacion,
       (SELECT COUNT(*) FROM src.Vehiculo) AS Origen,
       (SELECT SUM(CantidadVehiculos) FROM dbo.FactVehiculoAccidente) AS Modelo,
       (SELECT COUNT(*) FROM src.Vehiculo) - (SELECT SUM(CantidadVehiculos) FROM dbo.FactVehiculoAccidente) AS Diferencia;

-- C2 Vehículos por año
SELECT o.Anio, o.Origen, m.Modelo, o.Origen - ISNULL(m.Modelo, 0) AS Diferencia
FROM (SELECT YEAR(f.FechaCompleta) AS Anio, COUNT(*) AS Origen
      FROM src.Vehiculo v JOIN src.Fecha f ON f.IdFecha = v.IdFechaAccidente GROUP BY YEAR(f.FechaCompleta)) o
LEFT JOIN (SELECT t.Anio, SUM(x.CantidadVehiculos) AS Modelo
           FROM dbo.FactVehiculoAccidente x JOIN dbo.DimTiempo t ON t.SK_Tiempo = x.SK_Tiempo GROUP BY t.Anio) m
       ON m.Anio = o.Anio
ORDER BY o.Anio;

-- C3 Vehículos en accidentes con muertos
SELECT 'C3 Vehículos en accidentes con muertos' AS Comprobacion,
       (SELECT COUNT(*) FROM src.Vehiculo v JOIN src.GravedadAccidente g ON g.IdGravedadAccidente = v.IdGravedadAccidente
        WHERE UPPER(g.NombreGravedad) LIKE N'%MUERT%') AS Origen,
       (SELECT SUM(CAST(VehiculoAccidenteConMuertos AS INT)) FROM dbo.FactVehiculoAccidente) AS Modelo;   -- 20.659 / 20.659

-- C4 Vehículos por tipo de vehículo (las 28 filas deben tener diferencia 0)
SELECT o.NombreTipoVehiculo, o.Origen, m.Modelo, o.Origen - ISNULL(m.Modelo, 0) AS Diferencia
FROM (SELECT t.NombreTipoVehiculo, COUNT(*) AS Origen
      FROM src.Vehiculo v JOIN src.TipoVehiculo t ON t.IdTipoVehiculo = v.IdTipoVehiculo GROUP BY t.NombreTipoVehiculo) o
LEFT JOIN (SELECT d.TipoVehiculo, SUM(f.CantidadVehiculos) AS Modelo
           FROM dbo.FactVehiculoAccidente f JOIN dbo.DimTipoVehiculo d ON d.SK_TipoVehiculo = f.SK_TipoVehiculo
           GROUP BY d.TipoVehiculo) m
       ON m.TipoVehiculo COLLATE DATABASE_DEFAULT = o.NombreTipoVehiculo COLLATE DATABASE_DEFAULT
ORDER BY Diferencia DESC, o.Origen DESC;

-- C5 Vehículos por departamento, resueltos por IdDepartamentoMunicipio (no por nombre)
SELECT o.NombreDepartamento, o.Origen, m.Modelo, o.Origen - ISNULL(m.Modelo, 0) AS Diferencia
FROM (SELECT d.NombreDepartamento, COUNT(*) AS Origen
      FROM src.Vehiculo v
      JOIN src.DepartamentoMunicipio dm ON dm.IdDepartamentoMunicipio = v.IdDepartamentoMunicipio
      JOIN src.Departamento d ON d.IdDepartamento = dm.IdDepartamento
      GROUP BY d.NombreDepartamento) o
LEFT JOIN (SELECT u.Departamento, SUM(f.CantidadVehiculos) AS Modelo
           FROM dbo.FactVehiculoAccidente f JOIN dbo.DimUbicacion u ON u.SK_Ubicacion = f.SK_Ubicacion
           GROUP BY u.Departamento) m
       ON m.Departamento COLLATE DATABASE_DEFAULT = o.NombreDepartamento COLLATE DATABASE_DEFAULT
ORDER BY Diferencia DESC, o.Origen DESC;

-- C6 Cifras de la Etapa 4 reproducidas desde el modelo (motos 56,38 %; 10 marcas 73,83 %; mediana 6)
SELECT
  CAST(100.0 * SUM(CASE WHEN tv.TipoVehiculo = N'Motocicleta' THEN f.CantidadVehiculos ELSE 0 END) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctMotocicletas,
  CAST(100.0 * SUM(CASE WHEN m.GrupoMarca = N'10 marcas principales' THEN f.CantidadVehiculos ELSE 0 END) / SUM(f.CantidadVehiculos) AS DECIMAL(6,2)) AS PctTop10Marcas
FROM dbo.FactVehiculoAccidente f
JOIN dbo.DimTipoVehiculo tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
JOIN dbo.DimMarca        m  ON m.SK_Marca         = f.SK_Marca;

/* V7 · Coherencia de agregaciones (roll-up): mes -> año -> total y municipio -> total ---- */
SELECT
  (SELECT SUM(CantidadVehiculos) FROM dbo.FactVehiculoAccidente) AS Total,
  (SELECT SUM(n) FROM (SELECT t.AnioMes, SUM(f.CantidadVehiculos) n FROM dbo.FactVehiculoAccidente f
                       JOIN dbo.DimTiempo t ON t.SK_Tiempo = f.SK_Tiempo GROUP BY t.AnioMes) a) AS SumaDeMeses,
  (SELECT SUM(n) FROM (SELECT u.SK_Ubicacion, SUM(f.CantidadVehiculos) n FROM dbo.FactVehiculoAccidente f
                       JOIN dbo.DimUbicacion u ON u.SK_Ubicacion = f.SK_Ubicacion GROUP BY u.SK_Ubicacion) b) AS SumaDeMunicipios;
-- Esperado: 406.540 en las tres columnas.
GO
