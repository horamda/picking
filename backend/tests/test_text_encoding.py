import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIRS = (ROOT / 'backend', ROOT / 'frontend' / 'src', ROOT / 'android' / 'app' / 'src')
EXTENSIONS = {'.py', '.js', '.jsx', '.java', '.xml'}
MOJIBAKE = ('\u00c3', '\u00c2', '\u00e2', '\ufffd')


class TextEncodingTest(unittest.TestCase):
    def test_visible_source_text_has_no_mojibake(self):
        failures = []
        for directory in SOURCE_DIRS:
            for path in directory.rglob('*'):
                if path.suffix not in EXTENSIONS or not path.is_file():
                    continue
                text = path.read_text(encoding='utf-8')
                if any(marker in text for marker in MOJIBAKE):
                    failures.append(str(path.relative_to(ROOT)))
        self.assertEqual(failures, [], 'Archivos con caracteres dañados: ' + ', '.join(failures))

    def test_android_string_literals_have_no_replaced_letters(self):
        failures = []
        for path in (ROOT / 'android' / 'app' / 'src').rglob('*.java'):
            text = path.read_text(encoding='utf-8')
            literals = re.findall(r'"(?:\\.|[^"\\])*"', text)
            if any(re.search(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]\?[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]', value)
                   for value in literals):
                failures.append(str(path.relative_to(ROOT)))
        self.assertEqual(failures, [], 'Textos Android con letras reemplazadas: ' + ', '.join(failures))


if __name__ == '__main__':
    unittest.main()
