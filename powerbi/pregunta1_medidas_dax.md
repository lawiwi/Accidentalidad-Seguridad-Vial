# Pregunta 1 · Composición y distribución de la población — Medidas DAX

Informe: página **«1 · Composición»** del archivo PBIX del equipo.
Fuente: base SQL Server `IntegracionSiniestrosVehiculos` (tablas `Vehiculo`, `TipoVehiculo`, `Marca`, `GravedadAccidente`, `Fecha`).
Unidad de análisis: un registro de `Vehiculo` = un vehículo involucrado en un accidente con víctimas.

## 1. Relaciones del modelo usadas en esta página

| Desde (muchos) | Hacia (uno) | Cardinalidad | Dirección del filtro |
|---|---|---|---|
| `Vehiculo[IdTipoVehiculo]` | `TipoVehiculo[IdTipoVehiculo]` | Varios a uno | Única |
| `Vehiculo[IdMarca]` | `Marca[IdMarca]` | Varios a uno | Única |
| `Vehiculo[IdGravedadAccidente]` | `GravedadAccidente[IdGravedadAccidente]` | Varios a uno | Única |
| `Vehiculo[IdFechaAccidente]` | `Fecha[IdFecha]` | Varios a uno | Única |

No existe relación directa entre `Vehiculo` y `Siniestro` (son dos tablas de hechos distintas y de periodos distintos). Así se evita que los conteos se dupliquen.

## 2. Columnas calculadas

### Tabla `Vehiculo`

```dax
Edad al Accidente =
VAR AnioAccidente = RELATED ( Fecha[Anio] )
VAR Diferencia = AnioAccidente - Vehiculo[AnioModelo]
RETURN
    IF (
        ISBLANK ( Vehiculo[AnioModelo] ) || ISBLANK ( AnioAccidente ),
        BLANK (),
        MAX ( 0, Diferencia )
    )
```
*Por qué:* la columna `EdadVehiculo` de la fuente está calculada frente a 2026 y no frente al año del accidente (en 276.194 registros coincide con 2026 − año del modelo). Los modelos del año siguiente (por ejemplo, una moto modelo 2026 accidentada en 2025) quedan con edad 0.

```dax
Rango Edad =
SWITCH (
    TRUE (),
    ISBLANK ( Vehiculo[Edad al Accidente] ), "Sin dato",
    Vehiculo[Edad al Accidente] <= 2, "0-2 años",
    Vehiculo[Edad al Accidente] <= 5, "3-5 años",
    Vehiculo[Edad al Accidente] <= 10, "6-10 años",
    Vehiculo[Edad al Accidente] <= 15, "11-15 años",
    Vehiculo[Edad al Accidente] <= 20, "16-20 años",
    "Más de 20 años"
)
```

```dax
Orden Rango Edad =
VAR Edad = Vehiculo[Edad al Accidente]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( Edad ), 7,
        Edad <= 2, 1,
        Edad <= 5, 2,
        Edad <= 10, 3,
        Edad <= 15, 4,
        Edad <= 20, 5,
        6
    )
```
Luego se selecciona `Rango Edad` y en **Herramientas de columnas → Ordenar por columna** se elige `Orden Rango Edad`.
*Importante:* `Orden Rango Edad` se calcula desde `Edad al Accidente` y no desde `Rango Edad`; si dependiera de `Rango Edad`, Power BI mostraría un error de dependencia circular al ordenar.

### Tabla `TipoVehiculo`

```dax
Tipo Agrupado =
VAR Registros = CALCULATE ( COUNTROWS ( Vehiculo ) )
RETURN
    IF ( Registros >= 1000, TipoVehiculo[NombreTipoVehiculo], "Otros (menos de 1.000)" )
```
`CALCULATE` convierte la fila del tipo en filtro, así que cuenta los vehículos de cada tipo sin escribir los nombres a mano.

## 3. Medidas

Se recomienda crear una tabla vacía `_Medidas P1` (Inicio → Especificar datos → Cargar) y guardar ahí las medidas.

| Medida | Fórmula | Para qué se usa |
|---|---|---|
| Total Vehiculos | `COUNTROWS ( Vehiculo )` | Indicador 1, base de las demás medidas |
| % Participacion | ver abajo | Etiquetas de V1, V2 y V3 |
| % Motocicletas | ver abajo | Indicador 2 |
| Edad Mediana Accidente | `MEDIAN ( Vehiculo[Edad al Accidente] )` | Indicador 3 (MEDIAN ignora los vacíos) |
| % Top 10 Marcas | ver abajo | Indicador de apoyo para V2 |
| Marcas Distintas | `DISTINCTCOUNTNOBLANK ( Vehiculo[IdMarca] )` | Texto de V2 |
| Vehiculos Sin Marca | `CALCULATE ( [Total Vehiculos], ISBLANK ( Vehiculo[IdMarca] ) )` | Control de calidad |
| Tipo Predominante / Texto Composicion | ver abajo | Interpretación dinámica |

```dax
% Participacion =
VAR Denominador =
    CALCULATE (
        [Total Vehiculos],
        REMOVEFILTERS ( TipoVehiculo ),
        REMOVEFILTERS ( Marca ),
        REMOVEFILTERS ( Vehiculo[Rango Edad], Vehiculo[Orden Rango Edad] )
    )
RETURN
    DIVIDE ( [Total Vehiculos], Denominador )
```
**Denominador:** total de vehículos involucrados con los filtros de Año y Gravedad que estén seleccionados. Se quitan los filtros de tipo, marca y rango de edad para que el porcentaje de cada barra sea sobre el total y no sobre la misma barra. Tampoco se ve afectado por el filtro N superior = 10 del gráfico de marcas.

```dax
% Motocicletas =
DIVIDE (
    CALCULATE (
        [Total Vehiculos],
        KEEPFILTERS ( TipoVehiculo[NombreTipoVehiculo] = "Motocicleta" )
    ),
    [Total Vehiculos]
)
```

```dax
% Top 10 Marcas =
VAR Top10 =
    TOPN ( 10, VALUES ( Marca[NombreMarca] ), [Total Vehiculos], DESC )
RETURN
    DIVIDE ( CALCULATE ( [Total Vehiculos], Top10 ), [Total Vehiculos] )
```

```dax
Tipo Predominante =
VAR Top1 =
    TOPN ( 1, VALUES ( TipoVehiculo[NombreTipoVehiculo] ), [Total Vehiculos], DESC )
RETURN
    CONCATENATEX ( Top1, TipoVehiculo[NombreTipoVehiculo], ", " )
```

```dax
% Tipo Predominante =
VAR Top1 =
    TOPN ( 1, VALUES ( TipoVehiculo[NombreTipoVehiculo] ), [Total Vehiculos], DESC )
RETURN
    DIVIDE ( CALCULATE ( [Total Vehiculos], Top1 ), [Total Vehiculos] )
```

```dax
Texto Composicion =
"Con los filtros actuales hay "
    & FORMAT ( [Total Vehiculos], "#,0" )
    & " vehículos involucrados. El tipo predominante es "
    & [Tipo Predominante] & " ("
    & FORMAT ( [% Tipo Predominante], "0.0%" )
    & ") y la edad mediana al accidente es de "
    & FORMAT ( [Edad Mediana Accidente], "0" ) & " años."
```
Esta medida se muestra en una **tarjeta** (o en un cuadro de texto con valor dinámico), para que la interpretación cambie junto con los segmentadores.

## 4. Valores esperados sin filtros (para verificar)

| Medida | Valor |
|---|---|
| Total Vehiculos | 406.540 |
| % Motocicletas | 56,38 % |
| Edad Mediana Accidente | 6 |
| % Top 10 Marcas | 73,83 % |
| Marcas Distintas | 360 |
| Vehiculos Sin Marca | 44 |

Si alguna cifra no coincide, primero revisa la cantidad de filas de `dbo.Vehiculo` con `powerbi/pregunta1_validacion.sql`.
