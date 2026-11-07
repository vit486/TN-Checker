def check_accuracy_class(S_calc, S_rated_class):
    """S_calc — расчётная нагрузка; S_rated_class — номинал ТН в классе точности."""
    return S_calc <= S_rated_class