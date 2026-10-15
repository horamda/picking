"""Synthetic Chess-like PDFs: no operational data or external fixture files."""
from io import BytesIO

from reportlab.pdfgen import canvas


def planilla_pdf(repartos=('TEST-9001',), repeat_page=False):
    output = BytesIO()
    pdf = canvas.Canvas(output)
    for reparto in repartos:
        for _ in range(2 if repeat_page else 1):
            pdf.setFont('Helvetica', 10)
            for y, text in [(800, 'PLANILLA DE CARGA'),
                            (780, f'Reparto Nro: {reparto} | Fecha: 15/10/2026'),
                            (760, 'Transporte: 12 - (TEST123) | Chofer: Prueba | Deposito: Central'),
                            (740, '001 - CANCHA 1'), (720, 'Almacen: Bebidas')]:
                pdf.drawString(30, y, text)
            pdf.drawCentredString(420, 700, 'Bultos')
            pdf.drawCentredString(490, 700, 'Unids')
            for y, sku, bultos, unidades in [(680, '1001', 12, 3), (660, '1001', 2, 0),
                                            (640, '9999', 1, 0), (620, '2731', 2, 0)]:
                pdf.drawString(30, y, f'{sku} Producto prueba 15/10/2026')
                pdf.drawCentredString(420, y, str(bultos))
                pdf.drawCentredString(490, y, str(unidades))
            pdf.showPage()
    pdf.save()
    return output.getvalue()
