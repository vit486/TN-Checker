# reports/word_builder.py
from io import BytesIO
from docx import Document

def build_report(**data):
    doc = Document()
    doc.add_heading("Протокол проверки ТН по РД 34.35.305-79", 0)
    doc.add_paragraph(f"Нагрузка наиболее загруженной фазы: {data['S_nf']:.1f} В·А")
    doc.add_paragraph(f"Потери линейного напряжения: {data['dU']:.3f} В")
    table = doc.add_table(rows=1, cols=3)
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Участок", "Ток, А", "r, Ом"
    for idx, c in enumerate(data["cables"], 1):
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text = str(idx), f"{c['I']:.2f}", f"{c['r']:.4f}"
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf