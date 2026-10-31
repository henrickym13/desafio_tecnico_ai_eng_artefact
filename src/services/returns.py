"""Regras de prazo de troca/devolução (manual §4 e §8.1), calculadas em Python.

O LLM não faz conta de data. A data de recebimento real não existe nos dados:
usa-se `estimated_delivery` como proxy (suposição documentada no README).
Todas as regras assumem compra online (todos os pedidos têm envio/rastreio).
"""
from __future__ import annotations

from datetime import date

ARREPENDIMENTO_DIAS = 7   # §4.1 direito de arrependimento (dias corridos após o recebimento)
DEFEITO_DIAS = 30         # §4.2 troca por defeito de fabricação
PREFERENCIA_DIAS = 7      # §4.3 troca por preferência
GARANTIA_LEGAL_DIAS = 90  # §8.1 garantia legal

WINDOWS = {
    "arrependimento": ARREPENDIMENTO_DIAS,
    "troca_por_defeito": DEFEITO_DIAS,
    "troca_por_preferencia": PREFERENCIA_DIAS,
    "garantia_legal": GARANTIA_LEGAL_DIAS,
}


def evaluate_windows(reference_date: date, today: date) -> dict:
    days = (today - reference_date).days
    return {
        name: {
            "prazo_dias": limit,
            "dentro_do_prazo": days <= limit,
            "dias_restantes": max(limit - days, 0),
        }
        for name, limit in WINDOWS.items()
    }


def evaluate_return(status: str, estimated_delivery: date | None, today: date) -> dict:
    if status == "delivered":
        if estimated_delivery is None:
            return {
                "situacao": "entregue_sem_data",
                "janelas": None,
                "mensagem": "Pedido entregue, mas sem data de entrega registrada: encaminhar a um atendente.",
            }
        return {
            "situacao": "entregue",
            "data_referencia_entrega": estimated_delivery.isoformat(),
            "dias_desde_a_entrega": (today - estimated_delivery).days,
            "observacao_data": "Data real de entrega indisponível; usada a previsão de entrega como referência.",
            "janelas": evaluate_windows(estimated_delivery, today),
            "mensagem": "Condições do produto e do processo: consulte a política de trocas e devoluções.",
        }
    if status == "shipped":
        return {
            "situacao": "em_transito",
            "janelas": None,
            "mensagem": "Pedido ainda não recebido: os prazos de arrependimento e troca só começam a contar na entrega.",
        }
    if status in ("pending", "confirmed"):
        return {
            "situacao": "nao_enviado",
            "janelas": None,
            "mensagem": "Pedido ainda não enviado, então não é caso de devolução. O manual não detalha o "
                        "cancelamento nessa etapa: encaminhar a um atendente.",
        }
    return {  # cancelled
        "situacao": "cancelado",
        "janelas": None,
        "mensagem": "Pedido já cancelado: não há o que devolver.",
    }
