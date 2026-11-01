"""Tools de políticas: consultar_politicas (manual por seção, com página) e loja_aberta_agora."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from src.policies.notes import INTERNAL_NOTES
from src.policies.sectioner import TOPICS, PolicySection, get_policy
from src.services.store_hours import store_status

CONSULTAR_POLITICAS_SCHEMA = {
    "name": "consultar_politicas",
    "description": (
        "Consulta o manual de políticas da loja. Tópicos: sobre_a_loja (endereço, telefone, e-mail, "
        "o que a loja vende), horario, pagamento (formas e parcelamento), trocas_devolucoes, "
        "frete_entrega (prazos, rastreamento), promocoes, atendimento (tom, escopo, situações "
        "especiais), garantia, privacidade, disposicoes_finais. Responda SOMENTE com base no texto "
        "retornado; se a regra não estiver lá, diga que vai confirmar com a equipe. Para dúvidas que "
        "cruzam temas (ex.: devolução + garantia), consulte mais de um tópico."
    ),
    "parameters": {
        "type": "object",
        "properties": {"topico": {"type": "string", "enum": sorted(TOPICS)}},
        "required": ["topico"],
    },
}

LOJA_ABERTA_AGORA_SCHEMA = {
    "name": "loja_aberta_agora",
    "description": "Informa se a loja está aberta neste momento (fuso de Campo Grande/MS), o horário de "
                   "hoje e a próxima abertura. Use para 'estão abertos?' ou 'até que horas hoje?'.",
    "parameters": {"type": "object", "properties": {}},
}


def consultar_politicas(sections: list[PolicySection], *, topico: str) -> dict:
    found = get_policy(topico, sections)
    numbers = {s.number for s in found}
    notes = [n for number in sorted(numbers, key=int) for n in INTERNAL_NOTES.get(number, [])]
    return {
        "topico": topico,
        "secoes": [
            {"secao": s.number, "titulo": s.title, "paginas": s.pages_label, "texto": s.text}
            for s in found
        ],
        "notas_internas": notes,
        "instrucao": "Responda com base em 'secoes'. 'notas_internas' orientam você sobre contradições e "
                     "lacunas do manual: aplique-as, mas não as cite como se fossem texto do manual.",
    }


def loja_aberta_agora(now_fn: Callable[[], datetime]) -> dict:
    return store_status(now_fn())
