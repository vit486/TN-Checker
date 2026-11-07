import math

def calculate_resistance(length_m, cross_section_mm2, material="copper"):
    gamma = 57.0 if material == "copper" else 34.5
    return length_m / (gamma * cross_section_mm2)

def calculate_current(S_nf, scheme="star"):
    return S_nf / (100 / math.sqrt(3)) if scheme == "star" else S_nf / 100.0

def calculate_du(I, r, scheme="star"):
    K = math.sqrt(3) if scheme == "star" else 2.0
    return K * I * r
