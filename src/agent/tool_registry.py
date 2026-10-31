"""Registro explícito de tools: só o que está aqui pode ser executado."""
from __future__ import annotations

from src.tools.orders import CONSULTAR_PEDIDO_SCHEMA, ELEGIBILIDADE_DEVOLUCAO_SCHEMA
from src.tools.policies import CONSULTAR_POLITICAS_SCHEMA
from src.tools.products import BUSCAR_PRODUTOS_SCHEMA, DETALHES_PRODUTO_SCHEMA


class ToolRegistry:
    def __init__(self) -> None:
        self._schemas = [
            BUSCAR_PRODUTOS_SCHEMA,
            DETALHES_PRODUTO_SCHEMA,
            CONSULTAR_PEDIDO_SCHEMA,
            ELEGIBILIDADE_DEVOLUCAO_SCHEMA,
            CONSULTAR_POLITICAS_SCHEMA,
        ]
        self._handlers: dict = {}  # TODO: nome -> função (injetar repositórios/sessão)

    def get_schemas(self) -> list[dict]:
        return self._schemas

    def execute(self, name: str, args: dict, *, session) -> dict:
        """TODO: rejeitar tool desconhecida; validar args; capturar exceções -> erro estruturado."""
        raise NotImplementedError
