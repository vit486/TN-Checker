import streamlit as st
import pandas as pd
import math
from calculations.load import calculate_snf_star, calculate_snf_delta, suggest_optimization
from calculations.voltage_loss import calculate_resistance, calculate_current, calculate_du
from calculations.breakers import calculate_zk, calculate_ikz_min, check_breaker
from reports.word_builder import build_report

st.set_page_config(page_title="Проверка ТН по РД 34.35.305-79", layout="wide")
st.title("Проверка ТН и вторичных цепей (РД 34.35.305-79)")

# Инициализация состояния
if "num_windings" not in st.session_state:
    st.session_state.num_windings = 1

tab1, tab2, tab3 = st.tabs(["Нагрузка ТН", "Потери напряжения", "Проверка автоматов"])

# ============================================================
# ВКЛАДКА 1: НАГРУЗКА ТН
# ============================================================
with tab1:
    st.header("1. Расчёт нагрузки ТН")
    
    st.session_state.num_windings = st.number_input(
        "Количество вторичных обмоток ТН (1-4):", min_value=1, max_value=4, value=st.session_state.num_windings
    )

    windings_data = []
    
    # Используем форму, чтобы избежать сброса при вводе
    with st.form("load_form"):
        for i in range(st.session_state.num_windings):
            st.subheader(f"Обмотка {i+1}")
            col1, col2 = st.columns([1, 2])
            with col1:
                scheme = st.selectbox(
                    f"Схема соединения (Обмотка {i+1})",
                    ["Звезда с нулём", "Звезда без нуля", "Открытый треугольник"],
                    key=f"scheme_{i}"
                )
            with col2:
                rated_power = st.number_input(
                    f"Номинальная мощность в классе точности, В·А (Обмотка {i+1})",
                    min_value=10.0, value=50.0, step=10.0, format="%.2f", key=f"power_{i}"
                )

            st.write("Введите нагрузки (В·А):")
            c1, c2, c3, c4 = st.columns(4)
            S_ab = c1.number_input(f"S_ab (Обмотка {i+1})", value=0.0, step=0.5, format="%.5f", key=f"Sab_{i}")
            S_bc = c2.number_input(f"S_bc (Обмотка {i+1})", value=0.0, step=0.5, format="%.5f", key=f"Sbc_{i}")
            S_ca = c3.number_input(f"S_ca (Обмотка {i+1})", value=0.0, step=0.5, format="%.5f", key=f"Sca_{i}")
            
            S_phi = 0.0
            if scheme != "Открытый треугольник":
                S_phi = c4.number_input(f"S_ф (Обмотка {i+1})", value=0.0, step=0.5, format="%.5f", key=f"Sphi_{i}")
            else:
                c4.write("S_ф не используется")
            
            windings_data.append({
                "scheme": "star" if "Звезда" in scheme else "delta",
                "scheme_name": scheme,
                "rated_power": rated_power,
                "S_ab": S_ab, "S_bc": S_bc, "S_ca": S_ca, "S_phi": S_phi
            })
            
        submitted = st.form_submit_button("Рассчитать нагрузки")
        
    if submitted or "calc_results" in st.session_state:
        # Сохраняем введённые данные в сессию
        st.session_state.windings_data = windings_data
        
        st.write("---")
        st.subheader("Результаты расчёта")
        
        results = []
        for i, w in enumerate(windings_data):
            if w["scheme"] == "star":
                S_nf = calculate_snf_star(w["S_ab"], w["S_bc"], w["S_ca"], w["S_phi"])
                total_load = 3 * S_nf
            else:
                S_nf = calculate_snf_delta(w["S_ab"], w["S_bc"], w["S_ca"])
                total_load = S_nf
                
            is_overload = total_load > w["rated_power"]
            
            st.markdown(f"**Обмотка {i+1} ({w['scheme_name']})**")
            st.write(f"Нагрузка наиболее загруженной фазы S_нф: **{S_nf:.2f} В·А**")
            st.write(f"Расчётная нагрузка на ТН: **{total_load:.2f} В·А**")
            
            if is_overload:
                st.error(f"ПЕРЕГРУЗКА! Номинальная мощность: {w['rated_power']} В·А")
                # Предложение по оптимизации
                opt = suggest_optimization(w["S_ab"], w["S_bc"], w["S_ca"], w["S_phi"], w["scheme"], w["rated_power"])
                if opt:
                    st.info(f"💡 Рекомендация: перераспределите нагрузку. Например, перенесите нагрузку с наименее загруженной фазы: "
                            f"S_ab={opt['new_ab']:.2f}, S_bc={opt['new_bc']:.2f}, S_ca={opt['new_ca']:.2f} В·А. "
                            f"Тогда расчётная нагрузка составит {opt['new_total']:.2f} В·А.")
                else:
                    st.warning("Перераспределение не поможет. Требуется замена ТН на более мощный или подключение дополнительного ТН.")
            else:
                st.success(f"Нагрузка в пределах нормы (≤ {w['rated_power']} В·А).")
                
            results.append({
                **w, "S_nf": S_nf, "total_load": total_load
            })
        st.session_state.calc_results = results

# ============================================================
# ВКЛАДКА 2: ПОТЕРИ НАПРЯЖЕНИЯ
# ============================================================
with tab2:
    st.header("2. Расчёт потерь напряжения")
    
    if "calc_results" not in st.session_state:
        st.warning("Сначала выполните расчёт нагрузок на вкладке 1.")
    else:
        with st.form("voltage_form"):
            for i, w in enumerate(st.session_state.calc_results):
                st.subheader(f"Обмотка {i+1} ({w['scheme_name']})")
                c1, c2, c3 = st.columns(3)
                length = c1.number_input(f"Длина кабеля, м (Обмотка {i+1})", value=30.0, min_value=1.0, step=1.0, key=f"len_{i}")
                cross_section = c2.number_input(f"Сечение жилы, мм² (Обмотка {i+1})", value=2.5, min_value=0.5, step=0.5, format="%.1f", key=f"cs_{i}")
                material = c3.selectbox(f"Материал жилы (Обмотка {i+1})", ["Медь", "Алюминий"], key=f"mat_{i}")
                
                # Сохраняем параметры кабеля в сессию для отчёта
                if "cable_params" not in st.session_state:
                    st.session_state.cable_params = {}
                st.session_state.cable_params[i] = {"length": length, "cs": cross_section, "mat": material}

            sub_v = st.form_submit_button("Рассчитать потери")

        if sub_v or "voltage_results" in st.session_state:
            st.write("---")
            st.subheader("Результаты расчёта")
            v_results = []
            
            for i, w in enumerate(st.session_state.calc_results):
                params = st.session_state.cable_params[i]
                mat_key = "copper" if params["mat"] == "Медь" else "aluminum"
                
                r = calculate_resistance(params["length"], params["cs"], mat_key)
                I = calculate_current(w["S_nf"], w["scheme"])
                du = calculate_du(I, r, w["scheme"])
                
                st.markdown(f"**Обмотка {i+1}**")
                st.write(f"Сопротивление: {r:.4f} Ом | Ток: {I:.4f} А | Потери: **{du:.4f} В (= {du:.4f} %)**")
                
                v_results.append({**w, **params, "r": r, "I": I, "du": du})
                
            st.session_state.voltage_results = v_results

# ============================================================
# ВКЛАДКА 3: ПРОВЕРКА АВТОМАТОВ
# ============================================================
with tab3:
    st.header("3. Проверка автоматических выключателей")
    
    with st.form("breaker_form"):
        st.subheader("Параметры ТН и вторичной цепи")
        c1, c2, c3 = st.columns(3)
        uk = c1.number_input("Напряжение КЗ (Uк), %", value=6.0, step=0.1, format="%.2f")
        u_nom = c2.number_input("Номинальное напряжение обмотки, В", value=100.0)
        s_nom = c3.number_input("Номинальная мощность ТН (для расчета Zк), В·А", value=400.0, step=50.0)
        
        st.write("Сопротивление проводов до автомата (Ом):")
        c4, c5 = st.columns(2)
        r_phase = c4.number_input("Фазный провод (r_пр)", value=0.05, step=0.01, format="%.3f")
        r_zero = c5.number_input("Нулевой провод (r_0пр)", value=0.05, step=0.01, format="%.3f")
        
        st.subheader("Параметры автомата")
        c6, c7, c8 = st.columns(3)
        breaker_type = c6.selectbox("Тип автомата", ["AP50", "KEAZ OptiDin BM63"])
        I_nom = c7.number_input("Номинальный ток автомата, А", value=6.3, step=0.1, format="%.2f")
        
        characteristic = None
        if breaker_type == "KEAZ OptiDin BM63":
            characteristic = c8.selectbox("Характеристика", ["B", "C", "D", "Z", "L", "K"])

        sub_b = st.form_submit_button("Проверить автомат")

    if sub_b or "breaker_results" in st.session_state:
        st.write("---")
        st.subheader("Результаты проверки")
        
        zk = calculate_zk(uk, u_nom, s_nom)
        st.write(f"Сопротивление ТН (Zк): **{zk:.4f} Ом**")
        
        # Расчет минимального тока КЗ (для 3-фазной цепи по формулам П.12/П.13)
        # Используем U_мф = 100 В для основных обмоток
        Ikz_2 = calculate_ikz_min(100.0, zk, r_phase) # Двухфазное
        Ikz_1 = calculate_ikz_min(100.0, zk, r_phase, r_zero) # Однофазное
        
        st.write(f"Минимальный ток КЗ (2-фазный): **{Ikz_2:.2f} А**")
        st.write(f"Минимальный ток КЗ (1-фазный): **{Ikz_1:.2f} А**")
        
        # Для проверки берем меньший из токов
        Ikz_min = min(Ikz_2, Ikz_1)
        
        K_ch, success = check_breaker(Ikz_min, I_nom, breaker_type, characteristic)
        
        st.write(f"Коэффициент чувствительности Kч: **{K_ch:.2f}**")
        if success:
            st.success("Условие Kч ≥ 1.5 выполняется. Автомат выбран верно.")
        else:
            st.error("Условие Kч ≥ 1.5 НЕ выполняется. Требуется автомат с меньшим номиналом или увеличение сечения кабеля.")
            
        st.session_state.breaker_results = {
            "zk": zk, "Ikz_2": Ikz_2, "Ikz_1": Ikz_1, "Ikz": Ikz_min,
            "type": breaker_type, "I_nom": I_nom, "char": characteristic,
            "K_ch": K_ch, "success": success
        }

# ============================================================
# ГЕНЕРАЦИЯ ОТЧЁТА (Кнопка внизу страницы)
# ============================================================
st.write("---")
st.header("4. Формирование отчёта")

if "calc_results" in st.session_state and "voltage_results" in st.session_state and "breaker_results" in st.session_state:
    if st.button("Скачать отчёт в Word (.docx)"):
        # Подготовка данных для отчёта
        report_data = {
            "windings": [],
            "breaker": st.session_state.breaker_results
        }
        
        for i, w in enumerate(st.session_state.voltage_results):
            report_data["windings"].append({
                "scheme_name": w["scheme_name"],
                "S_ab": w["S_ab"], "S_bc": w["S_bc"], "S_ca": w["S_ca"], "S_phi": w["S_phi"],
                "S_nf": w["S_nf"], "total_load": w["total_load"], "rated_power": w["rated_power"],
                "r": w["r"], "I": w["I"], "du": w["du"]
            })
            
        buf = build_report(report_data)
        st.download_button(
            label="Нажмите здесь, если скачивание не началось автоматически",
            data=buf,
            file_name="TN_Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
else:
    st.info("Для формирования отчёта выполните расчёты на всех трёх вкладках.")
