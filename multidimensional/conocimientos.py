"""
Ocho conocimientos multidimensionales (dos por pregunta).

Las cifras de cada hallazgo NO están escritas a mano: la función `evidencia_*` las
calcula con consultas al modelo estrella cada vez que se abre la vista, y el texto
del hallazgo se llena con esos valores. Así lo que se lee en Flask coincide siempre
con la base consultada. tests/test_multidimensional.py verifica los valores esperados.

Cada conocimiento tiene los ocho elementos exigidos: pregunta, dimensiones y medidas,
procedimiento, evidencia, hallazgo, interpretación, utilidad y limitación. Las
interpretaciones que no se pueden comprobar con los datos se marcan como hipótesis.
"""
from functools import lru_cache

from . import cubo as C

MEDELLIN = "STRIA DE TTOYTTE MEDELLIN"


def n(valor):
    """Entero con separador de miles colombiano: 28794 -> '28.794'."""
    return f"{int(valor):,}".replace(",", ".")


def p(valor, dec=2):
    """Proporción (0-1) a porcentaje: 0.0508 -> '5,08 %'."""
    if valor is None:
        return "s. d."
    return f"{valor * 100:.{dec}f}".replace(".", ",").replace("-", "−") + " %"


def d(valor, dec=2):
    """Decimal con miles '.' y decimales ',': 2448.5 -> '2.448,5'."""
    if valor is None:
        return "s. d."
    return f"{valor:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _celda(ejes, filtros, *claves):
    filas, _ = C.agregar(ejes, filtros)
    for f in filas:
        if f["claves"] == tuple(claves):
            return f
    return C.derivar(tuple(claves), 0, 0, 0, 0)


def _por(ejes, filtros=None):
    filas, _ = C.agregar(ejes, filtros or {})
    return {f["claves"][0] if len(f["claves"]) == 1 else f["claves"]: f for f in filas}


# ---------------------------------------------------------------------------
# Evidencias (consultas reales)
# ---------------------------------------------------------------------------
def evidencia_1():
    jul = _celda([("tiempo", "mes")], {}, "2024-07")
    med = _por([("tiempo", "mes")], {("autoridad", "autoridad"): [MEDELLIN], ("tiempo", "anio"): [2024]})
    med_jul = med.get("2024-07", C.derivar((), 0, 0, 0, 0))["n"]
    ene_jun = [med[k]["n"] for k in ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"] if k in med]
    prom = sum(ene_jun) / len(ene_jun) if ene_jun else 0
    ant = _celda([("ubicacion", "departamento")], {("tiempo", "mes"): ["2024-07"]}, "Antioquia")
    return {
        "jul_total": n(jul["n"]), "ant_jul": n(ant["n"]), "pct_ant": p(ant["n"] / jul["n"] if jul["n"] else None),
        "med_jul": n(med_jul), "pct_med": p(med_jul / jul["n"] if jul["n"] else None),
        "prom_med": d(prom, 1), "veces": d(med_jul / prom if prom else None, 1),
        "_valores": {"jul_total": jul["n"], "med_jul": med_jul, "ant_jul": ant["n"]},
    }


def evidencia_2():
    anio = _por([("tiempo", "anio")])
    med = _por([("tiempo", "anio")], {("autoridad", "autoridad"): [MEDELLIN]})
    t24, t25 = anio[2024], anio[2025]
    m24 = med.get(2024, C.derivar((), 0, 0, 0, 0))["n"]
    m25 = med.get(2025, C.derivar((), 0, 0, 0, 0))["n"]
    caida = t24["n"] - t25["n"]
    nac = _por([("tiempo", "anio")], {("autoridad", "nivel"): ["Nacional"]})
    return {
        "t24": n(t24["n"]), "t25": n(t25["n"]), "var": p((t25["n"] - t24["n"]) / t24["n"]),
        "m24": n(m24), "m25": n(m25), "pct_caida_med": p((m24 - m25) / caida if caida else None),
        "pm24": p(t24["pct_con_muertos"]), "pm25": p(t25["pct_con_muertos"]),
        "nac24": p(nac[2024]["pct_con_muertos"]), "nac25": p(nac[2025]["pct_con_muertos"]),
        "peso_nac24": p(nac[2024]["n"] / t24["n"]), "peso_nac25": p(nac[2025]["n"] / t25["n"]),
        "_valores": {"t24": t24["n"], "t25": t25["n"], "m24": m24, "m25": m25},
    }


def evidencia_3():
    tot, _ = C.total()
    cat = _por([("tipo", "categoria")])
    tipo = _por([("tipo", "tipo")])
    carga, moto = cat["Vehículo de carga"], cat["Motocicletas y similares"]
    return {
        "pct_total": p(tot["pct_con_muertos"]), "pct_carga": p(carga["pct_con_muertos"]),
        "pct_moto": p(moto["pct_con_muertos"]), "pct_liv": p(cat["Vehículo liviano"]["pct_con_muertos"]),
        "pct_tracto": p(tipo["Tractocamion"]["pct_con_muertos"]), "pct_volq": p(tipo["Volqueta"]["pct_con_muertos"]),
        "pct_camion": p(tipo["Camion"]["pct_con_muertos"]),
        "peso_carga_veh": p(carga["n"] / tot["n"]), "peso_carga_m": p(carga["m"] / tot["m"]),
        "peso_moto_m": p(moto["m"] / tot["m"]), "n_carga": n(carga["n"]),
        "_valores": {"pct_carga": carga["pct_con_muertos"], "pct_moto": moto["pct_con_muertos"]},
    }


def evidencia_4():
    reg = _por([("ubicacion", "region")], {("tipo", "categoria"): ["Motocicletas y similares"]})
    reg_liv = _por([("ubicacion", "region")], {("tipo", "categoria"): ["Vehículo liviano"]})
    a, c, o, am = reg["Andina"], reg["Caribe"], reg["Orinoquía"], reg["Amazonía"]
    return {
        "andina": p(a["pct_con_muertos"]), "caribe": p(c["pct_con_muertos"]), "orinoquia": p(o["pct_con_muertos"]),
        "amazonia": p(am["pct_con_muertos"]), "n_amazonia": n(am["n"]),
        "veces": d(c["pct_con_muertos"] / a["pct_con_muertos"], 1),
        "liv_andina": p(reg_liv["Andina"]["pct_con_muertos"]), "liv_caribe": p(reg_liv["Caribe"]["pct_con_muertos"]),
        "_valores": {"andina": a["pct_con_muertos"], "caribe": c["pct_con_muertos"]},
    }


def evidencia_5():
    g = _por([("antiguedad", "grupo")])
    gm = _por([("antiguedad", "grupo")], {("tipo", "categoria"): ["Motocicletas y similares"]})
    gl = _por([("antiguedad", "grupo")], {("tipo", "categoria"): ["Vehículo liviano"]})
    r = _por([("antiguedad", "rango")])
    return {
        "g1": p(g["Hasta 5 años"]["pct_con_muertos"]), "g2": p(g["De 6 a 15 años"]["pct_con_muertos"]),
        "g3": p(g["Más de 15 años"]["pct_con_muertos"]),
        "r_ini": p(r["0-2 años"]["pct_con_muertos"]), "r_fin": p(r["Más de 20 años"]["pct_con_muertos"]),
        "m1": p(gm["Hasta 5 años"]["pct_con_muertos"]), "m3": p(gm["Más de 15 años"]["pct_con_muertos"]),
        "l1": p(gl["Hasta 5 años"]["pct_con_muertos"]), "l3": p(gl["Más de 15 años"]["pct_con_muertos"]),
        "_valores": {"g1": g["Hasta 5 años"]["pct_con_muertos"], "g3": g["Más de 15 años"]["pct_con_muertos"]},
    }


def evidencia_6():
    med = {c: C.mediana_edad({("tipo", "categoria"): [c]}) for c in
           ["Motocicletas y similares", "Vehículo liviano", "Transporte de pasajeros", "Vehículo de carga"]}
    x = _por([("tipo", "categoria"), ("antiguedad", "grupo")])
    def part(cat, grupo):
        tot = sum(f["n"] for k, f in x.items() if k[0] == cat)
        return x[(cat, grupo)]["n"] / tot if tot else None
    return {
        "med_moto": med["Motocicletas y similares"], "med_liv": med["Vehículo liviano"],
        "med_pas": med["Transporte de pasajeros"], "med_carga": med["Vehículo de carga"],
        "moto_5": p(part("Motocicletas y similares", "Hasta 5 años")),
        "carga_5": p(part("Vehículo de carga", "Hasta 5 años")),
        "carga_15": p(part("Vehículo de carga", "Más de 15 años")),
        "liv_15": p(part("Vehículo liviano", "Más de 15 años")),
        "med_total": C.mediana_edad(),
        "_valores": {"med_moto": med["Motocicletas y similares"], "med_carga": med["Vehículo de carga"]},
    }


def evidencia_7():
    x = _por([("tipo", "categoria"), ("marca", "grupo")])
    def top(cat):
        tot = sum(f["n"] for k, f in x.items() if k[0] == cat)
        return x[(cat, "10 marcas principales")]["n"] / tot if tot else None
    r = _por([("ubicacion", "region"), ("marca", "grupo")])
    reg = {}
    for (region, grupo), f in r.items():
        reg.setdefault(region, [0, 0])
        reg[region][1] += f["n"]
        if grupo == "10 marcas principales":
            reg[region][0] += f["n"]
    shares = {k: v[0] / v[1] for k, v in reg.items() if v[1] >= 1000}   # regiones con al menos 1.000 vehículos
    tot, _ = C.total()
    g = _por([("marca", "grupo")])
    return {
        "total": p(g["10 marcas principales"]["n"] / tot["n"]),
        "moto": p(top("Motocicletas y similares")), "liv": p(top("Vehículo liviano")),
        "pas": p(top("Transporte de pasajeros")), "carga": p(top("Vehículo de carga")),
        "reg_min": p(min(shares.values())), "reg_max": p(max(shares.values())),
        "reg_min_n": min(shares, key=shares.get), "reg_max_n": max(shares, key=shares.get),
        "_valores": {"moto": top("Motocicletas y similares"), "carga": top("Vehículo de carga")},
    }


def evidencia_8():
    f = {("tipo", "tipo"): ["Motocicleta"]}
    mk = _por([("marca", "marca")], f)
    tot, _ = C.total(f)
    b, s, y, k = mk["Bajaj"], mk["Suzuki"], mk["Yamaha"], mk["Kymco"]
    return {
        "motos": n(tot["n"]), "pct_motos": p(tot["pct_con_muertos"]),
        "b_part": p(b["n"] / tot["n"]), "b_part_m": p(b["m"] / tot["m"]), "b_pct": p(b["pct_con_muertos"]),
        "s_pct": p(s["pct_con_muertos"]), "y_pct": p(y["pct_con_muertos"]), "k_pct": p(k["pct_con_muertos"]),
        "y_part": p(y["n"] / tot["n"]), "y_part_m": p(y["m"] / tot["m"]),
        "_valores": {"b_pct": b["pct_con_muertos"], "k_pct": k["pct_con_muertos"]},
    }


# ---------------------------------------------------------------------------
# Textos (los {marcadores} se llenan con la evidencia calculada)
# ---------------------------------------------------------------------------
CONOCIMIENTOS = [
    {
        "id": 1, "pregunta_n": 1, "titulo": "El pico de julio de 2024 tiene un solo origen",
        "pregunta": "¿Qué territorio y qué organismo de tránsito producen el pico de julio de 2024?",
        "dimensiones": "Tiempo (Año > Mes), Ubicación (Región > Departamento > Municipio), Autoridad de tránsito. "
                       "Medidas: vehículos involucrados y participación.",
        "procedimiento": "Slice Año = 2024 y drill-down de Año a Mes en el gráfico 1; dice Mes = 2024-07; "
                         "drill-down en la matriz Región > Departamento (Antioquia) > Municipio y cambio de la "
                         "dimensión de filas a Autoridad. Se compara con el promedio mensual de enero a junio de "
                         "2024 de la misma autoridad.",
        "evidencia": "Vista 1: gráfico 1 a nivel Mes con filtro Año 2024; matriz con filas Autoridad y filtro "
                     "Departamento = Antioquia. Consulta 04 · P1-C1.",
        "hallazgo": "Julio de 2024 tiene {jul_total} vehículos; {ant_jul} ({pct_ant}) están en Antioquia y "
                    "{med_jul} ({pct_med} del mes) fueron reportados por la Secretaría de Tránsito de Medellín, "
                    "que de enero a junio de 2024 promedió {prom_med} vehículos por mes: {veces} veces más.",
        "interpretacion": "El pico que la Etapa 4 marcó como anomalía no es nacional: lo explica casi por completo "
                          "un único organismo en un único mes. Hipótesis (no comprobable con estos datos): una carga "
                          "acumulada o un cambio en el procedimiento de reporte de esa secretaría.",
        "utilidad": "Antes de leer tendencias mensuales conviene revisar o excluir ese reporte; permite pedir a la "
                    "fuente una aclaración concreta (organismo y mes).",
        "limitacion": "Los datos no indican si son accidentes de otros meses registrados en julio; no se puede "
                      "corregir la fecha ni afirmar que hubo más accidentes reales.",
        "evidencia_fn": evidencia_1,
    },
    {
        "id": 2, "pregunta_n": 1, "titulo": "La caída de 2025 es sobre todo un cambio de cobertura",
        "pregunta": "¿Qué explica la caída de vehículos de 2025 y el aumento del % con muertos en ese año?",
        "dimensiones": "Tiempo (Año), Autoridad de tránsito (Nivel territorial > Autoridad). Medidas: vehículos, "
                       "vehículos en accidentes con muertos y % con muertos.",
        "procedimiento": "Roll-up del gráfico 1 a Año; matriz con filas Autoridad (nivel territorial) y columnas "
                         "Año, métrica % con muertos; pivot para leer cada año como fila; slice Autoridad = "
                         "Secretaría de Tránsito de Medellín.",
        "evidencia": "Vista 1: matriz Autoridad × Año (métricas Vehículos y % con muertos). Consulta 04 · P1-C2.",
        "hallazgo": "Los vehículos pasaron de {t24} en 2024 a {t25} en 2025 ({var}). La Secretaría de Tránsito de "
                    "Medellín pasó de {m24} a {m25} registros: explica {pct_caida_med} de la caída. El % con "
                    "muertos subió de {pm24} a {pm25}, pero dentro de la Policía Nacional se mantuvo ({nac24} y "
                    "{nac25}); lo que cambió fue su peso en los registros: {peso_nac24} en 2024 y {peso_nac25} en 2025.",
        "interpretacion": "La caída y el aumento de la proporción de casos con muertos en 2025 coinciden con la "
                          "salida de un gran reportante urbano, con baja proporción de casos con muertos. Es un "
                          "efecto de composición de la fuente, no evidencia de que las vías se volvieran más "
                          "letales (hipótesis consistente con los datos, no comprobada).",
        "utilidad": "Compara años solo con los organismos que reportan de forma continua y evita conclusiones "
                    "de política basadas en 2025 y 2026 sin ajustar por cobertura.",
        "limitacion": "No se conoce la causa por la que Medellín dejó de reportar; tampoco hay datos de "
                      "exposición (parque automotor) para calcular tasas.",
        "evidencia_fn": evidencia_2,
    },
    {
        "id": 3, "pregunta_n": 2, "titulo": "Los vehículos de carga: pocos, pero en accidentes más graves",
        "pregunta": "¿Qué categorías y tipos de vehículo terminan con mayor proporción en accidentes con muertos?",
        "dimensiones": "Tipo de vehículo (Categoría > Tipo), Gravedad. Medidas: % con muertos, vehículos en "
                       "accidentes con muertos, vehículos.",
        "procedimiento": "Gráfico 1 a nivel Categoría con la medida % con muertos; drill-down de «Vehículo de "
                         "carga» a Tipo; participación de cada categoría en el total de vehículos y en los "
                         "vehículos en accidentes con muertos (denominadores distintos).",
        "evidencia": "Vista 2: gráfico 1 (Categoría y luego Tipo), indicadores 2 y 3. Consulta 04 · P2-C1.",
        "hallazgo": "El {pct_carga} de los vehículos de carga estuvo en accidentes con muertos, frente a {pct_moto} "
                    "de las motocicletas, {pct_liv} de los livianos y {pct_total} del total. Al bajar a tipo: "
                    "tractocamión {pct_tracto}, volqueta {pct_volq} y camión {pct_camion}. La carga es {peso_carga_veh} "
                    "de los vehículos pero {peso_carga_m} de los vehículos en accidentes con muertos; las motos, "
                    "con menor proporción, siguen siendo {peso_moto_m} de ese grupo.",
        "interpretacion": "La Etapa 4 mostró que la moto domina en cantidad; el cruce con gravedad muestra que el "
                          "riesgo relativo de terminar en un accidente fatal es mucho mayor cuando participa un "
                          "vehículo de carga. Ambas lecturas son complementarias: volumen (motos) y severidad (carga).",
        "utilidad": "Sustenta acciones diferenciadas: control de velocidad y descanso en transporte de carga y "
                    "campañas masivas para motociclistas.",
        "limitacion": "El indicador es por vehículo, no por víctima: un accidente con muertos entre un camión y "
                      "una moto marca a ambos. No identifica quién causó el accidente.",
        "evidencia_fn": evidencia_3,
    },
    {
        "id": 4, "pregunta_n": 2, "titulo": "La brecha regional se mantiene dentro de la misma categoría",
        "pregunta": "¿La diferencia del % con muertos entre regiones se debe solo a que cambian los tipos de vehículo?",
        "dimensiones": "Ubicación (Región), Tipo de vehículo (Categoría), Gravedad. Medida: % con muertos.",
        "procedimiento": "Dice: Categoría = Motocicletas y similares con la matriz Categoría × Región (métrica % con "
                         "muertos); se repite para Vehículo liviano. El porcentaje se recalcula en cada celda.",
        "evidencia": "Vista 2: matriz Categoría × Región con métrica % con muertos. Consulta 04 · P2-C2.",
        "hallazgo": "Entre motocicletas, el % con muertos es {andina} en la región Andina, {caribe} en el Caribe "
                    "({veces} veces más), {orinoquia} en la Orinoquía y {amazonia} en la Amazonía ({n_amazonia} "
                    "motos). En vehículos livianos: {liv_andina} en la Andina y {liv_caribe} en el Caribe.",
        "interpretacion": "La diferencia regional no desaparece al comparar el mismo tipo de vehículo. Hipótesis: "
                          "influyen el tipo de vía (más tramo rural y nacional fuera de la región Andina) y quién "
                          "reporta (la Policía Nacional, con mayor proporción de casos fatales, pesa más fuera de "
                          "las grandes ciudades).",
        "utilidad": "Orienta la priorización territorial de la seguridad para motociclistas hacia regiones con "
                    "mayor proporción de casos fatales, no solo hacia donde hay más registros.",
        "limitacion": "Las regiones con pocos vehículos (Amazonía, Insular) tienen porcentajes inestables; no hay "
                      "datos de vía ni de velocidad para comprobar la hipótesis.",
        "evidencia_fn": evidencia_4,
    },
    {
        "id": 5, "pregunta_n": 3, "titulo": "A mayor antigüedad, mayor proporción de casos con muertos",
        "pregunta": "¿Cambia el % de vehículos en accidentes con muertos entre grupos de antigüedad?",
        "dimensiones": "Antigüedad (Grupo > Rango > Años), Tipo de vehículo (Categoría), Gravedad. Medida: % con muertos.",
        "procedimiento": "Gráfico 1 por Grupo de antigüedad apilado por Gravedad; drill-down a Rango; dice con "
                         "Categoría = Motocicletas y similares y luego Vehículo liviano para descartar que el "
                         "patrón dependa solo de la mezcla de categorías.",
        "evidencia": "Vista 3: gráficos 1 y 2, indicador 3 (brecha en puntos porcentuales). Consulta 04 · P3-C1.",
        "hallazgo": "El % con muertos es {g1} en vehículos de hasta 5 años, {g2} de 6 a 15 años y {g3} con más de "
                    "15 años; por rango va de {r_ini} (0-2 años) a {r_fin} (más de 20). Dentro de las motos pasa "
                    "de {m1} a {m3} y dentro de los livianos de {l1} a {l3}.",
        "interpretacion": "La Etapa 4 describió una población joven; el cruce muestra que los vehículos antiguos, "
                          "aunque menos, aparecen con más frecuencia en accidentes con muertos, también dentro de "
                          "la misma categoría. Es una asociación, no una causa: la antigüedad puede ir unida a "
                          "otras condiciones (uso rural, mantenimiento) que no están en los datos.",
        "utilidad": "Apoya revisar la revisión técnico-mecánica y campañas para vehículos de más de 15 años.",
        "limitacion": "La edad es aproximada (fecha mensual y año del modelo) y los modelos posteriores al año "
                      "del accidente se dejaron en 0 años (14.233 registros).",
        "evidencia_fn": evidencia_5,
    },
    {
        "id": 6, "pregunta_n": 3, "titulo": "La «población joven» es un rasgo de las motos",
        "pregunta": "¿La edad mediana de 6 años de la Etapa 4 describe por igual a todas las categorías?",
        "dimensiones": "Antigüedad (Grupo), Tipo de vehículo (Categoría). Medidas: edad mediana, vehículos y "
                       "participación (% de la columna).",
        "procedimiento": "Matriz Grupo de antigüedad × Categoría con métrica «% de la columna»; slice por "
                         "Categoría para leer la edad mediana de cada una en el indicador 1.",
        "evidencia": "Vista 3: matriz y indicador 1 con el filtro de categoría. Consulta 04 · P3-C2.",
        "hallazgo": "La edad mediana general es {med_total} años, pero es {med_moto} en motos, {med_liv} en livianos, "
                    "{med_pas} en transporte de pasajeros y {med_carga} en carga. El {moto_5} de las motos tenía "
                    "hasta 5 años frente al {carga_5} de los vehículos de carga; el {carga_15} de la carga y el "
                    "{liv_15} de los livianos superaba los 15 años.",
        "interpretacion": "El dato agregado de la Etapa 4 está dominado por las motos. Fuera de ellas, la "
                          "población accidentada es claramente más antigua, lo que cambia el público objetivo.",
        "utilidad": "Las campañas «al momento de la compra» sirven para motos; para carga y livianos tiene más "
                    "sentido el control del estado del vehículo.",
        "limitacion": "Se observa la antigüedad de los vehículos accidentados, no la del parque automotor; sin "
                      "ese dato no se puede decir qué edades tienen más riesgo por vehículo en circulación.",
        "evidencia_fn": evidencia_6,
    },
    {
        "id": 7, "pregunta_n": 4, "titulo": "La concentración de marcas depende de la categoría, no del territorio",
        "pregunta": "¿Se mantiene la concentración del 73,8 % en las 10 marcas principales al separar por "
                    "categoría y por región?",
        "dimensiones": "Marca (Grupo > Marca), Tipo de vehículo (Categoría), Ubicación (Región). Medida: participación.",
        "procedimiento": "Matriz Grupo de marca × Categoría con métrica «% de la columna»; cambio de la dimensión "
                         "de columnas a Región (pivot de perspectiva) y drill-down de Grupo a Marca.",
        "evidencia": "Vista 4: matriz con columnas Categoría y luego Región. Consulta 04 · P4-C1.",
        "hallazgo": "Las 10 marcas principales reúnen el {total} de todos los vehículos, pero el {moto} de las "
                    "motos, el {liv} de los livianos, el {pas} del transporte de pasajeros y solo el {carga} de "
                    "los vehículos de carga. Entre regiones con al menos 1.000 vehículos la cifra varía poco: de "
                    "{reg_min} ({reg_min_n}) a {reg_max} ({reg_max_n}).",
        "interpretacion": "La concentración que mostró la Etapa 4 es un fenómeno de motos y livianos; en carga y "
                          "pasajeros la oferta está mucho más repartida. El territorio casi no la modifica.",
        "utilidad": "Coordinar con pocas marcas es eficaz para motos; para carga y pasajeros hay que trabajar "
                    "con gremios de transportadores más que con fabricantes.",
        "limitacion": "El grupo «10 marcas principales» se definió con el total del periodo; en otra selección "
                      "las 10 primeras pueden ser distintas.",
        "evidencia_fn": evidencia_7,
    },
    {
        "id": 8, "pregunta_n": 4, "titulo": "Entre motocicletas, la proporción fatal cambia según la marca",
        "pregunta": "Dentro de las motocicletas, ¿qué marcas reúnen más vehículos en accidentes con muertos?",
        "dimensiones": "Marca, Tipo de vehículo (slice Motocicleta), Gravedad. Medidas: participación, % con muertos.",
        "procedimiento": "Slice Tipo de vehículo = Motocicleta; gráfico 1 a nivel Marca (participación) y gráfico 2 "
                         "con % con muertos de las marcas con más vehículos; se comparan dos denominadores: todas las "
                         "motos y las motos en accidentes con muertos.",
        "evidencia": "Vista 4 con filtro Tipo = Motocicleta: gráficos 1 y 2. Consulta 04 · P4-C2.",
        "hallazgo": "Entre {motos} motocicletas ({pct_motos} con muertos), Bajaj es el {b_part} de las motos pero el "
                    "{b_part_m} de las que estuvieron en accidentes con muertos ({b_pct}); Suzuki llega a {s_pct}, "
                    "mientras Yamaha ({y_part} de las motos, {y_part_m} de las fatales) registra {y_pct} y Kymco {k_pct}.",
        "interpretacion": "La marca no se puede leer como medida de seguridad del vehículo. Hipótesis: las "
                          "diferencias reflejan el uso (trabajo, zonas rurales, cilindraje) de los modelos más "
                          "vendidos de cada marca, que no está en los datos.",
        "utilidad": "Permite focalizar con las marcas cuya clientela aparece más en casos fatales "
                    "(por ejemplo, formación en la entrega de motos de trabajo).",
        "limitacion": "No hay cilindraje, modelo comercial ni uso del vehículo; el % de marcas pequeñas es "
                      "inestable por su bajo número de registros.",
        "evidencia_fn": evidencia_8,
    },
]


@lru_cache(maxsize=1)
def calcular():
    """Devuelve los ocho conocimientos con el hallazgo completado con cifras reales."""
    return [_completar(k) for k in CONOCIMIENTOS]


def _completar(k):
    ev = k["evidencia_fn"]()
    visibles = {a: b for a, b in ev.items() if not a.startswith("_")}
    return {**{a: b for a, b in k.items() if a != "evidencia_fn"},
            "hallazgo": k["hallazgo"].format(**visibles), "valores": ev["_valores"]}


@lru_cache(maxsize=4)
def por_pregunta(numero):
    """Calcula solo los dos conocimientos que muestra la pregunta solicitada."""
    return [_completar(k) for k in CONOCIMIENTOS if k["pregunta_n"] == numero]
