"""Fase 1: testes do tratamento de dados (escritos junto com o loader)."""
import pytest


@pytest.mark.skip(reason="loader ainda não implementado")
def test_availability_rules():
    # produto 96: active + estoque 0 -> indisponível
    # produto 136: discontinued + estoque 13 -> indisponível
    # produto 130: coming_soon + estoque 2 -> indisponível
    ...


@pytest.mark.skip(reason="loader ainda não implementado")
def test_only_active_promotions():
    # só promotion_id 12, 14, 19, 24; Takamine GD20 (95) sem promoção ativa
    ...


@pytest.mark.skip(reason="repositório ainda não implementado")
def test_order_requires_owner_phone_or_email():
    # pedido 7 + telefone do cliente 14 -> ok; + telefone de outro cliente -> None
    # email bruno.martins@jmail.com (clientes 11 e 43) não identifica o pedido sozinho
    ...
