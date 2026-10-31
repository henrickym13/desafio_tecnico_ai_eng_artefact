"""Acesso a dados estruturados. É a ÚNICA camada que conhece o Dataset.

As tools chamam estes repositórios; o agente nunca toca em CSV/DataFrame.
"""
from __future__ import annotations

from src.data.loader import Dataset


class ProductRepository:
    def __init__(self, ds: Dataset) -> None:
        self.ds = ds

    def search(self, query: str | None, category: str | None,
               min_price: float | None, max_price: float | None,
               only_available: bool = True, limit: int = 10) -> list[dict]:
        """TODO: filtros + busca normalizada (sem acento) + fuzzy (rapidfuzz)."""
        raise NotImplementedError

    def get(self, name_or_id: str) -> dict | None:
        """TODO: retorna produto + promoção ATIVA (se houver) + preço final."""
        raise NotImplementedError


class OrderRepository:
    def __init__(self, ds: Dataset) -> None:
        self.ds = ds

    def get_verified(self, order_id: int, phone_or_email: str) -> dict | None:
        """TODO: devolve o pedido só se phone/email bater com o DONO do pedido.
        Nunca buscar cliente por email isolado (há email duplicado: clientes 11 e 43)."""
        raise NotImplementedError
