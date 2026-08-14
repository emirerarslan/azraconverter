import sys
import os
import json
import subprocess
import traceback
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import urlopen

# Dönüştürme kütüphaneleri açılışta değil, ilgili işlem seçildiğinde yüklenir.
# Böylece arayüz mümkün olan en kısa sürede görüntülenir.
OCR_AVAILABLE = None
_PDF_FONTS = None

from PySide6.QtCore import Qt, QObject, Signal, QThread, QUrl
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QPainterPath, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QFrame,
    QProgressBar, QSizePolicy, QSpacerItem, QDialog, QScrollArea,
    QTableWidget, QTableWidgetItem
)


APP_NAME = "AZRA CONVERTER"
APP_VERSION = "1.0.1"
UPDATE_CONFIG_FILE = "update_config.json"


def resource_path(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / name)


def app_folder_path(name):
    """Paketlenmiş uygulamanın yanındaki, kullanıcı tarafından düzenlenebilir dosya."""
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return base / name


def version_key(version):
    parts = []
    for part in str(version).strip().lstrip("vV").split("."):
        digits = "".join(char for char in part if char.isdigit())
        parts.append(int(digits or 0))
    return tuple((parts + [0, 0, 0])[:3])


def load_update_config():
    config_path = app_folder_path(UPDATE_CONFIG_FILE)
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}




def register_turkish_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    candidates = [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
    ]

    for regular, bold in candidates:
        if os.path.exists(regular):
            try:
                pdfmetrics.registerFont(TTFont("AzraFont", regular))
                if os.path.exists(bold):
                    pdfmetrics.registerFont(TTFont("AzraFontBold", bold))
                else:
                    pdfmetrics.registerFont(TTFont("AzraFontBold", regular))
                return "AzraFont", "AzraFontBold"
            except Exception:
                pass

    return "Helvetica", "Helvetica-Bold"


def get_pdf_fonts():
    global _PDF_FONTS
    if _PDF_FONTS is None:
        _PDF_FONTS = register_turkish_fonts()
    return _PDF_FONTS


def get_ocr_dependencies():
    global OCR_AVAILABLE

    if OCR_AVAILABLE is False:
        return None

    try:
        import fitz
        import pytesseract
        from PIL import Image
        OCR_AVAILABLE = True
        return fitz, pytesseract, Image
    except ImportError:
        OCR_AVAILABLE = False
        return None


def clean_text(value):
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def unique_output(path):
    path = Path(path)
    if not path.exists():
        return path

    i = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not candidate.exists():
            return candidate
        i += 1



def find_tesseract():
    candidates = [
        os.environ.get("TESSERACT_CMD", ""),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate

    try:
        import shutil
        return shutil.which("tesseract")
    except Exception:
        return None


def smart_ocr_page(page):
    """Taranmış PDF sayfasını OCR ile okuyup sütunları koordinatlardan çıkarır."""
    dependencies = get_ocr_dependencies()
    if not dependencies:
        raise RuntimeError(
            "OCR paketleri kurulu değil. "
            "python -m pip install pytesseract pillow pymupdf"
        )

    fitz, pytesseract, Image = dependencies

    tess = find_tesseract()

    if not tess:
        raise RuntimeError(
            r"Tesseract bulunamadı: C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

    pytesseract.pytesseract.tesseract_cmd = tess

    pix = page.get_pixmap(
        matrix=fitz.Matrix(2.5, 2.5),
        alpha=False
    )

    image = Image.frombytes(
        "RGB",
        [pix.width, pix.height],
        pix.samples
    )

    try:
        data = pytesseract.image_to_data(
            image,
            lang="tur+eng",
            config="--psm 6",
            output_type=pytesseract.Output.DICT,
        )
    except Exception:
        data = pytesseract.image_to_data(
            image,
            lang="eng",
            config="--psm 6",
            output_type=pytesseract.Output.DICT,
        )

    words = []

    for i, raw in enumerate(data.get("text", [])):
        text = str(raw).strip()

        try:
            confidence = float(data["conf"][i])
        except Exception:
            confidence = -1

        if not text or confidence < 15:
            continue

        left = int(data["left"][i])
        top = int(data["top"][i])
        width = int(data["width"][i])
        height = int(data["height"][i])

        words.append({
            "text": text,
            "left": left,
            "right": left + width,
            "top": top,
            "height": height,
            "center_y": top + height / 2,
        })

    # Kelimeleri yatay satırlara ayır.
    lines = []

    for word in sorted(
        words,
        key=lambda x: (x["top"], x["left"])
    ):
        target = None

        for line in lines:
            tolerance = max(
                8,
                int(line["avg_height"] * 0.65)
            )

            if abs(
                word["center_y"] - line["center_y"]
            ) <= tolerance:
                target = line
                break

        if target is None:
            lines.append({
                "center_y": word["center_y"],
                "avg_height": max(word["height"], 1),
                "words": [word],
            })
        else:
            target["words"].append(word)

            target["center_y"] = sum(
                x["center_y"]
                for x in target["words"]
            ) / len(target["words"])

            target["avg_height"] = sum(
                x["height"]
                for x in target["words"]
            ) / len(target["words"])

    rows = []

    for line in sorted(
        lines,
        key=lambda x: x["center_y"]
    ):
        row_words = sorted(
            line["words"],
            key=lambda x: x["left"]
        )

        cells = []

        for word in row_words:
            if not cells:
                cells.append({
                    "text": word["text"],
                    "right": word["right"],
                })
                continue

            gap = word["left"] - cells[-1]["right"]

            # Büyük yatay boşluk = yeni sütun.
            threshold = max(
                28,
                int(line["avg_height"] * 1.6)
            )

            if gap >= threshold:
                cells.append({
                    "text": word["text"],
                    "right": word["right"],
                })
            else:
                cells[-1]["text"] += " " + word["text"]
                cells[-1]["right"] = word["right"]

        if cells:
            rows.append([
                clean_text(cell["text"])
                for cell in cells
            ])

    return rows


def pdf_to_excel(src, progress):
    import pdfplumber
    src = Path(src)
    out = unique_output(
        src.with_name(src.stem + "_Excel.xlsx")
    )

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment

    wb = Workbook()
    first_sheet = True

    with pdfplumber.open(str(src)) as pdf:
        total = max(len(pdf.pages), 1)

        for page_no, page in enumerate(
            pdf.pages,
            start=1
        ):
            ws = (
                wb.active
                if first_sheet
                else wb.create_sheet()
            )

            ws.title = f"Sayfa {page_no}"
            first_sheet = False

            tables = page.extract_tables()

            if tables:
                row_index = 1

                for table in tables:
                    for row in table:
                        values = [
                            clean_text(x)
                            for x in (row or [])
                        ]

                        if values:
                            for col_index, value in enumerate(
                                values,
                                start=1
                            ):
                                ws.cell(
                                    row=row_index,
                                    column=col_index,
                                    value=value
                                )

                            row_index += 1

                    row_index += 1

            else:
                text = page.extract_text() or ""

                if text.strip():
                    rows = [
                        ocr_text_to_columns(line)
                        for line in text.splitlines()
                        if clean_text(line)
                    ]
                else:
                    # Taranmış PDF -> koordinat tabanlı OCR.
                    dependencies = get_ocr_dependencies()
                    if not dependencies:
                        raise RuntimeError("OCR paketleri kurulu değil.")
                    fitz, _, _ = dependencies
                    with fitz.open(str(src)) as ocr_doc:
                        rows = smart_ocr_page(
                            ocr_doc[page_no - 1]
                        )

                for row_index, values in enumerate(
                    rows,
                    start=1
                ):
                    for col_index, value in enumerate(
                        values,
                        start=1
                    ):
                        ws.cell(
                            row=row_index,
                            column=col_index,
                            value=clean_text(value)
                        )

            if ws.max_row:
                for cell in ws[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(
                        vertical="top"
                    )

            for col in ws.columns:
                letter = col[0].column_letter

                max_len = max(
                    (
                        len(clean_text(cell.value))
                        for cell in col
                    ),
                    default=0
                )

                ws.column_dimensions[
                    letter
                ].width = min(
                    max(max_len + 2, 10),
                    45
                )

            progress.emit(
                int(page_no / total * 100)
            )

    wb.save(str(out))
    return out



def pdf_to_word(src, progress):
    import pdfplumber
    from docx import Document
    from docx.shared import Pt
    src = Path(src)
    out = unique_output(
        src.with_name(src.stem + "_Word.docx")
    )

    doc = Document()

    with pdfplumber.open(str(src)) as pdf:
        total = max(len(pdf.pages), 1)

        for page_no, page in enumerate(
            pdf.pages,
            start=1
        ):
            if page_no > 1:
                doc.add_page_break()

            tables = page.extract_tables()

            if tables:
                for table_data in tables:
                    rows = [
                        [
                            clean_text(x)
                            for x in (row or [])
                        ]
                        for row in table_data
                    ]

                    max_cols = max(
                        (
                            len(row)
                            for row in rows
                        ),
                        default=0
                    )

                    if rows and max_cols:
                        table = doc.add_table(
                            rows=len(rows),
                            cols=max_cols
                        )

                        table.style = "Table Grid"

                        for r, row in enumerate(rows):
                            for c in range(max_cols):
                                table.cell(
                                    r,
                                    c
                                ).text = (
                                    row[c]
                                    if c < len(row)
                                    else ""
                                )

                        doc.add_paragraph()

            else:
                text = page.extract_text() or ""

                if text.strip():
                    lines = [
                        clean_text(line)
                        for line in text.splitlines()
                        if clean_text(line)
                    ]
                else:
                    dependencies = get_ocr_dependencies()
                    if not dependencies:
                        raise RuntimeError("OCR paketleri kurulu değil.")
                    fitz, _, _ = dependencies
                    with fitz.open(str(src)) as ocr_doc:
                        rows = smart_ocr_page(
                            ocr_doc[page_no - 1]
                        )

                    lines = [
                        "    ".join(row)
                        for row in rows
                        if row
                    ]

                for line in lines:
                    paragraph = doc.add_paragraph(line)
                    paragraph.paragraph_format.space_after = Pt(4)

            progress.emit(
                int(page_no / total * 100)
            )

    doc.save(str(out))
    return out



def make_pdf_styles():
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    pdf_font, pdf_font_bold = get_pdf_fonts()
    return {
        "title": ParagraphStyle(
            "AzraTitle",
            fontName=pdf_font_bold,
            fontSize=15,
            leading=19,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "AzraBody",
            fontName=pdf_font,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "AzraSmall",
            fontName=pdf_font,
            fontSize=7.5,
            leading=9,
        ),
    }


def excel_to_pdf(src, progress):
    from openpyxl import load_workbook
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak

    src = Path(src)
    out = unique_output(src.with_name(src.stem + "_PDF.pdf"))

    wb = load_workbook(str(src), data_only=True)
    sheet_names = wb.sheetnames
    styles = make_pdf_styles()
    pdf_font, pdf_font_bold = get_pdf_fonts()

    doc = SimpleDocTemplate(
        str(out),
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    story = []
    total = max(len(sheet_names), 1)

    for index, sheet_name in enumerate(sheet_names, start=1):
        ws = wb[sheet_name]

        story.append(Paragraph(clean_text(sheet_name), styles["title"]))

        data = []
        for row in ws.iter_rows(values_only=True):
            values = [clean_text(v) for v in row]
            while values and values[-1] == "":
                values.pop()
            if values:
                data.append(values)

        if data:
            max_cols = max(len(row) for row in data)
            data = [row + [""] * (max_cols - len(row)) for row in data]

            usable_width = landscape(A4)[0] - 20 * mm
            col_width = usable_width / max_cols

            table = Table(
                [[Paragraph(v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["small"])
                  for v in row] for row in data],
                colWidths=[col_width] * max_cols,
                repeatRows=1,
            )

            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D6B16B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), pdf_font_bold),
                ("FONTNAME", (0, 1), (-1, -1), pdf_font),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))

            story.append(table)
        else:
            story.append(Paragraph("Bu sayfada veri bulunamadı.", styles["body"]))

        if index < total:
            story.append(PageBreak())

        progress.emit(int(index / total * 100))

    doc.build(story)
    return out


def word_to_pdf_with_microsoft_word(src, out):
    """Eski .doc belgelerini Word'ün kendi PDF dışa aktarmasıyla dönüştürür."""
    def ps_quote(value):
        return str(value).replace("'", "''")

    script = (
        "$ErrorActionPreference = 'Stop'; "
        "$word = New-Object -ComObject Word.Application; "
        "try { "
        f"$document = $word.Documents.Open('{ps_quote(src)}', $false, $true); "
        f"$document.ExportAsFixedFormat('{ps_quote(out)}', 17); "
        "} finally { "
        "if ($document) { $document.Close($false) }; "
        "if ($word) { $word.Quit() } "
        "}"
    )
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        startupinfo=startupinfo,
        check=False,
    )
    if result.returncode != 0 or not out.exists():
        detail = clean_text(result.stderr) or clean_text(result.stdout)
        raise RuntimeError(
            "Bu .doc belgesini dönüştürmek için bilgisayarda Microsoft Word kurulu olmalıdır."
            + (f"\n\nAyrıntı: {detail}" if detail else "")
        )


def word_to_pdf(src, progress):
    from docx import Document
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    src = Path(src)
    out = unique_output(src.with_name(src.stem + "_PDF.pdf"))

    # python-docx eski ikili .doc biçimini okuyamaz. Word, biçimi koruyarak
    # hem .doc hem de .docx belgelerini PDF olarak dışa aktarabilir.
    if src.suffix.lower() == ".doc":
        progress.emit(10)
        word_to_pdf_with_microsoft_word(src, out)
        progress.emit(100)
        return out

    document = Document(str(src))
    styles = make_pdf_styles()
    pdf_font, pdf_font_bold = get_pdf_fonts()

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    story = []
    blocks = max(len(document.paragraphs) + len(document.tables), 1)
    done = 0

    for paragraph in document.paragraphs:
        text = clean_text(paragraph.text)

        if text:
            style = styles["body"]
            if paragraph.style and paragraph.style.name:
                name = paragraph.style.name.lower()
                if "title" in name or "heading" in name:
                    style = styles["title"]

            safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe, style))
            story.append(Spacer(1, 3 * mm))

        done += 1
        progress.emit(int(done / blocks * 100))

    for table_data in document.tables:
        rows = []

        for row in table_data.rows:
            values = []
            for cell in row.cells:
                values.append(clean_text(cell.text))
            rows.append(values)

        if rows:
            max_cols = max(len(r) for r in rows)
            rows = [r + [""] * (max_cols - len(r)) for r in rows]

            usable_width = A4[0] - 36 * mm
            col_width = usable_width / max_cols

            table = Table(
                [[Paragraph(v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["small"])
                  for v in row] for row in rows],
                colWidths=[col_width] * max_cols,
                repeatRows=1,
            )

            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D6B16B")),
                ("FONTNAME", (0, 0), (-1, 0), pdf_font_bold),
                ("FONTNAME", (0, 1), (-1, -1), pdf_font),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))

            story.append(Spacer(1, 4 * mm))
            story.append(table)
            story.append(Spacer(1, 4 * mm))

        done += 1
        progress.emit(int(done / blocks * 100))

    if not story:
        story.append(Paragraph("Belgede dönüştürülebilecek içerik bulunamadı.", styles["body"]))

    doc.build(story)
    return out


class UpdateWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def run(self):
        config = load_update_config()
        manifest_url = clean_text(config.get("manifest_url"))

        if not manifest_url:
            self.error.emit(
                "Güncelleme adresi tanımlı değil. Uygulamanın yanındaki "
                "update_config.json dosyasına sunucu adresini ekleyin."
            )
            return

        try:
            with urlopen(manifest_url, timeout=6) as response:
                manifest = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            self.error.emit(f"Güncelleme sunucusuna ulaşılamadı: {exc}")
            return

        latest = clean_text(manifest.get("version"))
        if not latest:
            self.error.emit("Güncelleme bilgisinde sürüm numarası bulunamadı.")
            return

        download_url = clean_text(manifest.get("download_url"))
        if download_url:
            download_url = urljoin(manifest_url, download_url)

        self.finished.emit({
            "version": latest,
            "is_new": version_key(latest) > version_key(APP_VERSION),
            "download_url": download_url,
            "notes": clean_text(manifest.get("notes")),
        })


class ConverterWorker(QObject):
    finished = Signal(str)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, mode, source):
        super().__init__()
        self.mode = mode
        self.source = source

    def run(self):
        try:
            if self.mode == "pdf_excel":
                result = pdf_to_excel(self.source, self.progress)
            elif self.mode == "pdf_word":
                result = pdf_to_word(self.source, self.progress)
            elif self.mode == "excel_pdf":
                result = excel_to_pdf(self.source, self.progress)
            elif self.mode == "word_pdf":
                result = word_to_pdf(self.source, self.progress)
            else:
                raise ValueError("Geçersiz dönüşüm seçildi.")

            self.finished.emit(str(result))
        except Exception as exc:
            # Kullanıcıya hata izinin tamamı yerine doğrudan çözüm odaklı mesajı göster.
            self.error.emit(str(exc) or traceback.format_exc())



class DropZone(QFrame):
    fileDropped = Signal(str)
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("dropZone")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("↓")
        icon.setAlignment(Qt.AlignCenter)
        icon.setObjectName("dropIcon")

        title = QLabel("DOSYAYI BURAYA BIRAK")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("dropTitle")

        sub = QLabel("PDF • Excel • Word")
        sub.setAlignment(Qt.AlignCenter)
        sub.setObjectName("dropSub")

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(sub)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.fileDropped.emit(path)
        event.acceptProposedAction()


class NavButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setCheckable(True)
        self.setMinimumHeight(46)


class ConversionCard(QFrame):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.setObjectName("conversionCard")
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(5)

        self.icon = QLabel("↗")
        self.icon.setObjectName("cardIcon")
        self.icon.setAlignment(Qt.AlignLeft)

        self.title = QLabel(title)
        self.title.setObjectName("cardTitle")

        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("cardSubtitle")
        self.subtitle.setWordWrap(True)

        layout.addWidget(self.icon)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)

        self.button = QPushButton("BAŞLAT")
        self.button.setObjectName("cardButton")
        self.button.setMinimumHeight(34)
        layout.addWidget(self.button)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.source_file = None
        self.thread = None
        self.worker = None
        self.current_page = "converter"

        self.setWindowTitle(APP_NAME)
        # Pencere serbestçe yeniden boyutlandırılabilir. İçerik, dar veya
        # kısa ekranlarda kaydırılabildiği için kartlar erişilemez kalmaz.
        self.setMinimumSize(900, 620)
        self.resize(1200, 780)

        icon_path = resource_path("azra_gold.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QMainWindow {
                background: #0A0A0B;
            }
            QScrollArea#contentScroll,
            QScrollArea#contentScroll > QWidget > QWidget {
                background: #0A0A0B;
                border: none;
            }
            QWidget {
                color: #F3F1EC;
                font-family: "Segoe UI";
            }
            QFrame#sidebar {
                background: #101011;
                border-right: 1px solid #252321;
            }
            QLabel#logoText {
                color: #D6B16B;
                font-size: 17px;
                font-weight: 600;
            }
            QLabel#version {
                color: #66615A;
                font-size: 11px;
            }
            QLabel#pageTitle {
                color: #F7F4ED;
                font-size: 29px;
                font-weight: 750;
            }
            QLabel#pageSubtitle {
                color: #85817A;
                font-size: 13px;
            }
            QLabel#eyebrow {
                color: #D6B16B;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QPushButton#nav {
                background: transparent;
                color: #8D8982;
                border: none;
                border-radius: 9px;
                text-align: left;
                padding: 0 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#nav:hover {
                background: #24211B;
                border: 1px solid #4A3C25;
                color: #E9E5DC;
            }
            QPushButton#nav:pressed {
                background: #2A241A;
                color: #E2C27C;
            }
            QPushButton#nav:checked {
                background: #211E18;
                color: #D6B16B;
                border-left: 2px solid #D6B16B;
            }
            QFrame#dropZone {
                background: #111112;
                border: 1px dashed #4A453D;
                border-radius: 16px;
                min-height: 210px;
            }
            QFrame#dropZone:hover,
            QFrame#dropZone[dragging="true"] {
                background: #15130F;
                border: 1px dashed #D6B16B;
            }
            QLabel#dropIcon {
                color: #D6B16B;
                font-size: 35px;
                font-weight: 300;
            }
            QLabel#dropTitle {
                color: #EDE9E1;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#dropSub {
                color: #68645D;
                font-size: 12px;
            }
            QFrame#fileBar {
                background: #121213;
                border: 1px solid #242321;
                border-radius: 10px;
            }
            QLabel#fileName {
                color: #C9C4BA;
                font-size: 12px;
            }
            QLabel#status {
                color: #817C73;
                font-size: 11px;
            }
            QPushButton#selectButton {
                background: #D6B16B;
                color: #11100E;
                border: none;
                border-radius: 9px;
                padding: 0 24px;
                font-weight: 800;
            }
            QPushButton#selectButton:hover {
                background: #E2C27C;
            }
            QFrame#conversionCard {
                background: #141414;
                border: 1px solid #272522;
                border-radius: 13px;
            }
            QFrame#conversionCard:hover {
                border: 1px solid #80683E;
                background: #171614;
            }
            QLabel#cardIcon {
                color: #D6B16B;
                font-size: 25px;
                font-weight: 600;
            }
            QLabel#cardTitle {
                color: #EDE9E1;
                font-size: 14px;
                font-weight: 750;
            }
            QLabel#cardSubtitle {
                color: #716D66;
                font-size: 10px;
            }
            QPushButton#cardButton {
                background: #1C1B19;
                color: #B9A276;
                border: 1px solid #39342C;
                border-radius: 7px;
                font-size: 10px;
                font-weight: 750;
            }
            QPushButton#cardButton:hover {
                background: #D6B16B;
                color: #11100E;
            }
            QPushButton#cardButton:disabled {
                color: #4B4843;
                border-color: #242320;
                background: #151514;
            }
            QProgressBar {
                background: #181817;
                border: none;
                border-radius: 5px;
                height: 8px;
            }
            QProgressBar::chunk {
                background: #D6B16B;
                border-radius: 5px;
            }
            QScrollBar:vertical {
                background: #0D0D0E;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #33312D;
                border-radius: 4px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(225)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 18)
        side.setSpacing(8)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo_pix = QPixmap(resource_path("azra_gold_logo_real_transparent.png"))
        if not logo_pix.isNull():
            logo_pix = logo_pix.scaled(165, 115, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(logo_pix)
        side.addWidget(logo)

        brand = QLabel("AZRA GOLD")
        brand.setObjectName("logoText")
        brand.setAlignment(Qt.AlignCenter)
        side.addWidget(brand)
        side.addSpacing(24)

        self.nav_converter = NavButton("  ◈   Dönüştürücü")
        self.nav_history = NavButton("  ◷   Geçmiş")
        self.nav_about = NavButton("  ⓘ   Hakkında")
        for b in [self.nav_converter, self.nav_history, self.nav_about]:
            b.setObjectName("nav")
            side.addWidget(b)

        # Sidebar navigation is active, not decorative.
        self.nav_converter.clicked.connect(self.show_converter)
        self.nav_history.clicked.connect(self.show_history)
        self.nav_about.clicked.connect(self.show_about)

        self.nav_converter.setChecked(True)
        side.addStretch(1)

        version = QLabel("Azra Converter\nv1.0.0")
        version.setObjectName("version")
        version.setAlignment(Qt.AlignCenter)
        side.addWidget(version)

        root.addWidget(sidebar)

        # Main content
        content = QWidget()
        content.setObjectName("mainContent")
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(42, 32, 42, 28)
        content_layout.setSpacing(15)

        top = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(4)

        eyebrow = QLabel("AZRA GOLD  •  DOCUMENT TOOLS")
        eyebrow.setObjectName("eyebrow")
        heading.addWidget(eyebrow)

        title = QLabel("Dosyalarınızı dönüştürün.")
        title.setObjectName("pageTitle")
        heading.addWidget(title)

        subtitle = QLabel("PDF, Word ve Excel arasında hızlı ve güvenli dönüşüm.")
        subtitle.setObjectName("pageSubtitle")
        heading.addWidget(subtitle)

        top.addLayout(heading)
        top.addStretch(1)

        content_layout.addLayout(top)

        self.drop_zone = DropZone()
        self.drop_zone.fileDropped.connect(self.set_file)
        self.drop_zone.clicked.connect(self.choose_file)
        content_layout.addWidget(self.drop_zone)

        file_bar = QFrame()
        file_bar.setObjectName("fileBar")
        file_layout = QHBoxLayout(file_bar)
        file_layout.setContentsMargins(14, 8, 8, 8)

        self.file_label = QLabel("Henüz dosya seçilmedi")
        self.file_label.setObjectName("fileName")
        file_layout.addWidget(self.file_label, 1)

        select_btn = QPushButton("DOSYA SEÇ")
        select_btn.setObjectName("selectButton")
        select_btn.setFixedHeight(38)
        select_btn.clicked.connect(self.choose_file)
        file_layout.addWidget(select_btn)

        content_layout.addWidget(file_bar)

        cards = QGridLayout()
        cards.setHorizontalSpacing(10)
        cards.setVerticalSpacing(10)

        self.pdf_excel_card = ConversionCard("PDF  →  EXCEL", "OCR + akıllı tablo algılama")
        self.pdf_word_card = ConversionCard("PDF  →  WORD", "OCR + düzenlenebilir metin")
        self.excel_pdf_card = ConversionCard("EXCEL  →  PDF", "Sayfa düzenini koru")
        self.word_pdf_card = ConversionCard("WORD  →  PDF", "Belgeyi PDF olarak dışa aktar")

        cards.addWidget(self.pdf_excel_card, 0, 0)
        cards.addWidget(self.pdf_word_card, 0, 1)
        cards.addWidget(self.excel_pdf_card, 1, 0)
        cards.addWidget(self.word_pdf_card, 1, 1)

        self.pdf_excel_card.button.clicked.connect(lambda: self.start_conversion("pdf_excel"))
        self.pdf_word_card.button.clicked.connect(lambda: self.start_conversion("pdf_word"))
        self.excel_pdf_card.button.clicked.connect(lambda: self.start_conversion("excel_pdf"))
        self.word_pdf_card.button.clicked.connect(lambda: self.start_conversion("word_pdf"))

        content_layout.addLayout(cards)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        content_layout.addWidget(self.progress)

        self.status = QLabel("Hazır")
        self.status.setObjectName("status")
        content_layout.addWidget(self.status)

        content_scroll = QScrollArea()
        content_scroll.setObjectName("contentScroll")
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.NoFrame)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_scroll.setWidget(content)
        root.addWidget(content_scroll, 1)

        self.update_buttons()

    def _select_nav(self, active):
        for button in [self.nav_converter, self.nav_history,
                       self.nav_about]:
            button.blockSignals(True)
            button.setChecked(button is active)
            button.blockSignals(False)

    def show_converter(self):
        self._select_nav(self.nav_converter)
        self.status.setText("Hazır")

    def _history_path(self):
        return Path.home() / "AzraConverter_history.json"

    def _load_history(self):
        import json
        p = self._history_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_history(self, mode, source, output, success=True):
        import json
        from datetime import datetime
        labels = {
            "pdf_excel": "PDF → Excel",
            "pdf_word": "PDF → Word",
            "excel_pdf": "Excel → PDF",
            "word_pdf": "Word → PDF",
        }
        data = self._load_history()
        data.insert(0, {
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "file": Path(source).name,
            "operation": labels.get(mode, mode),
            "output": str(output),
            "status": "Başarılı" if success else "Hata",
        })
        self._history_path().write_text(
            json.dumps(data[:100], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _dark_dialog(self, title, width=760, height=500):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(width, height)
        dialog.resize(width, height)
        dialog.setStyleSheet("""
            QDialog { background: #0F0F10; }
            QLabel { color: #E9E5DC; }
            QLabel#dialogTitle {
                color: #D6B16B; font-size: 22px; font-weight: 800;
            }
            QLabel#muted { color: #8E887E; font-size: 12px; }
            QTableWidget {
                background: #121212; color: #D9D4CB;
                gridline-color: #292824;
                border: 1px solid #2A2824; border-radius: 8px;
            }
            QHeaderView::section {
                background: #1B1A18; color: #D6B16B;
                border: none; padding: 9px; font-weight: 700;
            }
            QPushButton {
                background: #1A1917; color: #D6B16B;
                border: 1px solid #3B352B; border-radius: 8px;
                padding: 9px 20px; font-weight: 700;
            }
            QPushButton:hover {
                background: #D6B16B; color: #11100E;
            }
        """)
        return dialog

    def show_converter(self):
        self._select_nav(self.nav_converter)
        self.status.setText("Hazır")

    def show_history(self):
        self._select_nav(self.nav_history)

        # Modal dialog: exec() guarantees the history window is displayed.
        if hasattr(self, "_history_dialog") and self._history_dialog is not None:
            try:
                self._history_dialog.close()
            except Exception:
                pass

        dialog = self._dark_dialog("Azra Converter • Geçmiş", 820, 500)
        self._history_dialog = dialog
        dialog.finished.connect(lambda _=0: self._history_dialog_closed())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(12)

        title = QLabel("Dönüştürme Geçmişi")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        subtitle = QLabel("Son işlemleriniz burada tutulur.")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Tarih", "Dosya", "İşlem", "Durum", "Çıktı"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        history = self._load_history()
        table.setRowCount(len(history))

        for row, item in enumerate(history):
            values = [
                item.get("date", ""),
                item.get("file", ""),
                item.get("operation", ""),
                item.get("status", ""),
                Path(item.get("output", "")).name if item.get("output") else "",
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(str(value)))

        layout.addWidget(table, 1)

        close = QPushButton("KAPAT")
        close.clicked.connect(dialog.close)
        layout.addWidget(close, 0, Qt.AlignRight)

        dialog.exec()
        self._history_dialog = None
        self._select_nav(self.nav_converter)

    def _history_dialog_closed(self):
        self._history_dialog = None
        self._select_nav(self.nav_converter)

    def check_for_updates(self):
        if getattr(self, "_update_thread", None) is not None:
            return

        self.update_status.setText("Güncellemeler kontrol ediliyor...")
        self.update_button.setEnabled(False)
        self._update_thread = QThread()
        self._update_worker = UpdateWorker()
        self._update_worker.moveToThread(self._update_thread)
        self._update_thread.started.connect(self._update_worker.run)
        self._update_worker.finished.connect(self.update_check_finished)
        self._update_worker.error.connect(self.update_check_error)
        self._update_worker.finished.connect(self._update_thread.quit)
        self._update_worker.error.connect(self._update_thread.quit)
        self._update_thread.finished.connect(self._update_worker.deleteLater)
        self._update_thread.finished.connect(self._update_thread_finished)
        self._update_thread.start()

    def _update_thread_finished(self):
        self._update_thread = None
        self._update_worker = None

    def update_check_finished(self, result):
        latest = result["version"]
        if result["is_new"] and result["download_url"]:
            self._update_download_url = result["download_url"]
            note = f" — {result['notes']}" if result["notes"] else ""
            self.update_status.setText(f"Yeni sürüm hazır: v{latest}{note}")
            self.update_button.setText("YENİ SÜRÜMÜ İNDİR")
            self.update_button.setEnabled(True)
            try:
                self.update_button.clicked.disconnect()
            except RuntimeError:
                pass
            self.update_button.clicked.connect(self.download_latest_update)
        elif result["is_new"]:
            self.update_status.setText(f"v{latest} hazır; indirme bağlantısı tanımlı değil.")
            self.update_button.setEnabled(True)
        else:
            self.update_status.setText(f"Güncel sürümü kullanıyorsunuz (v{APP_VERSION}).")
            self.update_button.setText("GÜNCELLEMELERİ KONTROL ET")
            self.update_button.setEnabled(True)

    def update_check_error(self, message):
        self.update_status.setText(message)
        self.update_button.setText("GÜNCELLEMELERİ KONTROL ET")
        self.update_button.setEnabled(True)

    def download_latest_update(self):
        url = getattr(self, "_update_download_url", "")
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def show_about(self):
        self._select_nav(self.nav_about)

        dialog = self._dark_dialog("Azra Converter Hakkında", 620, 640)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(34, 28, 34, 24)
        layout.setSpacing(9)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        pix = QPixmap(resource_path("azra_gold_logo_real_transparent.png"))
        if not pix.isNull():
            logo.setPixmap(pix.scaled(220, 145, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(logo)

        brand = QLabel("AZRA GOLD")
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet(
            "color:#D6B16B; font-size:14px; font-weight:800; letter-spacing:2px;"
        )
        layout.addWidget(brand)

        title = QLabel("AZRA CONVERTER")
        title.setObjectName("dialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"Sürüm {APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color:#8E887E; font-size:12px; font-weight:600;")
        layout.addWidget(version)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#2D2A25;")
        layout.addWidget(line)

        purpose_title = QLabel("PROGRAMIN AMACI")
        purpose_title.setAlignment(Qt.AlignCenter)
        purpose_title.setStyleSheet(
            "color:#D6B16B; font-size:12px; font-weight:800; letter-spacing:1px;"
        )
        layout.addWidget(purpose_title)

        purpose = QLabel(
            "PDF, Word ve Excel belgeleri arasında hızlı ve kolay "
            "dönüştürme işlemleri yapmak.<br><br>"
            "PDF → Excel ve PDF → Word işlemlerinde OCR desteği ile "
            "taranmış belgelerdeki metinleri algılayarak düzenlenebilir "
            "çıktılar oluşturmak."
        )
        purpose.setAlignment(Qt.AlignCenter)
        purpose.setWordWrap(True)
        purpose.setStyleSheet("color:#C8C2B8; font-size:12px;")
        layout.addWidget(purpose)

        update_line = QFrame()
        update_line.setFrameShape(QFrame.HLine)
        update_line.setStyleSheet("color:#2D2A25;")
        layout.addWidget(update_line)

        update_title = QLabel("GÜNCELLEMELER")
        update_title.setAlignment(Qt.AlignCenter)
        update_title.setStyleSheet(
            "color:#D6B16B; font-size:12px; font-weight:800; letter-spacing:1px;"
        )
        layout.addWidget(update_title)

        self.update_status = QLabel("Güncellemeleri denetlemek için aşağıdaki düğmeyi kullanın.")
        self.update_status.setAlignment(Qt.AlignCenter)
        self.update_status.setWordWrap(True)
        self.update_status.setStyleSheet("color:#C8C2B8; font-size:11px;")
        layout.addWidget(self.update_status)

        self.update_button = QPushButton("GÜNCELLEMELERİ KONTROL ET")
        self.update_button.setMinimumHeight(36)
        self.update_button.clicked.connect(self.check_for_updates)
        layout.addWidget(self.update_button)

        layout.addStretch(1)

        signature = QLabel("Emir Can Erarslan")
        signature.setAlignment(Qt.AlignCenter)
        signature.setStyleSheet(
            "color:#D6B16B; font-size:16px; font-weight:700; font-style:italic;"
        )
        layout.addWidget(signature)

        signature_sub = QLabel("Azra Converter")
        signature_sub.setAlignment(Qt.AlignCenter)
        signature_sub.setStyleSheet("color:#777169; font-size:10px; letter-spacing:1px;")
        layout.addWidget(signature_sub)

        close = QPushButton("KAPAT")
        close.setMinimumHeight(38)
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)

        dialog.exec()
        self.nav_converter.setChecked(True)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Dosya Seç",
            "",
            "Desteklenen Dosyalar (*.pdf *.xlsx *.xlsm *.doc *.docx);;PDF (*.pdf);;Excel (*.xlsx *.xlsm);;Word (*.doc *.docx)"
        )
        if path:
            self.set_file(path)

    def set_file(self, path):
        path = Path(path)
        if path.suffix.lower() not in [".pdf", ".xlsx", ".xlsm", ".doc", ".docx"]:
            QMessageBox.warning(self, "Desteklenmeyen dosya",
                                "Bu dosya türü desteklenmiyor.\n\nPDF, Excel veya Word dosyası seçin.")
            return

        self.source_file = str(path)
        self.file_label.setText(f"Seçilen: {path.name}")
        self.status.setText("Dosya hazır. Bir dönüşüm seçin.")
        self.update_buttons()

    def update_buttons(self):
        ext = Path(self.source_file).suffix.lower() if self.source_file else ""
        self.pdf_excel_card.button.setEnabled(ext == ".pdf")
        self.pdf_word_card.button.setEnabled(ext == ".pdf")
        self.excel_pdf_card.button.setEnabled(ext in [".xlsx", ".xlsm"])
        self.word_pdf_card.button.setEnabled(ext in [".doc", ".docx"])

    def start_conversion(self, mode):
        if not self.source_file:
            QMessageBox.information(self, "Dosya seçin", "Önce bir dosya seçin.")
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status.setText("Dönüştürülüyor...")

        for card in [self.pdf_excel_card, self.pdf_word_card,
                     self.excel_pdf_card, self.word_pdf_card]:
            card.button.setEnabled(False)

        self.thread = QThread()
        self.worker = ConverterWorker(mode, self.source_file)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.error.connect(self.conversion_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.worker_thread_finished)
        self.thread.start()

    def worker_thread_finished(self):
        self.thread = None
        self.worker = None
        self.update_buttons()

    def conversion_finished(self, output):
        self.progress.setValue(100)
        self.status.setText("Dönüştürme tamamlandı.")
        if self.source_file and self.worker:
            self._save_history(self.worker.mode, self.source_file, output, True)
        answer = QMessageBox.question(
            self, "İşlem tamamlandı",
            f"Dosya başarıyla oluşturuldu:\n\n{Path(output).name}\n\nKlasörü açmak ister misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if answer == QMessageBox.Yes:
            os.startfile(str(Path(output).parent))

    def conversion_error(self, details):
        if self.source_file and self.worker:
            self._save_history(self.worker.mode, self.source_file, "", False)
        self.progress.setVisible(False)
        self.status.setText("Dönüştürme başarısız.")
        QMessageBox.critical(
            self, "Dönüştürme hatası",
            "İşlem sırasında hata oluştu.\n\n" +
            (details or "Bilinmeyen hata")
        )
        self.update_buttons()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    icon_path = resource_path("azra_gold.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
