import streamlit as st
import pandas as pd
import math
from calculations.load import calculate_snf_star, calculate_snf_delta, suggest_optimization
from calculations.voltage_loss import calculate_resistance, calculate_current, calculate_du
from calculations.breakers import (
    calculate_zk, calculate_ikz, get_trip_current,
    sensitivity_for_all_chars, BREAKER_MULTIPLIERS
)
from reports.word_builder import build_report

st.set_page_config(page_title="Проверка ТН по РД 34.35.305-79", layout="wide")
st.title("Проверка ТН и вторичных цепей (РД 34.35.305-79)")

SCHEMES = ["Звезда с нулём", "Звезда без нуля", "Открытый треугольник"]

if "num_windings" not in st.session_state:
    st.session_state.num_windings = 1
for k in ("calc_results", "voltage_results", "breaker_results", "cable_params"):
    if k not in st.session_state:
        st.session_state[k] = None

tab1, tab2, tab3 = st.tabs(["Нагрузка ТН", "Потери напряжения", "Автоматы"])

# ============================================================
# ВКЛАДКА 1
# ============================================================
with tab1:
    st.header("1. Расчёт нагрузки ТН")

    st.session_state.num_windings = int(st.number_input(
        "Количество вторичных обмоток (1–4):", min_value=1, max_value=4,
        value=st.session_state.num_windings,
    ))

    with st.form("load_form"):
        windings_input = []
        for i in range(st.session_state.num_windings):
            st.subheader(f"Обмотка {i+1}")
            c1, c2 = st.columns(2)
            scheme = c1.selectbox("Схема соединения", SCHEMES, key=f"sch_{i}")
            power = c2.number_input(
                "Sном в классе точности, В·А", min_value=1.0, value=50.0,
                step=10.0, format="%.2f", key=f"pow_{i}",
            )
            # поле S_ф — только для звезды с нулём
            show_phi = (scheme == "Звезда с нулём")

                      # ---- Хранилище ВСЕГДА содержит все колонки ----
            ALL_COLS = ["Прибор", "S_ab", "S_bc", "S_ca", "S_ф"]
            if f"df_{i}" not in st.session_state:
                st.session_state[f"df_{i}"] = pd.DataFrame(
                    [{c: ("" if c == "Прибор" else 0.0) for c in ALL_COLS}]
                )
            stored = st.session_state[f"df_{i}"]
            # Гарантируем наличие всех колонок
            for c in ALL_COLS:
                if c not in stored.columns:
                    stored[c] = "" if c == "Прибор" else 0.0

            # ---- Для отображения — только видимые колонки ----
            visible = ["Прибор", "S_ab", "S_bc", "S_ca"] + (["S_ф"] if show_phi else [])
            display_df = stored[visible].copy()

            edited = st.data_editor(
                display_df, num_rows="dynamic", key=f"de_{i}_{'phi' if show_phi else 'nophi'}",
                column_config={
                    "Прибор": st.column_config.TextColumn("Прибор"),
                    "S_ab": st.column_config.NumberColumn("S_ab (В·А)", min_value=0.0, step=0.01, format="%.5f"),
                    "S_bc": st.column_config.NumberColumn("S_bc (В·А)", min_value=0.0, step=0.01, format="%.5f"),
                    "S_ca": st.column_config.NumberColumn("S_ca (В·А)", min_value=0.0, step=0.01, format="%.5f"),
                    **({"S_ф": st.column_config.NumberColumn("S_ф (В·А)", min_value=0.0, step=0.01, format="%.5f")} if show_phi else {}),
                },
            )
            # Пересборка stored: берём все колонки из edited, недостающие (скрытые) — из старого stored
            new_df = edited.copy()
            for hidden in ALL_COLS:
                if hidden not in new_df.columns:
                    if hidden in stored.columns:
                        new_df[hidden] = stored[hidden].reindex(new_df.index).fillna(0.0).values
                    else:
                        new_df[hidden] = 0.0
            new_df = new_df[ALL_COLS]
            st.session_state[f"df_{i}"] = new_df

            def _sum(col):
                if col not in edited.columns: return 0.0
                return float(pd.to_numeric(edited[col], errors="coerce").fillna(0).sum())

            windings_input.append({
                "scheme": "star" if "Звезда" in scheme else "delta",
                "scheme_name": scheme,
                "rated_power": power,
                "S_ab": _sum("S_ab"),
                "S_bc": _sum("S_bc"),
                "S_ca": _sum("S_ca"),
                "S_phi": _sum("S_ф") if show_phi else 0.0,
            })

        submitted = st.form_submit_button("Рассчитать нагрузки")

    if submitted:
        results = []
        for w in windings_input:
            if w["scheme"] == "star":
                S_nf = calculate_snf_star(w["S_ab"], w["S_bc"], w["S_ca"], w["S_phi"])
                total = 3 * S_nf
            else:
                S_nf = calculate_snf_delta(w["S_ab"], w["S_bc"], w["S_ca"])
                total = S_nf
            results.append({**w, "S_nf": S_nf, "total_load": total})
        st.session_state.calc_results = results

    if st.session_state.calc_results:
        st.write("---")
        st.subheader("Результаты")
        for i, w in enumerate(st.session_state.calc_results):
            st.markdown(f"**Обмотка {i+1}: {w['scheme_name']}**")
            st.write(f"S_нф = **{w['S_nf']:.2f} В·А**, расчётная нагрузка = **{w['total_load']:.2f} В·А**")
            if w["total_load"] > w["rated_power"]:
                st.error(f"ПЕРЕГРУЗКА (номинал {w['rated_power']} В·А)")
                opt = suggest_optimization(
                    w["S_ab"], w["S_bc"], w["S_ca"], w["S_phi"],
                    w["scheme"], w["rated_power"]
                )
                if opt:
                    st.info(
                        f"💡 Рекомендация: перераспределите нагрузку на S_ab={opt['new_ab']:.2f}, "
                        f"S_bc={opt['new_bc']:.2f}, S_ca={opt['new_ca']:.2f} В·А. "
                        f"Новая расчётная нагрузка = {opt['new_total']:.2f} В·А."
                    )
                else:
                    st.warning("Перераспределение между фазами не поможет — требуется ТН большей мощности или дополнительный ТН.")
            else:
                st.success(f"OK (≤ {w['rated_power']} В·А)")

# ============================================================
# ВКЛАДКА 2
# ============================================================
with tab2:
    st.header("2. Потери напряжения")
    if not st.session_state.calc_results:
        st.warning("Сначала выполните расчёт нагрузок на вкладке 1.")
    else:
        with st.form("volt_form"):
            cable_params = []
            for i, w in enumerate(st.session_state.calc_results):
                st.subheader(f"Обмотка {i+1}: {w['scheme_name']}")
                c1, c2, c3 = st.columns(3)
                length = c1.number_input(f"Длина, м (обм. {i+1})", min_value=1.0, value=30.0, step=1.0, key=f"L_{i}")
                cs = c2.number_input(f"Сечение, мм² (обм. {i+1})", min_value=0.5, value=2.5, step=0.5, format="%.1f", key=f"cs_{i}")
                mat = c3.selectbox(f"Материал (обм. {i+1})", ["Медь", "Алюминий"], key=f"m_{i}")
                cable_params.append({"length": length, "cs": cs, "mat": mat})
            sub_v = st.form_submit_button("Рассчитать потери")

        if sub_v:
            st.session_state.cable_params = cable_params
            v_results = []
            for i, w in enumerate(st.session_state.calc_results):
                p = cable_params[i]
                mat_key = "copper" if p["mat"] == "Медь" else "aluminum"
                r = calculate_resistance(p["length"], p["cs"], mat_key)
                I = calculate_current(w["S_nf"], w["scheme"])
                du = calculate_du(I, r, w["scheme"])
                v_results.append({**w, **p, "r": r, "I": I, "du": du})
            st.session_state.voltage_results = v_results

        if st.session_state.voltage_results:
            st.write("---")
            for i, w in enumerate(st.session_state.voltage_results):
                st.markdown(f"**Обмотка {i+1}: {w['scheme_name']}**")
                st.write(f"r = {w['r']:.4f} Ом | I = {w['I']:.4f} А | ΔU = **{w['du']:.4f} В (= {w['du']:.4f} %)**")

# ============================================================
# ВКЛАДКА 3
# ============================================================
with tab3:
    st.header("3. Проверка автоматических выключателей")

    with st.form("br_form"):
        st.subheader("Параметры ТН и цепи")
        c1, c2, c3 = st.columns(3)
        uk = c1.number_input("Uк, %", min_value=0.1, value=6.0, step=0.1, format="%.2f")
        u_nom = c2.number_input("Uном обмотки, В", value=100.0)
        s_nom = c3.number_input("Sном ТН, В·А", min_value=10.0, value=400.0, step=50.0)

        st.subheader("Сопротивление проводов")
        use_from_tab2 = st.checkbox(
            "Взять длину и сечение из вкладки 2 (обмотка 1)",
            value=bool(st.session_state.cable_params),
        )
        if use_from_tab2 and st.session_state.cable_params:
            p = st.session_state.cable_params[0]
            r_phase = calculate_resistance(p["length"], p["cs"], "copper" if p["mat"] == "Медь" else "aluminum")
            r_zero = r_phase
            st.write(f"r_ф = r_0 = **{r_phase:.4f} Ом** (из обмотки 1)")
        else:
            cc1, cc2 = st.columns(2)
            r_phase = cc1.number_input("r фазного провода, Ом", min_value=0.001, value=0.05, step=0.001, format="%.3f")
            r_zero = cc2.number_input("r нулевого провода, Ом", min_value=0.001, value=0.05, step=0.001, format="%.3f")

        st.subheader("Параметры автомата")
        c6, c7, c8 = st.columns(3)
        btype = c6.selectbox("Тип", ["AP50", "KEAZ OptiDin BM63"])
        i_nom = c7.number_input("Iном, А", min_value=0.5, value=6.3, step=0.1, format="%.2f")
        char = None
        if btype.startswith("KEAZ"):
            char = c8.selectbox("Характеристика", list(BREAKER_MULTIPLIERS.keys()))

        sub_b = st.form_submit_button("Проверить")

    if sub_b:
        zk = calculate_zk(uk, u_nom, s_nom)
        ikz_2 = calculate_ikz(100.0, zk, r_phase)
        ikz_1 = calculate_ikz(100.0, zk, r_phase, r_zero)
        ikz_min = min(ikz_2, ikz_1)
        i_trip = get_trip_current(i_nom, btype, char)
        k_ch = ikz_min / i_trip
        success = k_ch >= 1.5

        st.session_state.breaker_results = {
            "zk": zk, "Ikz_2": ikz_2, "Ikz_1": ikz_1, "Ikz": ikz_min,
            "type": btype, "I_nom": i_nom, "char": char,
            "K_ch": k_ch, "success": success,
        }

    if st.session_state.breaker_results:
        b = st.session_state.breaker_results
        st.write("---")
        st.write(f"Zк = **{b['zk']:.4f} Ом**")
        st.write(f"Iкз (2ф) = {b['Ikz_2']:.2f} А | Iкз (1ф) = {b['Ikz_1']:.2f} А | расчётный = **{b['Ikz']:.2f} А**")
        st.write(f"Kч = **{b['K_ch']:.2f}**")
        if b["success"]:
            st.success("Kч ≥ 1.5 — автомат выбран верно.")
        else:
            st.error("Kч < 1.5 — требуется меньший номинал или большее сечение.")

        st.subheader("Сравнение характеристик KEAZ (при том же Iкз)")
        chars = sensitivity_for_all_chars(b["Ikz"], b["I_nom"])
        df_chart = pd.DataFrame({
            "Характеристика": list(chars.keys()),
            "Kч": list(chars.values()),
            "Статус": ["OK" if v >= 1.5 else "НЕТ" for v in chars.values()],
        })
        try:
            import plotly.express as px
            fig = px.bar(df_chart, x="Характеристика", y="Kч", color="Статус",
                         color_discrete_map={"OK": "#2ca02c", "НЕТ": "#d62728"})
            fig.add_hline(y=1.5, line_dash="dash", line_color="blue",
                          annotation_text="Порог 1.5")
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.bar_chart(df_chart.set_index("Характеристика")["Kч"])

        st.caption(
            "**Примечание.** Для проверки чувствительности используются верхние границы "
            "диапазона срабатывания отсечки: B=5·In, C=10·In, D=20·In, Z=3·In, L=5.5·In, K=14·In "
            "(ГОСТ Р 50030.2-2010). Это худший (наименее чувствительный) случай; "
            "внутри диапазона срабатывание носит вероятностный характер."
        )

# ============================================================
# ОТЧЁТ — ОДНИМ КЛИКОМ
# ============================================================
st.write("---")
if st.session_state.calc_results and st.session_state.voltage_results and st.session_state.breaker_results:
    report_data = {
        "windings": [
            {
                "scheme": w["scheme"],
                "scheme_name": w["scheme_name"],
                "S_ab": w["S_ab"], "S_bc": w["S_bc"], "S_ca": w["S_ca"], "S_phi": w["S_phi"],
                "S_nf": w["S_nf"], "total_load": w["total_load"],
                "rated_power": w["rated_power"],
                "r": w["r"], "I": w["I"], "du": w["du"],
            }
            for w in st.session_state.voltage_results
        ],
        "breaker": st.session_state.breaker_results,
    }
    buf = build_report(report_data)
    st.download_button(
        "📥 Скачать отчёт Word",
        data=buf,
        file_name="TN_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
else:
    st.info("Заполните все три вкладки, чтобы сформировать отчёт.")
