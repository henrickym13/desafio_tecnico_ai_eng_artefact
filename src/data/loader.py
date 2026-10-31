"""Fase 1: carrega e trata os CSVs. Executado uma vez no start (tudo em memória).

Tratamentos (ver README > Dados):
- products.specs: JSON em string -> dict
- products.available: status == 'active' e stock_quantity > 0
- products: nome normalizado (sem acento/minúsculas) para busca; nome da categoria
- promotions: só is_active == 1 entram nos produtos (promo_*); preço promocional calculado aqui
- orders: datas -> date; payment_method -> rótulo legível; notes nulo -> ""
- customers: telefone só com dígitos e email em minúsculas (verificação de identidade)
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PAYMENT_LABELS = {
    "pix": "PIX",
    "debit": "Cartão de débito",
    "boleto": "Boleto bancário",
    "credit_3x": "Cartão de crédito em 3x",
    "credit_6x": "Cartão de crédito em 6x",
    "credit_12x": "Cartão de crédito em 12x",
}


@dataclass
class Dataset:
    categories: pd.DataFrame
    customers: pd.DataFrame
    products: pd.DataFrame
    promotions: pd.DataFrame  # todas as linhas (histórico); só as ativas chegam em products
    orders: pd.DataFrame
    order_items: pd.DataFrame


def normalize_text(text: str) -> str:
    """minúsculas, sem acento, espaços colapsados. Usado em busca e comparação."""
    decomposed = unicodedata.normalize("NFKD", str(text))
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", no_accents).strip().lower()


def normalize_phone(phone: str) -> str:
    """Só dígitos; remove o DDI 55 se vier com ele (12-13 dígitos)."""
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) in (12, 13) and digits.startswith("55"):
        digits = digits[2:]
    return digits


def _parse_specs(raw: object) -> dict:
    try:
        value = json.loads(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _active_promotions(promotions: pd.DataFrame) -> pd.DataFrame:
    """Uma promoção ativa por produto (manual §6.2: não cumulativas -> maior desconto)."""
    active = promotions[promotions["is_active"] == 1]
    active = active.sort_values("discount_percent", ascending=False)
    active = active.drop_duplicates("product_id", keep="first")
    return active.rename(
        columns={
            "promotion_id": "promo_id",
            "discount_percent": "promo_discount_percent",
            "description": "promo_description",
        }
    )[["product_id", "promo_id", "promo_discount_percent", "promo_description"]]


def _prepare_products(
    products: pd.DataFrame, categories: pd.DataFrame, promotions: pd.DataFrame
) -> pd.DataFrame:
    df = products.copy()
    df["name"] = df["name"].str.strip()
    df["name_norm"] = df["name"].map(normalize_text)
    df["specs"] = df["specs"].map(_parse_specs)
    df["available"] = (df["status"] == "active") & (df["stock_quantity"] > 0)
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.date

    cats = categories.rename(columns={"name": "category_name"})[["category_id", "category_name"]]
    df = df.merge(cats, on="category_id", how="left")
    df["category_norm"] = df["category_name"].map(normalize_text)

    df = df.merge(_active_promotions(promotions), on="product_id", how="left")
    df["has_promo"] = df["promo_id"].notna()
    df["final_price_brl"] = (
        df["price_brl"] * (1 - df["promo_discount_percent"].fillna(0) / 100)
    ).round(2)
    return df


def _prepare_customers(customers: pd.DataFrame) -> pd.DataFrame:
    df = customers.copy()
    df["phone_digits"] = df["phone"].map(normalize_phone)
    df["email_norm"] = df["email"].str.strip().str.lower()
    return df


def _prepare_orders(orders: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()
    df["order_date"] = pd.to_datetime(df["order_date"]).dt.date
    df["estimated_delivery"] = pd.to_datetime(df["estimated_delivery"]).dt.date
    df["payment_label"] = df["payment_method"].map(PAYMENT_LABELS).fillna(df["payment_method"])
    df["notes"] = df["notes"].fillna("")
    df["tracking_code"] = df["tracking_code"].fillna("")
    return df


def load_dataset(raw_dir: Path) -> Dataset:
    raw_dir = Path(raw_dir)

    def read(name: str) -> pd.DataFrame:
        return pd.read_csv(raw_dir / f"{name}.csv")

    categories = read("categories")
    promotions = read("promotions")
    return Dataset(
        categories=categories,
        customers=_prepare_customers(read("customers")),
        products=_prepare_products(read("products"), categories, promotions),
        promotions=promotions,
        orders=_prepare_orders(read("orders")),
        order_items=read("order_items"),
    )