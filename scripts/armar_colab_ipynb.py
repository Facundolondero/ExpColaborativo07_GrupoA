# -*- coding: utf-8 -*-
"""Arma el notebook de Colab (kernel R, para Colab: Archivo > Subir notebook) a partir de exp07_grupoA_colab.R.
   Parte el script en sus secciones (los banners '# ====') y reemplaza el encabezado por celdas de texto.

   python armar_colab_ipynb.py              -> exp07_grupoA_colab.ipynb
   python armar_colab_ipynb.py --francisco  -> exp07_grupoA_colab_Francisco.ipynb y .R: el mismo codigo ya en modo
                                               "full" y con subir_kaggle TRUE, con el vector de semillas vacio para
                                               que Francisco ponga sus 5
   --concatenado <ruta.R>  deja ademas todas las celdas de codigo juntas en un .R, para probar que el notebook corre igual
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
args = sys.argv[1:]
francisco = "--francisco" in args
concatenado = Path(args[args.index("--concatenado") + 1]) if "--concatenado" in args else None

texto = (BASE / "exp07_grupoA_colab.R").read_text(encoding="utf-8")


def reemplazar(t, viejo, nuevo):
    assert t.count(viejo) == 1, (t.count(viejo), viejo[:60])
    return t.replace(viejo, nuevo)


if francisco:
    texto = reemplazar(texto, "# Modalidad Gerencial - Grupo A - Facundo Londero\n",
                       "# Modalidad Gerencial - Grupo A - Facundo Londero y Francisco Medina Raed\n"
                       "# Copia para que Francisco corra sus 5 semillas: ya esta en modo \"full\" y con subir_kaggle TRUE,\n"
                       "# solo hay que completar el vector semillas.\n")
    texto = reemplazar(texto, "4 variantes del primer mes de training y 10 semillas.",
                       "4 variantes del primer mes de training y 10 semillas (5 de cada integrante).")
    texto = reemplazar(texto, "4 variantes x 10 semillas = 40 corridas", "4 variantes x 5 semillas = 20 corridas")
    texto = reemplazar(texto, 'modo <- "test"           # "test" o "full"', 'modo <- "full"           # "test" o "full"')
    texto = reemplazar(texto, "subir_kaggle <- FALSE    #", "subir_kaggle <- TRUE     #")
    texto = reemplazar(
        texto,
        "# semillas: las mismas 10 en las 4 variantes, porque la comparacion es pareada por semilla\n"
        "semillas <- c(553897, 761897, 815197, 906187, 919531,\n"
        "              150001, 222247, 199999, 777781, 999983)\n",
        "# semillas: las 5 primigenias de Francisco, las mismas en las 4 variantes, porque la comparacion es pareada por semilla\n"
        "semillas <- c(                                        )   # <- completar con tus 5 semillas\n"
        'if (length(semillas) == 0) stop("Falta completar el vector semillas con tus 5 semillas")\n',
    )
    (BASE / "exp07_grupoA_colab_Francisco.R").write_text(texto, encoding="utf-8")
    salida = BASE / "exp07_grupoA_colab_Francisco.ipynb"
else:
    salida = BASE / "exp07_grupoA_colab.ipynb"

# saco el encabezado de comentarios: el codigo empieza en "modo <- "
codigo = texto[texto.index("modo <- "):]

# partes separadas por los banners de seccion
banner = re.compile(r"# =+\n#  [^\n]*\n# =+\n")
partes = [p.strip("\n") + "\n" for p in banner.split(codigo)]
assert len(partes) == 5, len(partes)

titulo = "# Experimento Colaborativo #07: Utilización de los meses de pandemia\n"
if francisco:
    intro = titulo + """Modalidad Gerencial, Grupo A. Facundo Londero y Francisco Medina Raed.

Es el workflow **z610** de la cátedra tal cual, corrido para 4 variantes del primer mes de training y 10 semillas, 5 de cada integrante. Validation 202107, entrenamiento final hasta 202107 y future 202109 (Kaggle). En cada corrida se vuelve a hacer el grid search completo."""
    como_correrlo = """**Cómo correrlo:** el entorno de ejecución tiene que ser **R**. Esta copia ya está en modo `"full"` y con `subir_kaggle <- TRUE`: corre las 20 corridas de tus 5 semillas y sube a Kaggle los 6 archivos de cada una apenas termina. Si una subida falla, por ejemplo porque se agotó el cupo de 100 envíos por día, queda anotada en `pendientes_kaggle.txt` y se reintenta al volver a correr la celda de las corridas. Lo único que hay que completar es el vector `semillas`, al principio de la primera celda de código. Necesita tu `kaggle.json`: lo copia la celda de arranque del z610, o se sube a `/content/` con el panel de archivos de la izquierda. La primera vez instala LightGBM, que tarda unos 7 minutos. Para que las corridas queden en el Drive y se puedan retomar, correr antes las dos celdas de arranque del z610 con el entorno en Python. La última celda baja tus puntajes de Kaggle y deja `puntajes_kaggle.csv`, que es el archivo para mandarle a Facundo."""
else:
    intro = titulo + """Modalidad Gerencial, Grupo A. Facundo Londero.

Es el workflow **z610** de la cátedra tal cual, corrido para 4 variantes del primer mes de training y 10 semillas. Validation 202107, entrenamiento final hasta 202107 y future 202109 (Kaggle). En cada corrida se vuelve a hacer el grid search completo."""
    como_correrlo = """**Cómo correrlo:** el entorno de ejecución tiene que ser **R**. Con `modo <- "test"` es una prueba de 2 minutos; con `"full"` son las 40 corridas (en Colab conviene de a una semilla). Con `subir_kaggle <- TRUE` sube a Kaggle los 6 archivos de cada corrida apenas termina; si una subida falla, queda anotada en `pendientes_kaggle.txt` y se reintenta al volver a correr la celda de las corridas. La primera vez instala LightGBM, que tarda unos 7 minutos. Para que los resultados queden en el Drive, correr antes las dos celdas de arranque del z610 con el entorno en Python."""

md = [
    intro + """

| Variante | Primer mes de training | Meses de training |
|---|---|---|
| V0 línea base (todos los meses) | 202005 | 14 |
| V1 sin ASPO | 202011 | 8 |
| V2 solo 2021 | 202101 | 6 |
| V3 últimos cuatro meses | 202103 | 4 |

Una diferencia con el notebook, igual en las cuatro variantes: el modelo final usa `modifyList(fijos, mejores)` en vez de `c(fijos, mejores)`. Con `c()` quedan num_leaves y min_data_in_leaf duplicados, LightGBM se queda con el primero (64 y 128) e ignora lo que eligió el grid search.

Por corrida se suben a Kaggle 6 cortes, los del notebook de a 100 (800, 900, 1000, 1100, 1200 y 1300 envíos). La ganancia de cada corrida es el promedio Public de esos 6 cortes.

""" + como_correrlo,
    """## Preprocesamiento
Idéntico al z610: Catastrophe Analysis de 202006, FE intra-mes y lags y deltas de orden 1 y 2.""",
    """## Modelado y producción para una variante y una semilla
Training strategy, grid search de 20 combinaciones, modelo final, predicción de 202109 y los 6 archivos para Kaggle.""",
    """## Corridas
Todas las variantes por todas las semillas, con la semilla afuera y la variante adentro. Saltea las corridas que ya tienen su PARAM.yml y, antes de empezar, reintenta las subidas a Kaggle que hayan quedado pendientes.""",
    """## Puntajes de Kaggle y test de Wilcoxon
Baja de Kaggle los puntajes de los envíos del experimento y, para cada semilla y variante, calcula la ganancia como el promedio Public de los 6 cortes. Solo entran las corridas que ya tienen los 6 cortes puntuados.

Después compara cada recorte con V0 de a pares por semilla, con el test de Wilcoxon de rangos con signo. La regla quedó fijada antes de ver resultados: un recorte es mejor que V0 si el Wilcoxon da p < 0,05 a su favor. Si gana alguno, la recomendación es entrenar desde su primer mes (si ganan dos, el de mayor diferencia promedio); si no gana ninguno, con todos los meses.

Necesita el `kaggle.json`: lo copia la celda de arranque del z610, o se toma de `/content/buckets/b1/kaggle/` o de `/content/` (subiéndolo con el panel de archivos de la izquierda). Esta celda se puede correr sola, después de la primera celda de código.""",
]


def celda(tipo, fuente):
    lineas = fuente.splitlines(keepends=True)
    c = {"cell_type": tipo, "metadata": {}, "source": lineas}
    if tipo == "code":
        c["execution_count"] = None
        c["outputs"] = []
    return c


celdas = []
for m, p in zip(md, partes):
    celdas.append(celda("markdown", m))
    celdas.append(celda("code", p.rstrip("\n")))

nb = {
    "cells": celdas,
    "metadata": {
        "colab": {"provenance": []},
        "kernelspec": {"name": "ir", "display_name": "R", "language": "R"},
        "language_info": {"name": "R"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}
salida.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
if concatenado:
    concatenado.write_text("\n".join(p for p in partes), encoding="utf-8")
print("celdas:", len(celdas), "->", salida)
