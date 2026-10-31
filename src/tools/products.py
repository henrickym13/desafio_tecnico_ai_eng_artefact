"""Tools de catálogo: buscar_produtos e detalhes_produto (já inclui promoção ativa)."""
from __future__ import annotations

from src.data.repositories import ProductRepository
from src.tools.errors import ToolError

BUSCAR_PRODUTOS_SCHEMA = {
    "name": "buscar_produtos",
    "description": (
        "Busca produtos do catálogo por categoria, faixa de preço ou texto livre. "
        "Os filtros de preço consideram o preço final (já com promoção ativa). "
        "Use SEMPRE antes de informar preço ou disponibilidade."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "consulta": {"type": "string", "description": "Texto livre: marca, modelo, tipo (ex.: 'nylon', 'elétrico')"},
            "categoria": {"type": "string", "description": "Ex.: violão, guitarra, baixo, bateria, teclado, ukulele"},
            "preco_min": {"type": "number", "description": "Em reais"},
            "preco_max": {"type": "number", "description": "Em reais"},
            "somente_disponiveis": {"type": "boolean", "description": "Padrão: true"},
        },
    },
}

DETALHES_PRODUTO_SCHEMA = {
    "name": "detalhes_produto",
    "description": (
        "Preço, disponibilidade, promoção ATIVA, preço no PIX, parcelamento e especificações de um "
        "produto específico. Se estiver indisponível, já traz alternativas. Use para 'quanto custa X?'."
    ),
    "parameters": {
        "type": "object",
        "properties": {"produto": {"type": "string", "description": "Nome, modelo ou id do produto"}},
        "required": ["produto"],
    },
}


def buscar_produtos(repo: ProductRepository, *, consulta: str | None = None, categoria: str | None = None,
                    preco_min: float | None = None, preco_max: float | None = None,
                    somente_disponiveis: bool = True) -> dict:
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise ToolError("preco_min não pode ser maior que preco_max.")
    return repo.search(query=consulta, category=categoria, min_price=preco_min,
                       max_price=preco_max, only_available=somente_disponiveis)


def detalhes_produto(repo: ProductRepository, *, produto: str) -> dict:
    return repo.get(produto)
