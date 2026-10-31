"""Tool consultar_politicas: devolve seções do manual com página (sem RAG vetorial)."""
from __future__ import annotations

from src.policies.sectioner import TOPICS

CONSULTAR_POLITICAS_SCHEMA = {
    "name": "consultar_politicas",
    "description": "Consulta o manual de políticas da loja (horário, pagamento, trocas, frete, "
                   "promoções, garantia...). Responda SOMENTE com base no texto retornado; "
                   "se não houver a regra, diga que vai confirmar com a equipe.",
    "parameters": {
        "type": "object",
        "properties": {"topico": {"type": "string", "enum": sorted(TOPICS)}},
        "required": ["topico"],
    },
}


def consultar_politicas(topico: str) -> dict:
    """TODO: sectioner.get_policy -> [{secao, titulo, texto, pagina}]."""
    raise NotImplementedError
