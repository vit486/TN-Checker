from io import BytesIO
from docx import Document
import datetime

def build_report(data):
    doc = Document()
    doc.add_heading("Протокол проверки ТН по РД 34.35.305-79", 0)
    doc.add_paragraph(f"Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")

    doc.add_heading("1. Нагрузка ТН", level=1)
    for i, w in enumerate(data["windings"]):
        doc.add_heading(f"Обмотка {i+1}: {w['scheme_name']}", level=2)
        doc.add_paragraph(
            f"S_ab={w['S_ab']:.2f}, S_bc={w['S_bc']:.2f}, "
            f"S_ca={w['S_ca']:.2f} В·А" + (
                f", S_ф={w['S_phi']:.2f} В·А" if "Звезда с" in w["scheme_name"] else ""
            )
        )
        doc.add_paragraph(f"S_нф = {w['S_nf']:.2f} В·А")
        doc.add_paragraph(f"Расчётная нагрузка = {w['total_load']:.2f} В·А")
        doc.add_paragraph(f"Номинал = {w['rated_power']} В·А")
        status = "ДОПУСТИМО" if w["total_load"] <= w["rated_power"] else "ПЕРЕГРУЗКА"
        doc.add_paragraph(f"Статус: {status}")

    doc.add_heading("2. Потери напряжения", level=1)
    for i, w in enumerate(data["windings"]):
        doc.add_paragraph(
            f"Обмотка {i+1}: r={w['r']:.4f} Ом, I={w['I']:.4f} А, "
            f"ΔU={w['du']:.4f} В ({w['du']:.4f} %)"
        )

    doc.add_heading("3. Автоматические выключатели", level=1)
    b = data["breaker"]
    doc.add_paragraph(f"Zк ТН = {b['zk']:.4f} Ом")
    doc.add_paragraph(f"Iкз (2ф) = {b['Ikz_2']:.2f} А, Iкз (1ф) = {b['Ikz_1']:.2f} А")
    doc.add_paragraph(f"Iкз расч. = {b['Ikz']:.2f} А")
    doc.add_paragraph(f"Автомат: {b['type']}, Iном={b['I_nom']} А" + (
        f", характеристика {b['char']}" if b["char"] else ""
    ))
    doc.add_paragraph(f"Kч = {b['K_ch']:.2f} — {'ОК' if b['success'] else 'НЕ ПРОЙДЕН'}")

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
