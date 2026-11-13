"""Exportación PDF legible de presupuestos BIMetrics."""

from html import escape
from io import BytesIO

from ..errors import ErrorApi


def exportar_presupuesto_pdf(presupuesto):
    """Genera un resumen PDF sin simular una firma digital certificada."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as error:
        raise ErrorApi(503, "La exportación PDF requiere instalar reportlab") from error

    stream = BytesIO()
    documento = SimpleDocTemplate(
        stream, pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"Presupuesto - {presupuesto.get('nombre_obra') or 'BIMetrics'}",
        author="BIMetrics",
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("BIMetricsTitle", parent=estilos["Title"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=colors.HexColor("#172554"), alignment=TA_CENTER, spaceAfter=4)
    subtitulo = ParagraphStyle("BIMetricsSub", parent=estilos["Normal"], fontSize=9, textColor=colors.HexColor("#475569"), alignment=TA_CENTER, spaceAfter=14)
    celda = ParagraphStyle("BIMetricsCell", parent=estilos["Normal"], fontSize=8, leading=10)
    celda_derecha = ParagraphStyle("BIMetricsRight", parent=celda, alignment=TA_RIGHT)
    historia = [
        Paragraph("BIMETRICS", titulo),
        Paragraph("PRESUPUESTO DE OBRA · COP", subtitulo),
    ]

    meta = [
        [Paragraph("<b>Proyecto</b>", celda), Paragraph(escape(str(presupuesto.get("nombre_obra") or "-")), celda), Paragraph("<b>Ciudad</b>", celda), Paragraph(escape(str(presupuesto.get("ciudad") or "-")), celda)],
        [Paragraph("<b>Presupuesto</b>", celda), Paragraph(f"#{int(presupuesto.get('id_presupuesto') or 0)}", celda), Paragraph("<b>Fecha</b>", celda), Paragraph(escape(str(presupuesto.get("fecha_calculo") or "-")), celda)],
    ]
    tabla_meta = Table(meta, colWidths=[25 * mm, 75 * mm, 20 * mm, 55 * mm])
    tabla_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    historia.extend([tabla_meta, Spacer(1, 10 * mm)])

    def moneda(valor):
        return f"$ {float(valor or 0):,.0f}".replace(",", ".")

    filas = [["#", "Insumo", "Unidad", "Cantidad", "Precio unitario", "Subtotal"]]
    filas_capitulo = []
    capitulo_anterior = None
    for indice, linea in enumerate(presupuesto.get("detalle") or [], start=1):
        capitulo = (linea.get("capitulo") or "").strip()
        if capitulo and capitulo != capitulo_anterior:
            filas_capitulo.append(len(filas))
            filas.append([Paragraph(f"<b>CAPÍTULO · {escape(capitulo)}</b>", celda), "", "", "", "", ""])
        capitulo_anterior = capitulo or capitulo_anterior
        filas.append([
            str(indice),
            Paragraph(escape(str(linea.get("nombre_insumo") or "")), celda),
            Paragraph(escape(str(linea.get("unidad_medida") or "")), celda),
            Paragraph(f"{float(linea.get('cantidad') or 0):,.3f}", celda_derecha),
            Paragraph(moneda(linea.get("costo_unitario_aplicado")), celda_derecha),
            Paragraph(moneda(linea.get("subtotal")), celda_derecha),
        ])
    tabla = Table(filas, colWidths=[8 * mm, 58 * mm, 17 * mm, 22 * mm, 34 * mm, 37 * mm], repeatRows=1)
    estilo_tabla = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for fila_capitulo in filas_capitulo:
        estilo_tabla.extend([
            ("SPAN", (0, fila_capitulo), (-1, fila_capitulo)),
            ("BACKGROUND", (0, fila_capitulo), (-1, fila_capitulo), colors.HexColor("#DBEAFE")),
            ("TEXTCOLOR", (0, fila_capitulo), (-1, fila_capitulo), colors.HexColor("#1E3A8A")),
            ("FONTNAME", (0, fila_capitulo), (-1, fila_capitulo), "Helvetica-Bold"),
            ("ALIGN", (0, fila_capitulo), (-1, fila_capitulo), "LEFT"),
        ])
    tabla.setStyle(TableStyle(estilo_tabla))
    historia.append(tabla)
    historia.append(Spacer(1, 5 * mm))
    resumen = [["Costo directo", moneda(presupuesto.get("costo_directo"))]]
    for etiqueta, nombre in (("administracion", "Administración"), ("imprevistos", "Imprevistos"), ("utilidad", "Utilidad")):
        porcentaje = float(presupuesto.get(f"porcentaje_{etiqueta}") or 0)
        resumen.append([f"{nombre} ({porcentaje:g}%)", moneda(presupuesto.get(f"valor_{etiqueta}"))])
    resumen.append(["TOTAL ESTIMADO", moneda(presupuesto.get("costo_total"))])
    tabla_resumen = Table(resumen, colWidths=[115 * mm, 55 * mm], hAlign="RIGHT")
    tabla_resumen.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DBEAFE")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    historia.extend([
        tabla_resumen,
        Spacer(1, 12 * mm),
        Paragraph("Este documento es una exportación del presupuesto registrado en BIMetrics. No contiene una firma digital certificada ni sustituye una revisión y aprobación formal.", ParagraphStyle("Nota", parent=celda, fontSize=8, textColor=colors.HexColor("#64748B"))),
    ])

    def pie(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(17 * mm, 11 * mm, "BIMetrics · Presupuesto de obra")
        canvas.drawRightString(A4[0] - 17 * mm, 11 * mm, f"Página {_doc.page}")
        canvas.restoreState()

    documento.build(historia, onFirstPage=pie, onLaterPages=pie)
    stream.seek(0)
    return stream
