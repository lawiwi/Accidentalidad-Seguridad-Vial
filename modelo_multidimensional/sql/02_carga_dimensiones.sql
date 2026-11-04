/* =====================================================================================
   02_carga_dimensiones.sql  ·  Transformación y carga de las 7 dimensiones
   -------------------------------------------------------------------------------------
   ===================================================================================== */
USE DW_AccidentalidadVial;
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;

/* 0. Vaciar en orden inverso a las llaves foráneas ---------------------------------- */
DELETE FROM dbo.FactVehiculoAccidente;
DELETE FROM dbo.DimTiempo;
DELETE FROM dbo.DimUbicacion;
DELETE FROM dbo.DimTipoVehiculo;
DELETE FROM dbo.DimMarca;
DELETE FROM dbo.DimGravedad;
DELETE FROM dbo.DimAutoridadTransito;
DELETE FROM dbo.DimAntiguedad;

/* 1. DimTiempo · grano mensual (la fuente registra la fecha por mes, día 1) -----------
      Rango: primer y último mes con vehículos. MesesConDatosAnio permite comparar
      periodos equivalentes (2026 es parcial).                                          */
DECLARE @Ini DATE, @Fin DATE;
SELECT @Ini = MIN(f.FechaCompleta), @Fin = MAX(f.FechaCompleta)
FROM src.Vehiculo AS v
JOIN src.Fecha    AS f ON f.IdFecha = v.IdFechaAccidente;
SET @Ini = DATEFROMPARTS(YEAR(@Ini), MONTH(@Ini), 1);
SET @Fin = DATEFROMPARTS(YEAR(@Fin), MONTH(@Fin), 1);

INSERT INTO dbo.DimTiempo VALUES
    (-1, NULL, 0, 0, 'Sin dato', 0, 'Sin dato', 0, N'Sin dato', N'N/D', 'Sin dato', 0, N'Sin dato');

WITH N AS (
    SELECT TOP (DATEDIFF(MONTH, @Ini, @Fin) + 1)
           ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
    FROM sys.all_objects
),
M AS (
    SELECT DATEADD(MONTH, n, @Ini) AS Mes FROM N
),
B AS (
    SELECT Mes, YEAR(Mes) AS A, MONTH(Mes) AS Nm,
           COUNT(*) OVER (PARTITION BY YEAR(Mes)) AS MesesAnio
    FROM M
)
INSERT INTO dbo.DimTiempo
    (SK_Tiempo, FechaInicioMes, Anio, Semestre, AnioSemestre, Trimestre, AnioTrimestre, NumeroMes,
     NombreMes, NombreMesCorto, AnioMes, MesesConDatosAnio, CoberturaAnio)
SELECT
    A * 100 + Nm,
    Mes,
    A,
    CASE WHEN Nm <= 6 THEN 1 ELSE 2 END,
    CONCAT(A, '-S', CASE WHEN Nm <= 6 THEN 1 ELSE 2 END),
    (Nm - 1) / 3 + 1,
    CONCAT(A, '-T', (Nm - 1) / 3 + 1),
    Nm,
    CHOOSE(Nm, N'Enero', N'Febrero', N'Marzo', N'Abril', N'Mayo', N'Junio', N'Julio', N'Agosto',
               N'Septiembre', N'Octubre', N'Noviembre', N'Diciembre'),
    CHOOSE(Nm, N'Ene', N'Feb', N'Mar', N'Abr', N'May', N'Jun', N'Jul', N'Ago', N'Sep', N'Oct', N'Nov', N'Dic'),
    CONCAT(A, '-', RIGHT('0' + CAST(Nm AS VARCHAR(2)), 2)),
    MesesAnio,
    CASE WHEN MesesAnio = 12 THEN N'Año completo' ELSE CONCAT(N'Parcial (', MesesAnio, N' meses)') END
FROM B;

/* 2. DimUbicacion · Región natural > Departamento > Municipio ------------------------- */
INSERT INTO dbo.DimUbicacion VALUES (-1, -1, N'Sin dato', N'Sin dato', N'Sin dato', N'Sin dato', N'Sin dato');

INSERT INTO dbo.DimUbicacion
    (SK_Ubicacion, IdDepartamentoMunicipio, RegionNatural, Departamento, Municipio, MunicipioDepartamento, AmbitoProyecto)
SELECT
    ROW_NUMBER() OVER (ORDER BY dm.IdDepartamentoMunicipio),
    dm.IdDepartamentoMunicipio,
    CASE
        WHEN UPPER(d.NombreDepartamento) COLLATE Latin1_General_CI_AI LIKE N'ARCHIPIELAGO%'
          OR UPPER(d.NombreDepartamento) COLLATE Latin1_General_CI_AI LIKE N'SAN ANDRES%' THEN N'Insular'
        WHEN d.NombreDepartamento COLLATE Latin1_General_CI_AI IN
             (N'Atlantico', N'Bolivar', N'Cesar', N'Cordoba', N'La Guajira', N'Magdalena', N'Sucre') THEN N'Caribe'
        WHEN d.NombreDepartamento COLLATE Latin1_General_CI_AI IN
             (N'Choco', N'Cauca', N'Narino', N'Valle del Cauca') THEN N'Pacífica'
        WHEN d.NombreDepartamento COLLATE Latin1_General_CI_AI IN
             (N'Arauca', N'Casanare', N'Meta', N'Vichada') THEN N'Orinoquía'
        WHEN d.NombreDepartamento COLLATE Latin1_General_CI_AI IN
             (N'Amazonas', N'Caqueta', N'Guainia', N'Guaviare', N'Putumayo', N'Vaupes') THEN N'Amazonía'
        WHEN d.NombreDepartamento COLLATE Latin1_General_CI_AI IN
             (N'Antioquia', N'Bogota D.C.', N'Boyaca', N'Caldas', N'Cundinamarca', N'Huila',
              N'Norte de Santander', N'Quindio', N'Risaralda', N'Santander', N'Tolima') THEN N'Andina'
        ELSE N'Sin clasificar'
    END,
    ISNULL(d.NombreDepartamento, N'Sin dato'),
    ISNULL(m.NombreMunicipio, N'Sin dato'),
    CONCAT(ISNULL(m.NombreMunicipio, N'Sin dato'), N' (', ISNULL(d.NombreDepartamento, N'Sin dato'), N')'),
    CASE
        WHEN d.NombreDepartamento COLLATE Latin1_General_CI_AI = N'Cundinamarca'
         AND m.NombreMunicipio COLLATE Latin1_General_CI_AI IN
             (N'Cajica', N'Chia', N'Cogua', N'Cota', N'Gachancipa', N'Nemocon', N'Sopo', N'Tabio',
              N'Tenjo', N'Tocancipa', N'Zipaquira')                                   THEN N'Sabana Centro'
        WHEN d.NombreDepartamento COLLATE Latin1_General_CI_AI = N'Cundinamarca'      THEN N'Resto de Cundinamarca'
        ELSE N'Otros departamentos'
    END
FROM src.DepartamentoMunicipio AS dm
LEFT JOIN src.Departamento     AS d ON d.IdDepartamento = dm.IdDepartamento
LEFT JOIN src.Municipio        AS m ON m.IdMunicipio    = dm.IdMunicipio
WHERE dm.IdDepartamentoMunicipio IN (SELECT IdDepartamentoMunicipio FROM src.Vehiculo);

/* 3. DimTipoVehiculo · Categoría > Tipo --------------------------------------------- */
INSERT INTO dbo.DimTipoVehiculo VALUES (-1, -1, N'Sin dato', N'Sin dato', 9);

INSERT INTO dbo.DimTipoVehiculo (SK_TipoVehiculo, IdTipoVehiculo, TipoVehiculo, CategoriaVehiculo, OrdenCategoria)
SELECT ROW_NUMBER() OVER (ORDER BY t.IdTipoVehiculo), t.IdTipoVehiculo,
       ISNULL(t.NombreTipoVehiculo, N'Sin dato'), x.Categoria,
       CASE x.Categoria WHEN N'Motocicletas y similares' THEN 1 WHEN N'Vehículo liviano' THEN 2
                        WHEN N'Transporte de pasajeros' THEN 3 WHEN N'Vehículo de carga' THEN 4 ELSE 5 END
FROM src.TipoVehiculo AS t
CROSS APPLY (SELECT CASE
    WHEN t.NombreTipoVehiculo COLLATE Latin1_General_CI_AI IN
         (N'Motocicleta', N'Motocarro', N'Ciclomotor', N'Cuatrimoto', N'Cuadriciclo') THEN N'Motocicletas y similares'
    WHEN t.NombreTipoVehiculo COLLATE Latin1_General_CI_AI IN
         (N'Automovil', N'Camioneta', N'Campero')                                     THEN N'Vehículo liviano'
    WHEN t.NombreTipoVehiculo COLLATE Latin1_General_CI_AI IN
         (N'Bus', N'Buseta', N'Microbus')                                             THEN N'Transporte de pasajeros'
    WHEN t.NombreTipoVehiculo COLLATE Latin1_General_CI_AI IN
         (N'Camion', N'Tractocamion', N'Volqueta', N'Remolque', N'Semiremolque')      THEN N'Vehículo de carga'
    ELSE N'Maquinaria agrícola e industrial' END AS Categoria) AS x;

/* 4. DimMarca · GrupoMarca > Marca (10 principales calculadas con los datos) ---------- */
INSERT INTO dbo.DimMarca VALUES (-1, -1, N'Sin dato (nulo)', N'Sin dato', NULL, N'Faltante (nulo en la fuente)');

WITH C AS (
    SELECT m.IdMarca, m.NombreMarca, COUNT(v.IdVehiculo) AS n
    FROM src.Marca AS m
    LEFT JOIN src.Vehiculo AS v ON v.IdMarca = m.IdMarca
    GROUP BY m.IdMarca, m.NombreMarca
),
P AS (
    SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC, NombreMarca) AS Posicion FROM C
)
INSERT INTO dbo.DimMarca (SK_Marca, IdMarca, Marca, GrupoMarca, PosicionMarca, CalidadDato)
SELECT ROW_NUMBER() OVER (ORDER BY IdMarca), IdMarca, ISNULL(NombreMarca, N'Sin dato'),
       CASE WHEN Posicion <= 10 THEN N'10 marcas principales' ELSE N'Resto de marcas' END,
       Posicion,
       CASE WHEN UPPER(LTRIM(RTRIM(ISNULL(NombreMarca, N'')))) COLLATE Latin1_General_CI_AI
                 IN (N'SIN MARCA', N'NO REGISTRADA', N'')
            THEN N'Categoría «Sin marca» declarada en la fuente'
            ELSE N'Marca informada' END
FROM P;

/* 5. DimGravedad --------------------------------------------------------------------- */
INSERT INTO dbo.DimGravedad VALUES (-1, -1, N'Sin dato', 0, N'Gravedad no reportada');

INSERT INTO dbo.DimGravedad (SK_Gravedad, IdGravedadAccidente, Gravedad, NivelSeveridad, DescripcionGravedad)
SELECT ROW_NUMBER() OVER (ORDER BY g.IdGravedadAccidente), g.IdGravedadAccidente,
       ISNULL(g.NombreGravedad, N'Sin dato'),
       CASE WHEN UPPER(g.NombreGravedad) LIKE N'%MUERT%' THEN 2
            WHEN UPPER(g.NombreGravedad) LIKE N'%HERID%' THEN 1 ELSE 0 END,
       CASE WHEN UPPER(g.NombreGravedad) LIKE N'%MUERT%' THEN N'Accidente con al menos una persona fallecida'
            WHEN UPPER(g.NombreGravedad) LIKE N'%HERID%' THEN N'Accidente con personas lesionadas y sin fallecidos'
            ELSE N'Gravedad no clasificada' END
FROM src.GravedadAccidente AS g;

/* 6. DimAutoridadTransito · NivelTerritorial > Autoridad ------------------------------ */
INSERT INTO dbo.DimAutoridadTransito VALUES (-1, -1, N'Sin dato', N'Sin dato', N'Sin dato');

INSERT INTO dbo.DimAutoridadTransito (SK_Autoridad, IdAutoridadTransito, Autoridad, TipoEntidad, NivelTerritorial)
SELECT ROW_NUMBER() OVER (ORDER BY a.IdAutoridadTransito), a.IdAutoridadTransito,
       ISNULL(a.NombreAutoridad, N'Sin dato'),
       CASE
         WHEN x.Nom LIKE N'%POLICIA NACIONAL%' OR x.Nom LIKE N'%DITRA%' THEN N'Policía Nacional (DITRA)'
         WHEN x.Nom LIKE N'STRIA%' OR x.Nom LIKE N'SECRETAR%' OR x.Nom LIKE N'SRIA%' OR x.Nom LIKE N'STARIA%'
           OR x.Nom LIKE N'SDT%' OR x.Nom LIKE N'SUB%'                   THEN N'Secretaría de tránsito y movilidad'
         WHEN x.Nom LIKE N'INSP%' OR x.Nom LIKE N'INPS%' OR x.Nom LIKE N'INS %' THEN N'Inspección de tránsito'
         WHEN x.Nom LIKE N'INST%' OR x.Nom LIKE N'ITBOY%'                 THEN N'Instituto de tránsito y transporte'
         WHEN x.Nom LIKE N'DIR%' OR x.Nom LIKE N'DPTO%' OR x.Nom LIKE N'DEPTO%' THEN N'Dirección o departamento administrativo'
         WHEN x.Nom LIKE N'UND %' OR x.Nom LIKE N'UNIDAD%' OR x.Nom LIKE N'U TEC%' THEN N'Unidad de tránsito'
         ELSE N'Otra entidad (alcaldía, fondo o agencia)'
       END,
       CASE
         WHEN x.Nom LIKE N'%POLICIA NACIONAL%' OR x.Nom LIKE N'%DITRA%' THEN N'Nacional'
         WHEN x.Nom LIKE N'%DPTAL%' OR x.Nom LIKE N'%CUND/%' OR x.Nom LIKE N'%ATLANTICO/%' OR x.Nom LIKE N'%HUILA/%'
           OR x.Nom LIKE N'%ARAUCA/%' OR x.Nom LIKE N'%DTAL NARINO%' OR x.Nom LIKE N'ITBOY%'
           OR x.Nom LIKE N'UND TTO CALDAS/%' OR x.Nom LIKE N'UNIDAD TTO CALDAS/%'
           OR x.Nom LIKE N'AGENCIA DE SEGURIDAD VIAL ANTIOQUIA%' OR x.Nom LIKE N'STRIA GOB%' THEN N'Departamental'
         WHEN x.Nom LIKE N'%DISTRITAL%' OR x.Nom LIKE N'%DIST CARTAGENA%' OR x.Nom LIKE N'%DTAL TTO BARRANQUILLA%'
           OR x.Nom LIKE N'%SANTA MARTA%'                              THEN N'Distrital'
         ELSE N'Municipal'
       END
FROM src.AutoridadTransito AS a
CROSS APPLY (SELECT UPPER(LTRIM(RTRIM(ISNULL(a.NombreAutoridad, N'')))) COLLATE Latin1_General_CI_AI AS Nom) AS x;

/* 7. DimAntiguedad · GrupoEdad > RangoEdad > EdadAnios -------------------------------
      EdadAlAccidente = MAX(0, año del accidente - año del modelo)  (regla de la Etapa 4) */
DECLARE @EdadMax INT;
SELECT @EdadMax = MAX(CASE WHEN YEAR(f.FechaCompleta) - v.AnioModelo < 0 THEN 0
                           ELSE YEAR(f.FechaCompleta) - v.AnioModelo END)
FROM src.Vehiculo AS v
JOIN src.Fecha    AS f ON f.IdFecha = v.IdFechaAccidente;

INSERT INTO dbo.DimAntiguedad VALUES (-1, -1, N'Sin dato', 7, N'Sin dato', 9);

WITH E AS (
    SELECT TOP (@EdadMax + 1) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS e FROM sys.all_objects
)
INSERT INTO dbo.DimAntiguedad (SK_Antiguedad, EdadAnios, RangoEdad, OrdenRango, GrupoEdad, OrdenGrupo)
SELECT e, e,
       CASE WHEN e <= 2 THEN N'0-2 años' WHEN e <= 5 THEN N'3-5 años' WHEN e <= 10 THEN N'6-10 años'
            WHEN e <= 15 THEN N'11-15 años' WHEN e <= 20 THEN N'16-20 años' ELSE N'Más de 20 años' END,
       CASE WHEN e <= 2 THEN 1 WHEN e <= 5 THEN 2 WHEN e <= 10 THEN 3 WHEN e <= 15 THEN 4 WHEN e <= 20 THEN 5 ELSE 6 END,
       CASE WHEN e <= 5 THEN N'Hasta 5 años' WHEN e <= 15 THEN N'De 6 a 15 años' ELSE N'Más de 15 años' END,
       CASE WHEN e <= 5 THEN 1 WHEN e <= 15 THEN 2 ELSE 3 END
FROM E;

COMMIT TRANSACTION;
GO

SELECT 'DimTiempo' AS Dimension, COUNT(*) AS Filas FROM dbo.DimTiempo            -- esperado: 51
UNION ALL SELECT 'DimUbicacion',         COUNT(*) FROM dbo.DimUbicacion          -- esperado: 556
UNION ALL SELECT 'DimTipoVehiculo',      COUNT(*) FROM dbo.DimTipoVehiculo       -- esperado: 29
UNION ALL SELECT 'DimMarca',             COUNT(*) FROM dbo.DimMarca              -- esperado: 361
UNION ALL SELECT 'DimGravedad',          COUNT(*) FROM dbo.DimGravedad           -- esperado: 3
UNION ALL SELECT 'DimAutoridadTransito', COUNT(*) FROM dbo.DimAutoridadTransito  -- esperado: 233
UNION ALL SELECT 'DimAntiguedad',        COUNT(*) FROM dbo.DimAntiguedad;        -- esperado: 89
GO
PRINT N'02 · Dimensiones cargadas. Ejecute ahora 03_carga_hechos.sql.';
GO
