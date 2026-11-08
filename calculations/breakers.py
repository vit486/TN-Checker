import math

BREAKER_MULTIPLIERS = {"B": 5, "C": 10, "D": 20, "Z": 3, "L": 5.5, "K": 14}

def calculate_zk(uk_percent, u_nom_v, s_nom_va):
    return (uk_percent * u_nom_v**2) / (100 * s_nom_va)

def calculate_ikz(u_mf, zk, r_phase, r_zero=None):
    if r_zero is not None:
        return (100 / math.sqrt(3)) / math.sqrt(zk**2 + (r_phase + r_zero)**2)
    return u_mf / (2 * math.sqrt(zk**2 + r_phase**2))

def get_trip_current(i_nom, breaker_type, characteristic=None):
    if breaker_type == "AP50":
        return 4 * i_nom
    return BREAKER_MULTIPLIERS.get(characteristic, 10) * i_nom

def sensitivity_for_all_chars(ikz_min, i_nom):
    return {c: ikz_min / (m * i_nom) for c, m in BREAKER_MULTIPLIERS.items()}
