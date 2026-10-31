"""Fase 1: carrega e trata os CSVs. Executado uma vez no start (tudo em memória).

Tratamentos (ver README > Dados):
- products.specs: JSON em string -> dict
- products: coluna derivada `available` = status == 'active' and stock_quantity > 0
- promotions: manter só is_active == 1 em `active_promotions`; preço promocional calculado aqui
- orders: payment_method (ex.: 'credit_6x') -> rótulo legível; datas -> date
- customers: telefone normalizado para dígitos (usado na verificação de identidade)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class Dataset:
    categories: pd.DataFrame
    customers: pd.DataFrame
    products: pd.DataFrame
    promotions: pd.DataFrame
    orders: pd.DataFrame
    order_items: pd.DataFrame


def load_dataset(raw_dir: Path) -> Dataset:
    """TODO: ler CSVs, aplicar os tratamentos acima e retornar Dataset."""
    raise NotImplementedError
