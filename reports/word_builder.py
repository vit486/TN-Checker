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
                f", S_ф={w['S_phi']:.2f} В·А" if w["scheme"] == "star" else ""
            )
        )
        doc.add_paragraph(f"S_нф = {w['S_nf']:.2f} В·А")
        doc.add_paragraph(f"Расчётная нагрузка = {w['total_load']:.2f} В·А ({w['hint']})")
        doc.add_paragraph(f"Номинал обмотки = {w['rated_power']} В·А")
        status = "ДОПУСТИМО" if not w["is_overload"] else "ПЕРЕГРУЗКА"
        doc.add_paragraph(f"Статус: {status}")

    doc.add_heading("2. Потери напряжения", level=1)
    for i, w in enumerate(data["windings"]):
        doc.add_paragraph(
            f"Обмотка {i+1} ({w['scheme_name']}): r={w['r']:.4f} Ом, "
            f"I={w['I']:.4f} А, ΔU={w['du']:.4f} В ({w['du']:.4f} %), "
            f"допустимо ≤ {w['allowed']:.2f} % — "
            f"{'OK' if w['du'] <= w['allowed'] else 'ПРЕВЫШЕНИЕ'}"
        )

    doc.add_heading("3. Автоматические выключатели", level=1)
    for i, w in enumerate(data["breakers_by_winding"]):
        doc.add_heading(f"Обмотка {i+1}: Zк = {w['zk']:.4f} Ом", level=2)
        for j, b in enumerate(w["breakers"]):
            doc.add_paragraph(
                f"Автомат {j+1}: {b['type']}"
                + (f" / {b['char']}" if b['char'] else "")
                + f", Iном={b['I_nom']} А, r_ф={b['r_phase']:.4f} Ом, r_0={b['r_zero']:.4f} Ом"
            )
            doc.add_paragraph(
                f"  Iкз(2ф)={b['ikz_2']:.2f} А, Iкз(1ф)={b['ikz_1']:.2f} А, "
                f"Iкз_min={b['ikz_min']:.2f} А, Kч={b['k_ch']:.2f} — "
                f"{'OK' if b['success'] else 'НЕ ПРОЙДЕН'}"
            )

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
