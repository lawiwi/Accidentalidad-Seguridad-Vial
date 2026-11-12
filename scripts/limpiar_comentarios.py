"""
Etapa 6 · Preparación de los comentarios para Orange.

Ubicación: scripts/limpiar_comentarios.py      Uso (desde la raíz): python scripts/limpiar_comentarios.py
Entrada : data/youtube/comentarios_crudos.csv        (descargado del cuaderno de Colab; no se publica)
Salidas : data/orange/comentarios_limpios.tab        ← corpus para Orange (Corpus widget)
          data/youtube/comentarios_descartados.csv   ← registro auditable de cada descarte (no se publica)
          data/youtube/reporte_calidad.json          ← conteos por paso para el informe

Decisiones de limpieza (en este orden; cada comentario descartado guarda el motivo):
  1. Vacíos o solo espacios.
  2. Normalización: Unicode NFC, entidades HTML, saltos de línea, URLs → «URL», menciones @usuario → «@usuario»,
     marcas de tiempo (03:15) → «TIEMPO». Los emojis se cuentan y se retiran del texto analizado.
  3. Duplicados exactos (mismo texto normalizado en el mismo video) y copias del mismo autor en varios videos.
  4. Spam / contenido irrelevante: enlaces promocionales, «suscríbete», sorteos, cripto, «primero/first», etc.
  5. Muy cortos: menos de 3 palabras con letras (no aportan contenido analizable: «jaja», «amén», «😢»).
  6. Idioma: se conservan los comentarios en español; se descartan los demás (se registran).
Además se añaden variables de apoyo para el análisis (longitud, signos de exclamación, mayúsculas) y
banderas temáticas (0/1) a partir de léxicos que conectan los comentarios con las variables del proyecto.
"""
import csv
import html
import json
import os
import re
import unicodedata
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
YT = os.path.join(RAIZ, "data", "youtube")
ENTRADA = os.path.join(YT, "comentarios_crudos.csv")
SALIDA_TAB = os.path.join(RAIZ, "data", "orange", "comentarios_limpios.tab")

URL = re.compile(r"(https?://\S+|www\.\S+)", re.I)
MENCION = re.compile(r"@[\w.\-]+")
TIEMPO = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF‍️]")
PALABRA = re.compile(r"[a-záéíóúüñ]+", re.I)
SPAM = re.compile(r"(suscr[ií]bete|suscribanse|s[ií]gueme|mi canal|visita mi|whatsapp\s*\+?\d|gana dinero|"
                  r"invierte|bitcoin|cripto|forex|sorteo|promo(ci[oó]n)?\b|^\s*(primero|first|1ro)\s*!*\s*$)", re.I)

# Palabras muy frecuentes del español: sirven para estimar el idioma sin librerías externas.
STOP_ES = set("""de la que el en y a los se del las un por con no una su para es al lo como más pero sus le ya o
este sí porque esta entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante todos uno les
ni contra otros ese eso ante ellos e esto mí antes algunos qué unos yo otro otras otra él tanto esa estos mucho
quienes nada muchos cual poco ella estar estas algunas algo nosotros mi mis tú te ti tu tus ellas nosotras vosotros
fue era son hace hacen van va ser está están tiene tienen pues así eso esos esas aquí allá gente vía""".split())
STOP_EN = set("the and is are was were this that with for you they have has not but what from your just like".split())

# Léxicos temáticos: cada tema se relaciona con una variable o hallazgo de los datos originales.
TEMAS = {
    "tema_motos": r"\bmoto(s|cicleta|ciclista|ciclistas|taxi)?\b|\bmotero|\bmotorizad|\bparrillero|\bdomiciliari",
    "tema_carga": r"tractomula|\bmula(s)?\b|tractocami[oó]n|cami[oó]n|volqueta|carga pesada|camionero|sobrepeso|cisterna|furg[oó]n",
    "tema_infraestructura": r"\bv[ií]a(s)?\b|carretera|hueco|bache|curva|se[ñn]alizaci|alumbrado|puente|t[uú]nel|doble calzada|peaje|berma|concesi",
    "tema_control_autoridad": r"polic[ií]a|tr[aá]nsito|agente|multa|comparendo|fotomulta|control|ret[eé]n|corrupc|mordida|soborno|ditra|autoridad",
    "tema_mantenimiento_antiguedad": r"frenos?|llanta|mantenimiento|t[eé]cnico.?mec[aá]nica|tecnomec|revisi[oó]n|viejo|chatarra|modelo|repuesto|falla mec",
    "tema_educacion_licencia": r"pase\b|licencia|escuela|curso|examen|educaci[oó]n|cultura|conciencia|no saben manejar",
    "tema_imprudencia": r"imprudent|irresponsab|velocidad|adelant|zigzag|piques|borrach|ebri|alcohol|celular|semáforo|sem[aá]foro|contrav[ií]a|afán|afan",
    "tema_soat_costos": r"\bsoat\b|seguro|aseguradora|costo|precio|impuesto|plata",
    "tema_victimas_familia": r"\bdep\b|descanse en paz|q\.?e\.?p\.?d|condolencia|familia|madre|padre|hijo|hija|dolor|fortaleza|que dios",
    "tema_justicia": r"c[aá]rcel|fiscal[ií]a|justicia|pena|condena|impunidad|ley\b|leyes|congreso|gobierno|alcald",
}
TEMAS = {k: re.compile(v, re.I) for k, v in TEMAS.items()}


def normalizar(texto):
    t = unicodedata.normalize("NFC", html.unescape(texto or ""))
    t = t.replace("\r", " ").replace("\n", " ")
    t = URL.sub(" URL ", t)
    t = MENCION.sub(" @usuario ", t)
    t = TIEMPO.sub(" TIEMPO ", t)
    n_emojis = len(EMOJI.findall(t))
    t = EMOJI.sub(" ", t)
    t = re.sub(r"(.)\1{3,}", r"\1\1\1", t)  # «noooooo» → «nooo»
    return re.sub(r"\s+", " ", t).strip(), n_emojis


def idioma(texto):
    palabras = [p.lower() for p in PALABRA.findall(texto)]
    if not palabras:
        return "indeterminado"
    es = sum(p in STOP_ES for p in palabras) / len(palabras)
    en = sum(p in STOP_EN for p in palabras) / len(palabras)
    if en > es and en >= 0.15:
        return "en"
    if es >= 0.08 or re.search(r"[ñáéíóú¿¡]", texto, re.I):
        return "es"
    return "es" if len(palabras) <= 6 else "otro"   # textos cortos sin marcadores: se asumen en español


def main():
    with open(ENTRADA, encoding="utf-8-sig") as f:
        crudos = list(csv.DictReader(f))
    conteo = Counter({"0_crudos": len(crudos)})
    vistos_video, vistos_autor, limpios, descartes = set(), {}, [], []

    for c in crudos:
        texto, n_emo = normalizar(c["texto"])
        motivo = None
        clave = (c["video_id"], texto.lower())
        n_pal = len(PALABRA.findall(texto))
        if not texto or texto in ("URL", "@usuario"):
            motivo = "1_vacio"
        elif clave in vistos_video:
            motivo = "3_duplicado_mismo_video"
        elif c["autor_hash"] and (c["autor_hash"], texto.lower()) in vistos_autor and n_pal >= 3:
            motivo = "3_copia_mismo_autor_otro_video"
        elif SPAM.search(texto) or texto.count("URL") >= 2:
            motivo = "4_spam_o_promocion"
        elif n_pal < 3:
            motivo = "5_muy_corto"
        else:
            lang = idioma(texto)
            if lang != "es":
                motivo = f"6_idioma_{lang}"
        vistos_video.add(clave)
        if c["autor_hash"]:
            vistos_autor[(c["autor_hash"], texto.lower())] = c["video_id"]
        if motivo:
            conteo[motivo] += 1
            descartes.append({"comentario_id": c["comentario_id"], "video_id": c["video_id"], "motivo": motivo, "texto": c["texto"][:300]})
            continue
        fila = {
            "texto": texto, "video_id": c["video_id"], "eje": c["eje"],
            "tipo": "respuesta" if c["es_respuesta"] == "1" else "comentario",
            "anio": c["publicado"][:4], "likes": int(c["likes"] or 0), "palabras": n_pal,
            "emojis": n_emo, "exclamaciones": texto.count("!"),
            "pct_mayusculas": round(100 * sum(ch.isupper() for ch in texto) / max(1, sum(ch.isalpha() for ch in texto)), 1),
            "comentario_id": c["comentario_id"],
        }
        for tema, rx in TEMAS.items():
            fila[tema] = int(bool(rx.search(texto)))
        fila["n_temas"] = sum(fila[t] for t in TEMAS)
        limpios.append(fila)
    conteo["9_limpios"] = len(limpios)

    # ---- Corpus para Orange (.tab con 3 filas de encabezado) ----
    os.makedirs(os.path.dirname(SALIDA_TAB), exist_ok=True)
    cols = ["eje", "tipo", "anio", "likes", "palabras", "emojis", "exclamaciones", "pct_mayusculas", *TEMAS, "n_temas",
            "texto", "video_id", "comentario_id"]
    tipos = {c: "c" for c in cols}
    tipos.update(eje="d", tipo="d", anio="d", texto="s", video_id="d", comentario_id="s")
    for t in TEMAS:
        tipos[t] = "d"
    roles = {c: "" for c in cols}
    roles.update(texto="meta include=True", video_id="meta", comentario_id="meta")
    with open(SALIDA_TAB, "w", encoding="utf-8", newline="") as f:
        f.write("\t".join(cols) + "\n" + "\t".join(tipos[c] for c in cols) + "\n" + "\t".join(roles[c] for c in cols) + "\n")
        for r in limpios:
            # Las comillas dobles se cambian por simples: Orange lee el .tab con reglas de CSV y una comilla
            # suelta uniría varias filas en una sola.
            f.write("\t".join(str(r[c]).replace("\t", " ").replace('"', "'") for c in cols) + "\n")

    with open(os.path.join(YT, "comentarios_descartados.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["comentario_id", "video_id", "motivo", "texto"])
        w.writeheader(); w.writerows(descartes)
    por_eje = Counter(r["eje"] for r in limpios)
    por_video = Counter(r["video_id"] for r in limpios)
    temas = {t: sum(r[t] for r in limpios) for t in TEMAS}
    reporte = {"pasos": dict(sorted(conteo.items())), "limpios_por_eje": dict(por_eje),
               "limpios_por_video": dict(por_video.most_common()),
               "comentarios_con_tema": {t: {"n": n, "pct": round(100 * n / max(1, len(limpios)), 1)} for t, n in temas.items()},
               "sin_tema": sum(r["n_temas"] == 0 for r in limpios)}
    with open(os.path.join(YT, "reporte_calidad.json"), "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    print(json.dumps(reporte["pasos"], ensure_ascii=False, indent=1))
    print("Corpus para Orange:", os.path.normpath(SALIDA_TAB))


if __name__ == "__main__":
    main()
