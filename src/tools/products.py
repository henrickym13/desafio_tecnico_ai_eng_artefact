"""Tools de catálogo: buscar_produtos e detalhes_produto (já inclui promoção ativa)."""
from __future__ import annotations

BUSCAR_PRODUTOS_SCHEMA = {
    "name": "buscar_produtos",
    "description": "Busca produtos do catálogo por categoria, faixa de preço ou texto. "
                   "Use SEMPRE antes de informar preço ou disponibilidade.",
    "parameters": {
        "type": "object",
        "properties": {
            "consulta": {"type": "string", "description": "Texto livre (marca, modelo, tipo de corda...)"},
            "categoria": {"type": "string"},
            "preco_min": {"type": "number"},
            "preco_max": {"type": "number"},
            "somente_disponiveis": {"type": "boolean", "default": True},
        },
    },
}

DETALHES_PRODUTO_SCHEMA = {
    "name": "detalhes_produto",
    "description": "Preço, disponibilidade e promoção ATIVA de um produto específico.",
    "parameters": {
        "type": "object",
        "properties": {"produto": {"type": "string", "description": "Nome ou id"}},
        "required": ["produto"],
    },
}


def buscar_produtos(**kwargs) -> dict:
    """TODO: validar args (pydantic) -> ProductRepository.search -> dict serializável."""
    raise NotImplementedError


def detalhes_produto(produto: str) -> dict:
    """TODO: ProductRepository.get."""
    raise NotImplementedError
