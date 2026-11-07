import math

def calculate_snf_star(S_ab, S_bc, S_ca, S_phi):
    """
    Расчёт нагрузки наиболее загруженной фазы для схемы «звезда».
    Согласно РД 34.35.305-79 п. 3.2.2 и Приложению 3.
    """
    loads = sorted([S_ab, S_bc, S_ca], reverse=True)
    S1, S2 = loads[0], loads[1]
    
    if S1 == 0 and S_phi == 0:
        return 0.0

    if S2 == 0:
        # Если есть только одна междуфазная нагрузка
        S_nf = S1 / math.sqrt(3)
    else:
        K = S1 / S2
        S_nf = (S2 / math.sqrt(3)) * math.sqrt(K**2 + K + 1)
        
    return S_nf + S_phi

def calculate_snf_delta(S_ab, S_bc, S_ca):
    """
    Расчёт нагрузки для схемы «открытый треугольник».
    Согласно РД 34.35.305-79 п. 3.2.4 и Примеру 1.
    """
    loads = sorted([S_ab, S_bc, S_ca], reverse=True)
    S1, S2 = loads[0], loads[1]
    
    if S2 == 0:
        return S1
        
    K = S1 / S2
    return S2 * math.sqrt(K**2 + K + 1)

def suggest_optimization(S_ab, S_bc, S_ca, S_phi, scheme, rated_power):
    """
    Предлагает вариант перераспределения нагрузки, если есть перегрузка.
    """
    if scheme == "star":
        current_snf = calculate_snf_star(S_ab, S_bc, S_ca, S_phi)
        current_total = 3 * current_snf
    else:
        current_snf = calculate_snf_delta(S_ab, S_bc, S_ca)
        current_total = current_snf

    if current_total <= rated_power:
        return None

    # Оптимизация: перенос наименьшей междуфазной нагрузки на две другие
    loads = [S_ab, S_bc, S_ca]
    min_idx = loads.index(min(loads))
    
    new_ab, new_bc, new_ca = S_ab, S_bc, S_ca
    moved_val = loads[min_idx]
    
    if min_idx == 0: # Переносим с S_ab
        new_ab = 0
        new_bc += moved_val / 2
        new_ca += moved_val / 2
    elif min_idx == 1: # Переносим с S_bc
        new_bc = 0
        new_ab += moved_val / 2
        new_ca += moved_val / 2
    else: # Переносим с S_ca
        new_ca = 0
        new_ab += moved_val / 2
        new_bc += moved_val / 2

    if scheme == "star":
        new_snf = calculate_snf_star(new_ab, new_bc, new_ca, S_phi)
        new_total = 3 * new_snf
    else:
        new_snf = calculate_snf_delta(new_ab, new_bc, new_ca)
        new_total = new_snf

    if new_total <= rated_power:
        return {
            "new_ab": new_ab, "new_bc": new_bc, "new_ca": new_ca,
            "new_snf": new_snf, "new_total": new_total
        }
    return None
