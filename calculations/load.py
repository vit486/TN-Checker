import math

def calculate_snf_star(S_ab, S_bc, S_ca, S_phi=0.0):
    """РД ф. (3): нагрузка наиболее загруженной фазы для звезды."""
    pairs = [(S_ab, S_ca), (S_ab, S_bc), (S_bc, S_ca)]
    max_between = 0.0
    for s1, s2 in pairs:
        val = math.sqrt(s1**2 + s1 * s2 + s2**2) / math.sqrt(3)
        if val > max_between:
            max_between = val
    return max_between + S_phi

def calculate_snf_delta(S_ab, S_bc, S_ca):
    """
    РД стр. 109: нагрузка на каждый ТН открытого треугольника.
    S_нагр.тн = S_2·√(K²+K+1), K = S_ca/S_2, S_2 = max(S_ab, S_bc).
    """
    S2 = max(S_ab, S_bc)
    if S2 == 0:
        return S_ca  # только перекрёстная
    K = S_ca / S2
    return S2 * math.sqrt(K**2 + K + 1)

def evaluate_winding(scheme, tn_type, S_ab, S_bc, S_ca, S_phi, S_nom):
    """
    Возвращает (S_nf, total_load, is_overload, hint).
    tn_type: '3phase' | '3single' | '2single_delta'
    """
    if scheme == "star":
        S_nf = calculate_snf_star(S_ab, S_bc, S_ca, S_phi)
        if tn_type == "3phase":
            total = 3 * S_nf
            hint = "3·S_нф (для трёхфазного ТН сравнивают с суммой трёх фаз)"
        else:  # 3single
            total = S_nf
            hint = "S_нф (для группы 3 однофазных — с мощностью одной фазы)"
    else:  # delta
        S_nf = calculate_snf_delta(S_ab, S_bc, S_ca)
        total = S_nf
        hint = "S_нагр.тн (для 2 однофазных — с мощностью одного ТН)"
    return S_nf, total, total > S_nom, hint

def suggest_optimization(S_ab, S_bc, S_ca, S_phi, scheme, tn_type, rated_power):
    if scheme == "star":
        cur_total = (3 if tn_type == "3phase" else 1) * calculate_snf_star(S_ab, S_bc, S_ca, S_phi)
    else:
        cur_total = calculate_snf_delta(S_ab, S_bc, S_ca)
    if cur_total <= rated_power:
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
        new_total = (3 if tn_type == "3phase" else 1) * calculate_snf_star(new[0], new[1], new[2], S_phi)
    else:
        new_total = calculate_snf_delta(new[0], new[1], new[2])

    if new_total <= rated_power:
        return {"new_ab": new[0], "new_bc": new[1], "new_ca": new[2], "new_total": new_total}
    return None
