"""Tool encaminhar_atendente: registra o encaminhamento para uma pessoa da equipe (SQLite)."""
from __future__ import annotations

from src.services.memory import Memory, SessionState

ENCAMINHAR_ATENDENTE_SCHEMA = {
    "name": "encaminhar_atendente",
    "description": (
        "Registra o encaminhamento da conversa para um atendente humano. Use para: reclamações, regra "
        "que o manual não cobre ou é contraditória, cancelamento de pedido ainda não enviado, "
        "cliente que pede para falar com uma pessoa. Só diga ao cliente que foi encaminhado depois de "
        "chamar esta ferramenta."
    ),
    "parameters": {
        "type": "object",
        "properties": {"motivo": {"type": "string", "description": "Resumo curto do que o cliente precisa"}},
        "required": ["motivo"],
    },
}


def encaminhar_atendente(memory: Memory, session: SessionState, *, motivo: str) -> dict:
    protocolo = memory.create_handoff(session.session_id, motivo[:500])
    return {
        "protocolo": protocolo,
        "prazo_retorno": "24 horas úteis",
        "observacao": "Prazo de retorno de 24 horas úteis é o do manual (§7.3) para reclamações.",
    }
