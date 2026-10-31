from datetime import date

from src.tools import orders as tools

# pedido 7: cliente 14 (Letícia), entregue, previsão 2026-02-17
LETICIA_PHONE, LETICIA_EMAIL = "(67) 99789-0123", "leticia.rocha@jmail.com"
PEDRO_PHONE = "(67) 98432-1098"  # cliente 3, dono do pedido 1


def test_verification_by_phone_or_email_of_the_owner(orders_repo):
    assert orders_repo.get_verified(7, LETICIA_PHONE)["customer_id"] == 14
    assert orders_repo.get_verified(7, "67997890123")["customer_id"] == 14
    assert orders_repo.get_verified(7, "LETICIA.ROCHA@jmail.com ")["customer_id"] == 14


def test_wrong_owner_credentials_fail(orders_repo):
    assert orders_repo.get_verified(7, PEDRO_PHONE) is None
    assert orders_repo.get_verified(7, "pedro.oliveira@jmail.com") is None
    assert orders_repo.get_verified(7, "") is None
    assert orders_repo.get_verified(9999, LETICIA_PHONE) is None


def test_duplicate_email_only_opens_the_order_of_its_owner(orders_repo):
    # bruno.martins@jmail.com existe nos clientes 11 e 43; o pedido 10 é do cliente 11
    assert orders_repo.get_verified(10, "bruno.martins@jmail.com")["customer_id"] == 11
    assert orders_repo.get_verified(7, "bruno.martins@jmail.com") is None


def test_consultar_pedido_public_view_has_no_private_data(orders_repo, session):
    r = tools.consultar_pedido(orders_repo, session, numero_pedido=7, telefone_ou_email=LETICIA_PHONE)
    assert r["ok"] and session.verified_customer_id == 14
    pedido = r["pedido"]
    assert pedido["status"] == "delivered" and pedido["itens"] and pedido["total_fmt"].startswith("R$ ")
    assert pedido["codigo_rastreio"] == "BRKR1122334BR" and pedido["previsao_entrega"] == "2026-02-17"
    assert not {"customer_id", "telefone", "email", "phone"} & set(pedido)


def test_unverified_without_credentials_is_asked_and_not_counted(orders_repo, session):
    r = tools.consultar_pedido(orders_repo, session, numero_pedido=7)
    assert not r["ok"] and r["precisa_verificacao"] and session.failed_verifications == 0


def test_verified_session_cannot_read_other_customers_orders(orders_repo, session):
    tools.consultar_pedido(orders_repo, session, numero_pedido=7, telefone_ou_email=LETICIA_PHONE)
    other = tools.consultar_pedido(orders_repo, session, numero_pedido=1)  # pedido do cliente 3
    missing = tools.consultar_pedido(orders_repo, session, numero_pedido=9999)
    assert not other["ok"] and other["mensagem"] == missing["mensagem"] == tools.NOT_FOUND_MESSAGE
    assert session.failed_verifications == 2


def test_lockout_after_repeated_failures(orders_repo, session):
    for _ in range(tools.MAX_FAILED_VERIFICATIONS):
        tools.consultar_pedido(orders_repo, session, numero_pedido=7, telefone_ou_email=PEDRO_PHONE)
    r = tools.consultar_pedido(orders_repo, session, numero_pedido=7, telefone_ou_email=LETICIA_PHONE)
    assert r["bloqueado"] and session.verified_customer_id is None


def test_cancelled_order_exposes_reason(orders_repo, session):
    # pedido 17: cliente 15, cancelado antes do processamento
    owner = orders_repo.ds.customers.set_index("customer_id").loc[15, "email"]
    r = tools.consultar_pedido(orders_repo, session, numero_pedido=17, telefone_ou_email=owner)
    assert r["pedido"]["status"] == "cancelled" and "cancelado" in r["pedido"]["observacoes"].lower()


def test_return_eligibility_requires_verification(orders_repo, session):
    r = tools.verificar_elegibilidade_devolucao(orders_repo, session, date(2026, 2, 20), numero_pedido=7)
    assert not r["ok"] and r["precisa_verificacao"]


def test_return_eligibility_inside_and_outside_regret_window(orders_repo, session):
    tools.consultar_pedido(orders_repo, session, numero_pedido=7, telefone_ou_email=LETICIA_EMAIL)
    inside = tools.verificar_elegibilidade_devolucao(orders_repo, session, date(2026, 2, 20), numero_pedido=7)
    assert inside["ok"] and inside["janelas"]["arrependimento"]["dentro_do_prazo"]
    outside = tools.verificar_elegibilidade_devolucao(orders_repo, session, date(2026, 10, 31), numero_pedido=7)
    assert not outside["janelas"]["arrependimento"]["dentro_do_prazo"]
    assert not outside["janelas"]["garantia_legal"]["dentro_do_prazo"]


def test_return_eligibility_other_customers_order_is_hidden(orders_repo, session):
    tools.consultar_pedido(orders_repo, session, numero_pedido=7, telefone_ou_email=LETICIA_EMAIL)
    r = tools.verificar_elegibilidade_devolucao(orders_repo, session, date(2026, 2, 20), numero_pedido=1)
    assert not r["ok"] and r["mensagem"] == tools.NOT_FOUND_MESSAGE
