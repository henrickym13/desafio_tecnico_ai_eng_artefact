from datetime import date

from src.services.returns import evaluate_return

DELIVERY = date(2026, 2, 17)


def test_delivered_inside_regret_window():
    r = evaluate_return("delivered", DELIVERY, date(2026, 2, 20))
    assert r["situacao"] == "entregue" and r["dias_desde_a_entrega"] == 3
    assert r["janelas"]["arrependimento"] == {"prazo_dias": 7, "dentro_do_prazo": True, "dias_restantes": 4}


def test_regret_window_boundary_is_day_7_inclusive():
    assert evaluate_return("delivered", DELIVERY, date(2026, 2, 24))["janelas"]["arrependimento"]["dentro_do_prazo"]
    assert not evaluate_return("delivered", DELIVERY, date(2026, 2, 25))["janelas"]["arrependimento"]["dentro_do_prazo"]


def test_defect_and_legal_warranty_windows():
    w = evaluate_return("delivered", DELIVERY, date(2026, 3, 30))["janelas"]  # 41 dias
    assert not w["arrependimento"]["dentro_do_prazo"]
    assert not w["troca_por_defeito"]["dentro_do_prazo"]
    assert w["garantia_legal"]["dentro_do_prazo"]
    assert w["garantia_legal"]["dias_restantes"] == 49


def test_non_delivered_statuses_have_no_windows():
    assert evaluate_return("shipped", None, date(2026, 3, 1))["situacao"] == "em_transito"
    assert evaluate_return("confirmed", None, date(2026, 3, 1))["situacao"] == "nao_enviado"
    assert evaluate_return("pending", None, date(2026, 3, 1))["situacao"] == "nao_enviado"
    assert evaluate_return("cancelled", None, date(2026, 3, 1))["situacao"] == "cancelado"
    assert evaluate_return("shipped", None, date(2026, 3, 1))["janelas"] is None
