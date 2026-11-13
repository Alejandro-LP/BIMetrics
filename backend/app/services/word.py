"""Exportación DOCX legible de presupuestos."""
from io import BytesIO

from ..errors import ErrorApi


def exportar_presupuesto_word(presupuesto):
    """Genera un documento editable; no añade firma digital certificada."""
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Inches, Pt
    except ImportError as error:
        raise ErrorApi(503, "La exportación Word requiere instalar python-docx") from error

    documento = Document()
    documento.add_heading("BIMetrics · Presupuesto de obra", level=0)
    datos = documento.add_paragraph()
    datos.add_run("Proyecto: ").bold = True
    datos.add_run(str(presupuesto.get("nombre_obra") or "-"))
    datos.add_run("    Ciudad: ").bold = True
    datos.add_run(str(presupuesto.get("ciudad") or "-"))
    datos.add_run("\nPresupuesto: ").bold = True
    datos.add_run(f"#{presupuesto.get('id_presupuesto', '-')}")
    datos.add_run("    Fecha: ").bold = True
    datos.add_run(str(presupuesto.get("fecha_calculo") or "-"))

    tabla = documento.add_table(rows=1, cols=6)
    tabla.style = "Light Shading Accent 1"
    for celda, texto in zip(tabla.rows[0].cells, ("#", "Insumo", "Unidad", "Cantidad", "Precio unitario", "Subtotal")):
        celda.text = texto
    capitulo_anterior = None
    for indice, linea in enumerate(presupuesto.get("detalle") or [], 1):
        capitulo = (linea.get("capitulo") or "").strip()
        if capitulo and capitulo != capitulo_anterior:
            celdas_capitulo = tabla.add_row().cells
            celda_capitulo = celdas_capitulo[0].merge(celdas_capitulo[-1])
            celda_capitulo.text = f"CAPÍTULO · {capitulo}"
            for corrida in celda_capitulo.paragraphs[0].runs:
                corrida.bold = True
            from docx.oxml import OxmlElement
            from docx.oxml.ns import qn
            sombreado = OxmlElement("w:shd")
            sombreado.set(qn("w:fill"), "DBEAFE")
            celda_capitulo._tc.get_or_add_tcPr().append(sombreado)
        capitulo_anterior = capitulo or capitulo_anterior
        celdas = tabla.add_row().cells
        valores = (indice, linea.get("nombre_insumo", ""), linea.get("unidad_medida", ""),
                   linea.get("cantidad", 0), linea.get("costo_unitario_aplicado", 0), linea.get("subtotal", 0))
        for celda, valor in zip(celdas, valores):
            celda.text = str(valor)
    documento.add_paragraph(f"Costo directo: COP {float(presupuesto.get('costo_directo') or 0):,.2f}")
    for clave, etiqueta in (("administracion", "Administración"), ("imprevistos", "Imprevistos"), ("utilidad", "Utilidad")):
        porcentaje = float(presupuesto.get(f"porcentaje_{clave}") or 0)
        valor = float(presupuesto.get(f"valor_{clave}") or 0)
        documento.add_paragraph(f"{etiqueta} ({porcentaje:g}%): COP {valor:,.2f}")
    total = documento.add_paragraph()
    total.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    corrida = total.add_run(f"TOTAL ESTIMADO: COP {float(presupuesto.get('costo_total') or 0):,.2f}")
    corrida.bold = True
    corrida.font.size = Pt(13)
    nota = documento.add_paragraph("Exportación editable de BIMetrics. Este archivo no contiene firma digital certificada.")
    nota.paragraph_format.space_before = Inches(0.2)

    stream = BytesIO()
    documento.save(stream)
    stream.seek(0)
    return stream
