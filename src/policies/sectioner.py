"""Divide o PDF de políticas por seção numerada, preservando a página.

Sem embeddings: o manual (8 págs, ~5 mil tokens) é indexado por tópico (enum).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# tópico exposto ao LLM -> números das seções do manual
TOPICS: dict[str, list[str]] = {
    "sobre_a_loja": ["1"],
    "horario": ["2"],
    "pagamento": ["3"],
    "trocas_devolucoes": ["4"],
    "frete_entrega": ["5"],
    "promocoes": ["6"],
    "atendimento": ["7"],
    "garantia": ["8"],
    "privacidade": ["9"],
}


@dataclass(frozen=True)
class PolicySection:
    number: str
    title: str
    text: str
    page: int


def load_sections(pdf_path: Path) -> list[PolicySection]:
    """TODO: extrair texto com PyMuPDF e quebrar em '1. ...', '2. ...'."""
    raise NotImplementedError


def get_policy(topic: str, sections: list[PolicySection]) -> list[PolicySection]:
    """TODO: retorna as seções do tópico (com página para citação)."""
    raise NotImplementedError
