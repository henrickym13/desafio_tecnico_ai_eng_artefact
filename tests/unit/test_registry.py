import pytest

from src.agent.tool_registry import validate_args
from src.tools.errors import ToolError
from src.tools.policies import CONSULTAR_POLITICAS_SCHEMA


def test_only_registered_tools_are_exposed(registry):
    names = {s["name"] for s in registry.get_schemas()}
    assert names == {"buscar_produtos", "detalhes_produto", "consultar_pedido", "verificar_elegibilidade_devolucao"}


def test_llm_never_sees_customer_id_in_schemas(registry):
    for schema in registry.get_schemas():
        assert "customer_id" not in schema["parameters"]["properties"]


def test_unknown_tool_is_rejected(registry, session):
    r = registry.execute("apagar_tudo", {}, session=session)
    assert not r["ok"] and "desconhecida" in r["erro"]


def test_args_are_coerced_validated_and_nulls_dropped(registry, session):
    r = registry.execute("buscar_produtos", {"categoria": "violão", "preco_max": "1000", "consulta": None}, session=session)
    assert r["ok"] and r["total"] > 0
    assert registry.execute("buscar_produtos", {"preco_maximo": 10}, session=session)["ok"] is False
    assert registry.execute("detalhes_produto", {}, session=session)["ok"] is False
    assert registry.execute("consultar_pedido", {"numero_pedido": "abc"}, session=session)["ok"] is False
    assert registry.execute("buscar_produtos", {"preco_min": 900, "preco_max": 100}, session=session)["ok"] is False


def test_enum_is_enforced():
    with pytest.raises(ToolError):
        validate_args(CONSULTAR_POLITICAS_SCHEMA, {"topico": "segredo_do_dono"})
    assert validate_args(CONSULTAR_POLITICAS_SCHEMA, {"topico": "horario"}) == {"topico": "horario"}


def test_tool_exception_becomes_structured_error(registry, session):
    def boom(session, **kw):
        raise RuntimeError("detalhe interno sensível")

    registry.register({"name": "quebrada", "description": "x", "parameters": {"type": "object", "properties": {}}}, boom)
    r = registry.execute("quebrada", {}, session=session)
    assert r["ok"] is False and "sensível" not in r["erro"]


def test_full_return_flow_through_registry(registry, session):
    # 'hoje' do fixture = 2026-02-20; pedido 7 entregue com previsão em 2026-02-17
    login = registry.execute("consultar_pedido", {"numero_pedido": 7, "telefone_ou_email": "(67) 99789-0123"}, session=session)
    assert login["ok"]
    r = registry.execute("verificar_elegibilidade_devolucao", {"numero_pedido": 7}, session=session)
    assert r["ok"] and r["janelas"]["arrependimento"]["dentro_do_prazo"] and r["hoje"] == "2026-02-20"
