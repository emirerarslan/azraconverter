import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


class _DummySignal:
    def connect(self, *_args, **_kwargs):
        return None

    def emit(self, *_args, **_kwargs):
        return None


class _DummyWidget:
    pass


def _install_pyside_stubs():
    package = types.ModuleType("PySide6")
    core = types.ModuleType("PySide6.QtCore")
    gui = types.ModuleType("PySide6.QtGui")
    widgets = types.ModuleType("PySide6.QtWidgets")
    core.Qt = types.SimpleNamespace()
    core.QObject = _DummyWidget
    core.Signal = lambda *_args, **_kwargs: _DummySignal()
    core.QThread = core.QTimer = _DummyWidget
    for name in ("QFont", "QIcon", "QPixmap", "QPainter", "QPainterPath"):
        setattr(gui, name, _DummyWidget)
    for name in (
        "QApplication", "QMainWindow", "QWidget", "QVBoxLayout", "QHBoxLayout",
        "QGridLayout", "QLabel", "QPushButton", "QFileDialog", "QMessageBox",
        "QFrame", "QProgressBar", "QSizePolicy", "QSpacerItem", "QDialog",
        "QScrollArea", "QTableWidget", "QTableWidgetItem",
    ):
        setattr(widgets, name, _DummyWidget)
    sys.modules.update({
        "PySide6": package,
        "PySide6.QtCore": core,
        "PySide6.QtGui": gui,
        "PySide6.QtWidgets": widgets,
    })


_install_pyside_stubs()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main  # noqa: E402


class Progress:
    def __init__(self):
        self.values = []

    def emit(self, value):
        self.values.append(value)


class ConversionTests(unittest.TestCase):
    def test_extension_catalog_covers_legacy_and_open_formats(self):
        expected = {
            ".pdf", ".doc", ".docx", ".docm", ".odt", ".rtf", ".txt",
            ".xls", ".xlsx", ".xlsm", ".xlsb", ".ods", ".csv", ".tsv",
        }
        self.assertTrue(expected.issubset(main.SUPPORTED_EXTENSIONS))

    def test_word_excel_and_excel_word_round_trip(self):
        from docx import Document
        from openpyxl import load_workbook

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "örnek.docx"
            document = Document()
            document.add_heading("Satış Raporu", level=1)
            document.add_paragraph("Türkçe karakter testi: çğıöşü İ")
            table = document.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "Ürün"
            table.cell(0, 1).text = "Tutar"
            table.cell(1, 0).text = "Altın"
            table.cell(1, 1).text = "1250"
            document.save(source)

            progress = Progress()
            excel_output = main.word_to_excel(source, progress)
            self.assertTrue(excel_output.exists())
            workbook = load_workbook(excel_output)
            self.assertIn("Belge Metni", workbook.sheetnames)
            self.assertIn("Tablo 1", workbook.sheetnames)
            self.assertEqual(workbook["Tablo 1"]["A2"].value, "Altın")

            word_output = main.excel_to_word(excel_output, progress)
            self.assertTrue(word_output.exists())
            converted = Document(word_output)
            self.assertGreaterEqual(len(converted.tables), 2)
            self.assertEqual(progress.values[-1], 100)

    def test_pdf_extraction_to_excel_and_word(self):
        from docx import Document
        from openpyxl import load_workbook
        from reportlab.pdfgen import canvas

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "sample.pdf"
            pdf = canvas.Canvas(str(source))
            pdf.drawString(72, 760, "Product | Amount")
            pdf.drawString(72, 740, "Gold | 1250")
            pdf.save()

            progress = Progress()
            excel_output = main.pdf_to_excel(source, progress)
            workbook = load_workbook(excel_output)
            self.assertEqual(workbook.active["A1"].value, "Product")
            self.assertEqual(workbook.active["B2"].value, "1250")

            with mock.patch.object(
                main, "word_to_docx_with_microsoft_word",
                side_effect=RuntimeError("fallback test"),
            ):
                word_output = main.pdf_to_word(source, progress)
            converted = Document(word_output)
            self.assertIn("Product", "\n".join(p.text for p in converted.paragraphs))

    def test_pdf_exports_are_valid(self):
        from docx import Document
        from openpyxl import Workbook
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            progress = Progress()

            word_source = folder / "source.docx"
            document = Document()
            document.add_heading("Başlık", level=1)
            document.add_paragraph("PDF kalite doğrulaması")
            document.save(word_source)
            word_pdf = main.word_to_pdf(word_source, progress)
            self.assertGreaterEqual(len(PdfReader(word_pdf).pages), 1)

            excel_source = folder / "source.xlsx"
            workbook = Workbook()
            workbook.active.append(["Ürün", "Tutar"])
            workbook.active.append(["Altın", 1250])
            workbook.save(excel_source)
            excel_pdf = main.excel_to_pdf(excel_source, progress)
            self.assertGreaterEqual(len(PdfReader(excel_pdf).pages), 1)

    def test_turkish_semicolon_csv_to_word(self):
        from docx import Document

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "veriler.csv"
            source.write_bytes("Ürün;Tutar\r\nÇeyrek;1250\r\n".encode("cp1254"))
            output = main.excel_to_word(source, Progress())
            document = Document(output)
            self.assertEqual(document.tables[0].cell(1, 0).text, "Çeyrek")
            self.assertEqual(document.tables[0].cell(1, 1).text, "1250")


if __name__ == "__main__":
    unittest.main()
