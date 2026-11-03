# -*- coding: utf-8 -*-
"""Filmina "Diseño experimental" del Grupo A con los cambios que pidio Denicolay el 29-oct, sola, para reemplazar la del deck.
   Misma estetica que la v3 y el mismo diseño, con dos cambios:
   - 6 cortes por corrida, los del notebook de a 100 (800 a 1.300), en vez de 15
   - la regla de decision queda solo con el p-value del Wilcoxon (se saca lo de 8 de 10 semillas)
   python build_pptx_diseno_6cortes.py  ->  Exp07_GrupoA_diseno_6cortes.pptx
"""
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "Exp07_GrupoA_diseno_6cortes.pptx"

AZUL = "002846"      # fondo de la portada del #7
BLANCO = "FFFFFF"
AMARILLO = "FFFF00"  # "Grupo A: Facundo Londero" en la portada
CELESTE = "9FC5E8"   # lineas de la tabla
FUENTE = "Calibri"
X0 = Inches(0.45)
ANCHO = Inches(9.1)

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


def texto(s, parrafos, top=1.25, alto=4.0, size=18, despues=10):
    """parrafos: str, o lista de (texto, color) para resaltar partes en amarillo."""
    tb = s.shapes.add_textbox(X0, Inches(top), ANCHO, Inches(alto))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, par in enumerate(parrafos):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(despues)
        p.line_spacing = 1.05
        for t, color, *tam in (par if isinstance(par, list) else [(par, BLANCO)]):
            correr(p, t, color, tam[0] if tam else size)
    return tb


def celda(cell, txt, color=BLANCO, size=13, bold=False, arriba=None, abajo=None):
    cell.text = ""
    p = cell.text_frame.paragraphs[0]
    correr(p, txt, color, size, bold)
    cell.margin_left = cell.margin_right = Inches(0.06)
    cell.margin_top = cell.margin_bottom = Inches(0.03)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    # bordes: solo lineas horizontales celestes, sin relleno (el orden de los hijos de tcPr lo fija el esquema)
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


s = filmina("Diseño experimental")
texto(s, [
    "Se corre el workflow z610 de la cátedra tal cual y lo único que varía es el primer mes de entrenamiento. Validación en 202107, entrenamiento final hasta 202107 y predicción de 202109.",
], top=0.98, alto=0.5, size=13, despues=0)
filas = [
    ("Variante", "Primer mes", "Meses de training", "Meses del entrenamiento final"),
    ("V0  todos los meses (línea base)", "202005", "14", "15"),
    ("V1  sin ASPO", "202011", "8", "9"),
    ("V2  solo 2021", "202101", "6", "7"),
    ("V3  últimos cuatro meses", "202103", "4", "5"),
]
anchos = [3.0, 1.3, 2.0, 2.75]
gf = s.shapes.add_table(len(filas), 4, X0 + Inches(0.05), Inches(1.6), Inches(sum(anchos)), Inches(0.27 * len(filas)))
tbl = gf.table
tbl._tbl.tblPr.find(qn("a:tableStyleId")).text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid
tbl.horz_banding = False
for j, w in enumerate(anchos):
    tbl.columns[j].width = Inches(w)
for i, fila in enumerate(filas):
    tbl.rows[i].height = Inches(0.27)
    for j, txt in enumerate(fila):
        celda(tbl.cell(i, j), txt,
              color=AMARILLO if i == 0 else BLANCO, size=12.5, bold=(i == 0),
              abajo=CELESTE if i in (0, len(filas) - 1) else None)
texto(s, [
    [("Cada variante se corre con las mismas 10 semillas y ", BLANCO),
     ("en cada corrida se vuelve a hacer el grid search completo de hiperparámetros", AMARILLO),
     (". Por corrida se suben a Kaggle 6 cortes, los del notebook de a 100 (800, 900, 1.000, 1.100, 1.200 y 1.300 envíos), y se mide el promedio de la curva de ganancia y no el mejor corte, porque el mejor Public casi nunca es el mejor Private (libro, 5.3).", BLANCO)],
    [("Cada recorte se compara con V0 de a pares por semilla, con el test de Wilcoxon. La regla quedó fijada antes de ver resultados: ", BLANCO),
     ("un recorte es mejor que V0 si el Wilcoxon da p < 0,05 a su favor", AMARILLO),
     (".", BLANCO)],
    "Un cambio al notebook, igual en las cuatro variantes: el entrenamiento final usa modifyList, porque con c(fijos, mejores) LightGBM ignora lo que eligió el grid search.",
], top=3.1, alto=2.3, size=13, despues=6)

prs.save(str(SALIDA))
print("guardado:", SALIDA)
