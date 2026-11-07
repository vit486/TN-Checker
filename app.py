import streamlit as st
from calculations.load import phase_load
from calculations.voltage_loss import voltage_loss
from reports.word_builder import build_report

st.set_page_config(page_title="Проверка ТН по РД 34.35.305-79", layout="wide")
st.title("Проверка трансформаторов напряжения и вторичных цепей")

tab1, tab2, tab3 = st.tabs(["Нагрузка ТН", "Потери напряжения", "Отчёт"])

with tab1:
    st.subheader("Расчёт нагрузки наиболее загруженной фазы")
    S1 = st.number_input("Наибольшая междуфазная нагрузка S₁, В·А", value=270.0)
    S2 = st.number_input("Вторая междуфазная нагрузка S₂, В·А", value=150.0)
    S_phi = st.number_input("Наибольшая фазная нагрузка Sф, В·А", value=0.0)
    S_nf = phase_load(S1, S2, S_phi)
    st.metric("Sн.ф", f"{S_nf:.1f} В·А")

with tab2:
    st.subheader("Потери напряжения в кабелях")
    n = st.number_input("Число последовательных участков", 1, 5, 1)
    cables = []
    for i in range(int(n)):
        c1, c2 = st.columns(2)
        I = c1.number_input(f"I{i+1}, А", value=1.0, key=f"i{i}")
        r = c2.number_input(f"r{i+1}, Ом", value=0.1, key=f"r{i}")
        cables.append({"I": I, "r": r})
    dU = voltage_loss(cables)
    st.metric("ΔU лин., В (= %)", f"{dU:.3f}")

with tab3:
    if st.button("Сформировать отчёт Word"):
        buf = build_report(S_nf=S_nf, dU=dU, cables=cables)
        st.download_button("Скачать .docx", buf, file_name="tn_report.docx")