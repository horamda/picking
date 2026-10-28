"""Column boundaries and optional expiry dates in warehouse PDFs."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.pdf_parser import parse_item_row
from services.pdf_parser import parse_pdf_file
from io import BytesIO
from reportlab.pdfgen import canvas

def word(text, left, right):
    return dict(text=text, x0=left, x1=right)

class PdfColumnsTest(unittest.TestCase):
    def test_missing_expiry_keeps_numeric_description_and_loose_units(self):
        row = [word('16371', 35, 60), word('RED BULL CAN 6X4', 70, 154), word('250', 156, 172), word('4', 440, 445)]
        item = parse_item_row(row, 366, 432.5)
        self.assertEqual((item['bultos'], item['unidades']), (0, 4))
        self.assertEqual(item['descripcion'], 'RED BULL CAN 6X4 250')
        self.assertIsNone(item['fecha_reparto'])

    def test_discharge_never_added_to_load(self):
        row = [word('1001', 35, 60), word('Producto', 70, 120), word('21/01/27', 280, 315),
               word('6', 375, 380), word('3', 440, 445), word('99', 500, 510), word('8', 570, 575)]
        item = parse_item_row(row, 366, 432.5)
        self.assertEqual((item['bultos'], item['unidades']), (6, 3))

    def test_undated_product_is_imported_but_empty_containers_are_not(self):
        output = BytesIO(); pdf = canvas.Canvas(output)
        pdf.setFont('Helvetica', 10)
        for y, text in [(800, 'PLANILLA DE CARGA'), (780, 'Reparto Nro: TEST | Fecha: 27/10/2026'),
                        (760, 'Transporte: 03 | Chofer: Test | Deposito: Central'),
                        (740, '001 - CANCHA 1'), (720, 'Almacen: Test')]:
            pdf.drawString(30, y, text)
        for x, label in [(30, 'SKU'), (280, 'Venc.'), (366, 'Bultos'), (432, 'Unids'), (496, 'Bultos'), (562, 'Unids')]:
            pdf.drawCentredString(x, 700, label)
        pdf.drawString(30, 680, '16371 Bebida 250'); pdf.drawCentredString(432, 680, '4')
        pdf.drawCentredString(496, 680, '99')
        pdf.drawString(30, 660, 'VACIOS CORRESPONDIENTES A LOS ARTICULOS A CARGAR')
        for x, label in [(30, 'SKU'), (366, 'Bultos'), (432, 'Unidades')]:
            pdf.drawCentredString(x, 640, label)
        pdf.drawString(30, 620, '2731 Envases'); pdf.drawCentredString(366, 620, '100')
        pdf.save(); output.seek(0)
        items = parse_pdf_file(output)['items']
        self.assertEqual([(i['sku'], i['bultos'], i['unidades']) for i in items], [('16371', 0, 4)])

if __name__ == '__main__':
    unittest.main()
