"""Configuração central, lida de variáveis de ambiente (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    max_tool_iterations: int = int(os.getenv("MAX_TOOL_ITERATIONS", "5"))
    history_db_path: Path = ROOT / os.getenv("HISTORY_DB_PATH", "data/history.sqlite3")
    raw_data_dir: Path = ROOT / "data" / "raw"
    policy_pdf: Path = ROOT / "data" / "policies" / "politicas_da_loja.pdf"

    @property
    def today(self) -> date:
        """'Hoje' para regras de prazo. TODAY_OVERRIDE permite reproduzir cenários."""
        override = os.getenv("TODAY_OVERRIDE", "").strip()
        return date.fromisoformat(override) if override else date.today()


settings = Settings()
