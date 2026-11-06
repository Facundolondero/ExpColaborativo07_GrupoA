# -*- coding: utf-8 -*-
"""Deck unico con todos los capitulos que faltan en el Google Slides del Grupo A, en el orden del libro (cap. 6.1):
   Limitaciones (reemplaza la que esta), Resultados (6), Discusion, Conclusiones, Recomendacion concreta,
   Futuros problemas y Anexo. Misma estetica que Diseño (fondo azul 002846, Calibri, amarillo).
   Lee ../resultados/ (lo que deja exp07_resultados.py, con METRICA = "max" y el promedio como chequeo) y
   hiperparametros_elegidos.csv (bordes de la grilla, AUC e iteraciones de las corridas del vector de semillas).

   python build_pptx_final.py  ->  Exp07_GrupoA_capitulos_finales.pptx
   python office_to_pdf.py Exp07_GrupoA_capitulos_finales.pptx   (PDF + render por pagina)
"""
import json
import re
from pathlib import Path

import pandas as pd
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

AQUI = Path(__file__).resolve().parent
# en la carpeta de trabajo resultados/ esta al lado de slides/; en el repositorio, dos niveles arriba
RES = AQUI.parent / "resultados" if (AQUI.parent / "resultados").is_dir() else AQUI.parent.parent / "resultados"
SALIDA = AQUI / "Exp07_GrupoA_capitulos_finales.pptx"
REPO_URL = "github.com/Facundolondero/ExpColaborativo07_GrupoA"

AZUL = "002846"
BLANCO = "FFFFFF"
AMARILLO = "FFFF00"
CELESTE = "9FC5E8"
VERDE = "199E70"      # V3 en los graficos
CORAL = "D95926"      # V2 en los graficos; aca marca el ASPO
CAJA = "27496D"       # meses que quedan afuera
FUENTE = "Calibri"
X0 = Inches(0.45)
ANCHO = Inches(9.1)
CORTES = list(range(800, 1301, 100))
ORDEN = ["V0_todo", "V1_sinASPO", "V2_2021", "V3_ultimos4"]
RECORTES = ORDEN[1:]
ETIQUETA = {"V0_todo": "V0 todos los meses", "V1_sinASPO": "V1 sin ASPO",
            "V2_2021": "V2 solo 2021", "V3_ultimos4": "V3 últimos cuatro meses"}
CORTA = {v: v.split("_")[0] for v in ORDEN}
PRIMER_MES = {"V0_todo": "202005", "V1_sinASPO": "202011", "V2_2021": "202101", "V3_ultimos4": "202103"}
MESES_TRAIN = {"V0_todo": 14, "V1_sinASPO": 8, "V2_2021": 6, "V3_ultimos4": 4}
FILAS_TRAIN = {"V0_todo": (179449, 853), "V1_sinASPO": (104483, 587), "V2_2021": (78630, 472), "V3_ultimos4": (52606, 333)}


def coma(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def signo(x, d=1):
    return ("+" if x >= 0 else "") + coma(x, d)


def miles(x):
    return f"{int(x):,}".replace(",", ".")


# ------------------------------------------------------------------------------------------ datos
tabla = pd.read_csv(RES / "tabla_semilla_variante.csv", index_col=0)
comp = pd.read_csv(RES / "tabla_variantes.csv").set_index("variante")
otra = pd.read_csv(RES / ("chequeo_promedio.csv" if (RES / "chequeo_promedio.csv").exists() else "chequeo_maximo.csv")).set_index("variante")
cortes = pd.read_csv(RES / "tabla_cortes.csv")
pares = pd.read_csv(RES / "pairwise_holm.csv")
meta = json.loads((RES / "meta.json").read_text(encoding="utf-8"))
DESC, DESC_OTRA = meta["descripcion"], meta["descripcion_otra"]
semillas = [i for i in tabla.index if i not in ("promedio", "desvio")]
n = len(semillas)
provisorio = n < 10
TAG = f"Provisorio: {n} de 10 semillas. " if provisorio else ""
medias_corte = cortes.pivot(index="envios", columns="variante", values="media").reindex(index=CORTES, columns=ORDEN)

# corridas del vector de semillas: bordes de la grilla, AUC e iteraciones (se actualiza solo cuando se sumen las de Francisco)
hip = pd.read_csv(RES / "hiperparametros_elegidos.csv")
hv = hip[hip["vector"]]
N_CORRIDAS = len(hv)
N_BORDE_MDL = int((hv["min_data_in_leaf"] == 64).sum())      # borde inferior de la grilla {64 ... 2048}
N_BORDE_LEAVES = int((hv["num_leaves"] == 512).sum())        # borde superior de la grilla {64 ... 512}
AUC_MEDIA = hv.groupby("variante")["AUC"].mean()
ITER_MEDIANA = hv.groupby("variante")["num_iterations"].median()
print(f"corridas del vector: {N_CORRIDAS} | min_data_in_leaf en el borde: {N_BORDE_MDL} | num_leaves en el borde: {N_BORDE_LEAVES}")
print("AUC medio:", {v: round(AUC_MEDIA[v], 3) for v in ORDEN}, "| iteraciones medianas:", {v: int(ITER_MEDIANA[v]) for v in ORDEN})

# corte en el que cae el maximo de cada corrida: cuantas semillas lo tienen en el primer o el ultimo corte
CARPETA_PUNTAJES = RES.parent / "puntajes" if (RES.parent / "puntajes").is_dir() else RES.parent
punt = pd.concat([pd.read_csv(a) for a in sorted(CARPETA_PUNTAJES.glob("puntajes_kaggle_*.csv"))], ignore_index=True)
punt = punt[punt["semilla"].astype(str).isin([str(x) for x in semillas]) & punt["envios"].isin(CORTES)]
assert punt.groupby("variante").size().eq(n * len(CORTES)).all(), "faltan o sobran envíos en los puntajes"
maximos = punt.loc[punt.groupby(["variante", "semilla"])["public"].idxmax()]
BORDE_CORTE = maximos[maximos["envios"].isin([CORTES[0], CORTES[-1]])].groupby("variante").size().reindex(ORDEN, fill_value=0)
print("máximo en el primer o último corte:", BORDE_CORTE.to_dict())

# ------------------------------------------------------------------------------------------ primitivas
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(10), Inches(5.625)
BLANK = prs.slide_layouts[6]


def rgb(h):
    return RGBColor.from_string(h)


def correr(p, texto, color=BLANCO, size=18, bold=False):
    r = p.add_run()
    r.text = texto
    r.font.size = Pt(size); r.font.name = FUENTE; r.font.bold = bold; r.font.color.rgb = rgb(color)
    return r


def filmina(titulo):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(AZUL)
    tb = s.shapes.add_textbox(X0, Inches(0.4), ANCHO, Inches(0.7))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    correr(p, "Grupo A: ", AMARILLO, 26, True)
    correr(p, titulo, BLANCO, 26)
    return s


def texto(s, parrafos, top=1.25, alto=4.0, size=18, despues=10, left=None, ancho=None, centrado=False):
    """parrafos: str, o lista de partes (texto, color[, tamaño[, negrita]]) para resaltar partes en amarillo."""
    tb = s.shapes.add_textbox(Inches(left) if left is not None else X0, Inches(top),
                              Inches(ancho) if ancho is not None else ANCHO, Inches(alto))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, par in enumerate(parrafos):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(despues)
        p.line_spacing = 1.05
        if centrado:
            p.alignment = PP_ALIGN.CENTER
        for parte in (par if isinstance(par, list) else [(par, BLANCO)]):
            t, color = parte[0], parte[1]
            tam = parte[2] if len(parte) > 2 and parte[2] else size
            bold = parte[3] if len(parte) > 3 else False
            correr(p, t, color, tam, bold)
    return tb


def puntos(s, items, top=1.1, alto=4.4, size=12, despues=6):
    """Un parrafo por item: entrada corta en amarillo y negrita, despues el texto."""
    texto(s, [[(entrada + " ", AMARILLO, size, True), (cuerpo, BLANCO)] for entrada, cuerpo in items],
          top=top, alto=alto, size=size, despues=despues)


def celda(cell, txt, color=BLANCO, size=13, bold=False, arriba=None, abajo=None):
    cell.text = ""
    p = cell.text_frame.paragraphs[0]
    correr(p, txt, color, size, bold)
    cell.margin_left = cell.margin_right = Inches(0.06)
    cell.margin_top = cell.margin_bottom = Inches(0.03)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    tcPr = cell._tc.get_or_add_tcPr()
    for hijo in list(tcPr):
        tcPr.remove(hijo)
    for tag, color_linea in (("a:lnL", None), ("a:lnR", None), ("a:lnT", arriba), ("a:lnB", abajo)):
        ln = etree.SubElement(tcPr, qn(tag))
        if color_linea is None:
            ln.set("w", "0")
            etree.SubElement(ln, qn("a:noFill"))
        else:
            ln.set("w", str(Pt(1)))
            sf = etree.SubElement(ln, qn("a:solidFill"))
            etree.SubElement(sf, qn("a:srgbClr")).set("val", color_linea)
    etree.SubElement(tcPr, qn("a:noFill"))


def tabla_pptx(s, filas, anchos, top, alto_fila=0.26, size=12.5, resaltes=None, negritas=()):
    resaltes = resaltes or set()
    gf = s.shapes.add_table(len(filas), len(anchos), X0 + Inches(0.05), Inches(top),
                            Inches(sum(anchos)), Inches(alto_fila * len(filas)))
    tbl = gf.table
    tbl._tbl.tblPr.find(qn("a:tableStyleId")).text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid
    tbl.horz_banding = False
    for j, w in enumerate(anchos):
        tbl.columns[j].width = Inches(w)
    for i, fila in enumerate(filas):
        tbl.rows[i].height = Inches(alto_fila)
        for j, txt in enumerate(fila):
            resaltar = (i, j) in resaltes
            celda(tbl.cell(i, j), txt,
                  color=AMARILLO if (i == 0 or resaltar) else BLANCO, size=size,
                  bold=(i == 0 or resaltar or i in negritas),
                  abajo=CELESTE if i in (0, len(filas) - 1) else None)
    return gf


def imagen(s, nombre, top, ancho=9.1):
    return s.shapes.add_picture(str(RES / nombre), X0, Inches(top), width=Inches(ancho))


def caja(s, left, top, w, h, relleno=None, txt="", color=BLANCO, size=9.5, borde=None, bold=False):
    """Rectangulo con texto centrado (para la tira de meses)."""
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(w), Inches(h))
    sh.shadow.inherit = False
    if relleno:
        sh.fill.solid(); sh.fill.fore_color.rgb = rgb(relleno)
    else:
        sh.fill.background()
    if borde:
        sh.line.color.rgb = rgb(borde); sh.line.width = Pt(1.5)
    else:
        sh.line.fill.background()
    tf = sh.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    if txt:
        correr(p, txt, color, size, bold)
    return sh


# ======================================================================================== 1. Limitaciones
s = filmina("Limitaciones")
puntos(s, [
    ("Public, no Private.",
     "Medimos sobre el Public de Kaggle, una parte de los clientes de un solo mes, con el máximo de 6 cortes. El Private "
     "recién se conoce el 15 de noviembre, después del video."),
    ("Cambio de métrica.",
     "El diseño decía promedio de los cortes; la cátedra aclaró después que en Kaggle la ganancia de una corrida es el "
     "máximo del Public. Reportamos el máximo y dejamos el promedio como chequeo: las dos dan el mismo ganador."),
    ("No hay una línea base sin pandemia.",
     "En el dataset gerencial, «todos los meses» empieza en 202005, es decir, en plena pandemia. El experimento compara "
     "cuánta pandemia dejar, no pandemia contra prepandemia."),
    ("Menos datos y menos pandemia van juntos.",
     "V3 entrena con el 29 % de las filas y el 39 % de las bajas de V0; el experimento no separa los dos efectos."),
    ("Los primeros meses de V0 están incompletos.",
     "El dataset gerencial arranca en 202005: ese mes no tiene lags y 202006 no tiene el de orden 2, y además 202006 tiene "
     "12 variables catastróficas en NA. V0 es la única variante que entrena con esos meses, así que parte de su menor "
     "ganancia puede deberse a la calidad de los datos y no a la pandemia."),
    ("V1 no es del todo sin pandemia.",
     "Los lags de noviembre y diciembre de 2020 todavía miran meses del ASPO. Ese efecto lo estudia el Problema #05."),
], top=1.1, alto=4.4, size=13, despues=8)

s = filmina("Limitaciones (continuación)")
puntos(s, [
    ("La validación es un único mes.",
     "El grid search y el early stopping se deciden solo con el AUC de 202107. Si julio no representa bien a septiembre, "
     "los hiperparámetros elegidos pueden no ser los óptimos."),
    ("Cortes del notebook.",
     "La curva media de V0 todavía sube en 1.300 envíos y la de V1 es más alta en 800, así que sus máximos pueden estar "
     f"algo subestimados: el máximo de la corrida cae en el primer o el último corte en {BORDE_CORTE['V0_todo']} de {n} "
     f"semillas en V0, {BORDE_CORTE['V1_sinASPO']} en V1, {BORDE_CORTE['V2_2021']} en V2 y {BORDE_CORTE['V3_ultimos4']} en V3."),
    ("Grilla del baseline.",
     f"El grid search eligió min_data_in_leaf = 64, el borde de la grilla, en {N_BORDE_MDL} de nuestras {N_CORRIDAS} "
     f"corridas, y num_leaves = 512 en {N_BORDE_LEAVES}. No la ampliamos para no tocar el workflow; con una grilla más "
     "amplia las ganancias podrían ser otras."),
    ("Alcance.",
     # el semiancho del IC 95 % de la diferencia pareada va de 2,3 a 3,7 puntos segun la comparacion
     "Con 10 semillas el p mínimo del Wilcoxon es 0,002, y con este ruido no se distinguen diferencias menores a unos 3 "
     "puntos, como la de V2 contra V3. El corte del ASPO es el del AMBA y no sabemos dónde viven los clientes. Los resultados del Grupo B, sobre julio de "
     "2021, se comparan con estos solo en conclusiones, no en ganancia."),
], top=1.1, alto=4.4, size=13, despues=8)

# ======================================================================================== 2. Resultados: tabla
s = filmina("Resultados: ganancia por semilla y variante")
texto(s, [[(TAG, AMARILLO), (f"Ganancia de cada corrida = {DESC} (800 a 1.300 envíos). "
                             "Mismas semillas en las cuatro variantes.", BLANCO)]],
      top=0.98, alto=0.55, size=13, despues=0)
filas = [("Semilla",) + tuple(ETIQUETA[v] for v in ORDEN)]
resaltes = set()
for i, sem in enumerate(semillas, start=1):
    valores = [tabla.loc[sem, v] for v in ORDEN]
    filas.append((str(sem),) + tuple(coma(x) for x in valores))
    resaltes.add((i, 1 + valores.index(max(valores))))
filas.append(("Promedio",) + tuple(coma(tabla.loc["promedio", v]) for v in ORDEN))
filas.append(("Desvío entre semillas",) + tuple(coma(tabla.loc["desvio", v]) for v in ORDEN))
alto_fila, letra, top_tabla = (0.26, 12.5, 1.62) if n <= 7 else (0.25, 11, 1.42)
tabla_pptx(s, filas, [1.9, 1.8, 1.6, 1.6, 2.2], top=top_tabla, alto_fila=alto_fila, size=letra,
           resaltes=resaltes, negritas={len(filas) - 2})
lectura = ", ".join(f"{CORTA[v]} {signo(comp.loc[v, 'dif_media_vs_V0'])} "
                    f"({int(comp.loc[v, 'semillas_que_superan_V0'])} de {n})" for v in RECORTES)
texto(s, [[("En amarillo, la mejor variante de cada semilla. Diferencia promedio contra V0 y semillas en que el "
            "recorte supera a V0: ", BLANCO), (lectura + ".", AMARILLO)]],
      top=top_tabla + alto_fila * len(filas) + 0.12, alto=0.8, size=12.5, despues=0)

# ======================================================================================== 3. Resultados: curvas
s = filmina("Resultados: curva de ganancia por corte")
texto(s, [[(TAG, AMARILLO), ("Promedio de las semillas en cada uno de los 6 cortes, una curva por variante.", BLANCO)]],
      top=0.98, alto=0.5, size=13, despues=0)
pic = imagen(s, "curvas_por_corte.png", top=1.45)
partes = []
for v in RECORTES:
    abajo = [c for c in CORTES if medias_corte.loc[c, v] <= medias_corte.loc[c, "V0_todo"]]
    partes.append(f"{CORTA[v]} supera a V0 en los 6 cortes" if not abajo
                  else f"{CORTA[v]} supera a V0 salvo en {' y '.join(miles(c) for c in abajo)}")
lectura_cortes = ("Los tres recortes quedan por encima de V0 en los 6 cortes."
                  if all(p.endswith("en los 6 cortes") for p in partes) else "; ".join(partes) + ".")
texto(s, [lectura_cortes], top=1.45 + pic.height / 914400 + 0.08, alto=0.6, size=13, despues=0)

# ======================================================================================== 4. Resultados: vs V0
s = filmina("Resultados: comparación con V0 por semilla")
texto(s, [[(TAG, AMARILLO), ("Diferencia de cada recorte contra V0 con la misma semilla.", BLANCO)]],
      top=0.98, alto=0.5, size=13, despues=0)
pic = imagen(s, "diferencias_vs_V0.png", top=1.42)
top_tabla = 1.42 + pic.height / 914400 + 0.12
filas = [("Comparación con V0", "Diferencia media", "Semillas que superan a V0", "p Wilcoxon", "Veredicto")]
resaltes = set()
for v in RECORTES:
    c = comp.loc[v]
    filas.append((ETIQUETA[v], signo(c["dif_media_vs_V0"], 2), f"{int(c['semillas_que_superan_V0'])} de {n}",
                  coma(c["wilcoxon_p"], 4), "pendiente" if provisorio else c["veredicto"]))
    if not provisorio and c["veredicto"] == "gana":
        resaltes.add((len(filas) - 1, 4))
tabla_pptx(s, filas, [2.3, 1.5, 2.1, 1.3, 1.9], top=top_tabla, alto_fila=0.25, size=12, resaltes=resaltes)
p_min = 2 / 2 ** n
nota = ("Test de Wilcoxon de rangos con signo, exacto, a dos colas. "
        + (f"Con {n} pares el p mínimo posible es {coma(p_min, 4)}: la regla (p < 0,05 a favor del recorte) "
           f"se aplica con las 10 semillas." if provisorio else "Regla fijada de antemano: p < 0,05 a favor del recorte."))
texto(s, [nota], top=top_tabla + 0.25 * len(filas) + 0.06, alto=0.5, size=11, despues=0)

# ======================================================================================== 5. Resultados: dispersion
s = filmina("Resultados: dispersión entre semillas")
texto(s, [[(TAG, AMARILLO), (f"Cada panel: las {n} corridas de una variante (líneas finas), su promedio "
                             "(línea gruesa) y el promedio de V0 como referencia (gris).", BLANCO)]],
      top=0.98, alto=0.55, size=13, despues=0)
pic = imagen(s, "dispersion_por_variante.png", top=1.5)
picos = {}
for v in ORDEN:
    picos.setdefault(int(medias_corte[v].idxmax()), []).append(CORTA[v])
partes = [f"{' y '.join(vs)} en {miles(c)}" for c, vs in sorted(picos.items())]
partes[0] += " envíos"
frase = ", ".join(partes[:-1]) + (" y " if len(partes) > 1 else "") + partes[-1]
texto(s, ["Máximo del promedio de cada variante: " + frase + "."],
      top=1.5 + pic.height / 914400 + 0.08, alto=0.6, size=13, despues=0)

# ======================================================================================== 6. Resultados: Holm
s = filmina("Resultados: todas las comparaciones")
texto(s, [[(TAG, AMARILLO), ("Las 6 comparaciones pareadas entre las 4 variantes, con corrección de Holm "
                             "(pairwise.wilcox.test); V0 es una variante más.", BLANCO)]],
      top=0.98, alto=0.55, size=13, despues=0)
filas = [("Comparación", "Diferencia media", "Gana en", "p Wilcoxon", "p corregido (Holm)")]
resaltes = set()
for _, r in pares.iterrows():
    filas.append((f"{CORTA[r['variante']]} contra {CORTA[r['contra']]}", signo(r["dif_media"], 2),
                  f"{int(r['gana'])} de {int(r['n_pares'])}", coma(r["wilcoxon_p"], 4), coma(r["p_holm"], 4)))
    if r["p_holm"] < 0.05:
        resaltes |= {(len(filas) - 1, j) for j in range(5)}
tabla_pptx(s, filas, [2.4, 1.8, 1.5, 1.6, 1.8], top=1.65, alto_fila=0.3, size=12.5, resaltes=resaltes)
significativas = pares[pares["p_holm"] < 0.05]
lectura = ("Con la corrección de Holm ninguna comparación queda por debajo de 0,05." if significativas.empty else
           "En amarillo, las que quedan por debajo de 0,05 con Holm: " + ", ".join(
               f"{CORTA[r['variante']]} contra {CORTA[r['contra']]} ({coma(r['p_holm'], 4)})"
               for _, r in significativas.iterrows()) + ".")
texto(s, [f"Ganancia de cada corrida = {DESC}. Test de Wilcoxon de rangos con signo, exacto, a dos colas. " + lectura],
      top=1.65 + 0.3 * len(filas) + 0.2, alto=0.9, size=13, despues=0)

# ======================================================================================== 7. Resultados: chequeo
s = filmina("Resultados: chequeo con la métrica original")
texto(s, [[(TAG, AMARILLO), (f"La misma comparación contra V0 con las dos métricas: {DESC} (la de la cátedra) y "
                             f"{DESC_OTRA} (la del diseño).", BLANCO)]],
      top=0.98, alto=0.55, size=13, despues=0)
filas = [("Comparación con V0", "Máximo: diferencia", "gana en", "p", "Promedio: diferencia", "gana en", "p")]
resaltes = set()
for v in RECORTES:
    a, b = comp.loc[v], otra.loc[v]
    filas.append((ETIQUETA[v], signo(a["dif_media_vs_V0"], 2), f"{int(a['semillas_que_superan_V0'])} de {n}",
                  coma(a["wilcoxon_p"], 4), signo(b["dif_media_vs_V0"], 2),
                  f"{int(b['semillas_que_superan_V0'])} de {n}", coma(b["wilcoxon_p"], 4)))
    if a["wilcoxon_p"] < 0.05:
        resaltes.add((len(filas) - 1, 3))
    if b["wilcoxon_p"] < 0.05:
        resaltes.add((len(filas) - 1, 6))
tabla_pptx(s, filas, [2.3, 1.45, 0.95, 0.85, 1.65, 0.95, 0.95], top=1.7, alto_fila=0.32, size=12, resaltes=resaltes)
ganan_max = [CORTA[v] for v in RECORTES if comp.loc[v, "veredicto"] == "gana"]
ganan_prom = [CORTA[v] for v in RECORTES if otra.loc[v, "veredicto"] == "gana"]
texto(s, [[("Las dos métricas dan el mismo orden y el mismo mejor recorte. ", BLANCO),
           (f"Pasan la regla (p < 0,05, en amarillo): con el máximo {', '.join(ganan_max)}; con el promedio "
            f"{', '.join(ganan_prom)}.", AMARILLO)],
          "Las ganancias medias por variante con el promedio: " + ", ".join(
              f"{CORTA[v]} {coma(otra.loc[v, 'ganancia_media'])}" for v in ORDEN) + "."],
      top=1.7 + 0.32 * len(filas) + 0.25, alto=1.2, size=13, despues=6)

# ======================================================================================== 8. Discusion
s = filmina("Discusión")
texto(s, [
    [("Los tres recortes dieron más ganancia que entrenar con todos los meses, y la mejora crece a medida que el "
      "entrenamiento se acerca a septiembre: ", BLANCO),
     ("21,6 sin ASPO, 24,5 solo 2021 y 25,0 con los últimos cuatro meses, contra 20,0 de la línea base", AMARILLO),
     (". V3 ganó en las 10 semillas (p 0,002) y es la única diferencia que sobrevive a la corrección de Holm; V2 y V3 "
      "no se distinguen entre sí (p 0,92).", BLANCO)],
    [("La primera parte de la hipótesis se sostiene y la segunda no. Pensábamos que cuatro meses eran pocos datos, "
      "pero V3 entrena con el 29 % de las filas y el 39 % de las bajas de V0 y aun así es la mejor. ", BLANCO),
     ("En este dataset, parecerse al mes que se predice pesa más que la cantidad de datos", AMARILLO),
     (": durante el ASPO se iban 44 clientes por mes y en 2021, 80. «Más meses siempre es mejor» vale cuando los meses "
      "son del mismo régimen.", BLANCO)],
    "Sacar solo el ASPO rinde poco: +1,7, 7 de 10 semillas, sin significación. Una explicación es que los lags de "
    "noviembre y diciembre de 2020 todavía miran meses del ASPO. Y el AUC de validación en julio va al revés de la "
    "ganancia (0,954 para V0 contra 0,949 para V3): ordenar bien julio no garantiza ganar en septiembre, por eso la "
    "comparación se hace solo por ganancia.",
    "El resultado es sobre el Public de un solo mes y con el máximo de 6 cortes; el Private del 15 de noviembre es la "
    "prueba de fuego. La curva de V0 todavía sube en 1.300 envíos, así que su máximo puede estar algo subestimado, "
    "pero con 5 puntos de diferencia y 10 de 10 semillas es difícil que eso dé vuelta el resultado.",
    "Con otros problemas: el Grupo B del Problema #01 no encontró diferencia significativa al reparar las variables rotas "
    "de junio de 2020 (interpolar +0,96, p 0,195), y con esta receta ese mes queda afuera, así que esa decisión deja de "
    "importar. En el Problema #08, con otro dataset, sacarle a la búsqueda meses recientes para validar en más meses no "
    "mejoró (3 meses: −3,44, p 0,11): va en el mismo sentido, pero sin significación.",
], top=1.05, alto=4.5, size=12, despues=6)

# ======================================================================================== 9. Conclusiones
s = filmina("Conclusiones")
texto(s, [
    [("Qué conviene. ", AMARILLO, 13, True),
     ("Para predecir septiembre de 2021 con el dataset gerencial, ", BLANCO),
     ("conviene no entrenar con los meses de 2020", AMARILLO),
     (". Entrenar desde marzo de 2021 dio 25,0 de ganancia Public contra 20,0 de la línea base y ganó en las 10 "
      "semillas (p 0,002); desde enero de 2021 quedó casi igual (24,5, 8 de 10 semillas). Sacar solo el ASPO no "
      "alcanza (21,6, 7 de 10, p 0,13).", BLANCO)],
    [("Qué pasó con la hipótesis. ", AMARILLO, 13, True),
     ("Acertó en el sentido y falló en el límite: más datos no fue mejor cuando esos datos son de otro régimen. El "
      "efecto es grande frente al ruido entre semillas: una diferencia media de 5,1 con un desvío de 3,5.", BLANCO)],
    [("Qué no sabemos. ", AMARILLO, 13, True),
     ("Si vale para otros meses y para el Private. Con el promedio de los cortes, la métrica original del diseño, el "
      "orden es el mismo y los tres recortes pasan la regla.", BLANCO)],
    [("Grupo B. ", AMARILLO, 13, True),
     ("Prueba otra palanca: bajarles el peso a esos meses en vez de sacarlos, evaluando en julio de 2021 sin Kaggle. Sus "
      "ganancias no se comparan con las nuestras. Si llega a lo mismo, la conclusión se refuerza; si no, el efecto depende "
      "del mes que se predice o de la forma de recortar.", BLANCO)],
], top=1.1, alto=4.4, size=13, despues=9)

# ======================================================================================== 10. Recomendacion
s = filmina("Recomendación concreta")
texto(s, [[("Para la predicción final gerencial con la z719: ", BLANCO),
           ("entrenar solo desde marzo de 2021", AMARILLO, 14, True),
           (": training del grid 202103 a 202106, validación 202107 y modelo final 202103 a 202107. Todo 2020 y enero y "
            "febrero de 2021 quedan afuera. El modelo final se arma con modifyList, como en el experimento; nada más "
            "cambia.", BLANCO)]],
      top=1.02, alto=0.85, size=13.5, despues=0)

# tira de meses: 15 meses con clase (202005 a 202107), un hueco y el mes a predecir (202109)
MESES = ["may", "jun", "jul", "ago", "sep", "oct", "nov", "dic", "ene", "feb", "mar", "abr", "may", "jun", "jul"]
W, G = 0.48, 0.06
x = lambda i: 0.45 + i * (W + G)
Y_ANIO, Y_ASPO, Y_CAJA, Y_ROTULO = 1.9, 2.17, 2.25, 2.72
texto(s, [[("2020", CELESTE, 10.5, True), ("    ASPO de mayo a octubre", CORAL, 9.5, True)]],
      top=Y_ANIO, alto=0.25, size=10, despues=0, left=x(0), ancho=8 * (W + G))
texto(s, [[("2021", CELESTE, 10.5, True)]], top=Y_ANIO, alto=0.25, size=10, despues=0, left=x(8), ancho=7 * (W + G))
caja(s, x(0), Y_ASPO, 6 * (W + G) - G, 0.05, relleno=CORAL)
for i, m in enumerate(MESES):
    entrena = i >= 10
    caja(s, x(i), Y_CAJA, W, 0.42, relleno=VERDE if entrena else CAJA, txt=m, color=BLANCO, size=9.5, bold=entrena)
xf = x(15) + 0.25
caja(s, xf, Y_CAJA, W, 0.42, borde=AMARILLO, txt="sep", color=AMARILLO, size=9.5, bold=True)
texto(s, ["Afuera: mayo de 2020 a febrero de 2021 (10 meses)"], top=Y_ROTULO, alto=0.3, size=9.5, despues=0,
      left=x(0), ancho=10 * (W + G) - G, centrado=True)
texto(s, [[("Training del modelo final: marzo a julio de 2021 (5 meses)", VERDE, 9.5, True)]], top=Y_ROTULO, alto=0.45,
      size=9.5, despues=0, left=x(10), ancho=5 * (W + G) - G, centrado=True)
texto(s, [[("Predice", AMARILLO, 9.5, True)]], top=Y_ROTULO, alto=0.3, size=9.5, despues=0,
      left=xf - 0.3, ancho=W + 0.6, centrado=True)

texto(s, [
    [("Efecto esperado: ", AMARILLO, 13, True),
     ("unos 5 puntos más de ganancia Public que la línea base (25,0 contra 20,0), con 10 de 10 semillas a favor y "
      "p 0,002.", BLANCO)],
    [("Opción prudente: ", AMARILLO, 13, True),
     ("si se prefiere conservar más datos, entrenar desde 202101 da casi lo mismo (24,5, 8 de 10 semillas, p 0,014). "
      "Lo que no conviene es entrenar con 2020 completo ni sacar solo los meses del ASPO.", BLANCO)],
    [("Revisión: ", AMARILLO, 13, True),
     ("la receta se contrasta el 15 de noviembre con el Private; si el orden cambia, vale más el Private que esto.",
      BLANCO)],
], top=3.3, alto=2.2, size=13, despues=8)

# ======================================================================================== 11. Futuros problemas
s = filmina("Futuros problemas y experimentos")
puntos(s, [
    ("Private.",
     "Repetir las comparaciones cuando cierre la competencia y ver si V3 sigue por encima de V2."),
    ("Separar los dos efectos.",
     "Entrenar con la misma cantidad de meses en distintas posiciones (cuatro meses de 2020 contra cuatro de 2021) y "
     "probar pesos decrecientes por antigüedad en vez de cortar."),
    ("Ventanas mes a mes.",
     "Primer mes de training entre noviembre de 2020 y abril de 2021, con más semillas, para ubicar dónde empieza a "
     "ganar el recorte y dónde empieza a perder: con 10 semillas, V2 y V3 no se distinguen."),
    ("Grilla.",
     "Ampliarla cuando el óptimo cae en el borde (min_data_in_leaf por debajo de 64, num_leaves por encima de 512) y "
     "repetir el experimento con la grilla nueva."),
    ("Validación en varios meses.",
     "Elegir el primer mes de training validando sobre varios meses con clase conocida o con walk forward validation, en "
     "lugar de un solo mes, en la línea de los Problemas #08 y #10."),
    ("Dataset de los analistas y Problema #05.",
     "El mismo experimento con el dataset que tiene meses previos a la pandemia, para probar «sin pandemia» de verdad y "
     "no solo «sin ASPO». Y combinarlo con el #05: limpiar los lags que miran meses del ASPO en vez de sacar los meses."),
], top=1.1, alto=4.4, size=12.5, despues=7)

# ======================================================================================== 12. Anexo
s = filmina("Anexo")
texto(s, [
    [("Repositorio: ", AMARILLO, 12, True), (REPO_URL, AMARILLO),
     (". Scripts de las corridas (R en una PC y notebook de Colab), de las subidas a Kaggle y del análisis; los puntajes "
      "Public de los 240 envíos de los dos integrantes; tablas, gráficos y tests; y de cada corrida PARAM.yml, el grid "
      "search completo y la importancia de variables.", BLANCO)],
    [("Cómo replicar: ", AMARILLO, 12, True),
     ("R con data.table, lightgbm, yaml y R.utils; Rscript exp07_batch.R full A corre las 40 corridas y descarga el "
      "dataset si falta; exp07_subir.py --subir sube los 6 cortes de cada corrida; exp07_bajar_puntajes.py y "
      "exp07_resultados.py arman las tablas y los tests. En Colab, subir el notebook con el entorno en R y correr en "
      "orden.", BLANCO)],
    [("Datos y semillas: ", AMARILLO, 12, True),
     ("gerencial_competencia_2026.csv.gz, meses 202005 a 202107 con clase, future 202109. Semillas 150001, 222247, "
      "199999, 777781 y 999983 (Facundo); 101929, 232327, 456791, 454451 y 123457 (Francisco).", BLANCO)],
], top=1.08, alto=2.2, size=12, despues=6)
filas = [("Variante", "Primer mes", "Meses", "Filas de training", "BAJA+2", "AUC validación", "Iteraciones")]
for v in ORDEN:
    filas.append((ETIQUETA[v], PRIMER_MES[v], str(MESES_TRAIN[v]), miles(FILAS_TRAIN[v][0]), miles(FILAS_TRAIN[v][1]),
                  coma(AUC_MEDIA[v], 3), str(int(ITER_MEDIANA[v] + 0.5))))
TOP_ANEXO = 3.25
tabla_pptx(s, filas, [2.3, 1.0, 0.8, 1.5, 0.9, 1.3, 1.2], top=TOP_ANEXO, alto_fila=0.27, size=11.5)
texto(s, ["Meses, filas y BAJA+2 del training (hasta 202106). AUC medio de validación en 202107; no se usa para comparar "
          "variantes. Iteraciones: mediana del modelo final, elegidas por early stopping (200) sobre un tope de 2.048."],
      top=TOP_ANEXO + 0.27 * len(filas) + 0.18, alto=0.6, size=10.5, despues=0)

# el link del repositorio queda clickeable, y en amarillo: el color de los links sale del tema, no del texto
for sh in s.shapes:
    if sh.has_text_frame:
        for parrafo in sh.text_frame.paragraphs:
            for corrida in parrafo.runs:
                if corrida.text == REPO_URL:
                    corrida.hyperlink.address = "https://" + REPO_URL
tema = prs.slide_masters[0].part.part_related_by(RT.THEME)
tema._blob = re.sub(rb'(<a:(?:hlink|folHlink)>\s*<a:srgbClr val=")[0-9A-Fa-f]{6}', rb"\g<1>" + AMARILLO.encode(), tema.blob)

prs.save(str(SALIDA))
print("guardado:", SALIDA, "| filminas:", len(prs.slides))
