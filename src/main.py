"""CLI: python -m src.main [--today YYYY-MM-DD] [--session ID] [--verbose]"""
from __future__ import annotations

import argparse
import logging
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Atendimento Empório da Música")
    parser.add_argument("--today", help="Data de referência (YYYY-MM-DD) para regras de prazo")
    parser.add_argument("--session", default="cli", help="ID da sessão (histórico)")
    parser.add_argument("--verbose", action="store_true", help="Mostra as ferramentas consultadas")
    args = parser.parse_args()
    if args.today:
        os.environ["TODAY_OVERRIDE"] = args.today  # antes de importar a config

    from src.app import build_orchestrator
    from src.config import settings
    from src.llm.base import LLMError
    from src.llm.gemini import GeminiClient

    logging.basicConfig(level=logging.WARNING)
    try:
        llm = GeminiClient(api_key=settings.llm_api_key, model=settings.llm_model,
                           thinking_level=settings.llm_thinking_level)
    except LLMError as exc:
        sys.exit(f"{exc} Copie .env.example para .env e preencha LLM_API_KEY.")
    agent = build_orchestrator(settings, llm)

    print(f"Empório da Música — atendimento (sessão '{args.session}', hoje = {settings.today:%d/%m/%Y}).")
    print("Digite sua mensagem. Comandos: /novo (apaga o histórico da sessão), /sair\n")
    while True:
        try:
            text = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text == "/sair":
            break
        if text == "/novo":
            agent.memory.clear(args.session)
            print("(histórico da sessão apagado)\n")
            continue
        reply = agent.process_message(text, args.session)
        if args.verbose:
            for call in agent.last_trace:
                print(f"  [tool] {call['tool']}({call['args']}) ok={call['ok']}")
        print(f"\nAtendente: {reply}\n")


if __name__ == "__main__":
    main()
