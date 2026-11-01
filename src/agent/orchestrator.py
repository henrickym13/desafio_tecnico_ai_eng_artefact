"""Loop do agente único (function calling). Agnóstico de provedor via `LLMClient`.

Ciclo: histórico -> LLM(+tools) -> [tool_calls -> executa -> devolve ao LLM]* (limite) -> resposta.
O loop permite encadear pedido + política no mesmo turno (caso da devolução).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Callable

from src.agent.prompt import build_system_prompt
from src.agent.tool_registry import ToolRegistry
from src.llm.base import LLMClient, LLMError
from src.policies.notes import STORE_PHONE
from src.services.memory import Memory, SessionState
from src.services.store_hours import TZ

log = logging.getLogger(__name__)

FALLBACK_LLM_ERROR = (f"Desculpe, estou com uma instabilidade aqui agora. Pode tentar de novo em instantes? "
                      f"Se preferir, fale com a equipe pelo {STORE_PHONE}.")
FALLBACK_TOOL_LIMIT = (f"Não consegui concluir essa consulta agora. Pode reformular o pedido ou falar "
                       f"com a equipe pelo {STORE_PHONE}?")
FALLBACK_EMPTY = "Não consegui formular uma resposta agora. Pode reformular a pergunta?"
EMPTY_INPUT_REPLY = "Pode me contar como posso ajudar? 🙂"


def _json_safe(data: dict) -> dict:
    return json.loads(json.dumps(data, default=str, ensure_ascii=False))


class AgentOrchestrator:
    def __init__(self, llm: LLMClient, tools: ToolRegistry, memory: Memory, max_iterations: int = 5,
                 now_fn: Callable[[], datetime] = lambda: datetime.now(TZ)) -> None:
        self.llm = llm
        self.tools = tools
        self.memory = memory
        self.max_iterations = max_iterations
        self.now_fn = now_fn
        self.last_trace: list[dict] = []  # chamadas de tool da última mensagem (para --verbose/exemplos)

    def process_message(self, message: str, session_id: str) -> str:
        message = message.strip()
        if not message:
            return EMPTY_INPUT_REPLY
        state = self.memory.get_session(session_id)
        self.last_trace = []
        try:
            final = self._run(message, state)
        except LLMError as exc:
            log.warning("Falha do LLM: %s", exc)
            return FALLBACK_LLM_ERROR  # turno não é gravado: o cliente pode tentar de novo
        finally:
            self.memory.save(state)  # verificação/tentativas valem mesmo se o turno falhar
        self.memory.append_message(session_id, "user", message)
        self.memory.append_message(session_id, "assistant", final)
        return final

    def _run(self, message: str, state: SessionState) -> str:
        system = build_system_prompt(self.now_fn())
        turn: list[dict] = [*state.messages, {"role": "user", "text": message}]
        schemas = self.tools.get_schemas()

        for round_no in range(self.max_iterations + 1):
            response = self.llm.generate(system=system, messages=turn, tools=schemas)
            if not response.tool_calls:
                return response.text.strip() or FALLBACK_EMPTY
            if round_no == self.max_iterations:
                log.warning("Limite de %s rodadas de tools atingido", self.max_iterations)
                return FALLBACK_TOOL_LIMIT

            turn.append({"role": "assistant", "text": response.text,
                         "tool_calls": response.tool_calls, "raw": response.raw})
            results = []
            for call in response.tool_calls:
                result = self.tools.execute(call.name, call.args, session=state)
                self.last_trace.append({"tool": call.name, "args": call.args, "ok": result.get("ok")})
                results.append({"name": call.name, "response": _json_safe(result)})
            turn.append({"role": "tool", "results": results})
        return FALLBACK_TOOL_LIMIT  # inalcançável
