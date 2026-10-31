from src.services.pricing import format_brl, max_installments, pix_price


def test_format_brl():
    assert format_brl(2199) == "R$ 2.199,00"
    assert format_brl(1234.5) == "R$ 1.234,50"
    assert format_brl(99.9) == "R$ 99,90"


def test_pix_price_is_5_percent_off():
    assert pix_price(2199.0) == 2089.05


def test_max_installments_follow_manual_3_1():
    assert max_installments(2199.0)["parcelas"] == 12            # 183,25 >= 100
    assert max_installments(599.9)["parcelas"] == 6              # 7x daria < R$ 100; 6x = 99,98 >= 80
    assert max_installments(599.9)["valor_parcela"] == 99.98
    assert max_installments(100.0)["parcelas"] == 2              # 3x daria < R$ 50
    assert max_installments(40.0)["parcelas"] == 1
