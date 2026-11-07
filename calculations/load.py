# calculations/load.py
import math

def calculate_snf_3phase(S_ab, S_bc, S_ca, S_phi_max):
    """
    Расчёт нагрузки наиболее загруженной фазы для 3-фазного ТН (звезда).
    Согласно РД 34.35.305-79 (Пример 2, стр. 115).
    """
    loads = sorted([S_ab, S_bc, S_ca], reverse=True)
    S1, S2 = loads[0], loads[1]
    
    if S2 == 0:
        return S1 + S_phi_max
    
    K = S1 / S2
    S_nf = (S2 / math.sqrt(3)) * math.sqrt(K**2 + K + 1)
    return S_nf + S_phi_max

def calculate_snf_open_delta(S_ab, S_bc, S_ca):
    """
    Расчёт нагрузки для схемы открытого треугольника (2 ТН).
    Согласно РД 34.35.305-79 (Пример 1, стр. 114).
    """
    loads = sorted([S_ab, S_bc, S_ca], reverse=True)
    S1, S2 = loads[0], loads[1]

    if S2 == 0:
        # Если есть только одна междуфазная нагрузка — она вся ложится на ТН
        return S1

    K = S1 / S2
    return S2 * math.sqrt(K**2 + K + 1)
