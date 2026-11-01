"""Tipos neutros de provedor e a interface do cliente LLM.

O orquestrador só conhece estes tipos. Cada provedor (Gemini, outro) implementa `LLMClient`
convertendo de/para o formato nativo.

Mensagens (lista de dicts):
- {"role": "user", "text": str}
- {"role": "assistant", "text": str, "tool_calls": [ToolCall], "raw": <mensagem nativa>}
- {"role": "tool", "results": [{"name": str, "response": dict}]}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class LLMError(Exception):
    """Falha ao falar com o LLM (rede, cota, resposta inválida). Mensagem segura para log."""


@dataclass
class ToolCall:
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None  # mensagem nativa do provedor, reenviada tal como veio no loop de tools


class LLMClient(Protocol):
    def generate(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...
