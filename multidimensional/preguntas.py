"""
Definición de las cuatro preguntas de análisis multidimensional y resolución de sus
consultas (indicadores, dos visualizaciones y una matriz por pregunta).

Cada vista envía su "estado" (filtros, niveles, ruta de drill-down, pivot y métrica)
a /analisis-multidimensional/api/pregunta/<n>. Este módulo valida el estado contra la
configuración (lista blanca), arma las consultas con cubo.agregar() y devuelve JSON.
"""
from . import cubo as C

# ---------------------------------------------------------------------------
# Utilidades de presentación
# ---------------------------------------------------------------------------
ORDINALES = {"tiempo", "antiguedad", "gravedad"}   # dimensiones que se muestran en su orden natural
METRICAS_MATRIZ = {
    "vehiculos": ("Vehículos", "n", "Conteo de registros de vehículo (suma de CantidadVehiculos)"),
    "pct_fila": ("% de la fila", "pct", "Denominador: total de vehículos de la fila"),
    "pct_columna": ("% de la columna", "pct", "Denominador: total de vehículos de la columna"),
    "pct_con_muertos": ("% en accidentes con muertos", "pct",
                        "Denominador: vehículos de la celda (SUM(ConMuertos) / SUM(Cantidad))"),
    "edad_promedio": ("Edad promedio al accidente", "anios", "SUM(EdadAlAccidente) / COUNT(EdadAlAccidente) de la celda"),
}
MEDIDAS_GRAFICO = {
    "vehiculos": ("Vehículos involucrados", "n"),
    "participacion": ("Participación en la selección", "pct"),
    "con_muertos": ("Vehículos en accidentes con muertos", "n"),
    "pct_con_muertos": ("% en accidentes con muertos", "pct"),
    "edad_promedio": ("Edad promedio al accidente (años)", "anios"),
}


def _sumar(filas, claves):
    n = sum(f["n"] for f in filas)
    m = sum(f["m"] for f in filas)
    se = sum(f["se"] for f in filas)
    ce = sum(f["ce"] for f in filas)
    return C.derivar(claves, n, m, se, ce)


def _limitar(filas, limite, indice=0):
    """Deja los 'limite' miembros con más vehículos y agrupa el resto en 'Otros (k)'.
    Las medidas de 'Otros' se recalculan desde sus componentes aditivos."""
    if not limite:
        return filas
    totales = {}
    for f in filas:
        totales[f["claves"][indice]] = totales.get(f["claves"][indice], 0) + f["n"]
    if len(totales) <= limite:
        return filas
    top = set(sorted(totales, key=lambda k: -totales[k])[:limite])
    resto = [k for k in totales if k not in top]
    etiqueta = f"Otros ({len(resto)})"
    salida, agrupado = [], {}
    for f in filas:
        if f["claves"][indice] in top:
            salida.append(f)
        else:
            clave = list(f["claves"])
            clave[indice] = etiqueta
            agrupado.setdefault(tuple(clave), []).append(f)
    salida.extend(_sumar(v, k) for k, v in agrupado.items())
    return salida


def _valor(fila, medida, total_n):
    if medida == "vehiculos":
        return fila["n"]
    if medida == "con_muertos":
        return fila["m"]
    if medida == "participacion":
        return (fila["n"] / total_n) if total_n else None
    if medida == "pct_con_muertos":
        return fila["pct_con_muertos"]
    if medida == "edad_promedio":
        return fila["edad_promedio"]
    raise C.ErrorConsulta("Medida no válida")


def _texto(v):
    return "Sin dato" if v is None else str(v)


# ---------------------------------------------------------------------------
# Configuración de las cuatro preguntas
# ---------------------------------------------------------------------------
PREGUNTAS = {
    1: {
        "slug": "pregunta1",
        "titulo": "Cobertura temporal y territorial del registro",
        "pregunta": ("¿Qué territorios y organismos de tránsito explican los cambios en la cantidad de "
                     "vehículos involucrados entre 2022 y 2026, en particular el pico de julio de 2024 y la "
                     "caída de 2025, cuando se baja del año al mes y de la región al municipio?"),
        "etapa4": ("Etapa 4, análisis temporal: los registros bajaron 2,51 % entre 2022 y 2023, subieron 7,82 % "
                   "en 2024 y julio de 2024 concentró el 23,93 % del año (28.794 vehículos). El pico se señaló "
                   "como posible anomalía de cobertura, sin identificar su origen."),
        "profundiza": ("Cruza Tiempo con Ubicación y Autoridad de tránsito para localizar qué organismo y qué "
                       "territorio producen los cambios, y compara meses equivalentes entre años."),
        "dimensiones": ["tiempo", "ubicacion", "autoridad"],
        "medidas": ["vehiculos", "participacion", "pct_con_muertos"],
        "jerarquias": ["Año > Semestre > Trimestre > Mes", "Región > Departamento > Municipio",
                       "Nivel territorial > Autoridad"],
        "filtros": [
            {"id": "anio", "dim": "tiempo", "nivel": "anio", "etiqueta": "Año (Tiempo)"},
            {"id": "departamento", "dim": "ubicacion", "nivel": "departamento", "etiqueta": "Departamento (Ubicación)"},
        ],
        "g1": {"titulo": "Evolución de los vehículos involucrados", "tipo": "line", "dim": "tiempo",
               "nivel": "anio", "medida": "vehiculos", "medidas": ["vehiculos", "pct_con_muertos"]},
        "g2": {"titulo": "Distribución por territorio o autoridad", "tipo": "barh", "dim": "ubicacion",
               "nivel": "region", "medida": "vehiculos", "dims": ["ubicacion", "autoridad"],
               "medidas": ["vehiculos", "participacion", "pct_con_muertos"], "limite": 12},
        "matriz": {"filas": {"dim": "ubicacion", "nivel": "region", "dims": ["ubicacion", "autoridad"]},
                   "columnas": {"dim": "tiempo", "nivel": "anio", "niveles": ["anio", "semestre", "mes_calendario"]},
                   "metrica": "vehiculos", "metricas": ["vehiculos", "pct_fila", "pct_columna", "pct_con_muertos"],
                   "limite_filas": 15},
    },
    2: {
        "slug": "pregunta2",
        "titulo": "Gravedad según tipo de vehículo y territorio",
        "pregunta": ("¿Cómo varía la proporción de vehículos involucrados en accidentes con muertos según la "
                     "categoría y el tipo de vehículo, y esa diferencia se mantiene entre regiones y departamentos?"),
        "etapa4": ("Etapa 4: la motocicleta es el 56,4 % de los vehículos (composición) y la participación de "
                   "registros «Con muertos» fue 4,57 % en 2023 y 4,37 % en 2024 (temporal). Ambos resultados se "
                   "leyeron por separado y sin cruzar gravedad con tipo de vehículo ni con territorio."),
        "profundiza": ("Cruza Tipo de vehículo, Gravedad y Ubicación: pasa de «cuántos» a «en qué proporción "
                       "terminan en accidentes con muertos», recalculando el porcentaje en cada nivel."),
        "dimensiones": ["tipo", "gravedad", "ubicacion", "tiempo"],
        "medidas": ["pct_con_muertos", "con_muertos", "vehiculos"],
        "jerarquias": ["Categoría > Tipo de vehículo", "Región > Departamento > Municipio"],
        "filtros": [
            {"id": "region", "dim": "ubicacion", "nivel": "region", "etiqueta": "Región (Ubicación)"},
            {"id": "anio", "dim": "tiempo", "nivel": "anio", "etiqueta": "Año (Tiempo)"},
        ],
        "g1": {"titulo": "% en accidentes con muertos por tipo de vehículo", "tipo": "bar", "dim": "tipo",
               "nivel": "categoria", "medida": "pct_con_muertos",
               "medidas": ["pct_con_muertos", "con_muertos", "vehiculos"], "limite": 12},
        "g2": {"titulo": "Composición por gravedad en cada territorio", "tipo": "stacked100", "dim": "ubicacion",
               "nivel": "region", "serie": ("gravedad", "gravedad"), "medida": "vehiculos", "limite": 12},
        "matriz": {"filas": {"dim": "tipo", "nivel": "categoria", "dims": ["tipo"]},
                   "columnas": {"dim": "ubicacion", "nivel": "region", "niveles": ["region", "ambito"]},
                   "metrica": "pct_con_muertos",
                   "metricas": ["pct_con_muertos", "vehiculos", "pct_fila", "pct_columna"], "limite_filas": 15},
    },
    3: {
        "slug": "pregunta3",
        "titulo": "Antigüedad del vehículo, categoría y gravedad",
        "pregunta": ("¿Cómo se distribuye la antigüedad al momento del accidente dentro de cada categoría de "
                     "vehículo y cambia la proporción de vehículos en accidentes con muertos entre grupos de antigüedad?"),
        "etapa4": ("Etapa 4, conocimiento C3: población «joven», con edad mediana de 6 años y 46,2 % de vehículos "
                   "con 5 años o menos (motos: mediana 4; automóviles: 10). No se relacionó la antigüedad con la gravedad."),
        "profundiza": ("Usa la jerarquía Grupo > Rango > Edad de la dimensión Antigüedad y la cruza con Tipo de "
                       "vehículo y Gravedad para ver si el patrón general se sostiene dentro de cada categoría."),
        "dimensiones": ["antiguedad", "tipo", "gravedad"],
        "medidas": ["vehiculos", "pct_con_muertos", "edad_promedio"],
        "jerarquias": ["Grupo de antigüedad > Rango > Años", "Categoría > Tipo de vehículo"],
        "filtros": [
            {"id": "categoria", "dim": "tipo", "nivel": "categoria", "etiqueta": "Categoría (Tipo de vehículo)"},
            {"id": "gravedad", "dim": "gravedad", "nivel": "gravedad", "etiqueta": "Gravedad"},
        ],
        "g1": {"titulo": "Vehículos por antigüedad y gravedad", "tipo": "stacked", "dim": "antiguedad",
               "nivel": "grupo", "serie": ("gravedad", "gravedad"), "medida": "vehiculos"},
        "g2": {"titulo": "% en accidentes con muertos por antigüedad y categoría", "tipo": "line",
               "dim": "antiguedad", "nivel": "rango", "serie": ("tipo", "categoria"),
               "medida": "pct_con_muertos", "medidas": ["pct_con_muertos", "vehiculos"], "min_n": 100},
        "matriz": {"filas": {"dim": "antiguedad", "nivel": "grupo", "dims": ["antiguedad"]},
                   "columnas": {"dim": "tipo", "nivel": "categoria", "niveles": ["categoria", "tipo"]},
                   "metrica": "pct_columna",
                   "metricas": ["pct_columna", "pct_fila", "vehiculos", "pct_con_muertos", "edad_promedio"],
                   "limite_filas": 25, "limite_columnas": 10},
    },
    4: {
        "slug": "pregunta4",
        "titulo": "Concentración de marcas por categoría y territorio",
        "pregunta": ("¿La concentración de vehículos en pocas marcas se mantiene al bajar por categoría de vehículo "
                     "y por región, y qué marcas reúnen más vehículos en accidentes con muertos?"),
        "etapa4": ("Etapa 4, conocimiento C2: de 360 marcas, 10 reúnen el 73,8 % de los vehículos y 5 el 51,1 %; "
                   "lideran Bajaj, Yamaha y Chevrolet. La concentración se midió sobre el total, sin separar por "
                   "categoría, territorio ni gravedad."),
        "profundiza": ("Cruza Marca con Tipo de vehículo, Ubicación y Gravedad; el pivot permite leer la "
                       "concentración por categoría o por región."),
        "dimensiones": ["marca", "tipo", "ubicacion", "gravedad"],
        "medidas": ["participacion", "vehiculos", "pct_con_muertos"],
        "jerarquias": ["Grupo de marca > Marca", "Categoría > Tipo de vehículo"],
        "filtros": [
            {"id": "region", "dim": "ubicacion", "nivel": "region", "etiqueta": "Región (Ubicación)"},
            {"id": "tipo", "dim": "tipo", "nivel": "tipo", "etiqueta": "Tipo de vehículo"},
        ],
        "g1": {"titulo": "Participación de las marcas", "tipo": "barh", "dim": "marca", "nivel": "grupo",
               "medida": "participacion", "medidas": ["participacion", "vehiculos"], "limite": 15},
        "g2": {"titulo": "% en accidentes con muertos por marca", "tipo": "barh", "dim": "marca", "nivel": "marca",
               "medida": "pct_con_muertos", "medidas": ["pct_con_muertos", "con_muertos"], "limite": 12,
               "excluir_otros": True},
        "matriz": {"filas": {"dim": "marca", "nivel": "grupo", "dims": ["marca"]},
                   "columnas": {"dim": "tipo", "nivel": "categoria", "niveles": ["categoria"],
                                "dims": ["tipo", "ubicacion"]},
                   "metrica": "pct_columna",
                   "metricas": ["pct_columna", "pct_fila", "vehiculos", "pct_con_muertos"], "limite_filas": 15},
    },
}


# ---------------------------------------------------------------------------
# Validación del estado enviado por el navegador
# ---------------------------------------------------------------------------
def _validar_nivel(dim, nivel):
    if dim not in C.DIMENSIONES or nivel not in C.DIMENSIONES[dim]["niveles"]:
        raise C.ErrorConsulta(f"Nivel no permitido: {dim}.{nivel}")
    return dim, nivel


def filtros_globales(cfg, estado):
    filtros = {}
    entrada = (estado or {}).get("filtros") or {}
    for f in cfg["filtros"]:
        valores = entrada.get(f["id"]) or []
        if not isinstance(valores, list):
            valores = [valores]
        valores = [int(v) if f["dim"] == "tiempo" and f["nivel"] == "anio" else str(v) for v in valores][:60]
        if valores:
            filtros[(f["dim"], f["nivel"])] = valores
    return filtros


def _filtros_con_ruta(base, dim, ruta):
    """Agrega la ruta de drill-down (miembros elegidos en niveles superiores) a los filtros."""
    filtros = {k: list(v) for k, v in base.items()}
    jer = C.DIMENSIONES[dim]["jerarquia"]
    for paso in ruta or []:
        nivel, valor = paso.get("nivel"), paso.get("valor")
        if nivel not in jer:
            raise C.ErrorConsulta("Ruta de drill-down no válida")
        if dim == "tiempo" and nivel == "anio":
            valor = int(valor)
        clave = (dim, nivel)
        filtros[clave] = [v for v in filtros[clave] if v == valor] if clave in filtros else [valor]
    return filtros


# ---------------------------------------------------------------------------
# Indicadores (3 por pregunta), siempre sobre la selección activa
# ---------------------------------------------------------------------------
def _kpi(etiqueta, valor, formato, nota, detalle=None):
    return {"etiqueta": etiqueta, "valor": valor, "formato": formato, "nota": nota, "detalle": detalle}


def kpis(numero, filtros):
    tot, _ = C.total(filtros)
    n = tot["n"]
    if numero == 1:
        meses, _ = C.agregar([("tiempo", "mes")], filtros)
        pico = max(meses, key=lambda f: f["n"]) if meses else None
        auts, _ = C.agregar([("autoridad", "autoridad")], filtros)
        top = max(auts, key=lambda f: f["n"]) if auts else None
        return [
            _kpi("Vehículos involucrados", n, "n", "Suma de CantidadVehiculos en la selección"),
            _kpi("Mes con más vehículos", (pico["n"] / n) if pico and n else None, "pct",
                 "Participación del mes sobre el total de la selección", pico and f"{pico['claves'][0]} · {pico['n']:,} vehículos".replace(",", ".")),
            _kpi("Autoridad con más registros", (top["n"] / n) if top and n else None, "pct",
                 "Participación de la autoridad sobre el total de la selección", top and top["claves"][0]),
        ]
    if numero == 2:
        cats, _ = C.agregar([("tipo", "categoria")], filtros)
        moto = next((f for f in cats if f["claves"][0] == "Motocicletas y similares"), None)
        tipos, _ = C.agregar([("tipo", "tipo")], filtros)
        validos = [f for f in tipos if f["n"] >= 500 and f["pct_con_muertos"] is not None]
        peor = max(validos, key=lambda f: f["pct_con_muertos"]) if validos else None
        return [
            _kpi("% en accidentes con muertos", tot["pct_con_muertos"], "pct",
                 "SUM(ConMuertos) / SUM(Cantidad) de la selección"),
            _kpi("Motos entre los vehículos con muertos", (moto["m"] / tot["m"]) if moto and tot["m"] else None, "pct",
                 "Denominador: vehículos en accidentes con muertos de la selección"),
            _kpi("Tipo con mayor % con muertos", peor["pct_con_muertos"] if peor else None, "pct",
                 "Solo tipos con 500 vehículos o más en la selección", peor and f"{peor['claves'][0]} · {peor['n']:,} vehículos".replace(",", ".")),
        ]
    if numero == 3:
        grupos, _ = C.agregar([("antiguedad", "grupo")], filtros)
        g = {f["claves"][0]: f for f in grupos}
        joven, viejo = g.get("Hasta 5 años"), g.get("Más de 15 años")
        brecha = None
        if joven and viejo and joven["pct_con_muertos"] is not None and viejo["pct_con_muertos"] is not None:
            brecha = (viejo["pct_con_muertos"] - joven["pct_con_muertos"]) * 100
        return [
            _kpi("Edad mediana al accidente", C.mediana_edad(filtros), "anios",
                 "Mediana de EdadAlAccidente (año del accidente − año del modelo)"),
            _kpi("Vehículos con hasta 5 años", (joven["n"] / n) if joven and n else None, "pct",
                 "Denominador: vehículos de la selección"),
            _kpi("Brecha de % con muertos (más de 15 vs. hasta 5 años)", brecha, "pp",
                 "Diferencia en puntos porcentuales; cada % se recalcula en su grupo"),
        ]
    if numero == 4:
        grupos, _ = C.agregar([("marca", "grupo")], filtros)
        top10 = next((f for f in grupos if f["claves"][0] == "10 marcas principales"), None)
        marcas, _ = C.agregar([("marca", "marca")], filtros)
        reales = [f for f in marcas if f["claves"][0] != "Sin dato (nulo)" and f["n"] > 0]
        lider = max(reales, key=lambda f: f["n"]) if reales else None
        return [
            _kpi("Participación de las 10 marcas principales", (top10["n"] / n) if top10 and n else None, "pct",
                 "Las 10 marcas con más vehículos en todo el periodo; denominador: selección"),
            _kpi("Marcas distintas con registros", len(reales), "n",
                 "Conteo de marcas distintas (entidades únicas), no de vehículos"),
            _kpi("Marca con más vehículos", (lider["n"] / n) if lider and n else None, "pct",
                 "Participación de la marca líder en la selección", lider and lider["claves"][0]),
        ]
    raise C.ErrorConsulta("Pregunta no válida")


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------
def grafico(cfg_g, base, est):
    est = est or {}
    dim = est.get("dim") or cfg_g["dim"]
    if dim not in (cfg_g.get("dims") or [cfg_g["dim"]]):
        raise C.ErrorConsulta("Dimensión de gráfico no permitida")
    jer = C.DIMENSIONES[dim]["jerarquia"]
    nivel = est.get("nivel") or (cfg_g["nivel"] if dim == cfg_g["dim"] else jer[0])
    _validar_nivel(dim, nivel)
    medida = est.get("medida") or cfg_g["medida"]
    if medida not in (cfg_g.get("medidas") or [cfg_g["medida"]]):
        raise C.ErrorConsulta("Medida no permitida")
    ruta = est.get("ruta") or []
    filtros = _filtros_con_ruta(base, dim, ruta)
    ejes = [(dim, nivel)]
    serie = cfg_g.get("serie")
    if serie:
        ejes.append(serie)
    filas, sql = C.agregar(ejes, filtros)
    total_sel = sum(f["n"] for f in filas)
    if dim not in ORDINALES and not serie:
        filas.sort(key=lambda f: -f["n"])
    filas = _limitar(filas, cfg_g.get("limite"))
    if cfg_g.get("excluir_otros"):
        filas = [f for f in filas if not str(f["claves"][0]).startswith("Otros (")]
    etiquetas = []
    for f in filas:
        if f["claves"][0] not in etiquetas:
            etiquetas.append(f["claves"][0])
    nombre_medida, formato = MEDIDAS_GRAFICO[medida]
    datasets = []
    if serie:
        series = []
        for f in filas:
            if f["claves"][1] not in series:
                series.append(f["claves"][1])
        por_barra = {}
        for f in filas:
            por_barra[f["claves"][0]] = por_barra.get(f["claves"][0], 0) + f["n"]
        min_n = cfg_g.get("min_n", 0)
        for s in series:
            datos = []
            for e in etiquetas:
                celda = next((f for f in filas if f["claves"] == (e, s)), None)
                if celda is None or celda["n"] < min_n:
                    datos.append(None)
                elif cfg_g["tipo"] == "stacked100":
                    datos.append(celda["n"] / por_barra[e] if por_barra[e] else None)
                else:
                    datos.append(_valor(celda, medida, total_sel))
            datasets.append({"label": _texto(s), "data": datos})
        if cfg_g["tipo"] == "stacked100":
            nombre_medida, formato = "% de los vehículos de cada barra", "pct"
    else:
        datasets.append({"label": nombre_medida,
                         "data": [_valor(f, medida, total_sel) for f in filas],
                         "n": [f["n"] for f in filas]})
    return {
        "titulo": cfg_g["titulo"], "tipo": cfg_g["tipo"], "dim": dim, "nivel": nivel, "ruta": ruta,
        "nombre_dim": C.DIMENSIONES[dim]["nombre"], "nombre_nivel": C.DIMENSIONES[dim]["niveles"][nivel][0],
        "medida": medida, "nombre_medida": nombre_medida, "formato": formato,
        "medidas": [{"id": m, "nombre": MEDIDAS_GRAFICO[m][0]} for m in (cfg_g.get("medidas") or [cfg_g["medida"]])],
        "dims": [{"id": d, "nombre": C.DIMENSIONES[d]["nombre"]} for d in (cfg_g.get("dims") or [cfg_g["dim"]])],
        "puede_bajar": C.nivel_inferior(dim, nivel) is not None,
        "puede_subir": C.nivel_superior(dim, nivel) is not None or bool(ruta),
        "nivel_inferior": C.nivel_inferior(dim, nivel), "nivel_superior": C.nivel_superior(dim, nivel),
        "jerarquia": [{"id": j, "nombre": C.DIMENSIONES[dim]["niveles"][j][0]} for j in jer],
        "etiquetas": [_texto(e) for e in etiquetas], "datasets": datasets,
        "total_seleccion": total_sel, "sql": sql,
        "drill_por_miembro": C.nivel_inferior(dim, nivel) is not None,
    }


# ---------------------------------------------------------------------------
# Matriz (con pivot)
# ---------------------------------------------------------------------------
def matriz(cfg_m, base, est):
    est = est or {}
    fdim = est.get("dim_filas") or cfg_m["filas"]["dim"]
    if fdim not in cfg_m["filas"]["dims"]:
        raise C.ErrorConsulta("Dimensión de filas no permitida")
    fjer = C.DIMENSIONES[fdim]["jerarquia"]
    fnivel = est.get("nivel_filas") or (cfg_m["filas"]["nivel"] if fdim == cfg_m["filas"]["dim"] else fjer[0])
    _validar_nivel(fdim, fnivel)
    cdim = est.get("dim_columnas") or cfg_m["columnas"]["dim"]
    if cdim not in (cfg_m["columnas"].get("dims") or [cfg_m["columnas"]["dim"]]):
        raise C.ErrorConsulta("Dimensión de columnas no permitida")
    niveles_c = cfg_m["columnas"]["niveles"] if cdim == cfg_m["columnas"]["dim"] else [C.DIMENSIONES[cdim]["jerarquia"][0]]
    cnivel = est.get("nivel_columnas") or niveles_c[0]
    if cnivel not in niveles_c:
        cnivel = niveles_c[0]
    metrica = est.get("metrica") or cfg_m["metrica"]
    if metrica not in cfg_m["metricas"]:
        raise C.ErrorConsulta("Métrica no permitida")
    pivot = bool(est.get("pivot"))
    ruta = est.get("ruta_filas") or []
    filtros = _filtros_con_ruta(base, fdim, ruta)

    filas, sql = C.agregar([(fdim, fnivel), (cdim, cnivel)], filtros)
    filas = _limitar(filas, cfg_m.get("limite_filas") if fdim not in ORDINALES else None, 0)
    filas = _limitar(filas, cfg_m.get("limite_columnas"), 1)
    # Pivot: se intercambian los ejes; los porcentajes se recalculan con los nuevos totales.
    i_f, i_c = (1, 0) if pivot else (0, 1)
    orden_f, orden_c, celdas = C.pivotar(filas, i_f, i_c)
    dim_f, niv_f, dim_c, niv_c = (cdim, cnivel, fdim, fnivel) if pivot else (fdim, fnivel, cdim, cnivel)
    if dim_f not in ORDINALES:
        tot_f = {k: sum(c["n"] for c in celdas[k].values()) for k in orden_f}
        orden_f.sort(key=lambda k: (str(k).startswith("Otros ("), -tot_f[k]))
    if dim_c not in ORDINALES:
        tot_c = {c: sum(celdas[k][c]["n"] for k in orden_f if c in celdas[k]) for c in orden_c}
        orden_c.sort(key=lambda c: (str(c).startswith("Otros ("), -tot_c[c]))
    tot_fila = {k: _sumar(list(celdas[k].values()), (k,)) for k in orden_f}
    tot_col = {c: _sumar([celdas[k][c] for k in orden_f if c in celdas[k]], (c,)) for c in orden_c}
    gran = _sumar(list(tot_fila.values()), ())

    def valor(celda, kf, kc):
        if celda is None:
            return None
        if metrica == "vehiculos":
            return celda["n"]
        if metrica == "pct_fila":
            return celda["n"] / tot_fila[kf]["n"] if tot_fila[kf]["n"] else None
        if metrica == "pct_columna":
            return celda["n"] / tot_col[kc]["n"] if tot_col[kc]["n"] else None
        if metrica == "pct_con_muertos":
            return celda["pct_con_muertos"]
        return celda["edad_promedio"]

    def valor_total(t, eje):
        if metrica == "vehiculos":
            return t["n"]
        if metrica in ("pct_fila", "pct_columna"):
            if (metrica == "pct_fila") == (eje == "fila"):
                return 1.0 if t["n"] else None
            return t["n"] / gran["n"] if gran["n"] else None
        if metrica == "pct_con_muertos":
            return t["pct_con_muertos"]
        return t["edad_promedio"]

    nombre, formato, denominador = METRICAS_MATRIZ[metrica]
    return {
        "dim_filas": dim_f, "nivel_filas": niv_f, "dim_columnas": dim_c, "nivel_columnas": niv_c,
        "nombre_filas": C.DIMENSIONES[dim_f]["niveles"][niv_f][0],
        "nombre_columnas": C.DIMENSIONES[dim_c]["niveles"][niv_c][0],
        "pivot": pivot, "metrica": metrica, "nombre_metrica": nombre, "formato": formato,
        "denominador": denominador, "ruta_filas": ruta,
        "metricas": [{"id": m, "nombre": METRICAS_MATRIZ[m][0]} for m in cfg_m["metricas"]],
        "dims_filas": [{"id": d, "nombre": C.DIMENSIONES[d]["nombre"]} for d in cfg_m["filas"]["dims"]],
        "dims_columnas": [{"id": d, "nombre": C.DIMENSIONES[d]["nombre"]} for d in
                          (cfg_m["columnas"].get("dims") or [cfg_m["columnas"]["dim"]])],
        "niveles_columnas": [{"id": x, "nombre": C.DIMENSIONES[cdim]["niveles"][x][0]} for x in niveles_c],
        "dim_filas_base": fdim, "nivel_filas_base": fnivel, "dim_columnas_base": cdim, "nivel_columnas_base": cnivel,
        "puede_bajar": C.nivel_inferior(fdim, fnivel) is not None,
        "puede_subir": C.nivel_superior(fdim, fnivel) is not None or bool(ruta),
        "nivel_inferior": C.nivel_inferior(fdim, fnivel), "nivel_superior": C.nivel_superior(fdim, fnivel),
        "filas": [_texto(k) for k in orden_f], "columnas": [_texto(c) for c in orden_c],
        "valores": [[valor(celdas[k].get(c), k, c) for c in orden_c] for k in orden_f],
        "n": [[(celdas[k][c]["n"] if c in celdas[k] else 0) for c in orden_c] for k in orden_f],
        "total_fila": [valor_total(tot_fila[k], "fila") for k in orden_f],
        "total_columna": [valor_total(tot_col[c], "columna") for c in orden_c],
        "total_general": valor_total(gran, "total") if metrica not in ("pct_fila", "pct_columna") else 1.0,
        "n_total": gran["n"], "sql": sql,
    }


# ---------------------------------------------------------------------------
# Descripción de la selección y operaciones activas
# ---------------------------------------------------------------------------
def describir(cfg, base, estado):
    partes, ops = [], []
    dims_filtradas = {dim for (dim, _), v in base.items() if v}
    for (dim, nivel), valores in base.items():
        partes.append(f"{C.DIMENSIONES[dim]['niveles'][nivel][0]} = {', '.join(map(str, valores))}")
    if len(dims_filtradas) == 1 and sum(len(v) for v in base.values()) == 1:
        ops.append("Slice")
    elif len(dims_filtradas) >= 2:
        ops.append("Dice")
    elif dims_filtradas:
        ops.append("Selección de varios miembros en una dimensión")
    for clave in ("g1", "g2"):
        g = (estado or {}).get(clave) or {}
        if g.get("ruta") or (g.get("nivel") and g.get("nivel") != cfg[clave]["nivel"]
                             and (g.get("dim") or cfg[clave]["dim"]) == cfg[clave]["dim"]):
            ops.append(f"Drill-down/Roll-up en gráfico {clave[1]}")
    m = (estado or {}).get("matriz") or {}
    if m.get("ruta_filas") or (m.get("nivel_filas") and m.get("nivel_filas") != cfg["matriz"]["filas"]["nivel"]):
        ops.append("Drill-down/Roll-up en la matriz")
    if m.get("pivot"):
        ops.append("Pivot")
    return {"filtros": partes or ["Sin filtros: conjunto completo (ene. 2022 – feb. 2026)"],
            "operaciones": ops, "ultima_operacion": (estado or {}).get("ultima_operacion")}


def resolver(numero, estado):
    if numero not in PREGUNTAS:
        raise C.ErrorConsulta("Pregunta no válida")
    cfg = PREGUNTAS[numero]
    base = filtros_globales(cfg, estado)
    estado = estado or {}
    return {
        "pregunta": numero,
        "seleccion": describir(cfg, base, estado),
        "kpis": kpis(numero, base),
        "g1": grafico(cfg["g1"], base, estado.get("g1")),
        "g2": grafico(cfg["g2"], base, estado.get("g2")),
        "matriz": matriz(cfg["matriz"], base, estado.get("matriz")),
    }


def opciones_filtros(numero):
    cfg = PREGUNTAS[numero]
    return [{**f, "valores": [_texto(v) if not isinstance(v, int) else v for v in C.miembros(f["dim"], f["nivel"])]}
            for f in cfg["filtros"]]
