"""Fase 1: testes do tratamento de dados, contra os CSVs reais."""
import datetime as dt

import pytest

from src.config import settings
from src.data.loader import load_dataset, normalize_phone, normalize_text


@pytest.fixture(scope="module")
def ds():
    return load_dataset(settings.raw_data_dir)


def _product(ds, product_id):
    return ds.products[ds.products["product_id"] == product_id].iloc[0]


def test_availability_rules(ds):
    assert not _product(ds, 96)["available"]    # active, estoque 0
    assert not _product(ds, 113)["available"]   # discontinued, estoque 0
    assert not _product(ds, 136)["available"]   # discontinued, estoque 13
    assert not _product(ds, 130)["available"]   # coming_soon, estoque 2
    assert _product(ds, 81)["available"]        # active com estoque


def test_only_active_promotions(ds):
    promo_ids = set(ds.products.loc[ds.products["has_promo"], "promo_id"].astype(int))
    assert promo_ids == {12, 14, 19, 24}
    assert ds.products["product_id"].is_unique  # merge não duplicou produtos


def test_takamine_gd20_has_no_active_promo(ds):
    gd20 = _product(ds, 95)
    assert "GD20" in gd20["name"]
    assert not gd20["has_promo"]
    assert gd20["final_price_brl"] == gd20["price_brl"] == 2199.0


def test_promo_price_is_computed(ds):
    p = _product(ds, 94)  # promo 24: 8%
    assert p["promo_discount_percent"] == 8
    assert p["final_price_brl"] == round(p["price_brl"] * 0.92, 2)


def test_specs_parsed_and_categories_joined(ds):
    assert all(isinstance(s, dict) for s in ds.products["specs"])
    assert _product(ds, 81)["specs"]["strings"] == "nylon"
    assert _product(ds, 81)["category_name"] == "Violões"


def test_empty_categories_are_known(ds):
    used = set(ds.products["category_id"])
    empty = set(ds.categories["category_id"]) - used
    assert empty == {6, 7, 8}  # sopros e cordas orquestrais: sem produtos no catálogo


def test_normalize_helpers():
    assert normalize_text("  Violão   ELÉTRICO ") == "violao eletrico"
    assert normalize_phone("(67) 99812-3456") == "67998123456"
    assert normalize_phone("+55 67 99812-3456") == "67998123456"


def test_customers_normalized(ds):
    assert ds.customers["phone_digits"].str.fullmatch(r"\d{10,11}").all()
    assert ds.customers["phone_digits"].is_unique
    dup = ds.customers[ds.customers["email_norm"] == "bruno.martins@jmail.com"]
    assert set(dup["customer_id"]) == {11, 43}  # email NÃO identifica um cliente sozinho


def test_orders_typed(ds):
    o = ds.orders[ds.orders["order_id"] == 7].iloc[0]
    assert o["estimated_delivery"] == dt.date(2026, 2, 17)
    assert o["customer_id"] == 14
    assert o["payment_label"] == "Cartão de crédito em 3x"
    assert ds.orders["notes"].notna().all()


def test_referential_integrity(ds):
    assert set(ds.orders["customer_id"]) <= set(ds.customers["customer_id"])
    assert set(ds.order_items["order_id"]) <= set(ds.orders["order_id"])
    assert set(ds.order_items["product_id"]) <= set(ds.products["product_id"])
