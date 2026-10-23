# Textos para la página «1 · Composición» de Power BI

Copia cada bloque en un cuadro de texto (Insertar → Cuadro de texto). Las cifras corresponden al conjunto completo (sin filtros).

---

## TÍTULO
Composición y distribución de los vehículos involucrados en accidentes (2022–2026)

## PREGUNTA
¿Cómo se compone la población de vehículos involucrados en accidentes de tránsito con víctimas en Colombia entre 2022 y 2026, según tipo de vehículo, marca y antigüedad al momento del accidente, y qué grupos resultan predominantes y cuáles minoritarios?

## VARIABLES
Unidad: un registro = un vehículo involucrado en un accidente (no es un accidente ni un vehículo único).
Tipo de vehículo (28 categorías; las de menos de 1.000 registros se agrupan en «Otros») · Marca (360) · Edad al accidente = año del accidente − año del modelo · Rango de edad · Gravedad · Año.
Fuente: Datos Abiertos Colombia, «Vehículos involucrados en un accidente de tránsito» (6jmc-vaxk). Periodo: ene-2022 a feb-2026.

## NOTA DE DENOMINADOR (debajo de los indicadores)
Porcentajes calculados sobre el total de vehículos involucrados con los filtros seleccionados.

## INTERPRETACIÓN V1 – Vehículos por tipo
Sin filtros, la motocicleta representa el 56,4 % (229.212), el automóvil el 22,7 % y la camioneta el 8,4 %. Motos y automóviles suman el 79,1 %. Los 18 tipos minoritarios, casi todos maquinaria, suman 0,28 %.

## INTERPRETACIÓN V2 – 10 marcas principales
Bajaj (13,0 %), Yamaha (12,6 %) y Chevrolet (11,4 %) lideran. Las 10 primeras reúnen el 73,8 % de 360 marcas, y 280 marcas tienen menos de 100 registros.

## INTERPRETACIÓN V3 – Rango de edad
El rango de 0 a 2 años es el más frecuente (29,2 %). El 46,2 % de los vehículos tenía 5 años o menos y solo el 12,0 % más de 15. Mediana de 4 años en motos y de 10 en automóviles.

## CONOCIMIENTO 1 – Predominio de la motocicleta
Pregunta: ¿qué tipos concentran la población? · Variables: tipo de vehículo, total de vehículos · Procedimiento: conteo por tipo ÷ 406.540 · Evidencia: KPI «% Motocicletas», V1 · Hallazgo: 56,4 % son motos; con los automóviles llegan al 79,1 %; se mantuvo entre 54,9 % y 58,0 % en cada año completo · Interpretación: más de la mitad de los vehículos en accidentes con víctimas son motos · Utilidad: enfocar campañas y controles en motociclistas · Limitación: sin el parque automotor no se puede afirmar que la moto sea más riesgosa por vehículo.

## CONOCIMIENTO 2 – Concentración de marcas
Pregunta: ¿se concentra la población en pocas marcas? · Variables: marca, total de vehículos · Procedimiento: conteo por marca, orden descendente, % acumulado · Evidencia: KPI «% Top 10 Marcas», V2 · Hallazgo: 5 marcas = 51,1 %, 10 marcas = 73,8 %; Bajaj, Yamaha y AKT (motos) suman 33,4 % · Interpretación: la concentración por marca refleja el predominio de motos de bajo cilindraje · Utilidad: coordinar campañas con fabricantes y concesionarios · Limitación: más registros no implica menos seguridad; probablemente refleja más unidades en circulación (hipótesis).

## CONOCIMIENTO 3 – Población joven
Pregunta: ¿qué antigüedad tienen los vehículos al accidentarse? · Variables: año del modelo, año del accidente, edad calculada, rango, tipo · Procedimiento: edad recalculada frente al año del accidente (la de la fuente estaba referida a 2026), agrupada en 6 rangos, con mediana general y por tipo · Evidencia: KPI «Edad mediana», V3 · Hallazgo: mediana de 6 años; 46,2 % con ≤ 5 años; motos con mediana de 4 y 59,5 % con ≤ 5 años · Interpretación: predominan vehículos relativamente nuevos, sobre todo motos · Utilidad: reforzar la formación al momento de la compra · Limitación: la edad es aproximada (fecha mensual); 3.077 vehículos de más de 40 años se revisaron y se conservaron.

## LIMITACIÓN DEL ANÁLISIS
Los porcentajes describen la composición de los vehículos accidentados, no el riesgo: sin el número de vehículos en circulación no se pueden calcular tasas. En 2025 y 2026 la cantidad de registros es menor (probable cambio de cobertura). Julio de 2024 es inusual (Antioquia: 23.553 vehículos frente a ~3.200 en junio); se conservó tras revisarlo y quitarlo solo lleva el % de motos de 56,4 % a 57,2 %.

## DECISIÓN
Priorizar a los motociclistas y a los vehículos de hasta 5 años en los programas de prevención, con un módulo de conducción segura al momento de la venta coordinado con Bajaj, Yamaha, AKT y Honda.
