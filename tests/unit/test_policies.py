from datetime import datetime

import pytest

from src.config import settings
from src.policies.sectioner import TOPICS, get_policy, parse_pages
from src.services.store_hours import HOURS, TZ, store_status
from src.tools import policies as policy_tools


def _section(sections, number):
    return next(s for s in sections if s.number == number)


def _flat(section) -> str:
    """Texto da seção com quebras de linha do PDF colapsadas."""
    return " ".join(section.text.split())


def test_ten_sections_in_order_with_titles(policy_sections):
    assert [s.number for s in policy_sections] == [str(i) for i in range(1, 11)]
    assert _section(policy_sections, "4").title == "Política de Trocas e Devoluções"
    assert _section(policy_sections, "10").title == "Disposições Finais"


def test_pages_are_tracked_including_sections_that_span_pages(policy_sections):
    pages = {s.number: (s.page, s.end_page) for s in policy_sections}
    assert pages["3"] == (3, 3) and pages["4"] == (4, 4)
    assert pages["5"] == (4, 5)           # título na pág. 4, conteúdo na 5
    assert pages["7"] == (6, 7) and pages["9"] == (7, 8)
    assert _section(policy_sections, "5").pages_label == "4–5"


def test_numbered_steps_of_section_7_are_not_mistaken_for_headings(policy_sections):
    s7 = _section(policy_sections, "7").text
    assert "Saudação" in s7 and "Fechamento" in s7 and "Reclamação" in s7


def test_page_headers_and_footers_are_removed(policy_sections):
    for s in policy_sections:
        assert "Manual de Políticas e Procedimentos" not in s.text
        assert "Página " not in s.text


def test_key_rules_are_present_verbatim(policy_sections):
    assert "Rua 14 de Maio, 3200" in _section(policy_sections, "1").text
    assert "7 (sete) dias corridos" in _flat(_section(policy_sections, "4"))
    assert "30 (trinta) dias" in _flat(_section(policy_sections, "4"))
    assert "R$ 80,00" in _flat(_section(policy_sections, "3"))
    assert "R$ 500,00" in _flat(_section(policy_sections, "5"))
    assert "BR4K7M2X9P1BR" in _flat(_section(policy_sections, "5"))
    assert "90 (noventa) dias" in _flat(_section(policy_sections, "8"))


def test_topics_cover_every_section_exactly_once():
    numbers = [n for nums in TOPICS.values() for n in nums]
    assert sorted(numbers, key=int) == [str(i) for i in range(1, 11)]


def test_unexpected_pdf_structure_fails_loudly():
    with pytest.raises(ValueError):
        parse_pages(["1. Sobre\ntexto\n2. Horário\ntexto\n4. Pulou a 3"])


def test_get_policy_returns_topic_sections(policy_sections):
    assert [s.number for s in get_policy("trocas_devolucoes", policy_sections)] == ["4"]
    with pytest.raises(ValueError):
        get_policy("inexistente", policy_sections)


def test_consultar_politicas_returns_text_pages_and_internal_notes(policy_sections):
    r = policy_tools.consultar_politicas(policy_sections, topico="trocas_devolucoes")
    sec = r["secoes"][0]
    assert sec["secao"] == "4" and sec["paginas"] == "4" and "arrependimento" in sec["texto"].lower()
    assert any("garantia legal" in n for n in r["notas_internas"])
    assert any("cancelar" in n for n in r["notas_internas"])  # lacuna do manual sinalizada


def test_internal_notes_resolve_documented_contradictions(policy_sections):
    pagamento = policy_tools.consultar_politicas(policy_sections, topico="pagamento")
    assert any("§3.1" in n for n in pagamento["notas_internas"])
    assert any("3341-4444" in n for n in policy_tools.consultar_politicas(policy_sections, topico="atendimento")["notas_internas"])


# ---------- horário de funcionamento ----------
def test_store_hours_match_the_manual(policy_sections):
    text = _section(policy_sections, "2").text
    assert "Segunda a Sexta-feira 09:00 às 18:00" in text and (HOURS[0][0].hour, HOURS[4][1].hour) == (9, 18)
    assert "Sábado 09:00 às 13:00" in text and HOURS[5][1].hour == 13
    assert "Domingo e Feriados Fechado" in text and 6 not in HOURS


def _at(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


def test_open_during_weekday_hours():
    r = store_status(_at(2026, 11, 2, 10, 0))  # segunda
    assert r["aberta_agora"] and r["horario_hoje"] == "09:00 às 18:00" and r["proxima_abertura"] is None


def test_before_opening_next_opening_is_today():
    r = store_status(_at(2026, 11, 2, 8, 59))
    assert not r["aberta_agora"] and r["proxima_abertura"] == {"dia_semana": "segunda-feira", "data": "2026-11-02", "hora": "09:00"}


def test_closing_time_is_exclusive_and_next_opening_is_tomorrow():
    r = store_status(_at(2026, 11, 6, 18, 0))  # sexta, 18:00
    assert not r["aberta_agora"] and r["proxima_abertura"]["dia_semana"] == "sábado"


def test_saturday_closes_at_1pm_and_sunday_is_closed():
    assert store_status(_at(2026, 11, 7, 12, 59))["aberta_agora"]
    sat = store_status(_at(2026, 11, 7, 13, 0))
    assert not sat["aberta_agora"] and sat["proxima_abertura"] == {"dia_semana": "segunda-feira", "data": "2026-11-09", "hora": "09:00"}
    sun = store_status(_at(2026, 11, 1, 11, 0))
    assert not sun["aberta_agora"] and sun["horario_hoje"] == "Fechado" and sun["proxima_abertura"]["data"] == "2026-11-02"


def test_naive_datetime_is_treated_as_local_time():
    assert store_status(datetime(2026, 11, 2, 10, 0))["aberta_agora"]


def test_settings_now_honours_today_override():
    import os
    os.environ["TODAY_OVERRIDE"] = "2026-02-20"
    try:
        assert settings.now.date().isoformat() == "2026-02-20" and settings.now.tzinfo is not None
    finally:
        del os.environ["TODAY_OVERRIDE"]


# ---------- via registry (como o LLM chama) ----------
def test_registry_exposes_policy_tools_and_rejects_bad_topic(registry, session):
    ok = registry.execute("consultar_politicas", {"topico": "horario"}, session=session)
    assert ok["ok"] and "09:00" in ok["secoes"][0]["texto"]
    assert not registry.execute("consultar_politicas", {"topico": "fofoca"}, session=session)["ok"]
    assert not registry.execute("consultar_politicas", {}, session=session)["ok"]


def test_registry_store_open_now(registry, session):
    r = registry.execute("loja_aberta_agora", {}, session=session)  # sexta 10:00 (fixture)
    assert r["ok"] and r["aberta_agora"] and r["dia_semana"] == "sexta-feira"


def test_return_scenario_chains_order_data_and_policy(registry, session):
    """Caso não trivial do desafio: pedido real + regra do manual no mesmo atendimento."""
    registry.execute("consultar_pedido", {"numero_pedido": 7, "telefone_ou_email": "leticia.rocha@jmail.com"}, session=session)
    elig = registry.execute("verificar_elegibilidade_devolucao", {"numero_pedido": 7}, session=session)
    policy = registry.execute("consultar_politicas", {"topico": "trocas_devolucoes"}, session=session)
    assert elig["janelas"]["arrependimento"]["dentro_do_prazo"]
    assert "embalagem original" in policy["secoes"][0]["texto"]
    assert "frete de devolução é por conta da loja" in " ".join(policy["secoes"][0]["texto"].split())
