"""Cálculos de preço determinísticos (o LLM não faz conta; manual §3, §3.1 e §6.2)."""
from __future__ import annotations

PIX_DISCOUNT = 0.05  # §3: 5% sobre o preço de tabela (não vale sobre preço promocional, §6.2)


def format_brl(value: float) -> str:
    """2199 -> 'R$ 2.199,00'."""
    text = f"{value:,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def pix_price(list_price: float) -> float:
    return round(list_price * (1 - PIX_DISCOUNT), 2)


def _min_installment(n: int) -> float:
    """Parcela mínima por número de parcelas, conforme §3.1.

    Suposição: §3.1 prevalece sobre a tabela do §3 (que cita R$ 100 para todo crédito).
    Em 2x–3x interpreto "exceto abaixo de R$ 50,00" como parcela mínima de R$ 50.
    """
    if n >= 7:
        return 100.0
    if n >= 4:
        return 80.0
    if n >= 2:
        return 50.0
    return 0.0


def max_installments(price: float) -> dict:
    """Maior número de parcelas sem juros (até 12x) respeitando a parcela mínima."""
    for n in range(12, 0, -1):
        if price / n >= _min_installment(n):
            value = round(price / n, 2)
            return {"parcelas": n, "valor_parcela": value, "valor_parcela_fmt": format_brl(value)}
    return {"parcelas": 1, "valor_parcela": round(price, 2), "valor_parcela_fmt": format_brl(price)}
