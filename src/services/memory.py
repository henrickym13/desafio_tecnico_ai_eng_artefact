"""Histórico da conversa (SQLite) + estado da sessão.

O `verified_customer_id` vive aqui, em Python — NUNCA é argumento de tool do LLM.
Memória limitada: guardar só o necessário (LGPD, §9 do manual).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SessionState:
    session_id: str
    verified_customer_id: int | None = None
    failed_verifications: int = 0
    messages: list[dict] = field(default_factory=list)


class Memory:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def get_session(self, session_id: str) -> SessionState:
        """TODO: carregar do SQLite (ou criar)."""
        raise NotImplementedError

    def save(self, state: SessionState) -> None:
        """TODO: persistir mensagens (janela limitada) e estado de verificação."""
        raise NotImplementedError
