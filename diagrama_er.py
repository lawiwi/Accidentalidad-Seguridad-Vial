import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ============================================================
# CONFIGURACIÓN
# ============================================================

fig, ax = plt.subplots(figsize=(16, 10))

ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis("off")

# ============================================================
# FUNCIÓN PARA CREAR ENTIDADES
# ============================================================

def crear_entidad(x, y, ancho, alto, titulo, atributos, color):
    # Caja principal
    caja = FancyBboxPatch(
        (x, y),
        ancho,
        alto,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.8,
        edgecolor="black",
        facecolor="white"
    )

    ax.add_patch(caja)

    # Encabezado
    encabezado = FancyBboxPatch(
        (x, y + alto - 0.7),
        ancho,
        0.7,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=0,
        facecolor=color
    )

    ax.add_patch(encabezado)

    # Título
    ax.text(
        x + ancho / 2,
        y + alto - 0.35,
        titulo,
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color="white"
    )

    # Atributos
    posicion_y = y + alto - 1.05

    for atributo, tipo in atributos:
        if tipo == "PK":
            texto = f"🔑 PK   {atributo}"
            peso = "bold"
        elif tipo == "FK":
            texto = f"🔗 FK   {atributo}"
            peso = "bold"
        else:
            texto = f"       {atributo}"
            peso = "normal"

        ax.text(
            x + 0.25,
            posicion_y,
            texto,
            ha="left",
            va="top",
            fontsize=10.5,
            fontweight=peso
        )

        posicion_y -= 0.43


# ============================================================
# ENTIDAD SINIESTRO
# ============================================================

atributos_siniestro = [
    ("id_siniestro", "PK"),
    ("fecha_hecho", ""),
    ("mes", ""),
    ("departamento", ""),
    ("municipio", ""),
    ("ubicacion", ""),
    ("latitud", ""),
    ("longitud", ""),
    ("hipotesis", ""),
    ("medio_conocimiento", ""),
    ("muertos", ""),
    ("lesionados", ""),
    ("total_victimas", ""),
    ("clasificacion", "")
]

crear_entidad(
    0.5,
    2.0,
    4.2,
    7.0,
    "SINIESTRO",
    atributos_siniestro,
    "#2F5597"
)


# ============================================================
# ENTIDAD SINIESTRO_VEHICULO
# ============================================================

atributos_relacion = [
    ("id_relacion", "PK"),
    ("id_siniestro", "FK"),
    ("id_vehiculo", "FK"),
    ("nivel_coincidencia", ""),
    ("criterios_coincidentes", "")
]

crear_entidad(
    5.9,
    3.0,
    4.2,
    5.0,
    "SINIESTRO_VEHICULO",
    atributos_relacion,
    "#C55A11"
)


# ============================================================
# ENTIDAD VEHICULO
# ============================================================

atributos_vehiculo = [
    ("id_vehiculo", "PK"),
    ("marca", ""),
    ("modelo", ""),
    ("tipo_vehiculo", ""),
    ("edad_vehiculo", ""),
    ("fecha_accidente", ""),
    ("gravedad", ""),
    ("departamento", ""),
    ("municipio", ""),
    ("autoridad_transito", "")
]

crear_entidad(
    11.3,
    2.0,
    4.2,
    7.0,
    "VEHICULO",
    atributos_vehiculo,
    "#548235"
)


# ============================================================
# RELACIÓN SINIESTRO → SINIESTRO_VEHICULO
# ============================================================

ax.annotate(
    "",
    xy=(5.9, 5.5),
    xytext=(4.7, 5.5),
    arrowprops=dict(
        arrowstyle="-",
        linewidth=2,
        color="black"
    )
)

ax.text(
    5.15,
    5.75,
    "1",
    fontsize=13,
    fontweight="bold",
    ha="center"
)

ax.text(
    5.55,
    5.75,
    "N",
    fontsize=13,
    fontweight="bold",
    ha="center"
)


# ============================================================
# RELACIÓN SINIESTRO_VEHICULO → VEHICULO
# ============================================================

ax.annotate(
    "",
    xy=(11.3, 5.5),
    xytext=(10.1, 5.5),
    arrowprops=dict(
        arrowstyle="-",
        linewidth=2,
        color="black"
    )
)

ax.text(
    10.45,
    5.75,
    "N",
    fontsize=13,
    fontweight="bold",
    ha="center"
)

ax.text(
    10.85,
    5.75,
    "1",
    fontsize=13,
    fontweight="bold",
    ha="center"
)


# ============================================================
# TÍTULO
# ============================================================

ax.text(
    8,
    9.65,
    "MODELO ENTIDAD-RELACIÓN",
    ha="center",
    va="center",
    fontsize=21,
    fontweight="bold"
)

ax.text(
    8,
    9.25,
    "Accidentalidad y Seguridad Vial",
    ha="center",
    va="center",
    fontsize=13
)


# ============================================================
# LEYENDA
# ============================================================

ax.text(
    8,
    0.65,
    "PK = Clave primaria     FK = Clave foránea     1:N = Cardinalidad",
    ha="center",
    fontsize=10
)


# ============================================================
# GUARDAR
# ============================================================

plt.savefig(
    "diagrama_ER_accidentalidad.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print("Diagrama generado correctamente.")
print("Archivo: diagrama_ER_accidentalidad.png")