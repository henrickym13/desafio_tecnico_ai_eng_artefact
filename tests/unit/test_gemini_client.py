from src.llm.base import LLMError, ToolCall
from src.llm.gemini import GeminiClient, parse_response, to_config, to_contents
from tests.fakes import FakeGenAIClient, SDKError, sdk_fc, sdk_part, sdk_response

TOOLS = [{"name": "buscar_produtos", "description": "Busca.",
          "parameters": {"type": "object", "properties": {"categoria": {"type": "string"}}}}]


def _client(*script, **kw):
    fake = FakeGenAIClient(*script)
    sleeps = []
    return GeminiClient(client=fake, model="gemini-3.8-flash", sleep=sleeps.append, **kw), fake, sleeps


def test_config_declares_tools_with_json_schema_and_disables_auto_calling():
    cfg = to_config("sistema", TOOLS, "low")
    decl = cfg["tools"][0]["function_declarations"][0]
    assert decl == {"name": "buscar_produtos", "description": "Busca.", "parameters_json_schema": TOOLS[0]["parameters"]}
    assert cfg["system_instruction"] == "sistema"
    assert cfg["automatic_function_calling"] == {"disable": True}
    assert cfg["thinking_config"] == {"thinking_level": "low"}


def test_config_has_no_sampling_params_and_omits_empty_tools_and_thinking():
    cfg = to_config("s", [], None)
    assert not {"temperature", "top_p", "top_k", "tools", "thinking_config"} & set(cfg)


def test_contents_conversion_for_a_full_tool_round_trip():
    raw = object()  # mensagem nativa do modelo (com thought signatures), reenviada intacta
    msgs = [
        {"role": "user", "text": "oi"},
        {"role": "assistant", "text": "olá"},                                   # histórico em texto
        {"role": "user", "text": "violões até 1000"},
        {"role": "assistant", "text": "", "tool_calls": [ToolCall("buscar_produtos", {"categoria": "violão"})], "raw": raw},
        {"role": "tool", "results": [{"name": "buscar_produtos", "response": {"total": 2}}]},
    ]
    c = to_contents(msgs)
    assert c[0] == {"role": "user", "parts": [{"text": "oi"}]}
    assert c[1] == {"role": "model", "parts": [{"text": "olá"}]}
    assert c[3] is raw
    assert c[4] == {"role": "user", "parts": [{"function_response": {"name": "buscar_produtos", "response": {"total": 2}}}]}


def test_parse_text_and_function_calls_skipping_thoughts():
    resp = sdk_response(sdk_part(text="pensando...", thought=True), sdk_part(text="Olá, "), sdk_part(text="tudo bem?"),
                        sdk_part(function_call=sdk_fc("buscar_produtos", {"categoria": "violão"})))
    out = parse_response(resp)
    assert out.text == "Olá, tudo bem?" and out.tool_calls == [ToolCall("buscar_produtos", {"categoria": "violão"})]
    assert out.raw is resp.candidates[0].content


def test_parse_empty_or_blocked_response():
    assert parse_response(type("R", (), {"candidates": []})()).text == ""
    blocked = type("R", (), {"candidates": [type("C", (), {"content": None})()]})()
    out = parse_response(blocked)
    assert out.text == "" and out.tool_calls == []


def test_generate_sends_model_contents_and_config():
    llm, fake, _ = _client(sdk_response(sdk_part(text="ok")))
    out = llm.generate(system="s", messages=[{"role": "user", "text": "oi"}], tools=TOOLS)
    kw = fake.kwargs[0]
    assert out.text == "ok" and kw["model"] == "gemini-3.8-flash"
    assert kw["contents"] == [{"role": "user", "parts": [{"text": "oi"}]}]
    assert kw["config"]["system_instruction"] == "s"


def test_retries_on_429_with_backoff_then_succeeds():
    llm, fake, sleeps = _client(SDKError(429), SDKError(503), sdk_response(sdk_part(text="ok")))
    assert llm.generate(system="s", messages=[{"role": "user", "text": "x"}], tools=[]).text == "ok"
    assert sleeps == [2, 4] and len(fake.kwargs) == 3


def test_gives_up_after_retries_without_leaking_original_error():
    secret = "https://x?key=SEGREDO-123"
    llm, _, sleeps = _client(SDKError(429, secret), SDKError(429, secret), SDKError(429, secret))
    try:
        llm.generate(system="s", messages=[{"role": "user", "text": "x"}], tools=[])
        assert False, "deveria levantar LLMError"
    except LLMError as exc:
        assert "429" in str(exc) and "SEGREDO" not in str(exc)
    assert len(sleeps) == 2


def test_non_retryable_error_fails_immediately():
    llm, fake, sleeps = _client(SDKError(400, "bad request"))
    try:
        llm.generate(system="s", messages=[{"role": "user", "text": "x"}], tools=[])
        assert False
    except LLMError as exc:
        assert "400" in str(exc)
    assert sleeps == [] and len(fake.kwargs) == 1


def test_missing_api_key_is_a_clear_error():
    try:
        GeminiClient(api_key="")
        assert False
    except LLMError as exc:
        assert "LLM_API_KEY" in str(exc)
