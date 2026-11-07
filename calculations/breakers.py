import math

# Кратность срабатывания отсечки (верхняя граница по IEC 60898-1 / ГОСТ Р 50030.2)
BREAKER_MULTIPLIERS = {
    "B": 5, "C": 10, "D": 20, "Z": 3, "L": 5.5, "K": 14
}

def calculate_zk(uk_percent, u_nom_v, s_nom_va):
    return (uk_percent * u_nom_v**2) / (100 * s_nom_va)

def calculate_ikz(U_mf, zk, r_phase, r_zero=None):
    """П.12 (2-фазное) и П.13 (1-фазное) из РД."""
    if r_zero is not None:
        return (100 / math.sqrt(3)) / math.sqrt(zk**2 + (r_phase + r_zero)**2)
    return U_mf / (2 * math.sqrt(zk**2 + r_phase**2))

def get_trip_current(I_nom, breaker_type, characteristic=None):
    if breaker_type == "AP50":
        return 4 * I_nom
    return BREAKER_MULTIPLIERS.get(characteristic, 10) * I_nom

def sensitivity_for_all_chars(Ikz_min, I_nom):
    """Для графика: Kч по всем характеристикам KEAZ."""
    return {c: Ikz_min / (mult * I_nom) for c, mult in BREAKER_MULTIPLIERS.items()}
