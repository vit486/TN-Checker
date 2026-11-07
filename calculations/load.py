import math

def calculate_snf_star(S_ab, S_bc, S_ca, S_phi=0.0):
    """
    Нагрузка наиболее загруженной фазы для звезды (РД, формула 3).
    Пары нагрузок, приходящих на одну фазу:
      фаза a: (S_ab, S_ca), b: (S_ab, S_bc), c: (S_bc, S_ca)
    Для каждой пары: S_ф_пары = sqrt(S1² + S1·S2 + S2²) / √3
    """
    pairs = [(S_ab, S_ca), (S_ab, S_bc), (S_bc, S_ca)]
    max_between = 0.0
    for s1, s2 in pairs:
        val = math.sqrt(s1**2 + s1*s2 + s2**2) / math.sqrt(3)
        if val > max_between:
            max_between = val
    return max_between + S_phi

def calculate_snf_delta(S_ab, S_bc, S_ca):
    """
    Нагрузка на каждый ТН для открытого треугольника (РД, стр. 109).
    S2 = max(S_ab, S_bc), K = S_ca / S2
    """
    S2 = max(S_ab, S_bc)
    if S2 == 0:
        if S_ca == 0:
            return 0.0
        # Только перекрёстная нагрузка: каждый ТН несёт ~ S_ca
        return S_ca
    K = S_ca / S2
    return S2 * math.sqrt(K**2 + K + 1)

def suggest_optimization(S_ab, S_bc, S_ca, S_phi, scheme, rated_power):
    """Перераспределение нагрузки между междуфазными составляющими."""
    if scheme == "star":
        current = 3 * calculate_snf_star(S_ab, S_bc, S_ca, S_phi)
    else:
        current = calculate_snf_delta(S_ab, S_bc, S_ca)
    if current <= rated_power:
        return None

    loads = [S_ab, S_bc, S_ca]
    min_idx = loads.index(min(loads))
    new = list(loads)
    moved = new[min_idx]
    new[min_idx] = 0
    for j in range(3):
        if j != min_idx:
            new[j] += moved / 2

    if scheme == "star":
        new_total = 3 * calculate_snf_star(new[0], new[1], new[2], S_phi)
    else:
        new_total = calculate_snf_delta(new[0], new[1], new[2])

    if new_total <= rated_power:
        return {"new_ab": new[0], "new_bc": new[1], "new_ca": new[2], "new_total": new_total}
    return None
