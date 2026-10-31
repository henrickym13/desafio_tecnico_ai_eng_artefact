def test_violoes_ate_1000_only_available_and_sorted(products_repo):
    r = products_repo.search(category="violão", max_price=1000)
    assert r["total"] > 0
    prices = [p["preco_final"] for p in r["produtos"]]
    assert prices == sorted(prices) and max(prices) <= 1000
    assert all(p["categoria"] == "Violões" and p["disponivel"] for p in r["produtos"])
    assert not {96, 113, 130, 136} & {p["id"] for p in r["produtos"]}


def test_search_by_text(products_repo):
    r = products_repo.search(query="Takamine")
    assert r["total"] >= 1 and all("Takamine" in p["nome"] for p in r["produtos"])


def test_empty_category_is_reported_not_invented(products_repo):
    r = products_repo.search(category="saxofone")
    assert r["total"] == 0
    assert any("não há produtos" in a for a in r["avisos"])


def test_hidden_unavailable_products_are_reported(products_repo):
    r = products_repo.search(category="violão", only_available=True, limit=100)
    shown = {p["id"] for p in r["produtos"]}
    everything = products_repo.search(category="violão", only_available=False, limit=100)
    assert len(everything["produtos"]) > len(r["produtos"])
    assert {p["id"] for p in everything["produtos"]} - shown  # há indisponíveis fora da lista
    assert any("indisponíveis" in a for a in r["avisos"])


def test_price_of_takamine_gd20_no_active_promo(products_repo):
    r = products_repo.get("Takamine GD20")
    assert r["encontrado"]
    p = r["produto"]
    assert p["id"] == 95 and p["promocao"] is None
    assert p["preco_final"] == 2199.0 and p["preco_final_fmt"] == "R$ 2.199,00"
    assert p["preco_pix"] == 2089.05
    assert p["parcelamento_sem_juros"]["parcelas"] == 12


def test_promo_product_shows_both_prices_and_no_pix_discount(products_repo):
    p = products_repo.get(94)["produto"]
    assert p["promocao"]["percentual"] == 8
    assert p["preco_final"] < p["preco_tabela"]
    assert p["preco_pix"] is None and "§6.2" in p["observacao_pix"]


def test_unavailable_product_comes_with_alternatives(products_repo):
    p = products_repo.get(136)["produto"]  # descontinuado com estoque
    assert not p["disponivel"] and p["motivo_indisponibilidade"] == "descontinuado"
    assert 0 < len(p["alternativas"]) <= 3
    assert all(a["disponivel"] and a["categoria"] == p["categoria"] for a in p["alternativas"])


def test_out_of_stock_active_product_reason(products_repo):
    p = products_repo.get(96)["produto"]
    assert p["status_catalogo"] == "ativo" and p["motivo_indisponibilidade"] == "esgotado"


def test_typo_still_finds_product(products_repo):
    r = products_repo.get("Takamne GD20")
    assert r["encontrado"] and r["produto"]["id"] == 95 and r.get("correspondencia_aproximada")


def test_ambiguous_and_unknown_names(products_repo):
    amb = products_repo.get("Yamaha")
    assert not amb["encontrado"] and amb["ambiguo"] and len(amb["candidatos"]) >= 2
    assert not products_repo.get("Flauta Mágica Zebra")["encontrado"]
    assert not products_repo.get(99999)["encontrado"]
