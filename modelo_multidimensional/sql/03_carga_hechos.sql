/* =====================================================================================
   03_carga_hechos.sql  ·  Carga de FactVehiculoAccidente
   -------------------------------------------------------------------------------------
   Requiere: 01 y 02. Reejecutable (vacía la tabla de hechos antes de cargar).
   Una fila del hecho = una fila de dbo.Vehiculo (406.540 esperadas). La clave primaria
   IdRegistroOrigen impide cargar dos veces el mismo registro.
   Resolución de claves: LEFT JOIN a cada dimensión por su clave de negocio; si no hay
   coincidencia, ISNULL(..., -1) asigna el miembro "Sin dato" en vez de perder el hecho.
   ===================================================================================== */
USE DW_AccidentalidadVial;
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;

DELETE FROM dbo.FactVehiculoAccidente;

INSERT INTO dbo.FactVehiculoAccidente
    (IdRegistroOrigen, FilaOrigen, SK_Tiempo, SK_Ubicacion, SK_TipoVehiculo, SK_Marca, SK_Gravedad,
     SK_Autoridad, SK_Antiguedad, AnioModelo, CantidadVehiculos, VehiculoAccidenteConMuertos,
     EdadAlAccidente, ModeloPosteriorAlAccidente)
SELECT
    v.IdVehiculo,
    v.FilaOrigen,
    ISNULL(dt.SK_Tiempo,       -1),
    ISNULL(du.SK_Ubicacion,    -1),
    ISNULL(dtv.SK_TipoVehiculo,-1),
    ISNULL(dm.SK_Marca,        -1),
    ISNULL(dg.SK_Gravedad,     -1),
    ISNULL(da.SK_Autoridad,    -1),
    ISNULL(dan.SK_Antiguedad,  -1),
    v.AnioModelo,
    1,
    CASE WHEN dg.NivelSeveridad = 2 THEN 1 ELSE 0 END,
    e.Edad,
    CASE WHEN v.AnioModelo > YEAR(f.FechaCompleta) THEN 1 ELSE 0 END
FROM src.Vehiculo AS v
LEFT JOIN src.Fecha AS f ON f.IdFecha = v.IdFechaAccidente
CROSS APPLY (SELECT CASE WHEN v.AnioModelo IS NULL OR f.FechaCompleta IS NULL THEN NULL
                         WHEN YEAR(f.FechaCompleta) - v.AnioModelo < 0 THEN 0
                         ELSE YEAR(f.FechaCompleta) - v.AnioModelo END AS Edad) AS e
LEFT JOIN dbo.DimTiempo            AS dt  ON dt.SK_Tiempo = YEAR(f.FechaCompleta) * 100 + MONTH(f.FechaCompleta)
LEFT JOIN dbo.DimUbicacion         AS du  ON du.IdDepartamentoMunicipio = v.IdDepartamentoMunicipio
LEFT JOIN dbo.DimTipoVehiculo      AS dtv ON dtv.IdTipoVehiculo        = v.IdTipoVehiculo
LEFT JOIN dbo.DimMarca             AS dm  ON dm.IdMarca               = ISNULL(v.IdMarca, -1)
LEFT JOIN dbo.DimGravedad          AS dg  ON dg.IdGravedadAccidente   = v.IdGravedadAccidente
LEFT JOIN dbo.DimAutoridadTransito AS da  ON da.IdAutoridadTransito   = v.IdAutoridadTransito
LEFT JOIN dbo.DimAntiguedad        AS dan ON dan.EdadAnios            = e.Edad;

COMMIT TRANSACTION;
GO

/* Vista "aplanada" opcional para consultas rápidas y Power BI (no se usa en Flask). */
CREATE OR ALTER VIEW dbo.vw_CuboVehiculos
AS
SELECT f.IdRegistroOrigen, t.Anio, t.Semestre, t.AnioSemestre, t.Trimestre, t.AnioTrimestre, t.NumeroMes,
       t.NombreMes, t.AnioMes, t.CoberturaAnio,
       u.RegionNatural, u.Departamento, u.Municipio, u.AmbitoProyecto,
       tv.CategoriaVehiculo, tv.TipoVehiculo, m.GrupoMarca, m.Marca, m.CalidadDato AS CalidadMarca,
       g.Gravedad, g.NivelSeveridad, a.NivelTerritorial, a.TipoEntidad, a.Autoridad,
       an.GrupoEdad, an.RangoEdad, an.EdadAnios,
       f.CantidadVehiculos, f.VehiculoAccidenteConMuertos, f.EdadAlAccidente, f.ModeloPosteriorAlAccidente
FROM dbo.FactVehiculoAccidente AS f
JOIN dbo.DimTiempo            AS t  ON t.SK_Tiempo        = f.SK_Tiempo
JOIN dbo.DimUbicacion         AS u  ON u.SK_Ubicacion     = f.SK_Ubicacion
JOIN dbo.DimTipoVehiculo      AS tv ON tv.SK_TipoVehiculo = f.SK_TipoVehiculo
JOIN dbo.DimMarca             AS m  ON m.SK_Marca         = f.SK_Marca
JOIN dbo.DimGravedad          AS g  ON g.SK_Gravedad      = f.SK_Gravedad
JOIN dbo.DimAutoridadTransito AS a  ON a.SK_Autoridad     = f.SK_Autoridad
JOIN dbo.DimAntiguedad        AS an ON an.SK_Antiguedad   = f.SK_Antiguedad;
GO

SELECT COUNT(*) AS FilasHecho FROM dbo.FactVehiculoAccidente;   -- esperado: 406540
GO
PRINT N'03 · Hechos cargados. Ejecute 05_validaciones.sql y luego 04_consultas_analisis.sql.';
GO
