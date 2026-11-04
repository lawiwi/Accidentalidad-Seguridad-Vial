/* =====================================================================================
   ETAPA 5 · ANÁLISIS MULTIDIMENSIONAL - VEHÍCULOS INVOLUCRADOS EN ACCIDENTES
   01_creacion_modelo_estrella.sql
   -------------------------------------------------------------------------------------
   Crea la bodega DW_AccidentalidadVial con el modelo estrella:
       FactVehiculoAccidente  + 7 dimensiones
   Origen: base tratada de la Etapa 3 (IntegracionSiniestrosVehiculos, respaldo FILE = 3),
           SOLO la tabla dbo.Vehiculo y sus catálogos. No se usa dbo.Siniestro.

   ===================================================================================== */
SET NOCOUNT ON;
GO

/* -------------------------------------------------------------------------------------
   1. Crear la bodega
   ------------------------------------------------------------------------------------- */
IF DB_ID(N'DW_AccidentalidadVial') IS NULL
    CREATE DATABASE DW_AccidentalidadVial;
GO
USE DW_AccidentalidadVial;
GO

/* -------------------------------------------------------------------------------------
   2. Sinónimos hacia la base tratada (esquema src)
      Los scripts 02, 03 y 05 leen siempre src.<tabla>; así el nombre de la base de
      origen se escribe una sola vez.
   ------------------------------------------------------------------------------------- */
IF SCHEMA_ID(N'src') IS NULL EXEC (N'CREATE SCHEMA src');
GO

DECLARE @BaseOrigen SYSNAME = N'IntegracionSiniestrosVehiculos';   -- <<< AJUSTAR SI ES NECESARIO

IF DB_ID(@BaseOrigen) IS NULL
BEGIN
    RAISERROR(N'La base de origen indicada en @BaseOrigen no existe. Restaure el .bak con WITH FILE = 3.', 16, 1);
    RETURN;
END;

DECLARE @t SYSNAME, @sql NVARCHAR(MAX);
DECLARE c CURSOR LOCAL FAST_FORWARD FOR
    SELECT v FROM (VALUES (N'Vehiculo'), (N'Fecha'), (N'DepartamentoMunicipio'), (N'Departamento'),
                          (N'Municipio'), (N'Marca'), (N'TipoVehiculo'), (N'GravedadAccidente'),
                          (N'AutoridadTransito')) AS x(v);
OPEN c;
FETCH NEXT FROM c INTO @t;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'DROP SYNONYM IF EXISTS src.' + QUOTENAME(@t) + N'; '
             + N'CREATE SYNONYM src.' + QUOTENAME(@t) + N' FOR ' + QUOTENAME(@BaseOrigen) + N'.dbo.' + QUOTENAME(@t) + N';';
    EXEC sys.sp_executesql @sql;
    FETCH NEXT FROM c INTO @t;
END;
CLOSE c; DEALLOCATE c;

-- Comprobación: la tabla de vehículos debe tener datos (los respaldos FILE = 1 y 2 la tienen vacía)
IF NOT EXISTS (SELECT 1 FROM src.Vehiculo)
    RAISERROR(N'src.Vehiculo está vacía: se restauró un respaldo distinto de FILE = 3.', 16, 1);
GO

/* -------------------------------------------------------------------------------------
   3. Eliminar objetos previos (también los de la versión preliminar del modelo)
   ------------------------------------------------------------------------------------- */
-- Primero vistas y tablas de hechos (tienen las llaves foráneas), después dimensiones.
DROP VIEW  IF EXISTS dbo.vw_AccidentalidadVehiculos;          -- versión preliminar
DROP VIEW  IF EXISTS dbo.vw_CuboVehiculos;
DROP TABLE IF EXISTS dbo.FactAccidentalidadVehiculo;          -- versión preliminar
DROP TABLE IF EXISTS dbo.FactVehiculoAccidente;
DROP TABLE IF EXISTS dbo.DimVehiculo;                         -- versión preliminar
DROP TABLE IF EXISTS dbo.DimTiempo;                           -- versión preliminar (diaria) o actual
DROP TABLE IF EXISTS dbo.DimUbicacion;
DROP TABLE IF EXISTS dbo.DimTipoVehiculo;
DROP TABLE IF EXISTS dbo.DimMarca;
DROP TABLE IF EXISTS dbo.DimGravedad;
DROP TABLE IF EXISTS dbo.DimAutoridadTransito;
DROP TABLE IF EXISTS dbo.DimAntiguedad;
GO

/* -------------------------------------------------------------------------------------
   4. Dimensiones
   Las claves sustitutas se asignan en 02 con ROW_NUMBER ordenado por la clave de negocio,
   de modo que el resultado es determinista y coincide con la réplica SQLite que usa Flask.
   El valor -1 es el miembro "Sin dato" de cada dimensión.
   ------------------------------------------------------------------------------------- */

-- ¿CUÁNDO? Jerarquía: Anio > Semestre > Trimestre > Mes  (grano mensual)
CREATE TABLE dbo.DimTiempo (
    SK_Tiempo          INT           NOT NULL,   -- AAAAMM
    FechaInicioMes     DATE          NULL,
    Anio               SMALLINT      NOT NULL,
    Semestre           TINYINT       NOT NULL,
    AnioSemestre       VARCHAR(10)   NOT NULL,
    Trimestre          TINYINT       NOT NULL,
    AnioTrimestre      VARCHAR(10)   NOT NULL,
    NumeroMes          TINYINT       NOT NULL,
    NombreMes          NVARCHAR(15)  NOT NULL,
    NombreMesCorto     NVARCHAR(3)   NOT NULL,
    AnioMes            VARCHAR(10)   NOT NULL,
    MesesConDatosAnio  TINYINT       NOT NULL,
    CoberturaAnio      NVARCHAR(25)  NOT NULL,
    CONSTRAINT PK_DimTiempo PRIMARY KEY CLUSTERED (SK_Tiempo),
    CONSTRAINT UQ_DimTiempo_AnioMes UNIQUE (AnioMes),
    CONSTRAINT CK_DimTiempo_Mes CHECK (NumeroMes BETWEEN 0 AND 12)
);

-- ¿DÓNDE? Jerarquía: RegionNatural > Departamento > Municipio
CREATE TABLE dbo.DimUbicacion (
    SK_Ubicacion             INT            NOT NULL,
    IdDepartamentoMunicipio  INT            NOT NULL,   -- clave de negocio
    RegionNatural            NVARCHAR(20)   NOT NULL,
    Departamento             NVARCHAR(100)  NOT NULL,
    Municipio                NVARCHAR(100)  NOT NULL,
    MunicipioDepartamento    NVARCHAR(210)  NOT NULL,
    AmbitoProyecto           NVARCHAR(30)   NOT NULL,   -- Sabana Centro / Resto de Cundinamarca / Otros
    CONSTRAINT PK_DimUbicacion PRIMARY KEY CLUSTERED (SK_Ubicacion),
    CONSTRAINT UQ_DimUbicacion_BK UNIQUE (IdDepartamentoMunicipio)
);

-- ¿QUÉ VEHÍCULO? Jerarquía: CategoriaVehiculo > TipoVehiculo
CREATE TABLE dbo.DimTipoVehiculo (
    SK_TipoVehiculo    INT            NOT NULL,
    IdTipoVehiculo     INT            NOT NULL,
    TipoVehiculo       NVARCHAR(100)  NOT NULL,
    CategoriaVehiculo  NVARCHAR(40)   NOT NULL,
    OrdenCategoria     TINYINT        NOT NULL,
    CONSTRAINT PK_DimTipoVehiculo PRIMARY KEY CLUSTERED (SK_TipoVehiculo),
    CONSTRAINT UQ_DimTipoVehiculo_BK UNIQUE (IdTipoVehiculo)
);

-- ¿QUÉ MARCA? Jerarquía: GrupoMarca > Marca
CREATE TABLE dbo.DimMarca (
    SK_Marca       INT            NOT NULL,
    IdMarca        INT            NOT NULL,   -- -1 = marca nula en la fuente
    Marca          NVARCHAR(100)  NOT NULL,
    GrupoMarca     NVARCHAR(30)   NOT NULL,
    PosicionMarca  INT            NULL,
    CalidadDato    NVARCHAR(60)   NOT NULL,
    CONSTRAINT PK_DimMarca PRIMARY KEY CLUSTERED (SK_Marca),
    CONSTRAINT UQ_DimMarca_BK UNIQUE (IdMarca)
);

-- ¿QUÉ PASÓ? Gravedad del accidente
CREATE TABLE dbo.DimGravedad (
    SK_Gravedad          INT            NOT NULL,
    IdGravedadAccidente  INT            NOT NULL,
    Gravedad             NVARCHAR(100)  NOT NULL,
    NivelSeveridad       TINYINT        NOT NULL,   -- 1 = con heridos, 2 = con muertos
    DescripcionGravedad  NVARCHAR(200)  NOT NULL,
    CONSTRAINT PK_DimGravedad PRIMARY KEY CLUSTERED (SK_Gravedad),
    CONSTRAINT UQ_DimGravedad_BK UNIQUE (IdGravedadAccidente)
);

-- ¿QUIÉN REGISTRA? Jerarquía: NivelTerritorial > Autoridad
CREATE TABLE dbo.DimAutoridadTransito (
    SK_Autoridad         INT            NOT NULL,
    IdAutoridadTransito  INT            NOT NULL,
    Autoridad            NVARCHAR(250)  NOT NULL,
    TipoEntidad          NVARCHAR(60)   NOT NULL,
    NivelTerritorial     NVARCHAR(20)   NOT NULL,
    CONSTRAINT PK_DimAutoridadTransito PRIMARY KEY CLUSTERED (SK_Autoridad),
    CONSTRAINT UQ_DimAutoridadTransito_BK UNIQUE (IdAutoridadTransito)
);

-- ¿QUÉ ANTIGÜEDAD? Jerarquía: GrupoEdad > RangoEdad > EdadAnios
CREATE TABLE dbo.DimAntiguedad (
    SK_Antiguedad  INT            NOT NULL,   -- igual a EdadAnios; -1 = sin dato
    EdadAnios      INT            NOT NULL,
    RangoEdad      NVARCHAR(20)   NOT NULL,
    OrdenRango     TINYINT        NOT NULL,
    GrupoEdad      NVARCHAR(20)   NOT NULL,
    OrdenGrupo     TINYINT        NOT NULL,
    CONSTRAINT PK_DimAntiguedad PRIMARY KEY CLUSTERED (SK_Antiguedad),
    CONSTRAINT UQ_DimAntiguedad_Edad UNIQUE (EdadAnios)
);
GO

/* -------------------------------------------------------------------------------------
   5. Tabla de hechos
   Granularidad: un registro de dbo.Vehiculo = un vehículo involucrado en un accidente de
   tránsito con víctimas, en un mes, un municipio y reportado por un organismo de tránsito.
   ------------------------------------------------------------------------------------- */
CREATE TABLE dbo.FactVehiculoAccidente (
    IdRegistroOrigen             INT       NOT NULL,   -- dbo.Vehiculo.IdVehiculo (dimensión degenerada)
    FilaOrigen                   INT       NOT NULL,   -- fila del CSV original
    SK_Tiempo                    INT       NOT NULL,
    SK_Ubicacion                 INT       NOT NULL,
    SK_TipoVehiculo              INT       NOT NULL,
    SK_Marca                     INT       NOT NULL,
    SK_Gravedad                  INT       NOT NULL,
    SK_Autoridad                 INT       NOT NULL,
    SK_Antiguedad                INT       NOT NULL,
    AnioModelo                   SMALLINT  NULL,
    -- Medidas
    CantidadVehiculos            INT       NOT NULL CONSTRAINT DF_Fact_Cantidad DEFAULT (1),
    VehiculoAccidenteConMuertos  TINYINT   NOT NULL,
    EdadAlAccidente              SMALLINT  NULL,
    ModeloPosteriorAlAccidente   TINYINT   NOT NULL,   -- indicador de calidad (edad truncada a 0)
    CONSTRAINT PK_FactVehiculoAccidente PRIMARY KEY CLUSTERED (IdRegistroOrigen),
    CONSTRAINT UQ_Fact_FilaOrigen UNIQUE (FilaOrigen),
    CONSTRAINT FK_Fact_Tiempo       FOREIGN KEY (SK_Tiempo)       REFERENCES dbo.DimTiempo (SK_Tiempo),
    CONSTRAINT FK_Fact_Ubicacion    FOREIGN KEY (SK_Ubicacion)    REFERENCES dbo.DimUbicacion (SK_Ubicacion),
    CONSTRAINT FK_Fact_TipoVehiculo FOREIGN KEY (SK_TipoVehiculo) REFERENCES dbo.DimTipoVehiculo (SK_TipoVehiculo),
    CONSTRAINT FK_Fact_Marca        FOREIGN KEY (SK_Marca)        REFERENCES dbo.DimMarca (SK_Marca),
    CONSTRAINT FK_Fact_Gravedad     FOREIGN KEY (SK_Gravedad)     REFERENCES dbo.DimGravedad (SK_Gravedad),
    CONSTRAINT FK_Fact_Autoridad    FOREIGN KEY (SK_Autoridad)    REFERENCES dbo.DimAutoridadTransito (SK_Autoridad),
    CONSTRAINT FK_Fact_Antiguedad   FOREIGN KEY (SK_Antiguedad)   REFERENCES dbo.DimAntiguedad (SK_Antiguedad),
    CONSTRAINT CK_Fact_Cantidad     CHECK (CantidadVehiculos = 1),
    CONSTRAINT CK_Fact_ConMuertos   CHECK (VehiculoAccidenteConMuertos IN (0, 1)),
    CONSTRAINT CK_Fact_Edad         CHECK (EdadAlAccidente IS NULL OR EdadAlAccidente >= 0),
    CONSTRAINT CK_Fact_ModeloPost   CHECK (ModeloPosteriorAlAccidente IN (0, 1))
);
GO

/* -------------------------------------------------------------------------------------
   6. Índices de apoyo (una clave foránea por índice, con las medidas incluidas)
   ------------------------------------------------------------------------------------- */
CREATE NONCLUSTERED INDEX IX_Fact_Tiempo       ON dbo.FactVehiculoAccidente (SK_Tiempo)       INCLUDE (CantidadVehiculos, VehiculoAccidenteConMuertos, EdadAlAccidente);
CREATE NONCLUSTERED INDEX IX_Fact_Ubicacion    ON dbo.FactVehiculoAccidente (SK_Ubicacion)    INCLUDE (CantidadVehiculos, VehiculoAccidenteConMuertos, EdadAlAccidente);
CREATE NONCLUSTERED INDEX IX_Fact_TipoVehiculo ON dbo.FactVehiculoAccidente (SK_TipoVehiculo) INCLUDE (CantidadVehiculos, VehiculoAccidenteConMuertos, EdadAlAccidente);
CREATE NONCLUSTERED INDEX IX_Fact_Marca        ON dbo.FactVehiculoAccidente (SK_Marca)        INCLUDE (CantidadVehiculos, VehiculoAccidenteConMuertos);
CREATE NONCLUSTERED INDEX IX_Fact_Gravedad     ON dbo.FactVehiculoAccidente (SK_Gravedad)     INCLUDE (CantidadVehiculos);
CREATE NONCLUSTERED INDEX IX_Fact_Autoridad    ON dbo.FactVehiculoAccidente (SK_Autoridad)    INCLUDE (CantidadVehiculos, VehiculoAccidenteConMuertos);
CREATE NONCLUSTERED INDEX IX_Fact_Antiguedad   ON dbo.FactVehiculoAccidente (SK_Antiguedad)   INCLUDE (CantidadVehiculos, VehiculoAccidenteConMuertos);
GO

PRINT N'01 · Modelo estrella creado (vacío). Ejecute ahora 02_carga_dimensiones.sql.';
GO
