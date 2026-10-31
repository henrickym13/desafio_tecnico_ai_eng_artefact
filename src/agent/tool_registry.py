"""Registro explícito de tools: só o que está registrado pode ser executado.

Valida e converte os argumentos do LLM conforme o schema e devolve erros estruturados
(nunca deixa uma exceção da tool derrubar o loop do agente).
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Callable

from src.data.repositories import OrderRepository, ProductRepository
from src.services.memory import SessionState
from src.tools import orders as order_tools
from src.tools import products as product_tools
from src.tools.errors import ToolError

log = logging.getLogger(__name__)

Handler = Callable[..., dict]


def _coerce(name: str, spec: dict, value: Any) -> Any:
    kind = spec.get("type")
    try:
        if kind == "integer":
            if isinstance(value, bool):
                raise ValueError
            number = float(str(value).replace(",", ".")) if isinstance(value, str) else float(value)
            if number != int(number):
                raise ValueError
            return int(number)
        if kind == "number":
            if isinstance(value, bool):
                raise ValueError
            return float(str(value).replace(",", ".")) if isinstance(value, str) else float(value)
        if kind == "boolean":
            if isinstance(value, bool):
                return value
            if str(value).strip().lower() in ("true", "sim", "1"):
                return True
            if str(value).strip().lower() in ("false", "nao", "não", "0"):
                return False
            raise ValueError
        if kind == "string":
            if isinstance(value, (dict, list)):
                raise ValueError
            return str(value).strip()
    except (TypeError, ValueError):
        raise ToolError(f"Argumento '{name}' inválido (esperado {kind}).") from None
    return value


def validate_args(schema: dict, args: Any) -> dict:
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ToolError("Argumentos devem ser um objeto.")
    params = schema["parameters"]
    props = params.get("properties", {})
    unknown = set(args) - set(props)
    if unknown:
        raise ToolError(f"Argumentos desconhecidos: {', '.join(sorted(unknown))}.")
    clean: dict = {}
    for name, value in args.items():
        if value is None:
            continue
        value = _coerce(name, props[name], value)
        if "enum" in props[name] and value not in props[name]["enum"]:
            raise ToolError(f"Valor inválido para '{name}'. Opções: {', '.join(props[name]['enum'])}.")
        clean[name] = value
    missing = [r for r in params.get("required", []) if r not in clean]
    if missing:
        raise ToolError(f"Argumentos obrigatórios ausentes: {', '.join(missing)}.")
    return clean


class ToolRegistry:
    def __init__(self, *, products: ProductRepository, orders: OrderRepository,
                 today_fn: Callable[[], date] = date.today) -> None:
        self._tools: dict[str, tuple[dict, Handler]] = {}
        self.register(product_tools.BUSCAR_PRODUTOS_SCHEMA,
                      lambda session, **kw: product_tools.buscar_produtos(products, **kw))
        self.register(product_tools.DETALHES_PRODUTO_SCHEMA,
                      lambda session, **kw: product_tools.detalhes_produto(products, **kw))
        self.register(order_tools.CONSULTAR_PEDIDO_SCHEMA,
                      lambda session, **kw: order_tools.consultar_pedido(orders, session, **kw))
        self.register(order_tools.ELEGIBILIDADE_DEVOLUCAO_SCHEMA,
                      lambda session, **kw: order_tools.verificar_elegibilidade_devolucao(
                          orders, session, today_fn(), **kw))
        # consultar_politicas é registrada na Fase 3 (register(CONSULTAR_POLITICAS_SCHEMA, ...)).

    def register(self, schema: dict, handler: Handler) -> None:
        self._tools[schema["name"]] = (schema, handler)

    def get_schemas(self) -> list[dict]:
        return [schema for schema, _ in self._tools.values()]

    def execute(self, name: str, args: Any, *, session: SessionState) -> dict:
        if name not in self._tools:
            return {"ok": False, "erro": f"Ferramenta desconhecida: {name}."}
        schema, handler = self._tools[name]
        try:
            clean = validate_args(schema, args)
            result = handler(session, **clean)
        except ToolError as exc:
            return {"ok": False, "erro": str(exc)}
        except Exception:  # noqa: BLE001 - falha da tool não pode derrubar o agente
            log.exception("Falha ao executar a tool %s", name)
            return {"ok": False, "erro": "Falha interna ao executar a ferramenta."}
        result.setdefault("ok", True)
        return result
