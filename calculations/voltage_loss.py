# calculations/voltage_loss.py
import math

def calculate_resistance(length_m, cross_section_mm2, material="copper"):
    """
    Формула (6) из РД 34.35.305-79.
    Удельная проводимость: медь = 57, алюминий = 34.5.
    """
    gamma = 57.0 if material == "copper" else 34.5
    return length_m / (gamma * cross_section_mm2)

def calculate_current(S_nf, mode="3phase"):
    """
    Ток нагрузки в фазе.
    Для 3-фазного (линейное 100В, фазное 100/√3): I = S / (100/√3)
    Для 2-проводного (линейное 100В): I = S / 100
    """
    if mode == "3phase":
        return S_nf / (100 / math.sqrt(3))
    else:
        return S_nf / 100.0

def calculate_du(I, r, mode="3phase"):
    """
    Потери напряжения по формулам (7) и (8).
    Для 3 фаз K = √3, для 2 жил K = 2.
    """
    K = math.sqrt(3) if mode == "3phase" else 2.0
    return K * I * r
