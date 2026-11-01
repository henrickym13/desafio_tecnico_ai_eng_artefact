"""Smoke test do Gemini: valida chave, modelo e function calling (3 chamadas).

Uso: python -m scripts.smoke_gemini     (lê LLM_API_KEY/LLM_MODEL do .env)
Não imprime a chave. Código de saída 0 = tudo certo.
"""
from __future__ import annotations

import sys

from src.config import settings
from src.llm.base import LLMError
from src.llm.gemini import GeminiClient

TOOL = {
    "name": "buscar_produtos",
    "description": "Busca produtos do catálogo por categoria e preço máximo.",
    "parameters": {"type": "object", "properties": {
        "categoria": {"type": "string"}, "preco_max": {"type": "number"}}},
}


def main() -> int:
    print(f"Modelo: {settings.llm_model} | raciocínio: {settings.llm_thinking_level} | "
          f"chave configurada: {'sim' if settings.llm_api_key else 'NÃO'}")
    try:
        llm = GeminiClient(api_key=settings.llm_api_key, model=settings.llm_model,
                           thinking_level=settings.llm_thinking_level)
        r1 = llm.generate(system="Responda em uma palavra.", tools=[],
                          messages=[{"role": "user", "text": "Diga apenas: ok"}])
        print(f"[1] texto simples: {r1.text!r}")

        msgs = [{"role": "user", "text": "Quais violões vocês têm até R$ 1.000?"}]
        r2 = llm.generate(system="Use a ferramenta para consultar o catálogo.", tools=[TOOL], messages=msgs)
        print(f"[2] function calling: {[(c.name, c.args) for c in r2.tool_calls]}")
        if not r2.tool_calls:
            print("    ! o modelo não chamou a ferramenta"); return 1

        msgs += [{"role": "assistant", "text": r2.text, "tool_calls": r2.tool_calls, "raw": r2.raw},
                 {"role": "tool", "results": [{"name": r2.tool_calls[0].name,
                                                "response": {"total": 1, "produtos": [
                                                    {"nome": "Violão de teste", "preco_final_fmt": "R$ 899,00"}]}}]}]
        r3 = llm.generate(system="Use a ferramenta para consultar o catálogo.", tools=[TOOL], messages=msgs)
        print(f"[3] resposta após o resultado da tool: {r3.text!r}")
        return 0 if r3.text else 1
    except LLMError as exc:
        print(f"ERRO: {exc}"); return 1


if __name__ == "__main__":
    sys.exit(main())
