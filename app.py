import streamlit as st
import pandas as pd
import math
from calculations.load import (
    calculate_snf_star, calculate_snf_delta, evaluate_winding, suggest_optimization
)
from calculations.voltage_loss import (
    calculate_resistance, calculate_current, calculate_du, ALLOWED_LOSS
)
from calculations.breakers import (
    calculate_zk, calculate_ikz, get_trip_current,
    sensitivity_for_all_chars, BREAKER_MULTIPLIERS
)
from reports.word_builder import build_report

st.set_page_config(page_title="Проверка ТН по РД 34.35.305-79", layout="wide")
st.title("Проверка ТН и вторичных цепей (РД 34.35.305-79)")

SCHEMES = ["Звезда с нулём", "Звезда без нуля", "Открытый треугольник"]
TN_TYPES_STAR = ["3-фазный ТН (Sном — суммарная)", "Группа 3 однофазных (Sном — одной фазы)"]

# Инициализация
defaults = {
    "num_windings": 1,
    "calc_results": None,
    "voltage_results": None,
    "breakers_by_winding": None,
    "cable_params": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

tab1, tab2, tab3 = st.tabs(["Нагрузка ТН", "Потери напряжения", "Автоматы"])

# ==========================================================
# ВКЛАДКА 1 — Нагрузка ТН
# ==========================================================
with tab1:
    st.header("1. Расчёт нагрузки ТН")
    st.session_state.num_windings = int(st.number_input(
        "Количество вторичных обмоток (1–4):", min_value=1, max_value=4,
        value=st.session_state.num_windings,
    ))

    ALL_COLS = ["Прибор", "S_ab", "S_bc", "S_ca", "S_ф"]

    with st.form("load_form"):
        windings_input = []
        for i in range(st.session_state.num_windings):
            st.subheader(f"Обмотка {i+1}")
            c1, c2, c3 = st.columns(3)
            scheme = c1.selectbox("Схема соединения", SCHEMES, key=f"sch_{i}")

            if scheme == "Открытый треугольник":
                tn_type = "2single_delta"
                c2.write("")
                c2.write("**2 однофазных ТН**")
                rated_power = c3.number_input(
                    "Sном одного ТН в классе точности, В·А",
                    min_value=1.0, value=50.0, step=10.0, format="%.2f", key=f"pow_{i}"
                )
            else:
                tn_type_label = c2.selectbox("Тип", TN_TYPES_STAR, key=f"tn_{i}")
                tn_type = "3phase" if tn_type_label.startswith("3-фазный") else "3single"
                label_snom = ("Sном трёхфазного ТН (сумма фаз)" if tn_type == "3phase"
                              else "Sном одной фазы (однофазного ТН)")
                rated_power = c3.number_input(
                    label_snom + ", В·А",
                    min_value=1.0, value=(120.0 if tn_type == "3phase" else 50.0),
                    step=10.0, format="%.2f", key=f"pow_{i}"
                )

            show_phi = (scheme == "Звезда с нулём")

            if f"df_{i}" not in st.session_state:
                st.session_state[f"df_{i}"] = pd.DataFrame(
                    [{c: ("" if c == "Прибор" else 0.0) for c in ALL_COLS}]
                )
            stored = st.session_state[f"df_{i}"]
            for c in ALL_COLS:
                if c not in stored.columns:
                    stored[c] = "" if c == "Прибор" else 0.0

            visible = ["Прибор", "S_ab", "S_bc", "S_ca"] + (["S_ф"] if show_phi else [])
            display_df = stored[visible].copy()

            edited = st.data_editor(
                display_df, num_rows="dynamic",
                key=f"de_{i}_{'phi' if show_phi else 'nophi'}",
                column_config={
                    "Прибор": st.column_config.TextColumn("Прибор"),
                    "S_ab": st.column_config.NumberColumn("S_ab (В·А)", min_value=0.0, step=0.01, format="%.5f"),
                    "S_bc": st.column_config.NumberColumn("S_bc (В·А)", min_value=0.0, step=0.01, format="%.5f"),
                    "S_ca": st.column_config.NumberColumn("S_ca (В·А)", min_value=0.0, step=0.01, format="%.5f"),
                    **({"S_ф": st.column_config.NumberColumn("S_ф (В·А)", min_value=0.0, step=0.01, format="%.5f")} if show_phi else {}),
                },
            )
            # Слияние через reindex (безопасно при добавлении строк)
            new_df = edited.copy()
            for hidden in ALL_COLS:
                if hidden not in new_df.columns:
                    if hidden in stored.columns:
                        new_df[hidden] = stored[hidden].reindex(new_df.index).fillna(0.0).values
                    else:
                        new_df[hidden] = 0.0
            new_df = new_df[ALL_COLS]
            st.session_state[f"df_{i}"] = new_df

            if scheme == "Открытый треугольник":
                st.caption("S_ab, S_bc, S_ca — междуфазные нагрузки, включённые на соответствующие напряжения открытого треугольника (РД, стр. 109).")

            def _sum(col):
                if col not in new_df.columns: return 0.0
                return float(pd.to_numeric(new_df[col], errors="coerce").fillna(0).sum())

            windings_input.append({
                "scheme": "star" if "Звезда" in scheme else "delta",
                "scheme_name": scheme,
                "tn_type": tn_type,
                "rated_power": rated_power,
                "S_ab": _sum("S_ab"), "S_bc": _sum("S_bc"), "S_ca": _sum("S_ca"),
                "S_phi": _sum("S_ф") if show_phi else 0.0,
            })

        submitted = st.form_submit_button("Рассчитать нагрузки")

    if submitted:
        results = []
        for w in windings_input:
            S_nf, total, is_over, hint = evaluate_winding(
                w["scheme"], w["tn_type"],
                w["S_ab"], w["S_bc"], w["S_ca"], w["S_phi"], w["rated_power"]
            )
            results.append({**w, "S_nf": S_nf, "total_load": total,
                            "is_overload": is_over, "hint": hint})
        st.session_state.calc_results = results

    if st.session_state.calc_results:
        st.write("---")
        st.subheader("Результаты")
        for i, w in enumerate(st.session_state.calc_results):
            st.markdown(f"**Обмотка {i+1}: {w['scheme_name']}**")
            st.write(f"S_нф = **{w['S_nf']:.2f} В·А**, нагрузка для проверки = "
                     f"**{w['total_load']:.2f} В·А** ({w['hint']})")
            if w["is_overload"]:
                st.error(f"ПЕРЕГРУЗКА (номинал {w['rated_power']} В·А)")
                opt = suggest_optimization(
                    w["S_ab"], w["S_bc"], w["S_ca"], w["S_phi"],
                    w["scheme"], w["tn_type"], w["rated_power"]
                )
                if opt:
                    st.info(
                        f"💡 Рекомендация: перераспределите междуфазные нагрузки — "
                        f"S_ab={opt['new_ab']:.2f}, S_bc={opt['new_bc']:.2f}, "
                        f"S_ca={opt['new_ca']:.2f} В·А. Новая нагрузка = {opt['new_total']:.2f} В·А."
                    )
                else:
                    st.warning("Перераспределение между фазами не поможет — требуется ТН большей мощности или дополнительный ТН.")
            else:
                st.success(f"OK (≤ {w['rated_power']} В·А)")

# ==========================================================
# ВКЛАДКА 2 — Потери напряжения
# ==========================================================
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
                length = c1.number_input(f"Длина, м", min_value=1.0, value=30.0, step=1.0, key=f"L_{i}")
                cs = c2.number_input(f"Сечение, мм²", min_value=0.5, value=2.5, step=0.5, format="%.1f", key=f"cs_{i}")
                mat = c3.selectbox(f"Материал", ["Медь", "Алюминий"], key=f"m_{i}")
                purpose = st.selectbox(
                    f"Назначение цепи (допустимые потери)",
                    list(ALLOWED_LOSS.keys()), key=f"purp_{i}"
                )
                cable_params.append({
                    "length": length, "cs": cs, "mat": mat,
                    "purpose": purpose, "allowed": ALLOWED_LOSS[purpose],
                })
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
                st.write(f"r = {w['r']:.4f} Ом | I = {w['I']:.4f} А | "
                         f"ΔU = **{w['du']:.4f} %** | допустимо ≤ {w['allowed']:.2f} %")
                if w["du"] <= w["allowed"]:
                    st.success(f"OK: {w['du']:.4f}% ≤ {w['allowed']:.2f}%")
                else:
                    st.error(f"ПРЕВЫШЕНИЕ: {w['du']:.4f}% > {w['allowed']:.2f}%. "
                             f"Увеличьте сечение или разгрузите цепь.")

# ==========================================================
# ВКЛАДКА 3 — Автоматы (по обмоткам, до 10 параллельных на обмотку)
# ==========================================================
with tab3:
    st.header("3. Проверка автоматических выключателей")
    if not st.session_state.calc_results:
        st.warning("Сначала выполните расчёт нагрузок на вкладке 1.")
    else:
        with st.form("br_form"):
            breakers_data = []
            for i, w in enumerate(st.session_state.calc_results):
                st.subheader(f"Обмотка {i+1}: {w['scheme_name']}")

                # Параметры для Zк обмотки (по РД П.5)
                c1, c2, c3 = st.columns(3)
                uk = c1.number_input(f"Uк, % (обм. {i+1})", min_value=0.1, value=6.0, step=0.1, format="%.2f", key=f"uk_{i}")
                u_nom = c2.number_input(f"Uном обмотки, В (обм. {i+1})", value=(100.0 if w["scheme"] == "delta" else 100.0/math.sqrt(3)), key=f"unom_{i}")
                s_nom = c3.number_input(f"Sном ТН, В·А (обм. {i+1})", min_value=10.0, value=float(w["rated_power"]) if w["rated_power"] else 400.0, step=50.0, key=f"snom_{i}")

                # Параллельные автоматы
                n_br = st.number_input(f"Количество параллельных автоматов на обмотке (1–10)",
                                       min_value=1, max_value=10, value=1, key=f"nbr_{i}")
                st.markdown(f"*Автоматы обмотки {i+1}*")
                breakers = []
                for j in range(int(n_br)):
                    st.markdown(f"**Автомат {j+1} (обмотка {i+1})**")
                    bc1, bc2, bc3, bc4 = st.columns(4)
                    btype = bc1.selectbox("Тип", ["AP50", "KEAZ OptiDin BM63"], key=f"bt_{i}_{j}")
                    i_nom = bc2.number_input("Iном, А", min_value=0.5, value=6.3, step=0.1, format="%.2f", key=f"in_{i}_{j}")
                    char = None
                    if btype.startswith("KEAZ"):
                        char = bc3.selectbox("Характеристика", list(BREAKER_MULTIPLIERS.keys()), key=f"ch_{i}_{j}")
                    else:
                        bc3.write("—")
                    bc4.write(f"")  # spacer

                    bc5, bc6 = st.columns(2)
                    r_phase = bc5.number_input("r фазного провода, Ом", min_value=0.001, value=0.05, step=0.001, format="%.3f", key=f"rp_{i}_{j}")
                    r_zero = bc6.number_input("r нулевого провода, Ом", min_value=0.001, value=0.05, step=0.001, format="%.3f", key=f"rz_{i}_{j}")

                    breakers.append({
                        "type": btype, "I_nom": i_nom, "char": char,
                        "r_phase": r_phase, "r_zero": r_zero,
                    })
                breakers_data.append({
                    "uk": uk, "u_nom": u_nom, "s_nom": s_nom, "breakers": breakers,
                })

            sub_b = st.form_submit_button("Проверить автоматы")

        if sub_b:
            results_all = []
            for i, w in enumerate(st.session_state.calc_results):
                bd = breakers_data[i]
                zk = calculate_zk(bd["uk"], bd["u_nom"], bd["s_nom"])
                br_results = []
                for b in bd["breakers"]:
                    ikz_2 = calculate_ikz(100.0, zk, b["r_phase"])
                    ikz_1 = calculate_ikz(100.0, zk, b["r_phase"], b["r_zero"])
                    ikz_min = min(ikz_2, ikz_1)
                    i_trip = get_trip_current(b["I_nom"], b["type"], b["char"])
                    k_ch = ikz_min / i_trip
                    br_results.append({
                        **b, "ikz_2": ikz_2, "ikz_1": ikz_1,
                        "ikz_min": ikz_min, "k_ch": k_ch, "success": k_ch >= 1.5,
                    })
                results_all.append({"zk": zk, "breakers": br_results})
            st.session_state.breakers_by_winding = results_all

        if st.session_state.breakers_by_winding:
            st.write("---")
            for i, w in enumerate(st.session_state.breakers_by_winding):
                st.markdown(f"**Обмотка {i+1}: Zк = {w['zk']:.4f} Ом**")
                for j, b in enumerate(w["breakers"]):
                    st.write(
                        f"Автомат {j+1} ({b['type']}"
                        + (f"/{b['char']}" if b['char'] else "")
                        + f", Iном={b['I_nom']} А): "
                        f"Iкз_min={b['ikz_min']:.2f} А, Kч={b['k_ch']:.2f} — "
                        + ("✅ OK" if b["success"] else "❌ НЕ ПРОЙДЕН")
                    )
                # граф. сравнение для первого автомата обмотки
                if w["breakers"]:
                    b0 = w["breakers"][0]
                    st.caption(f"Сравнение характеристик при Iкз_min = {b0['ikz_min']:.2f} А, Iном = {b0['I_nom']} А:")
                    chars = sensitivity_for_all_chars(b0["ikz_min"], b0["I_nom"])
                    df_chart = pd.DataFrame({
                        "Характеристика": list(chars.keys()),
                        "Kч": list(chars.values()),
                        "Статус": ["OK" if v >= 1.5 else "НЕТ" for v in chars.values()],
                    })
                    try:
                        import plotly.express as px
                        fig = px.bar(df_chart, x="Характеристика", y="Kч",
                                     color="Статус",
                                     color_discrete_map={"OK": "#2ca02c", "НЕТ": "#d62728"})
                        fig.add_hline(y=1.5, line_dash="dash", line_color="blue",
                                      annotation_text="Порог 1.5")
                        st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}")
                    except ImportError:
                        st.bar_chart(df_chart.set_index("Характеристика")["Kч"])

        st.caption(
            "Кратности отсечки (верхние границы по ГОСТ Р 50030.2-2010): "
            "B=5, C=10, D=20, Z=3, L=5.5, K=14. Для АП50 — 4·Iном (РД п. 3.4.4)."
        )

# ==========================================================
# ОТЧЁТ — одним кликом
# ==========================================================
st.write("---")
ready = (st.session_state.calc_results
         and st.session_state.voltage_results
         and st.session_state.breakers_by_winding)

if ready:
    report_data = {
        "windings": [
            {
                "scheme": w["scheme"],
                "scheme_name": w["scheme_name"],
                "S_ab": w["S_ab"], "S_bc": w["S_bc"], "S_ca": w["S_ca"],
                "S_phi": w["S_phi"], "S_nf": w["S_nf"],
                "total_load": w["total_load"], "rated_power": w["rated_power"],
                "is_overload": w["is_overload"], "hint": w["hint"],
                "r": w["r"], "I": w["I"], "du": w["du"], "allowed": w["allowed"],
            }
            for w in st.session_state.voltage_results
        ],
        "breakers_by_winding": st.session_state.breakers_by_winding,
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
