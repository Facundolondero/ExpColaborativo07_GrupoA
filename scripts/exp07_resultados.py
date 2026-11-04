# -*- coding: utf-8 -*-
"""Resultados del Experimento 07 (Grupo A): tablas y graficos a partir de los puntajes de Kaggle ya bajados.

  python exp07_resultados.py      lee puntajes_kaggle_*.csv (lo que bajo exp07_bajar_puntajes.py), se queda con las
                                  semillas del vector del experimento (SEMILLAS_VECTOR en exp07_bajar_puntajes.py) y
                                  deja todo en resultados/

La ganancia de cada corrida es METRICA: el maximo Public de los 6 cortes, criterio de la catedra; el promedio queda
como chequeo. Mientras el vector tenga menos de 10 semillas, todo sale marcado como provisorio.

Salidas en resultados/:
  tabla_semilla_variante.csv   ganancia de cada corrida (METRICA) por semilla y variante,
                               diferencias contra V0, y las filas promedio y desvio
  tabla_variantes.csv          por variante: media, desvio, diferencia pareada contra V0, semillas que superan a V0,
                               p del Wilcoxon exacto a dos colas y veredicto (pendiente mientras falten semillas)
  tabla_cortes.csv             por variante y corte: media, desvio, minimo y maximo entre semillas
  chequeo_promedio.csv         como tabla_variantes pero con la otra metrica (el promedio de los 6 cortes de cada
                               corrida; si METRICA = "mean", es el maximo y se llama chequeo_maximo.csv)
  pairwise_holm.csv            las 6 comparaciones pareadas entre las 4 variantes con correccion de Holm (todos contra
                               todos, como pairwise.wilcox.test(paired = TRUE) de R; V0 es una variante mas)
  meta.json                    metrica usada, cantidad de semillas y si es provisorio (lo lee slides/build_pptx_final.py)
  curvas_por_corte.png         ganancia media por corte, una curva por variante
  dispersion_por_variante.png  un panel por variante con la curva de cada semilla, el promedio y el promedio de V0
  diferencias_vs_V0.png        diferencia de cada recorte contra V0, semilla por semilla
  resumen.txt                  lo que imprime el script
"""
import itertools
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import BoxStyle, FancyBboxPatch, Patch, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exp07_bajar_puntajes import (BASE, CARPETA_PUNTAJES, CORTES, ORDEN_VARIANTES, PRIMER_MES,  # noqa: E402
                                  SEMILLAS_VECTOR, wilcoxon_p)

SALIDA = BASE / "resultados"
RECORTES = [v for v in ORDEN_VARIANTES if v != "V0_todo"]

# Metrica de cada corrida: "mean" = promedio Public de los 6 cortes (lo que dice el diseño aprobado) o "max" = mejor
# corte (lo que la catedra usa en Kaggle, Clase 08). La otra se calcula igual, como chequeo.
METRICA = "max"   # 02-nov: la catedra fija en Zulip que en Kaggle la ganancia de la corrida es el maximo del Public
OTRA = "max" if METRICA == "mean" else "mean"
DESCRIPCION = {"mean": "promedio Public de los 6 cortes", "max": "máximo Public de los 6 cortes"}
ETIQUETA = {"V0_todo": "V0 todos los meses", "V1_sinASPO": "V1 sin ASPO",
            "V2_2021": "V2 solo 2021", "V3_ultimos4": "V3 últimos cuatro meses"}
CORTA = {v: v.split("_")[0] for v in ORDEN_VARIANTES}

# Estetica del deck del Grupo A: fondo azul 002846, Calibri, amarillo para resaltar. V0 es la linea base y va en gris
# claro; los tres recortes llevan los tres primeros colores categoricos de la paleta de referencia (azul, naranja,
# aqua), validados sobre este fondo: pasan los chequeos de daltonismo y de contraste con todos los pares.
FONDO = "#002846"
COLOR = {"V0_todo": "#c3c2b7", "V1_sinASPO": "#3987e5", "V2_2021": "#d95926", "V3_ultimos4": "#199e70"}
TINTA, TINTA2, TINTA_SUAVE = "#f0efec", "#c3c2b7", "#8f9bab"
GRILLA, EJE = "#143b60", "#2e5a85"

plt.rcParams.update({
    "font.family": "Calibri", "font.size": 11,
    "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "axes.edgecolor": EJE, "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "text.color": TINTA, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRILLA, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "legend.frameon": False, "legend.fontsize": 10.5, "axes.titlesize": 11.5, "axes.labelsize": 10.5,
    "xtick.labelsize": 10, "ytick.labelsize": 10,
})


def miles(x):
    return f"{int(x):,}".replace(",", ".")


def coma(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def estilo(ax):
    ax.set_axisbelow(True)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_linewidth(0.8)
    ax.tick_params(length=3, width=0.8)


def marcador(**extra):
    """Marcador grande con un anillo del color del fondo, para que se lea donde se cruza con otra linea."""
    return dict(marker="o", markersize=6.5, markeredgecolor=FONDO, markeredgewidth=1.3, **extra)


# ----------------------------------------------------------------------------------------------- datos

def cargar():
    archivos = sorted(a for a in CARPETA_PUNTAJES.glob("puntajes_kaggle_*.csv") if not a.name.startswith("puntajes_kaggle_v2_"))
    if not archivos:
        sys.exit("No hay puntajes_kaggle_*.csv: correr antes exp07_bajar_puntajes.py")
    df = pd.concat([pd.read_csv(a) for a in archivos], ignore_index=True)
    df = df.sort_values("fecha").drop_duplicates(["variante", "semilla", "envios"], keep="last")
    df = df[df["envios"].isin(CORTES) & df["semilla"].isin(SEMILLAS_VECTOR)]
    completos = df.groupby(["variante", "semilla"])["envios"].transform("count") == len(CORTES)
    return df[completos].copy(), [a.name for a in archivos]


def semillas_completas(df):
    """Semillas del vector que tienen las cuatro variantes con los 6 cortes puntuados (las que entran a los pares)."""
    por_semilla = df.groupby("semilla")["variante"].nunique()
    return [s for s in SEMILLAS_VECTOR if por_semilla.get(s, 0) == len(ORDEN_VARIANTES)]


def tabla_semillas(df, semillas, como):
    """Semilla x variante con la ganancia de cada corrida: como = "mean" (promedio de los 6 cortes) o "max"."""
    corridas = df.groupby(["variante", "semilla"])["public"].agg(como).unstack("variante")
    return corridas.reindex(index=semillas, columns=ORDEN_VARIANTES)


def holm(ps):
    """Correccion de Holm; devuelve los p ajustados en el mismo orden que ps."""
    m = len(ps)
    orden = sorted(range(m), key=lambda i: ps[i])
    ajustados, tope = [None] * m, 0.0
    for k, i in enumerate(orden):
        tope = max(tope, min(1.0, (m - k) * ps[i]))
        ajustados[i] = tope
    return ajustados


def todos_contra_todos(piv):
    """Las 6 comparaciones pareadas entre las 4 variantes (Wilcoxon exacto a dos colas) con correccion de Holm,
    como pairwise.wilcox.test(paired = TRUE) de R; V0 es una variante mas."""
    filas = []
    for a, b in itertools.combinations(ORDEN_VARIANTES, 2):
        dif = (piv[b] - piv[a]).dropna()
        p = wilcoxon_p(dif) if len(dif) >= 5 and (dif != 0).any() else np.nan
        filas.append({"variante": b, "contra": a, "n_pares": len(dif), "dif_media": dif.mean(),
                      "gana": int((dif > 0).sum()), "wilcoxon_p": p})
    t = pd.DataFrame(filas)
    validos = t["wilcoxon_p"].notna()
    t["p_holm"] = np.nan
    if validos.any():
        t.loc[validos, "p_holm"] = holm(t.loc[validos, "wilcoxon_p"].tolist())
    return t


def comparar(piv):
    """Por variante: media, desvio y la comparacion pareada por semilla contra V0."""
    filas = []
    for v in ORDEN_VARIANTES:
        fila = {"variante": v, "primer_mes": PRIMER_MES[v], "n_semillas": int(piv[v].notna().sum()),
                "ganancia_media": piv[v].mean(), "desvio_entre_semillas": piv[v].std()}
        if v != "V0_todo":
            dif = (piv[v] - piv["V0_todo"]).dropna()
            fila.update({"n_pares_vs_V0": len(dif), "dif_media_vs_V0": dif.mean(), "dif_desvio": dif.std(),
                         "semillas_que_superan_V0": int((dif > 0).sum()),
                         "wilcoxon_p": wilcoxon_p(dif) if len(dif) >= 5 and (dif != 0).any() else np.nan})
            if len(dif) < 10:
                fila["veredicto"] = f"pendiente ({len(dif)} de 10 semillas)"
            else:
                gana = fila["wilcoxon_p"] < 0.05 and dif.mean() > 0
                fila["veredicto"] = "gana" if gana else "no gana"
        filas.append(fila)
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------------------------------- graficos

def grafico_curvas(df, semillas, nota):
    sub = df[df["semilla"].isin(semillas)]
    medias = (sub.groupby(["variante", "envios"])["public"].mean().unstack("variante")
              .reindex(index=CORTES, columns=ORDEN_VARIANTES))
    fig, ax = plt.subplots(figsize=(9.1, 3.6), dpi=200)
    fig.subplots_adjust(left=0.075, right=0.895, top=0.87, bottom=0.2)
    estilo(ax)
    for v in ORDEN_VARIANTES:
        ax.plot(CORTES, medias[v], color=COLOR[v], linewidth=2.2, solid_joinstyle="round", solid_capstyle="round",
                label=ETIQUETA[v], zorder=3, **marcador())
    lo, hi = medias.min().min(), medias.max().max()
    ymin, ymax = np.floor(lo - 1.5), np.ceil(hi + 1.5)
    ax.set_ylim(ymin, ymax)
    ax.set_xlim(770, 1330)
    ax.set_xticks(CORTES)
    ax.set_xticklabels([miles(c) for c in CORTES])
    ax.set_xlabel("Envíos (clientes estimulados)")
    ax.set_ylabel("Ganancia Public, promedio de las semillas")
    # etiquetas directas al final de cada curva, corridas si se pisan
    finales = sorted(((medias[v].iloc[-1], v) for v in ORDEN_VARIANTES))
    gap = 0.075 * (ymax - ymin)
    ys = []
    for valor, v in finales:
        y = valor if not ys else max(valor, ys[-1] + gap)
        ys.append(y)
        ax.annotate(f"{CORTA[v]}  {coma(valor)}", xy=(1300, valor), xytext=(1318, y),
                    textcoords="data", va="center", ha="left", fontsize=10, color=TINTA,
                    annotation_clip=False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, handlelength=1.8, columnspacing=1.6)
    fig.text(0.075, 0.035, nota, color=TINTA_SUAVE, fontsize=9)
    fig.savefig(SALIDA / "curvas_por_corte.png")
    plt.close(fig)
    return medias


def grafico_dispersion(df, semillas, nota):
    sub = df[df["semilla"].isin(semillas)]
    v0 = sub[sub["variante"] == "V0_todo"].groupby("envios")["public"].mean().reindex(CORTES)
    fig, axes = plt.subplots(1, 4, figsize=(9.1, 3.4), dpi=200, sharey=True)
    fig.subplots_adjust(left=0.065, right=0.985, top=0.84, bottom=0.27, wspace=0.12)
    for ax, v in zip(axes, ORDEN_VARIANTES):
        estilo(ax)
        for s in semillas:
            curva = (sub[(sub["variante"] == v) & (sub["semilla"] == s)]
                     .set_index("envios")["public"].reindex(CORTES))
            ax.plot(CORTES, curva, color=COLOR[v], linewidth=1.1, alpha=0.45, zorder=2)
        media = sub[sub["variante"] == v].groupby("envios")["public"].mean().reindex(CORTES)
        if v != "V0_todo":
            ax.plot(CORTES, v0, color=COLOR["V0_todo"], linewidth=1.6, zorder=3)
        ax.plot(CORTES, media, color=COLOR[v], linewidth=2.4, zorder=4, **marcador())
        ax.set_title(ETIQUETA[v], color=TINTA, pad=6)
        ax.set_xticks(CORTES)
        ax.set_xticklabels([miles(c) for c in CORTES], fontsize=8.5)
        ax.set_xlim(770, 1330)
    axes[0].set_ylabel("Ganancia Public")
    proxies = [Line2D([], [], color=TINTA2, linewidth=1.1, alpha=0.6),
               Line2D([], [], color=TINTA, linewidth=2.4, **marcador()),
               Line2D([], [], color=COLOR["V0_todo"], linewidth=1.6)]
    fig.legend(proxies, ["una semilla", "promedio de la variante", "promedio de V0, como referencia"],
               loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0), columnspacing=2.0)
    fig.text(0.065, 0.945, nota, color=TINTA_SUAVE, fontsize=9)
    fig.savefig(SALIDA / "dispersion_por_variante.png")
    plt.close(fig)


def barra_redondeada(ax, x, y, ancho, radio, aspecto, color):
    """Barra de 0 a y con el extremo de datos redondeado y la base cuadrada: caja redondeada mas un rectangulo
    del mismo color que tapa las esquinas del lado de la base."""
    alto = abs(y)
    if alto == 0:
        return
    base = min(0, y)
    ax.add_patch(FancyBboxPatch((x - ancho / 2, base), ancho, alto,
                                boxstyle=BoxStyle("Round", pad=0, rounding_size=radio), mutation_aspect=aspecto,
                                facecolor=color, edgecolor="none", zorder=3))
    mitad = alto / 2
    ax.add_patch(Rectangle((x - ancho / 2, 0 if y > 0 else -mitad), ancho, mitad,
                           facecolor=color, edgecolor="none", zorder=3))


def grafico_diferencias(piv, comp, nota):
    semillas = list(piv.index)
    difs = {v: (piv[v] - piv["V0_todo"]).to_numpy() for v in RECORTES}
    todos = np.concatenate(list(difs.values()))
    fig, ax = plt.subplots(figsize=(9.1, 2.55), dpi=200)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.80, bottom=0.25)
    estilo(ax)
    ymin, ymax = min(0.0, todos.min()) - 1.0, todos.max() + 1.0
    ax.set_ylim(ymin, ymax)
    xmin, xmax = -0.6, len(semillas) - 0.4
    ax.set_xlim(xmin, xmax)
    ax.axhline(0, color=EJE, linewidth=1.0, zorder=2)
    fig.canvas.draw()
    bb = ax.get_window_extent()
    ancho_in, alto_in = bb.width / fig.dpi, bb.height / fig.dpi
    aspecto = ((ymax - ymin) / alto_in) / ((xmax - xmin) / ancho_in)   # para que el redondeo sea circular
    radio = 0.045 * (xmax - xmin) / ancho_in                            # ~0,045 pulgadas en el extremo
    ancho, paso = 0.16, 0.19
    for k, v in enumerate(RECORTES):
        for i, d in enumerate(difs[v]):
            barra_redondeada(ax, i + (k - 1) * paso, d, ancho, radio, aspecto, COLOR[v])
    ax.set_xticks(range(len(semillas)))
    ax.set_xticklabels([str(s) for s in semillas])
    ax.set_xlabel("Semilla")
    ax.set_ylabel("Diferencia contra V0")
    medias = comp.set_index("variante")["dif_media_vs_V0"]
    ax.legend([Patch(facecolor=COLOR[v]) for v in RECORTES],
              [f"{ETIQUETA[v]} (promedio {'+' if medias[v] >= 0 else ''}{coma(medias[v])})" for v in RECORTES],
              loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, handlelength=1.2, columnspacing=1.8)
    fig.text(0.075, 0.035, nota, color=TINTA_SUAVE, fontsize=9)
    fig.savefig(SALIDA / "diferencias_vs_V0.png")
    plt.close(fig)


# ----------------------------------------------------------------------------------------------- principal

def main():
    SALIDA.mkdir(exist_ok=True)
    df, archivos = cargar()
    semillas = semillas_completas(df)
    if not semillas:
        sys.exit("Ninguna semilla del vector tiene las cuatro variantes completas todavia")
    faltan = 10 - len(semillas)
    provisorio = faltan > 0
    nota = f"Promedio de {len(semillas)} semillas." + (f"  Provisorio: faltan {faltan} de las 10 semillas." if provisorio else "")

    # tablas
    piv = tabla_semillas(df, semillas, METRICA)
    tabla = piv.copy()
    for v in RECORTES:
        tabla[f"dif_{v}_vs_V0"] = tabla[v] - tabla["V0_todo"]
    tabla = pd.concat([tabla, pd.DataFrame({"promedio": tabla.mean(), "desvio": tabla.std()}).T])
    tabla.index.name = "semilla"
    tabla.round(3).to_csv(SALIDA / "tabla_semilla_variante.csv")

    comp = comparar(piv)
    comp.round(4).to_csv(SALIDA / "tabla_variantes.csv", index=False)
    comp_otra = comparar(tabla_semillas(df, semillas, OTRA))
    comp_otra.round(4).to_csv(SALIDA / ("chequeo_maximo.csv" if OTRA == "max" else "chequeo_promedio.csv"), index=False)
    pares = todos_contra_todos(piv)
    pares.round(4).to_csv(SALIDA / "pairwise_holm.csv", index=False)
    (SALIDA / "meta.json").write_text(json.dumps(
        {"metrica": METRICA, "descripcion": DESCRIPCION[METRICA], "otra": OTRA, "descripcion_otra": DESCRIPCION[OTRA],
         "n_semillas": len(semillas), "provisorio": provisorio, "semillas": semillas}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    sub = df[df["semilla"].isin(semillas)]
    cortes = (sub.groupby(["variante", "envios"])["public"]
                 .agg(media="mean", desvio="std", minimo="min", maximo="max").reset_index())
    cortes["variante"] = pd.Categorical(cortes["variante"], categories=ORDEN_VARIANTES, ordered=True)
    cortes = cortes.sort_values(["variante", "envios"])
    cortes.round(3).to_csv(SALIDA / "tabla_cortes.csv", index=False)

    # graficos
    extra = f"  Provisorio: faltan {faltan} de las 10 semillas." if provisorio else ""
    medias_corte = grafico_curvas(df, semillas, f"Cada punto es el promedio de las {len(semillas)} semillas en ese corte." + extra)
    grafico_dispersion(df, semillas, f"Una línea fina por semilla ({len(semillas)} por variante); la gruesa es su promedio y la gris, el promedio de V0." + extra)
    grafico_diferencias(piv, comp, "Una barra por semilla y recorte: ganancia del recorte menos la de V0 con la misma semilla." + extra)

    # resumen
    pd.set_option("display.width", 160)
    lineas = [f"Resultados del Experimento 07, Grupo A ({'PROVISORIO' if provisorio else 'completo'})",
              f"Archivos de puntajes: {', '.join(archivos)}",
              f"Semillas del vector con las 4 variantes completas: {len(semillas)} de 10 -> {semillas}",
              f"Metrica de cada corrida: {DESCRIPCION[METRICA]} (chequeo con {DESCRIPCION[OTRA]})",
              "", f"Ganancia de cada corrida ({DESCRIPCION[METRICA]}), por semilla y variante:",
              tabla.round(2).to_string(),
              "", "Ganancia media por corte y variante:",
              medias_corte.round(2).to_string(),
              "", f"Comparacion pareada contra V0 ({DESCRIPCION[METRICA]}):",
              comp.round(4).to_string(index=False),
              "", f"Chequeo con {DESCRIPCION[OTRA]}:",
              comp_otra.round(4).to_string(index=False),
              "", "Todos contra todos (Wilcoxon pareado exacto, correccion de Holm):",
              pares.round(4).to_string(index=False)]
    p_min = 2 / 2 ** len(semillas)
    lineas += ["", f"Con {len(semillas)} pares, el p minimo posible del Wilcoxon a dos colas es {p_min:.4f}."]
    if provisorio:
        lineas += ["El veredicto (p < 0,05 a favor del recorte) se define con las 10 semillas."]
    else:
        ganadoras = comp[(comp["variante"] != "V0_todo") & (comp["veredicto"] == "gana")]
        if len(ganadoras):
            mejor = ganadoras.loc[ganadoras["dif_media_vs_V0"].idxmax(), "variante"]
            lineas += [f"Recomendacion: entrenar desde {PRIMER_MES[mejor]} ({mejor})"]
        else:
            lineas += ["Recomendacion: ningun recorte cumple la regla, entrenar con todos los meses desde 202005"]
    texto = "\n".join(lineas)
    (SALIDA / "resumen.txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)
    print(f"\nSalidas en {SALIDA}")


if __name__ == "__main__":
    main()
