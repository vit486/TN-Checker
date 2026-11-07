# app.py
import streamlit as st
import json
import math
from calculations.load import calculate_snf_3phase, calculate_snf_open_delta
from calculations.voltage_loss import calculate_resistance, calculate_current, calculate_du

# Загрузка справочника
with open('data/equipment.json', 'r', encoding='utf-8') as f:
    equipment_db = json.load(f)

st.set_page_config(page_title="Проверка ТН по РД 34.35.305-79", layout="wide")
st.title("Проверка ТН и вторичных цепей (РД 34.35.305-79)")

tab1, tab2, tab3 = st.tabs(["Нагрузка ТН", "Потери напряжения", "Проверка автоматов"])

# --- ВКЛАДКА 1: НАГРУЗКА ---
with tab1:
    st.header("1. Расчёт нагрузки наиболее загруженной фазы")
    scheme = st.radio("Схема соединения обмоток ТН:", ["Звезда (3-фазный)", "Открытый треугольник (2 ТН)"])
    
    st.subheader("Добавьте аппаратуру")
    
    # Динамическая таблица (пользователь может добавлять строки)
    default_df = [
        {"Прибор": "Счетчик", "Тип": "Междуфазная", "S_ab": 6.0, "S_bc": 6.0, "S_ca": 0.0, "S_a": 0.0, "S_b": 0.0, "S_c": 0.0}
    ]
    
    # Используем data_editor для удобного ввода
    edited_df = st.data_editor(
        default_df,
        num_rows="dynamic",
        column_config={
            "Прибор": st.column_config.TextColumn("Название"),
            "Тип": st.column_config.SelectboxColumn("Тип нагрузки", options=["Междуфазная", "Фазная"]),
            "S_ab": st.column_config.NumberColumn("S_ab (В·А)", min_value=0.0),
            "S_bc": st.column_config.NumberColumn("S_bc (В·А)", min_value=0.0),
            "S_ca": st.column_config.NumberColumn("S_ca (В·А)", min_value=0.0),
            "S_a": st.column_config.NumberColumn("S_a (В·А)", min_value=0.0),
            "S_b": st.column_config.NumberColumn("S_b (В·А)", min_value=0.0),
            "S_c": st.column_config.NumberColumn("S_c (В·А)", min_value=0.0),
        }
    )
    
    # Суммирование нагрузок
    S_ab = edited_df["S_ab"].sum()
    S_bc = edited_df["S_bc"].sum()
    S_ca = edited_df["S_ca"].sum()
    S_a = edited_df["S_a"].sum()
    S_b = edited_df["S_b"].sum()
    S_c = edited_df["S_c"].sum()
    S_phi_max = max(S_a, S_b, S_c)
    
    st.write(f"Суммарные междуфазные нагрузки: S_ab={S_ab:.1f}, S_bc={S_bc:.1f}, S_ca={S_ca:.1f} В·А")
    st.write(f"Суммарные фазные нагрузки: S_a={S_a:.1f}, S_b={S_b:.1f}, S_c={S_c:.1f} В·А")
    
    if scheme == "Звезда (3-фазный)":
        S_nf = calculate_snf_3phase(S_ab, S_bc, S_ca, S_phi_max)
        st.metric("Нагрузка наиболее загруженной фазы (Sнф)", f"{S_nf:.1f} В·А")
        st.info("Расчёт по РД (Пример 2, стр. 115). Сравните 3*Sнф с мощностью ТН в классе точности.")
    else:
        S_nf = calculate_snf_open_delta(S_ab, S_bc, S_ca)
        st.metric("Нагрузка наиболее загруженного ТН (Sнф)", f"{S_nf:.1f} В·А")
        st.info("Расчёт по РД (Пример 1, стр. 114). Сравните Sнф с мощностью одного ТН в классе точности.")

# --- ВКЛАДКА 2: ПОТЕРИ НАПРЯЖЕНИЯ ---
with tab2:
    st.header("2. Расчёт потерь напряжения во вторичных цепях")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        length = st.number_input("Длина кабеля, м", value=30.0, min_value=1.0)
        cross_section = st.number_input("Сечение жилы, мм²", value=2.5, min_value=0.5)
    with col2:
        material = st.selectbox("Материал жилы", ["Медь (57)", "Алюминий (34.5)"])
        mode = st.radio("Режим цепи", ["3-фазная (K=√3)", "2-проводная (K=2)"])
    with col3:
        S_load = st.number_input("Нагрузка Sнф, В·А (из вкладки 1)", value=S_nf)
    
    # Расчёт
    mat_key = "copper" if "Медь" in material else "aluminum"
    mode_key = "3phase" if "3-фазная" in mode else "2wire"
    
    r = calculate_resistance(length, cross_section, mat_key)
    I = calculate_current(S_load, mode_key)
    dU = calculate_du(I, r, mode_key)
    
    st.write("---")
    st.subheader("Результаты расчёта")
    st.write(f"Сопротивление жилы: **{r:.3f} Ом** (формула 6)")
    st.write(f"Ток нагрузки: **{I:.2f} А**")
    st.metric("Потери напряжения (ΔU)", f"{dU:.3f} В (= {dU:.3f} %)")
    
    st.subheader("Проверка допустимых потерь (п. 1.4 РД)")
    st.write("Согласно РД 34.35.305-79, допустимые потери:")
    st.markdown("- до расчетных счетчиков межсистемных линий: **0.25%**\n- до других расчетных счетчиков: **0.5%**\n- до щитовых приборов: **1.5%**\n- до ФИП: **2%**\n- до реле защиты и автоматики: **3%**")
    
    target = st.selectbox("Выберите назначение цепи для проверки:", 
                          ["0.25% (межсистемные счетчики)", "0.5% (счетчики)", "1.5% (щитовые приборы)", "2% (ФИП)", "3% (реле защиты)"])
    limit = float(target.split("%")[0])
    
    if dU <= limit:
        st.success(f"Условие выполняется: {dU:.3f}% ≤ {limit}%")
    else:
        st.error(f"Условие НЕ выполняется: {dU:.3f}% > {limit}%. Требуется увеличить сечение кабеля или разгрузить цепь.")

# --- ВКЛАДКА 3: ПРОВЕРКА АВТОМАТОВ ---
with tab3:
    st.header("3. Проверка автоматических выключателей")
    st.info("В разработке. Здесь будут учтены характеристики АП50 и KEAZ OptiDin BM63.")
    
    breaker_type = st.selectbox("Тип автомата", ["АП50 (старый)", "KEAZ OptiDin BM63"])
    I_kz = st.number_input("Минимальный ток КЗ, А", value=50.0)
    I_nom = st.number_input("Номинальный ток расцепителя, А", value=6.3)
    
    if breaker_type == "АП50 (старый)":
        st.write("Согласно РД, для АП50 ток срабатывания отсечки принимается 4*Iном.")
        K_ch = I_kz / (4 * I_nom)
    else:
        char = st.selectbox("Характеристика KEAZ", ["B", "C", "D"])
        mult = {"B": 5, "C": 10, "D": 20}[char]
        K_ch = I_kz / (mult * I_nom)
        
    st.write(f"Коэффициент чувствительности Kч = **{K_ch:.2f}**")
    if K_ch >= 1.5:
        st.success("Kч ≥ 1.5 (Условие выполняется)")
    else:
        st.error("Kч < 1.5 (Условие не выполняется)")
