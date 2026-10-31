"""Acesso a dados estruturados. É a ÚNICA camada que conhece o Dataset.

As tools chamam estes repositórios; o agente nunca toca em CSV/DataFrame.
"""
from __future__ import annotations

import difflib
import re

import pandas as pd

from src.data.loader import Dataset, normalize_phone, normalize_text
from src.services.pricing import format_brl, max_installments, pix_price

CATEGORY_ALIASES: dict[int, list[str]] = {
    1: ["guitarra", "guitarras"],
    2: ["baixo", "baixos"],
    3: ["bateria", "baterias", "percussao"],
    4: ["teclado", "teclados", "piano", "pianos", "sintetizador"],
    5: ["violao", "violoes"],
    6: ["sopro", "flauta", "clarinete", "saxofone", "sax", "oboe"],
    7: ["sopro", "trompete", "trombone", "tuba", "trompa", "metais"],
    8: ["violino", "viola", "violoncelo", "cello", "contrabaixo acustico", "cordas orquestrais"],
    9: ["ukulele", "ukeleles", "ukulele"],
}
STATUS_LABELS = {"active": "ativo", "discontinued": "descontinuado", "coming_soon": "em_breve"}
FUZZY_CUTOFF = 0.8

ORDER_STATUS_DESCRIPTIONS = {
    "pending": "Aguardando confirmação do pagamento",
    "confirmed": "Pagamento confirmado, pedido em preparação (ainda sem código de rastreio)",
    "shipped": "Enviado, a caminho",
    "delivered": "Entregue",
    "cancelled": "Cancelado",
}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", normalize_text(text)) if len(t) > 1]


def _best_ratio(token: str, words: list[str]) -> float:
    return max((difflib.SequenceMatcher(None, token, w).ratio() for w in words), default=0.0)


class ProductRepository:
    def __init__(self, ds: Dataset) -> None:
        df = ds.products.copy()
        aliases = df["category_id"].map(lambda c: " ".join(CATEGORY_ALIASES.get(int(c), [])))
        df["_core_words"] = (df["name_norm"] + " " + df["category_norm"] + " " + aliases).map(_tokens)
        extra = (
            df["description"].map(normalize_text) + " "
            + df["specs"].map(lambda s: normalize_text(" ".join(str(v) for v in s.values())))
        ).map(_tokens)
        df["_all_words"] = [c + e for c, e in zip(df["_core_words"], extra)]
        self.df = df
        self._category_names = dict(zip(ds.categories["category_id"], ds.categories["name"]))

    # ---------- resolução de entrada ----------
    def _resolve_categories(self, text: str) -> set[int]:
        norm = normalize_text(text)
        found = set()
        for cid, aliases in CATEGORY_ALIASES.items():
            for alias in aliases:
                if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", norm):
                    found.add(cid)
        return found

    def _text_mask(self, df: pd.DataFrame, tokens: list[str], fuzzy: bool) -> pd.Series:
        def matches(row) -> bool:
            for tok in tokens:
                if any(w.startswith(tok) for w in row["_all_words"]):
                    continue
                if fuzzy and _best_ratio(tok, row["_core_words"]) >= FUZZY_CUTOFF:
                    continue
                return False
            return True

        return df.apply(matches, axis=1) if len(df) else pd.Series([], dtype=bool)

    # ---------- serialização ----------
    @staticmethod
    def _reason(row) -> str | None:
        if row["available"]:
            return None
        return {"discontinued": "descontinuado", "coming_soon": "em_breve"}.get(row["status"], "esgotado")

    def _summary(self, row) -> dict:
        list_price, final_price = float(row["price_brl"]), float(row["final_price_brl"])
        promo = None
        if bool(row["has_promo"]):
            promo = {
                "descricao": str(row["promo_description"]),
                "percentual": int(row["promo_discount_percent"]),
                "preco_promocional": final_price,
                "preco_promocional_fmt": format_brl(final_price),
            }
        return {
            "id": int(row["product_id"]),
            "nome": str(row["name"]),
            "categoria": str(row["category_name"]),
            "status_catalogo": STATUS_LABELS.get(row["status"], str(row["status"])),
            "disponivel": bool(row["available"]),
            "motivo_indisponibilidade": self._reason(row),
            "estoque": int(row["stock_quantity"]),
            "preco_tabela": list_price,
            "preco_tabela_fmt": format_brl(list_price),
            "promocao": promo,
            "preco_final": final_price,
            "preco_final_fmt": format_brl(final_price),
        }

    def _detail(self, row) -> dict:
        data = self._summary(row)
        data["descricao"] = str(row["description"])
        data["especificacoes"] = dict(row["specs"])
        final_price = data["preco_final"]
        data["parcelamento_sem_juros"] = max_installments(final_price)
        if data["promocao"] is None:
            pix = pix_price(data["preco_tabela"])
            data.update(preco_pix=pix, preco_pix_fmt=format_brl(pix))
        else:
            data.update(preco_pix=None, preco_pix_fmt=None,
                        observacao_pix="Desconto de PIX não se aplica a preço promocional (manual §6.2).")
        if not data["disponivel"]:
            alt = self.df[
                (self.df["category_id"] == row["category_id"])
                & self.df["available"]
                & (self.df["product_id"] != row["product_id"])
            ].copy()
            alt["_dist"] = (alt["final_price_brl"] - row["final_price_brl"]).abs()
            data["alternativas"] = [self._summary(r) for _, r in alt.sort_values("_dist").head(3).iterrows()]
        return data

    # ---------- consultas ----------
    def search(self, query: str | None = None, category: str | None = None,
               min_price: float | None = None, max_price: float | None = None,
               only_available: bool = True, limit: int = 10) -> dict:
        df, avisos, approx = self.df, [], False
        text = query or ""

        if category:
            cat_ids = self._resolve_categories(category)
            if cat_ids:
                df = df[df["category_id"].isin(cat_ids)]
                if df.empty:
                    labels = ", ".join(self._category_names[int(c)] for c in sorted(cat_ids))
                    avisos.append(f"A categoria ({labels}) existe, mas não há produtos no catálogo no momento.")
            else:
                text = f"{text} {category}".strip()
                avisos.append(f"Categoria '{category}' não reconhecida; busquei como texto livre.")

        tokens = _tokens(text)
        if tokens and not df.empty:
            exact = df[self._text_mask(df, tokens, fuzzy=False)]
            if exact.empty:
                fuzzy = df[self._text_mask(df, tokens, fuzzy=True)]
                if not fuzzy.empty:
                    approx = True
                df = fuzzy
            else:
                df = exact

        if min_price is not None:
            df = df[df["final_price_brl"] >= min_price]
        if max_price is not None:
            df = df[df["final_price_brl"] <= max_price]

        if only_available:
            hidden = int((~df["available"]).sum())
            df = df[df["available"]]
            if hidden:
                avisos.append(f"{hidden} produto(s) da busca estão indisponíveis (esgotados/descontinuados/em breve) e foram ocultados.")

        df = df.sort_values(["final_price_brl", "name"])
        items = [self._summary(r) for _, r in df.head(limit).iterrows()]
        return {"total": int(len(df)), "retornados": len(items), "produtos": items,
                "avisos": avisos, "busca_aproximada": approx}

    def get(self, name_or_id: str | int) -> dict:
        text = str(name_or_id).strip()
        df = self.df
        if text.isdigit():
            hit = df[df["product_id"] == int(text)]
            if hit.empty:
                return {"encontrado": False, "mensagem": f"Nenhum produto com id {text}."}
            return {"encontrado": True, "produto": self._detail(hit.iloc[0])}

        norm = normalize_text(text)
        exact = df[df["name_norm"] == norm]
        if len(exact) == 1:
            return {"encontrado": True, "produto": self._detail(exact.iloc[0])}

        tokens = _tokens(text)
        if not tokens:
            return {"encontrado": False, "mensagem": "Informe o nome ou modelo do produto."}

        for fuzzy in (False, True):
            cand = df[self._text_mask(df, tokens, fuzzy=fuzzy)]
            if len(cand) == 1:
                out = {"encontrado": True, "produto": self._detail(cand.iloc[0])}
                if fuzzy:
                    out["correspondencia_aproximada"] = True
                return out
            if len(cand) > 1:
                return {"encontrado": False, "ambiguo": True,
                        "mensagem": "Mais de um produto corresponde. Peça ao cliente para especificar o modelo.",
                        "candidatos": [self._summary(r) for _, r in cand.head(5).iterrows()]}
        return {"encontrado": False, "mensagem": "Não encontrei esse produto no catálogo."}


class OrderRepository:
    def __init__(self, ds: Dataset) -> None:
        self.ds = ds

    def _build(self, order_row) -> dict:
        customer = self.ds.customers[self.ds.customers["customer_id"] == order_row["customer_id"]].iloc[0]
        items = self.ds.order_items[self.ds.order_items["order_id"] == order_row["order_id"]]
        names = self.ds.products.set_index("product_id")["name"]
        return {
            "order_id": int(order_row["order_id"]),
            "customer_id": int(order_row["customer_id"]),
            "customer_first_name": str(customer["name"]).split()[0],
            "status": str(order_row["status"]),
            "order_date": order_row["order_date"],
            "estimated_delivery": order_row["estimated_delivery"] if pd.notna(order_row["estimated_delivery"]) else None,
            "total_brl": float(order_row["total_brl"]),
            "payment_label": str(order_row["payment_label"]),
            "tracking_code": str(order_row["tracking_code"]) or None,
            "notes": str(order_row["notes"]) or None,
            "items": [
                {"produto": str(names.get(int(i["product_id"]), f"Produto #{int(i['product_id'])}")),
                 "quantidade": int(i["quantity"])}
                for _, i in items.iterrows()
            ],
        }

    def _row(self, order_id: int):
        hit = self.ds.orders[self.ds.orders["order_id"] == order_id]
        return None if hit.empty else hit.iloc[0]

    def get_verified(self, order_id: int, phone_or_email: str) -> dict | None:
        """Devolve o pedido só se phone/email bater com o DONO do pedido.

        Nunca busca cliente por email isolado (há email duplicado: clientes 11 e 43).
        """
        row = self._row(order_id)
        if row is None:
            return None
        owner = self.ds.customers[self.ds.customers["customer_id"] == row["customer_id"]].iloc[0]
        cred = str(phone_or_email).strip()
        if "@" in cred:
            ok = cred.lower() == owner["email_norm"]
        else:
            digits = normalize_phone(cred)
            ok = len(digits) >= 10 and digits == owner["phone_digits"]
        return self._build(row) if ok else None

    def get_for_customer(self, order_id: int, customer_id: int) -> dict | None:
        """Para sessão já verificada: só devolve pedidos do próprio cliente."""
        row = self._row(order_id)
        if row is None or int(row["customer_id"]) != int(customer_id):
            return None
        return self._build(row)