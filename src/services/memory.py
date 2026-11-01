"""Histórico da conversa (SQLite) + estado da sessão + registro de encaminhamentos.

- O `verified_customer_id` vive aqui, em Python — NUNCA é argumento de tool do LLM.
- Só texto de usuário/assistente é guardado (resultados de tools não), numa janela limitada:
  memória mínima, em linha com a LGPD (§9 do manual).
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HISTORY_WINDOW = 20      # mensagens enviadas ao LLM
RETENTION_LIMIT = 50     # mensagens mantidas por sessão


@dataclass
class SessionState:
    session_id: str
    verified_customer_id: int | None = None
    failed_verifications: int = 0
    messages: list[dict] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Memory:
    def __init__(self, db_path: Path, history_window: int = HISTORY_WINDOW) -> None:
        self.db_path = Path(db_path)
        self.history_window = history_window
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    verified_customer_id INTEGER,
                    failed_verifications INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL, role TEXT NOT NULL,
                    text TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
                CREATE TABLE IF NOT EXISTS handoffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL);
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    def get_session(self, session_id: str) -> SessionState:
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            msgs = db.execute(
                "SELECT role, text FROM (SELECT id, role, text FROM messages WHERE session_id = ? "
                "ORDER BY id DESC LIMIT ?) ORDER BY id ASC", (session_id, self.history_window)).fetchall()
        return SessionState(
            session_id=session_id,
            verified_customer_id=row["verified_customer_id"] if row else None,
            failed_verifications=row["failed_verifications"] if row else 0,
            messages=[{"role": m["role"], "text": m["text"]} for m in msgs],
        )

    def save(self, state: SessionState) -> None:
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO sessions (session_id, verified_customer_id, failed_verifications, updated_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
                "verified_customer_id = excluded.verified_customer_id, "
                "failed_verifications = excluded.failed_verifications, updated_at = excluded.updated_at",
                (state.session_id, state.verified_customer_id, state.failed_verifications, _now()))

    def append_message(self, session_id: str, role: str, text: str) -> None:
        with closing(self._connect()) as db, db:
            db.execute("INSERT INTO messages (session_id, role, text, created_at) VALUES (?, ?, ?, ?)",
                       (session_id, role, text, _now()))
            db.execute(
                "DELETE FROM messages WHERE session_id = ? AND id NOT IN "
                "(SELECT id FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?)",
                (session_id, session_id, RETENTION_LIMIT))

    def create_handoff(self, session_id: str, reason: str) -> int:
        with closing(self._connect()) as db, db:
            cur = db.execute("INSERT INTO handoffs (session_id, reason, created_at) VALUES (?, ?, ?)",
                             (session_id, reason, _now()))
            return int(cur.lastrowid)

    def clear(self, session_id: str) -> None:
        """Apaga histórico e estado da sessão (direito de exclusão, LGPD §9)."""
        with closing(self._connect()) as db, db:
            db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
