"""
Pruebas de la sección Análisis multidimensional (Etapa 5).

Ejecutar desde la raíz del repositorio:
    pip install pytest
    pytest -q tests/test_multidimensional.py

Requiere la base modelo_multidimensional/dw/dw_accidentalidad_vial.sqlite
(se genera con: python modelo_multidimensional/etl/construir_dw.py).
Los valores esperados son los obtenidos con los datos tratados de la Etapa 3
(respaldo FILE = 3, tabla dbo.Vehiculo, 406.540 filas).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from multidimensional import conocimientos as K  # noqa: E402
from multidimensional import cubo as C  # noqa: E402
from multidimensional import preguntas as P  # noqa: E402

TOTAL = 406540


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ------------------------------------------------------------------ navegación
@pytest.mark.parametrize("url", ["/", "/health", "/Etapa1", "/Etapa2", "/Etapa3", "/Etapa4",
                                 "/analisis-multidimensional/"] +
                         [f"/analisis-multidimensional/pregunta/{n}" for n in range(1, 5)])
def test_paginas_responden(client, url):
    assert client.get(url).status_code == 200


def test_menu_tiene_opcion_nueva(client):
    html = client.get("/").data.decode("utf-8")
    assert "Análisis multidimensional" in html
    assert "Conocimiento evidente" in html          # no se reemplazó la opción anterior


def test_pregunta_inexistente(client):
    assert client.get("/analisis-multidimensional/pregunta/9").status_code == 404


# ------------------------------------------------------------------ secciones del recorrido
SECCIONES = ["contexto", "modelo", "dimensiones", "medidas", "operaciones",
             "validacion", "conocimientos", "conclusiones"]


@pytest.mark.parametrize("slug", SECCIONES)
def test_secciones_responden_y_navegan(client, slug):
    resp = client.get(f"/analisis-multidimensional/seccion/{slug}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert 'aria-current="page"' in html                       # la sección actual se marca
    for otra in SECCIONES:                                       # se puede saltar a cualquier otra
        assert f"/analisis-multidimensional/seccion/{otra}" in html


def test_mapa_enlaza_secciones_y_preguntas(client):
    html = client.get("/analisis-multidimensional/").data.decode("utf-8")
    for slug in SECCIONES:
        assert f"/analisis-multidimensional/seccion/{slug}" in html
    for n in range(1, 5):
        assert f"/analisis-multidimensional/pregunta/{n}" in html


def test_seccion_inexistente(client):
    assert client.get("/analisis-multidimensional/seccion/otra").status_code == 404


def test_secciones_muestran_datos_del_modelo(client):
    dims = client.get("/analisis-multidimensional/seccion/dimensiones").data.decode("utf-8")
    assert "DimAntiguedad" in dims and "Grupo > Rango > Años" in dims
    con = client.get("/analisis-multidimensional/seccion/conocimientos").data.decode("utf-8")
    assert con.count("<tr><td>C") == 8                          # los ocho conocimientos


# ------------------------------------------------------------------ modelo
def test_total_y_medidas_basicas():
    t, _ = C.total()
    assert t["n"] == TOTAL
    assert t["m"] == 20659
    assert C.mediana_edad() == 6                     # coincide con la Etapa 4


def test_rollup_coherente_en_tiempo():
    anios, _ = C.agregar([("tiempo", "anio")])
    meses, _ = C.agregar([("tiempo", "mes")])
    assert sum(f["n"] for f in anios) == sum(f["n"] for f in meses) == TOTAL
    a2024 = next(f for f in anios if f["claves"][0] == 2024)
    assert a2024["n"] == sum(f["n"] for f in meses if str(f["claves"][0]).startswith("2024-")) == 120342


def test_porcentaje_se_recalcula_y_no_se_suma():
    tipos, _ = C.agregar([("tipo", "categoria"), ("tipo", "tipo")])
    carga = [f for f in tipos if f["claves"][0] == "Vehículo de carga"]
    cat, _ = C.agregar([("tipo", "categoria")], {("tipo", "categoria"): ["Vehículo de carga"]})
    esperado = sum(f["m"] for f in carga) / sum(f["n"] for f in carga)
    assert abs(cat[0]["pct_con_muertos"] - esperado) < 1e-12
    assert abs(cat[0]["pct_con_muertos"] - sum(f["pct_con_muertos"] for f in carga)) > 0.01


def test_promedio_ponderado_de_edad():
    grupos, _ = C.agregar([("antiguedad", "grupo")])
    total, _ = C.total()
    ponderado = sum(f["se"] for f in grupos) / sum(f["ce"] for f in grupos)
    assert abs(ponderado - total["edad_promedio"]) < 1e-9


# ------------------------------------------------------------------ operaciones vía API
def _api(client, n, estado):
    r = client.post(f"/analisis-multidimensional/api/pregunta/{n}", json=estado)
    assert r.status_code == 200, r.json
    return r.json


def test_drill_down_y_roll_up(client):
    base = _api(client, 1, {})
    assert base["g1"]["nivel"] == "anio" and len(base["g1"]["etiquetas"]) == 5
    abajo = _api(client, 1, {"g1": {"nivel": "mes", "ruta": [{"nivel": "anio", "valor": 2024}]}})
    assert abajo["g1"]["etiquetas"][0] == "2024-01" and len(abajo["g1"]["etiquetas"]) == 12
    assert sum(abajo["g1"]["datasets"][0]["data"]) == 120342
    arriba = _api(client, 1, {"g1": {"nivel": "anio", "ruta": []}})
    assert arriba["g1"]["etiquetas"] == base["g1"]["etiquetas"]


def test_slice_y_dice(client):
    s = _api(client, 4, {"filtros": {"tipo": ["Motocicleta"]}})
    assert "Slice" in s["seleccion"]["operaciones"] and s["kpis"][0]["valor"] > 0.83
    d = _api(client, 2, {"filtros": {"region": ["Caribe"], "anio": [2024]}})
    assert "Dice" in d["seleccion"]["operaciones"]
    assert d["matriz"]["n_total"] == 8163


def test_pivot_intercambia_y_recalcula(client):
    normal = _api(client, 3, {"matriz": {"metrica": "pct_fila"}})
    pivot = _api(client, 3, {"matriz": {"metrica": "pct_fila", "pivot": True}})
    assert normal["matriz"]["filas"] == pivot["matriz"]["columnas"]
    assert normal["matriz"]["columnas"] == pivot["matriz"]["filas"]
    assert all(abs(t - 1.0) < 1e-9 for t in pivot["matriz"]["total_fila"])
    assert normal["matriz"]["valores"][0][0] != pivot["matriz"]["valores"][0][0]


def test_parametros_no_permitidos(client):
    r = client.post("/analisis-multidimensional/api/pregunta/2", json={"g1": {"nivel": "x; DROP TABLE"}})
    assert r.status_code == 400


def test_cada_vista_tiene_tres_kpis_dos_graficos_y_matriz(client):
    for n in range(1, 5):
        r = _api(client, n, {})
        assert len(r["kpis"]) == 3
        assert r["g1"]["etiquetas"] and r["g2"]["etiquetas"]
        assert r["matriz"]["filas"] and r["matriz"]["columnas"]


def test_las_cuatro_preguntas_usan_todas_las_dimensiones():
    usadas = set()
    for cfg in P.PREGUNTAS.values():
        usadas.update(cfg["dimensiones"])
        assert len(cfg["dimensiones"]) >= 2
        assert len({f["dim"] for f in cfg["filtros"]}) == 2
    assert usadas == set(C.DIMENSIONES)


# ------------------------------------------------------------------ conocimientos
def test_ocho_conocimientos_completos():
    ks = K.calcular()
    assert len(ks) == 8
    for k in ks:
        for campo in ["pregunta", "dimensiones", "procedimiento", "evidencia", "hallazgo",
                      "interpretacion", "utilidad", "limitacion"]:
            assert k[campo]
    assert sorted(k["pregunta_n"] for k in ks) == [1, 1, 2, 2, 3, 3, 4, 4]


def test_valores_de_los_conocimientos():
    v = {k["id"]: k["valores"] for k in K.calcular()}
    assert v[1] == {"jul_total": 28794, "med_jul": 22667, "ant_jul": 23553}
    assert v[2] == {"t24": 120342, "t25": 57867, "m24": 44092, "m25": 5}
    assert round(v[3]["pct_carga"], 4) == 0.2110 and round(v[3]["pct_moto"], 4) == 0.0484
    assert round(v[4]["andina"], 4) == 0.0354 and round(v[4]["caribe"], 4) == 0.1162
    assert round(v[5]["g1"], 4) == 0.0463 and round(v[5]["g3"], 4) == 0.0704
    assert v[6] == {"med_moto": 4, "med_carga": 11}
    assert round(v[7]["moto"], 4) == 0.8339 and round(v[7]["carga"], 4) == 0.2986
    assert round(v[8]["b_pct"], 4) == 0.0549 and round(v[8]["k_pct"], 4) == 0.0168
