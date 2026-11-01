from src.services.memory import RETENTION_LIMIT, Memory


def test_new_session_is_empty(memory):
    s = memory.get_session("a")
    assert s.verified_customer_id is None and s.failed_verifications == 0 and s.messages == []


def test_state_and_messages_persist_across_instances(memory):
    s = memory.get_session("a")
    s.verified_customer_id, s.failed_verifications = 14, 2
    memory.save(s)
    memory.append_message("a", "user", "oi")
    memory.append_message("a", "assistant", "olá!")
    again = Memory(memory.db_path).get_session("a")  # "reiniciou o programa"
    assert (again.verified_customer_id, again.failed_verifications) == (14, 2)
    assert again.messages == [{"role": "user", "text": "oi"}, {"role": "assistant", "text": "olá!"}]


def test_sessions_are_isolated(memory):
    s = memory.get_session("a"); s.verified_customer_id = 14; memory.save(s)
    memory.append_message("a", "user", "segredo")
    other = memory.get_session("b")
    assert other.verified_customer_id is None and other.messages == []


def test_history_window_returns_latest_messages_in_order(memory):
    small = Memory(memory.db_path, history_window=3)
    for i in range(6):
        small.append_message("a", "user", f"m{i}")
    assert [m["text"] for m in small.get_session("a").messages] == ["m3", "m4", "m5"]


def test_retention_limit_prunes_old_messages(memory):
    for i in range(RETENTION_LIMIT + 10):
        memory.append_message("a", "user", f"m{i}")
    wide = Memory(memory.db_path, history_window=1000)
    texts = [m["text"] for m in wide.get_session("a").messages]
    assert len(texts) == RETENTION_LIMIT and texts[0] == "m10" and texts[-1] == f"m{RETENTION_LIMIT + 9}"


def test_clear_erases_history_and_verification(memory):
    s = memory.get_session("a"); s.verified_customer_id = 14; memory.save(s)
    memory.append_message("a", "user", "oi")
    memory.clear("a")
    cleared = memory.get_session("a")
    assert cleared.verified_customer_id is None and cleared.messages == []


def test_handoff_is_recorded(memory):
    first = memory.create_handoff("a", "reclamação")
    assert memory.create_handoff("a", "outra") == first + 1
