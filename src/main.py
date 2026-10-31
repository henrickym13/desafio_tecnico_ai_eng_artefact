"""CLI: python -m src.main [--today YYYY-MM-DD] [--session ID]"""
from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Atendimento Empório da Música")
    parser.add_argument("--today", help="Data de referência (YYYY-MM-DD) para regras de prazo")
    parser.add_argument("--session", default="cli", help="ID da sessão (histórico)")
    args = parser.parse_args()
    if args.today:
        os.environ["TODAY_OVERRIDE"] = args.today
    # TODO: montar dataset, repositórios, registry, memória, llm e orchestrator; loop de input().
    raise NotImplementedError("Estrutura criada; implementação nas próximas fases.")


if __name__ == "__main__":
    main()
