import math

def calculate_zk(uk_percent, u_nom_v, s_nom_va):
    """Сопротивление КЗ ТН, приведенное к вторичной обмотке (формула П.5)"""
    return (uk_percent * (u_nom_v**2)) / (100 * s_nom_va)

def calculate_ikz_min(U_mf, zk, r_sum, r_zero_sum=None):
    """
    Минимальный ток КЗ (формулы П.12 и П.13).
    r_sum - сопротивление фазного провода.
    r_zero_sum - сопротивление нулевого провода (для однофазного КЗ).
    """
    if r_zero_sum is not None:
        # Однофазное КЗ (формула П.13)
        return (100 / math.sqrt(3)) / math.sqrt(zk**2 + (r_sum + r_zero_sum)**2)
    else:
        # Двухфазное КЗ (формула П.12)
        return U_mf / (2 * math.sqrt(zk**2 + r_sum**2))

def check_breaker(Ikz_min, I_nom, breaker_type, characteristic=None):
    """Проверка чувствительности автомата"""
    if breaker_type == "AP50":
        # Для АП50 по РД принимаем 4*Iном (для обеспечения Kч >= 1.5)
        I_srab = 4 * I_nom
    else:
        # Для KEAZ OptiDin BM63 (по IEC 60898-1)
        multipliers = {
            "B": 5, "C": 10, "D": 20, "Z": 3, "L": 5.5, "K": 14
        }
        I_srab = multipliers.get(characteristic, 10) * I_nom
        
    K_ch = Ikz_min / I_srab
    return K_ch, K_ch >= 1.5
