"""Tools de pedido: consultar_pedido e verificar_elegibilidade_devolucao.

Regras:
- Identidade: order_id + telefone/email que bata com o dono do pedido.
- O cliente verificado fica em `session.verified_customer_id` (Python); o LLM nunca informa customer_id.
- Falha -> mensagem genérica (não revela se o pedido existe nem de quem é).
- Tentativas inválidas são limitadas por sessão.
- O LLM NÃO calcula datas: a elegibilidade (§4 do manual) é decidida em Python.
"""
from __future__ import annotations

from datetime import date

from src.data.repositories import ORDER_STATUS_DESCRIPTIONS, OrderRepository
from src.services.memory import SessionState
from src.services.pricing import format_brl
from src.services.returns import evaluate_return

MAX_FAILED_VERIFICATIONS = 5

NOT_FOUND_MESSAGE = (
    "Não encontrei um pedido com esses dados. Confira o número do pedido e o telefone ou email "
    "usados na compra."
)

CONSULTAR_PEDIDO_SCHEMA = {
    "name": "consultar_pedido",
    "description": (
        "Status, itens, rastreio e previsão de entrega de um pedido. Exige o número do pedido e o "
        "telefone OU email do titular na primeira consulta; depois de verificado na conversa, o "
        "titular pode consultar outros pedidos dele sem informar de novo."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "numero_pedido": {"type": "integer"},
            "telefone_ou_email": {"type": "string", "description": "Telefone ou email do titular do pedido"},
        },
        "required": ["numero_pedido"],
    },
}

ELEGIBILIDADE_DEVOLUCAO_SCHEMA = {
    "name": "verificar_elegibilidade_devolucao",
    "description": (
        "Calcula se um pedido do cliente (já verificado na conversa) está dentro dos prazos de "
        "arrependimento (7 dias), troca por defeito (30), troca por preferência (7) e garantia legal "
        "(90). Use junto com consultar_politicas('trocas_devolucoes') para explicar as condições."
    ),
    "parameters": {
        "type": "object",
        "properties": {"numero_pedido": {"type": "integer"}},
        "required": ["numero_pedido"],
    },
}


def _public_view(order: dict) -> dict:
    """Só o que o cliente pode ver: sem customer_id, telefone ou email."""
    return {
        "numero_pedido": order["order_id"],
        "cliente": order["customer_first_name"],
        "status": order["status"],
        "status_descricao": ORDER_STATUS_DESCRIPTIONS.get(order["status"], order["status"]),
        "data_pedido": order["order_date"].isoformat(),
        "itens": order["items"],
        "total": order["total_brl"],
        "total_fmt": format_brl(order["total_brl"]),
        "forma_pagamento": order["payment_label"],
        "codigo_rastreio": order["tracking_code"],
        "previsao_entrega": order["estimated_delivery"].isoformat() if order["estimated_delivery"] else None,
        "observacoes": order["notes"],
    }


def _blocked(session: SessionState) -> dict | None:
    if session.failed_verifications >= MAX_FAILED_VERIFICATIONS:
        return {"ok": False, "bloqueado": True,
                "mensagem": "Por segurança, não consigo mais verificar pedidos nesta conversa. "
                            "Posso encaminhar você a um atendente."}
    return None


def _needs_verification() -> dict:
    return {"ok": False, "precisa_verificacao": True,
            "mensagem": "Para consultar um pedido preciso do número do pedido e do telefone ou email do titular."}


def consultar_pedido(orders: OrderRepository, session: SessionState, *, numero_pedido: int,
                     telefone_ou_email: str | None = None) -> dict:
    if (blocked := _blocked(session)) is not None:
        return blocked
    if telefone_ou_email:
        order = orders.get_verified(numero_pedido, telefone_ou_email)
    elif session.verified_customer_id is not None:
        order = orders.get_for_customer(numero_pedido, session.verified_customer_id)
    else:
        return _needs_verification()

    if order is None:
        session.failed_verifications += 1
        return {"ok": False, "mensagem": NOT_FOUND_MESSAGE}
    session.verified_customer_id = order["customer_id"]
    session.failed_verifications = 0
    return {"ok": True, "pedido": _public_view(order)}


def verificar_elegibilidade_devolucao(orders: OrderRepository, session: SessionState, today: date, *,
                                      numero_pedido: int) -> dict:
    if (blocked := _blocked(session)) is not None:
        return blocked
    if session.verified_customer_id is None:
        return _needs_verification()
    order = orders.get_for_customer(numero_pedido, session.verified_customer_id)
    if order is None:
        session.failed_verifications += 1
        return {"ok": False, "mensagem": NOT_FOUND_MESSAGE}
    result = evaluate_return(order["status"], order["estimated_delivery"], today)
    return {"ok": True, "numero_pedido": order["order_id"], "status": order["status"],
            "hoje": today.isoformat(), **result}