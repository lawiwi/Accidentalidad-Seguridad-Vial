/* ============================================================
   CREACIÓN DE LA BASE DE DATOS
   ============================================================ */

CREATE DATABASE IntegracionSiniestrosVehiculos;
GO

USE IntegracionSiniestrosVehiculos;
GO


/* ============================================================
   1. TABLA: DEPARTAMENTO
   Fuente:
   - siniestros.csv -> depto_hech
   - vehiculos.csv  -> departamento_accidente
   ============================================================ */

CREATE TABLE Departamento (
    IdDepartamento INT IDENTITY(1,1) NOT NULL,
    NombreDepartamento VARCHAR(100) NOT NULL,

    CONSTRAINT PK_Departamento
        PRIMARY KEY (IdDepartamento),

    CONSTRAINT UQ_Departamento_Nombre
        UNIQUE (NombreDepartamento)
);
GO


/* ============================================================
   2. TABLA: MUNICIPIO
   Fuente:
   - siniestros.csv -> municipio_
   - vehiculos.csv  -> municipio_accidente
   ============================================================ */

CREATE TABLE Municipio (
    IdMunicipio INT IDENTITY(1,1) NOT NULL,
    NombreMunicipio VARCHAR(100) NOT NULL,

    CONSTRAINT PK_Municipio
        PRIMARY KEY (IdMunicipio)
);
GO


/* ============================================================
   3. TABLA: DEPARTAMENTO_MUNICIPIO
   Relación:
   Departamento 1:N DepartamentoMunicipio N:1 Municipio
   ============================================================ */

CREATE TABLE DepartamentoMunicipio (
    IdDepartamentoMunicipio INT IDENTITY(1,1) NOT NULL,
    IdDepartamento INT NOT NULL,
    IdMunicipio INT NOT NULL,

    CONSTRAINT PK_DepartamentoMunicipio
        PRIMARY KEY (IdDepartamentoMunicipio),

    CONSTRAINT FK_DepartamentoMunicipio_Departamento
        FOREIGN KEY (IdDepartamento)
        REFERENCES Departamento(IdDepartamento),

    CONSTRAINT FK_DepartamentoMunicipio_Municipio
        FOREIGN KEY (IdMunicipio)
        REFERENCES Municipio(IdMunicipio),

    CONSTRAINT UQ_DepartamentoMunicipio
        UNIQUE (IdDepartamento, IdMunicipio)
);
GO


/* ============================================================
   4. TABLA: FECHA
   Dimensión temporal compartida por ambas fuentes.
   ============================================================ */

CREATE TABLE Fecha (
    IdFecha INT IDENTITY(1,1) NOT NULL,
    FechaCompleta DATE NOT NULL,

    Anio INT NOT NULL,
    Trimestre INT NOT NULL,
    NumeroMes INT NOT NULL,
    NombreMes VARCHAR(20) NOT NULL,

    NumeroDia INT NOT NULL,
    DiaSemana INT NOT NULL,
    NombreDiaSemana VARCHAR(20) NOT NULL,

    CONSTRAINT PK_Fecha
        PRIMARY KEY (IdFecha),

    CONSTRAINT UQ_Fecha_FechaCompleta
        UNIQUE (FechaCompleta),

    CONSTRAINT CK_Fecha_Trimestre
        CHECK (Trimestre BETWEEN 1 AND 4),

    CONSTRAINT CK_Fecha_NumeroMes
        CHECK (NumeroMes BETWEEN 1 AND 12),

    CONSTRAINT CK_Fecha_NumeroDia
        CHECK (NumeroDia BETWEEN 1 AND 31),

    CONSTRAINT CK_Fecha_DiaSemana
        CHECK (DiaSemana BETWEEN 1 AND 7)
);
GO


/* ============================================================
   5. TABLA: CLASIFICACION_SINIESTRO
   Fuente:
   siniestros.csv -> sievi_clas
   ============================================================ */

CREATE TABLE ClasificacionSiniestro (
    IdClasificacionSiniestro INT IDENTITY(1,1) NOT NULL,
    NombreClasificacion VARCHAR(150) NOT NULL,

    CONSTRAINT PK_ClasificacionSiniestro
        PRIMARY KEY (IdClasificacionSiniestro),

    CONSTRAINT UQ_ClasificacionSiniestro_Nombre
        UNIQUE (NombreClasificacion)
);
GO


/* ============================================================
   6. TABLA: HIPOTESIS
   Fuente:
   siniestros.csv -> hipotesis_
   ============================================================ */

CREATE TABLE Hipotesis (
    IdHipotesis INT IDENTITY(1,1) NOT NULL,
    DescripcionHipotesis VARCHAR(250) NOT NULL,

    CONSTRAINT PK_Hipotesis
        PRIMARY KEY (IdHipotesis),

    CONSTRAINT UQ_Hipotesis_Descripcion
        UNIQUE (DescripcionHipotesis)
);
GO


/* ============================================================
   7. TABLA: MEDIO_CONOCIMIENTO
   Fuente:
   siniestros.csv -> medio_cono
   ============================================================ */

CREATE TABLE MedioConocimiento (
    IdMedioConocimiento INT IDENTITY(1,1) NOT NULL,
    NombreMedio VARCHAR(250) NOT NULL,

    CONSTRAINT PK_MedioConocimiento
        PRIMARY KEY (IdMedioConocimiento),

    CONSTRAINT UQ_MedioConocimiento_Nombre
        UNIQUE (NombreMedio)
);
GO


/* ============================================================
   8. TABLA: MARCA
   Fuente:
   vehiculos.csv -> marca_vehiculo
   ============================================================ */

CREATE TABLE Marca (
    IdMarca INT IDENTITY(1,1) NOT NULL,
    NombreMarca VARCHAR(100) NOT NULL,

    CONSTRAINT PK_Marca
        PRIMARY KEY (IdMarca),

    CONSTRAINT UQ_Marca_Nombre
        UNIQUE (NombreMarca)
);
GO


/* ============================================================
   9. TABLA: TIPO_VEHICULO
   Fuente:
   vehiculos.csv -> tipo_vehiculo
   ============================================================ */

CREATE TABLE TipoVehiculo (
    IdTipoVehiculo INT IDENTITY(1,1) NOT NULL,
    NombreTipoVehiculo VARCHAR(100) NOT NULL,

    CONSTRAINT PK_TipoVehiculo
        PRIMARY KEY (IdTipoVehiculo),

    CONSTRAINT UQ_TipoVehiculo_Nombre
        UNIQUE (NombreTipoVehiculo)
);
GO


/* ============================================================
   10. TABLA: AUTORIDAD_TRANSITO
   Fuente:
   vehiculos.csv -> autoridad_de_transito
   ============================================================ */

CREATE TABLE AutoridadTransito (
    IdAutoridadTransito INT IDENTITY(1,1) NOT NULL,
    NombreAutoridad VARCHAR(250) NOT NULL,

    CONSTRAINT PK_AutoridadTransito
        PRIMARY KEY (IdAutoridadTransito),

    CONSTRAINT UQ_AutoridadTransito_Nombre
        UNIQUE (NombreAutoridad)
);
GO


/* ============================================================
   11. TABLA: GRAVEDAD_ACCIDENTE
   Fuente:
   vehiculos.csv -> gravedad_accidente
   ============================================================ */

CREATE TABLE GravedadAccidente (
    IdGravedadAccidente INT IDENTITY(1,1) NOT NULL,
    NombreGravedad VARCHAR(100) NOT NULL,

    CONSTRAINT PK_GravedadAccidente
        PRIMARY KEY (IdGravedadAccidente),

    CONSTRAINT UQ_GravedadAccidente_Nombre
        UNIQUE (NombreGravedad)
);
GO


/* ============================================================
   12. TABLA: SINIESTRO
   Fuente:
   siniestros.csv

   IMPORTANTE:
   Esta tabla NO tiene ninguna relación con Vehiculo.
   ============================================================ */

CREATE TABLE Siniestro (
    IdSiniestro INT NOT NULL,
    IdHecho INT NULL,

    Latitud DECIMAL(10,7) NULL,
    Longitud DECIMAL(10,7) NULL,

    TotalMuertos INT NULL,
    TotalVictimas INT NULL,
    TotalLesionados INT NULL,

    IdFechaHecho INT NULL,

    TipoLugar VARCHAR(150) NULL,
    CodigoCaso VARCHAR(100) NULL,

    IdDepartamentoMunicipio INT NOT NULL,

    IdClasificacionSiniestro INT NULL,
    IdHipotesis INT NULL,
    IdMedioConocimiento INT NULL,

    CONSTRAINT PK_Siniestro
        PRIMARY KEY (IdSiniestro),

    CONSTRAINT FK_Siniestro_Fecha
        FOREIGN KEY (IdFechaHecho)
        REFERENCES Fecha(IdFecha),

    CONSTRAINT FK_Siniestro_DepartamentoMunicipio
        FOREIGN KEY (IdDepartamentoMunicipio)
        REFERENCES DepartamentoMunicipio(IdDepartamentoMunicipio),

    CONSTRAINT FK_Siniestro_Clasificacion
        FOREIGN KEY (IdClasificacionSiniestro)
        REFERENCES ClasificacionSiniestro(IdClasificacionSiniestro),

    CONSTRAINT FK_Siniestro_Hipotesis
        FOREIGN KEY (IdHipotesis)
        REFERENCES Hipotesis(IdHipotesis),

    CONSTRAINT FK_Siniestro_MedioConocimiento
        FOREIGN KEY (IdMedioConocimiento)
        REFERENCES MedioConocimiento(IdMedioConocimiento),

    CONSTRAINT CK_Siniestro_TotalMuertos
        CHECK (TotalMuertos IS NULL OR TotalMuertos >= 0),

    CONSTRAINT CK_Siniestro_TotalVictimas
        CHECK (TotalVictimas IS NULL OR TotalVictimas >= 0),

    CONSTRAINT CK_Siniestro_TotalLesionados
        CHECK (TotalLesionados IS NULL OR TotalLesionados >= 0)
);
GO


/* ============================================================
   13. TABLA: VEHICULO
   Fuente:
   vehiculos.csv

   IMPORTANTE:
   Esta tabla NO tiene IdSiniestro.
   No existe relación directa con Siniestro.
   ============================================================ */

CREATE TABLE Vehiculo (
    IdVehiculo INT IDENTITY(1,1) NOT NULL,

    AnioModelo INT NULL,
    EdadVehiculo INT NULL,

    IdFechaAccidente INT NULL,

    IdDepartamentoMunicipio INT NOT NULL,

    IdMarca INT NULL,
    IdTipoVehiculo INT NULL,
    IdGravedadAccidente INT NULL,
    IdAutoridadTransito INT NULL,

    CONSTRAINT PK_Vehiculo
        PRIMARY KEY (IdVehiculo),

    CONSTRAINT FK_Vehiculo_Fecha
        FOREIGN KEY (IdFechaAccidente)
        REFERENCES Fecha(IdFecha),

    CONSTRAINT FK_Vehiculo_DepartamentoMunicipio
        FOREIGN KEY (IdDepartamentoMunicipio)
        REFERENCES DepartamentoMunicipio(IdDepartamentoMunicipio),

    CONSTRAINT FK_Vehiculo_Marca
        FOREIGN KEY (IdMarca)
        REFERENCES Marca(IdMarca),

    CONSTRAINT FK_Vehiculo_TipoVehiculo
        FOREIGN KEY (IdTipoVehiculo)
        REFERENCES TipoVehiculo(IdTipoVehiculo),

    CONSTRAINT FK_Vehiculo_GravedadAccidente
        FOREIGN KEY (IdGravedadAccidente)
        REFERENCES GravedadAccidente(IdGravedadAccidente),

    CONSTRAINT FK_Vehiculo_AutoridadTransito
        FOREIGN KEY (IdAutoridadTransito)
        REFERENCES AutoridadTransito(IdAutoridadTransito),

    CONSTRAINT CK_Vehiculo_Edad
        CHECK (EdadVehiculo IS NULL OR EdadVehiculo >= 0),

    CONSTRAINT CK_Vehiculo_AnioModelo
        CHECK (
            AnioModelo IS NULL
            OR AnioModelo BETWEEN 1900 AND 2100
        )
);
GO