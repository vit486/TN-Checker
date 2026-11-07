# calculations/breakers.py

def check_ap50(I_kz_min, I_nom_rascep):
    """
    Проверка чувствительности отсечки АП50.
    Согласно РД п. 3.4.4, коэффициент чувствительности K_ч >= 1.5.
    Для АП50 с кратностью 3.5, ток срабатывания ~ 4 * I_ном.
    """
    I_srab = 4 * I_nom_rascep
    K_ch = I_kz_min / I_srab
    return K_ch >= 1.5, K_ch

def check_keaz_optidin(I_kz_min, I_nom, characteristic="C"):
    """
    Проверка автоматов KEAZ OptiDin BM63.
    Характеристики B, C, D.
    """
    # Примерные кратности для KEAZ (нужно уточнять по паспорту):
    # B: 3-5, C: 5-10, D: 10-20
    multipliers = {"B": 5, "C": 10, "D": 20}
    I_srab = multipliers.get(characteristic, 10) * I_nom
    K_ch = I_kz_min / I_srab
    return K_ch >= 1.5, K_ch
