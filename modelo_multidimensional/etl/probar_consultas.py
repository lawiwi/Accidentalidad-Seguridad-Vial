"""Ejecuta modelo_multidimensional/sql/consultas_prueba_sqlite.sql sobre la réplica SQLite y muestra cada resultado."""
import os
import re
import sqlite3

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cn = sqlite3.connect(os.path.join(RAIZ, "dw", "dw_accidentalidad_vial.sqlite"))
texto = open(os.path.join(RAIZ, "sql", "consultas_prueba_sqlite.sql"), encoding="utf-8").read()
for bloque in texto.split(";"):
    titulo = re.findall(r"-- (T\d.*)", bloque)
    consulta = re.sub(r"--[^\n]*", "", bloque).strip()
    if consulta:
        print(titulo[-1] if titulo else "", "=>", cn.execute(consulta).fetchall())
