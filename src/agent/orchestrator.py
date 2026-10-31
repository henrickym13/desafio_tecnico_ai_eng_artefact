"""Loop do agente único (function calling). Agnóstico de provedor via `llm`.

Ciclo: histórico -> LLM(+tools) -> [tool_calls -> executa -> devolve ao LLM]* (limite) -> resposta.
O loop permite encadear pedido + política no mesmo turno (caso da devolução).
"""
from __future__ import annotations

from src.agent.tool_registry import ToolRegistry
from src.services.memory import Memory


class AgentOrchestrator:
    def __init__(self, llm, tools: ToolRegistry, memory: Memory, max_iterations: int = 5) -> None:
        self.llm = llm
        self.tools = tools
        self.memory = memory
        self.max_iterations = max_iterations

    def process_message(self, message: str, session_id: str) -> str:
        """TODO: implementar ciclo (adaptar ao formato de mensagens do provedor escolhido)."""
        raise NotImplementedError
