"""Convierte .pptx o .docx a PDF con Office (COM) y el PDF a PNG por pagina con PyMuPDF.
   python office_to_pdf.py archivo.pptx [dpi]
"""
import os
import sys

import pymupdf
import win32com.client as win32

src = os.path.abspath(sys.argv[1])
dpi = int(sys.argv[2]) if len(sys.argv) > 2 else 110
pdf = os.path.splitext(src)[0] + ".pdf"
ext = os.path.splitext(src)[1].lower()

if ext == ".pptx":
    app = win32.Dispatch("PowerPoint.Application")
    pres = app.Presentations.Open(src, WithWindow=False)
    pres.SaveAs(pdf, 32)  # ppSaveAsPDF
    pres.Close()
    app.Quit()
elif ext == ".docx":
    app = win32.Dispatch("Word.Application")
    app.Visible = False
    doc = app.Documents.Open(src)
    doc.SaveAs2(pdf, FileFormat=17)  # wdFormatPDF
    doc.Close(False)
    app.Quit()
else:
    sys.exit("extension no soportada")

carpeta = os.path.join(os.path.dirname(src), "render_" + os.path.splitext(os.path.basename(src))[0])
os.makedirs(carpeta, exist_ok=True)
for f in os.listdir(carpeta):
    os.remove(os.path.join(carpeta, f))
doc = pymupdf.open(pdf)
for i, page in enumerate(doc, 1):
    page.get_pixmap(dpi=dpi).save(os.path.join(carpeta, f"p{i:02d}.png"))
print(f"{len(doc)} paginas -> {carpeta}")
