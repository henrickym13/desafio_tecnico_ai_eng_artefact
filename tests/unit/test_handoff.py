def test_handoff_tool_records_and_returns_protocol(registry, session, memory):
    r = registry.execute("encaminhar_atendente", {"motivo": "Cliente quer cancelar o pedido 13 antes do envio"}, session=session)
    assert r["ok"] and r["protocolo"] >= 1 and r["prazo_retorno"] == "24 horas úteis"
    assert memory.create_handoff("x", "y") == r["protocolo"] + 1


def test_handoff_requires_reason(registry, session):
    assert registry.execute("encaminhar_atendente", {}, session=session)["ok"] is False


def test_long_reason_is_truncated(registry, session):
    assert registry.execute("encaminhar_atendente", {"motivo": "x" * 5000}, session=session)["ok"]
