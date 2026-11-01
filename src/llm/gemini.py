"""Cliente Gemini (API `generateContent` via SDK google-genai) com function calling.

Decisões:
- generateContent em vez da Interactions API: o histórico é nosso (SQLite) e o formato de
  function calling é estável e bem documentado. Trocar de interface = nova classe `LLMClient`.
- A configuração é passada como dict (o SDK aceita), sem importar tipos do SDK: o módulo é
  testável sem rede e sem o pacote instalado. O SDK só é importado ao criar o cliente real.
- Gemini 3.x não usa temperature/top_p/top_k: não são enviados. O nível de raciocínio padrão
  ("medium") é mais lento; usamos "low" por padrão (LLM_THINKING_LEVEL).
- A mensagem do modelo (`raw`) é reenviada intacta no loop de tools: isso preserva as thought
  signatures exigidas pelo Gemini 3 entre a chamada da função e a resposta.
- Retry com backoff em 429/5xx (o plano gratuito limita requisições).
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from src.llm.base import LLMError, LLMResponse, ToolCall

log = logging.getLogger(__name__)

RETRYABLE_CODES = {429, 500, 503, 504}


def to_contents(messages: list[dict]) -> list[Any]:
    contents: list[Any] = []
    for m in messages:
        role = m["role"]
        if role == "user":
            contents.append({"role": "user", "parts": [{"text": m["text"]}]})
        elif role == "assistant":
            if m.get("raw") is not None:
                contents.append(m["raw"])  # inclui thought signatures
            else:
                parts: list[dict] = []
                if m.get("text"):
                    parts.append({"text": m["text"]})
                for call in m.get("tool_calls", []):
                    parts.append({"function_call": {"name": call.name, "args": call.args}})
                contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            contents.append({
                "role": "user",
                "parts": [{"function_response": {"name": r["name"], "response": r["response"]}}
                          for r in m["results"]],
            })
        else:
            raise ValueError(f"Papel de mensagem desconhecido: {role}")
    return contents


def to_config(system: str, tools: list[dict], thinking_level: str | None) -> dict:
    config: dict[str, Any] = {
        "system_instruction": system,
        "automatic_function_calling": {"disable": True},  # nós executamos as tools
    }
    if tools:
        config["tools"] = [{
            "function_declarations": [
                {"name": t["name"], "description": t["description"],
                 "parameters_json_schema": t["parameters"]}
                for t in tools
            ]
        }]
    if thinking_level:
        config["thinking_config"] = {"thinking_level": thinking_level}
    return config


def parse_response(resp: Any) -> LLMResponse:
    candidates = getattr(resp, "candidates", None) or []
    content = getattr(candidates[0], "content", None) if candidates else None
    if content is None or not getattr(content, "parts", None):
        return LLMResponse()
    texts: list[str] = []
    calls: list[ToolCall] = []
    for part in content.parts:
        if getattr(part, "thought", False):
            continue
        if getattr(part, "function_call", None):
            fc = part.function_call
            calls.append(ToolCall(name=fc.name, args=dict(fc.args or {})))
        elif getattr(part, "text", None):
            texts.append(part.text)
    return LLMResponse(text="".join(texts), tool_calls=calls, raw=content)


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str = "gemini-3.8-flash",
                 thinking_level: str | None = "low", *, client: Any = None,
                 max_retries: int = 2, sleep: Callable[[float], None] = time.sleep) -> None:
        if client is None:
            if not api_key:
                raise LLMError("LLM_API_KEY não configurada.")
            from google import genai  # import tardio: só o cliente real precisa do SDK
            client = genai.Client(api_key=api_key)
        self._client = client
        self.model = model
        self.thinking_level = thinking_level
        self.max_retries = max_retries
        self._sleep = sleep

    def generate(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        kwargs = {"model": self.model, "contents": to_contents(messages),
                  "config": to_config(system, tools, self.thinking_level)}
        for attempt in range(self.max_retries + 1):
            try:
                return parse_response(self._client.models.generate_content(**kwargs))
            except Exception as exc:  # noqa: BLE001 - SDK levanta tipos variados
                code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                if code in RETRYABLE_CODES and attempt < self.max_retries:
                    delay = 2 ** (attempt + 1)
                    log.warning("Gemini retornou %s; nova tentativa em %ss", code, delay)
                    self._sleep(delay)
                    continue
                # a mensagem não inclui a exceção original: pode ecoar a URL/chave
                raise LLMError(f"Falha na chamada ao Gemini (código {code or 'desconhecido'}, "
                               f"{type(exc).__name__}).") from None
        raise LLMError("Falha na chamada ao Gemini.")  # inalcançável; satisfaz o type checker
