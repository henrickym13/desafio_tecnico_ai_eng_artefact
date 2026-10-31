"""Tools de pedido: consultar_pedido e verificar_elegibilidade_devolucao.

Regras:
- Identidade: order_id + telefone/email que bata com o dono do pedido.
- Falha -> mensagem genérica (não revela se o pedido existe).
- O LLM NÃO calcula datas: a elegibilidade (§4 do manual) é decidida em Python.
- Entrega real não existe nos dados: usa-se estimated_delivery como proxy (documentado).
"""
from __future__ import annotations

CONSULTAR_PEDIDO_SCHEMA = {
    "name": "consultar_pedido",
    "description": "Status, itens, rastreio e previsão de um pedido. Exige número do pedido "
                   "e telefone OU email do titular.",
    "parameters": {
        "type": "object",
        "properties": {
            "numero_pedido": {"type": "integer"},
            "telefone_ou_email": {"type": "string"},
        },
        "required": ["numero_pedido", "telefone_ou_email"],
    },
}

ELEGIBILIDADE_DEVOLUCAO_SCHEMA = {
    "name": "verificar_elegibilidade_devolucao",
    "description": "Calcula se um pedido do cliente já verificado na sessão está dentro dos "
                   "prazos de arrependimento (7 dias), troca por defeito (30) e garantia legal (90).",
    "parameters": {
        "type": "object",
        "properties": {"numero_pedido": {"type": "integer"}},
        "required": ["numero_pedido"],
    },
}


def consultar_pedido(numero_pedido: int, telefone_ou_email: str, *, session) -> dict:
    """TODO: OrderRepository.get_verified; em sucesso, grava session.verified_customer_id."""
    raise NotImplementedError


def verificar_elegibilidade_devolucao(numero_pedido: int, *, session, today) -> dict:
    """TODO: exige sessão verificada e pedido do mesmo cliente; só status 'delivered'
    entra em arrependimento; pending/confirmed -> orientar cancelamento (lacuna do manual
    -> encaminhar a atendente humano)."""
    raise NotImplementedError
