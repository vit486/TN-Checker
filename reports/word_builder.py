from io import BytesIO
from docx import Document
import datetime

def build_report(data):
    doc = Document()
    doc.add_heading("Протокол проверки ТН по РД 34.35.305-79", 0)
    doc.add_paragraph(f"Дата формирования: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")

    doc.add_heading("1. Расчёт нагрузки ТН", level=1)
    for i, w in enumerate(data["windings"]):
        doc.add_heading(f"Обмотка {i+1} ({w['scheme_name']})", level=2)
        doc.add_paragraph(f"Междуфазные нагрузки: S_ab={w['S_ab']:.2f}, S_bc={w['S_bc']:.2f}, S_ca={w['S_ca']:.2f} В·А")
        if w['scheme'] == 'star':
            doc.add_paragraph(f"Фазная нагрузка: S_ф={w['S_phi']:.2f} В·А")
            doc.add_paragraph(f"Нагрузка наиболее загруженной фазы: S_нф={w['S_nf']:.2f} В·А")
            doc.add_paragraph(f"Суммарная нагрузка на ТН (3*S_нф): {w['total_load']:.2f} В·А")
        else:
            doc.add_paragraph(f"Нагрузка наиболее загруженного ТН: S_нф={w['S_nf']:.2f} В·А")
        
        status = "ДОПУСТИМО" if w['total_load'] <= w['rated_power'] else "ПЕРЕГРУЗКА"
        doc.add_paragraph(f"Номинальная мощность в классе точности: {w['rated_power']} В·А. Статус: {status}")

    doc.add_heading("2. Потери напряжения", level=1)
    for i, w in enumerate(data["windings"]):
        doc.add_paragraph(f"Обмотка {i+1}: R={w['r']:.4f} Ом, I={w['I']:.4f} А, ΔU={w['du']:.4f} В (%).")

    doc.add_heading("3. Проверка автоматических выключателей", level=1)
    doc.add_paragraph(f"Рассчитанный ток КЗ: {data['breaker']['Ikz']:.2f} А")
    doc.add_paragraph(f"Автомат: {data['breaker']['type']}, Iном={data['breaker']['I_nom']} А")
    doc.add_paragraph(f"Коэффициент чувствительности Kч = {data['breaker']['K_ch']:.2f}")
    doc.add_paragraph(f"Результат: {'УСПЕШНО' if data['breaker']['success'] else 'НЕ ПРОЙДЕН'}")

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
