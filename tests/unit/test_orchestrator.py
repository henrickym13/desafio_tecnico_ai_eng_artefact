from datetime import datetime

from src.agent.orchestrator import (FALLBACK_EMPTY, FALLBACK_LLM_ERROR, FALLBACK_TOOL_LIMIT,
                                    AgentOrchestrator)
from src.agent.prompt import build_system_prompt
from src.llm.base import LLMError
from src.services.store_hours import TZ
from tests.fakes import ScriptedLLM, call, say

NOW = datetime(2026, 2, 20, 10, 30, tzinfo=TZ)  # sexta-feira


def _agent(registry, memory, *script, max_iterations=5):
    llm = ScriptedLLM(*script)
    return AgentOrchestrator(llm, registry, memory, max_iterations=max_iterations, now_fn=lambda: NOW), llm


def test_direct_answer_without_tools(registry, memory):
    agent, llm = _agent(registry, memory, say("Posso ajudar com produtos, pedidos e serviços da loja."))
    assert agent.process_message("Qual a previsão do tempo?", "s1").startswith("Posso ajudar")
    assert agent.last_trace == [] and len(llm.calls) == 1


def test_tool_loop_executes_tool_and_returns_result_to_llm(registry, memory):
    agent, llm = _agent(registry, memory,
                        call(("buscar_produtos", {"categoria": "violão", "preco_max": 1000})),
                        say("Tenho estas opções de violão."))
    assert agent.process_message("violões até R$1000", "s1") == "Tenho estas opções de violão."
    assert [t["tool"] for t in agent.last_trace] == ["buscar_produtos"] and agent.last_trace[0]["ok"]
    second = llm.calls[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "tool"]
    tool_msg = second[2]["results"][0]
    assert tool_msg["name"] == "buscar_produtos" and tool_msg["response"]["total"] > 0
    assert second[1]["raw"] == {"raw_of": ["buscar_produtos"]}  # mensagem nativa reenviada intacta


def test_parallel_tool_calls_are_all_executed_in_order(registry, memory):
    agent, llm = _agent(registry, memory,
                        call(("loja_aberta_agora", {}), ("consultar_politicas", {"topico": "horario"})),
                        say("Abrimos de segunda a sexta, das 9h às 18h."))
    agent.process_message("horário?", "s1")
    results = llm.calls[1]["messages"][-1]["results"]
    assert [r["name"] for r in results] == ["loja_aberta_agora", "consultar_politicas"]


def test_unknown_tool_and_bad_args_do_not_break_the_loop(registry, memory):
    agent, llm = _agent(registry, memory, call(("apagar_tudo", {}), ("detalhes_produto", {})), say("Desculpe, não consegui consultar."))
    assert agent.process_message("oi", "s1").startswith("Desculpe")
    results = llm.calls[1]["messages"][-1]["results"]
    assert all(r["response"]["ok"] is False for r in results)


def test_tool_loop_is_capped(registry, memory):
    agent, llm = _agent(registry, memory, *[call(("loja_aberta_agora", {}))] * 4, max_iterations=3)
    assert agent.process_message("oi", "s1") == FALLBACK_TOOL_LIMIT
    assert len(llm.calls) == 4  # 3 rodadas de tools + a chamada que estourou o limite


def test_llm_error_returns_friendly_message_and_does_not_save_the_turn(registry, memory):
    agent, _ = _agent(registry, memory, LLMError("429"))
    assert agent.process_message("oi", "s1") == FALLBACK_LLM_ERROR
    assert memory.get_session("s1").messages == []


def test_empty_model_response_has_fallback(registry, memory):
    agent, _ = _agent(registry, memory, say("   "))
    assert agent.process_message("oi", "s1") == FALLBACK_EMPTY


def test_blank_input_does_not_call_the_llm(registry, memory):
    agent, llm = _agent(registry, memory)
    assert "ajudar" in agent.process_message("   ", "s1") and llm.calls == []


def test_only_text_is_persisted_and_history_is_sent_next_turn(registry, memory):
    agent, llm = _agent(registry, memory,
                        call(("buscar_produtos", {"categoria": "violão"})), say("Aqui vão os violões."),
                        say("O primeiro custa menos."))
    agent.process_message("violões?", "s1")
    stored = memory.get_session("s1").messages
    assert stored == [{"role": "user", "text": "violões?"}, {"role": "assistant", "text": "Aqui vão os violões."}]
    agent.process_message("qual o mais barato?", "s1")
    sent = llm.calls[2]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"] and sent[-1]["text"] == "qual o mais barato?"


def test_verification_persists_across_turns_and_restarts(registry, memory, products_repo, orders_repo, policy_sections):
    from datetime import date
    from src.agent.tool_registry import ToolRegistry
    a1, _ = _agent(registry, memory,
                   call(("consultar_pedido", {"numero_pedido": 7, "telefone_ou_email": "(67) 99789-0123"})), say("Achei seu pedido."))
    a1.process_message("pedido 7, meu telefone é (67) 99789-0123", "s1")
    assert memory.get_session("s1").verified_customer_id == 14

    new_registry = ToolRegistry(products=products_repo, orders=orders_repo, policy_sections=policy_sections,
                                memory=memory, today_fn=lambda: date(2026, 2, 20))
    a2, llm2 = _agent(new_registry, memory, call(("consultar_pedido", {"numero_pedido": 7})), say("Entregue."))
    a2.process_message("e o status?", "s1")
    assert llm2.calls[1]["messages"][-1]["results"][0]["response"]["ok"] is True  # sem pedir credenciais de novo


def test_failed_verification_attempts_are_saved_even_if_llm_fails_later(registry, memory):
    agent, _ = _agent(registry, memory,
                      call(("consultar_pedido", {"numero_pedido": 7, "telefone_ou_email": "(67) 98432-1098"})), LLMError("503"))
    assert agent.process_message("pedido 7", "s1") == FALLBACK_LLM_ERROR
    assert memory.get_session("s1").failed_verifications == 1


def test_tool_results_have_no_internal_ids_visible_to_the_llm(registry, memory):
    agent, llm = _agent(registry, memory,
                        call(("consultar_pedido", {"numero_pedido": 7, "telefone_ou_email": "leticia.rocha@jmail.com"})), say("ok"))
    agent.process_message("pedido 7", "s1")
    response = llm.calls[1]["messages"][-1]["results"][0]["response"]
    assert "customer_id" not in str(response) and "99789" not in str(response)


def test_system_prompt_carries_current_date_and_rules():
    prompt = build_system_prompt(NOW)
    assert "sexta-feira, 20/02/2026, 10:30" in prompt
    assert "{WEEKDAY}" not in prompt and "encaminhar_atendente" in prompt
