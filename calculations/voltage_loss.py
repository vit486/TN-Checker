import math

def voltage_loss(cables, phase_mode="three_phase"):
    """
    cables: список словарей {'I': ток, А; 'r': сопротивление, Ом}
    phase_mode: 'three_phase' → K=√3; 'two_wire' → K=2
    Возвращает потерю линейного напряжения, В (численно равна %).
    """
    K = math.sqrt(3) if phase_mode == "three_phase" else 2.0
    return sum(K * c["I"] * c["r"] for c in cables)

def voltage_loss_3u0(cables):
    """Потери в цепи 3U0 по формуле (8)."""
    return 2 * sum(c["I"] * c["r"] for c in cables)