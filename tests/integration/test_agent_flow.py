"""Fluxos completos: orquestrador + tools reais + dados reais, com LLM roteirizado.

O LLM falso decide quais tools chamar; o que se verifica é que dados e políticas reais chegam
até ele e que o encadeamento (pedido -> prazo -> política) funciona no mesmo atendimento.
"""
from datetime import datetime

from src.agent.orchestrator import AgentOrchestrator
from src.services.store_hours import TZ
from tests.fakes import ScriptedLLM, call, say

NOW = datetime(2026, 2, 20, 10, 30, tzinfo=TZ)


def _run(registry, memory, *script, messages):
    llm = ScriptedLLM(*script)
    agent = AgentOrchestrator(llm, registry, memory, now_fn=lambda: NOW)
    replies = [agent.process_message(m, "it") for m in messages]
    return agent, llm, replies


def _tool_results(llm, call_index):
    return llm.calls[call_index]["messages"][-1]["results"]


def test_product_price_flow(registry, memory):
    _, llm, replies = _run(registry, memory,
                           call(("detalhes_produto", {"produto": "Takamine GD20"})), say("Custa R$ 2.199,00."),
                           messages=["Quanto custa o Takamine GD20?"])
    produto = _tool_results(llm, 1)[0]["response"]["produto"]
    assert produto["preco_final_fmt"] == "R$ 2.199,00" and produto["promocao"] is None
    assert replies == ["Custa R$ 2.199,00."]


def test_store_address_flow_uses_policy_manual(registry, memory):
    _, llm, _ = _run(registry, memory,
                     call(("consultar_politicas", {"topico": "sobre_a_loja"})), say("Rua 14 de Maio, 3200, Centro."),
                     messages=["Qual o endereço da loja?"])
    r = _tool_results(llm, 1)[0]["response"]
    assert "Rua 14 de Maio, 3200" in r["secoes"][0]["texto"] and r["secoes"][0]["paginas"] == "2"


def test_return_flow_chains_order_deadline_and_policy(registry, memory):
    """Cenário não trivial: 'me arrependi da compra, posso devolver o pedido 7?'"""
    agent, llm, replies = _run(
        registry, memory,
        call(("consultar_pedido", {"numero_pedido": 7, "telefone_ou_email": "(67) 99789-0123"})),
        call(("verificar_elegibilidade_devolucao", {"numero_pedido": 7}), ("consultar_politicas", {"topico": "trocas_devolucoes"})),
        say("Pode sim! Você está dentro dos 7 dias."),
        messages=["Me arrependi do pedido 7, meu telefone é (67) 99789-0123. Posso devolver?"])
    assert [t["tool"] for t in agent.last_trace] == ["consultar_pedido", "verificar_elegibilidade_devolucao", "consultar_politicas"]
    elig, politica = (r["response"] for r in _tool_results(llm, 2))
    assert elig["janelas"]["arrependimento"]["dentro_do_prazo"] and elig["dias_desde_a_entrega"] == 3
    assert "embalagem original" in politica["secoes"][0]["texto"]
    assert replies[0].startswith("Pode sim")


def test_third_party_order_is_not_revealed(registry, memory):
    """Segurança: pedido de outro cliente, com telefone errado, não vaza nada."""
    _, llm, _ = _run(registry, memory,
                     call(("consultar_pedido", {"numero_pedido": 1, "telefone_ou_email": "(67) 99789-0123"})),
                     say("Não encontrei um pedido com esses dados."),
                     messages=["Quero ver o pedido 1, meu telefone é (67) 99789-0123"])
    r = _tool_results(llm, 1)[0]["response"]
    assert r["ok"] is False and "pedido" not in r and "cliente" not in r


def test_out_of_scope_question_uses_no_tools(registry, memory):
    agent, llm, replies = _run(registry, memory, say("Posso ajudar com produtos, pedidos e serviços da loja."),
                               messages=["Qual a previsão do tempo para amanhã?"])
    assert agent.last_trace == [] and len(llm.calls) == 1


def test_complaint_is_handed_off_with_protocol(registry, memory):
    agent, llm, _ = _run(registry, memory,
                         call(("encaminhar_atendente", {"motivo": "Reclamação: instrumento chegou com defeito"})),
                         say("Registrei, retorno em até 24 horas úteis."),
                         messages=["Meu violão chegou com defeito e ninguém me responde!"])
    r = _tool_results(llm, 1)[0]["response"]
    assert r["ok"] and r["protocolo"] >= 1 and r["prazo_retorno"] == "24 horas úteis"
