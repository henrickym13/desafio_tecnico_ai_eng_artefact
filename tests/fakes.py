"""LLM falso e respostas do SDK falsas, para testar sem rede."""
from __future__ import annotations

from types import SimpleNamespace

from src.llm.base import LLMError, LLMResponse, ToolCall


def say(text: str) -> LLMResponse:
    return LLMResponse(text=text)


def call(*calls: tuple[str, dict], text: str = "") -> LLMResponse:
    return LLMResponse(text=text, tool_calls=[ToolCall(n, a) for n, a in calls], raw={"raw_of": [n for n, _ in calls]})


class ScriptedLLM:
    """Devolve respostas pré-definidas (ou levanta a exceção) e registra o que recebeu."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls: list[dict] = []

    def generate(self, *, system, messages, tools):
        self.calls.append({"system": system, "messages": [dict(m) for m in messages], "tools": tools})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


# ---- respostas no formato do SDK google-genai (duck-typed) ----
def sdk_part(text=None, function_call=None, thought=False):
    return SimpleNamespace(text=text, function_call=function_call, thought=thought)


def sdk_fc(name, args):
    return SimpleNamespace(name=name, args=args)


def sdk_response(*parts):
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(role="model", parts=list(parts)))])


class SDKError(Exception):
    def __init__(self, code, message="erro"):
        super().__init__(message)
        self.code = code


class FakeGenAIClient:
    """Imita client.models.generate_content; cada item do script é resposta ou exceção."""

    def __init__(self, *script):
        self.script, self.kwargs = list(script), []
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs):
        self.kwargs.append(kwargs)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
