"""Divide o manual de políticas (PDF) por seção numerada, preservando as páginas.

Sem embeddings: o manual tem 8 páginas (~1.700 palavras), então é indexado por tópico (enum).
Cada seção carrega a página de origem para citação.

Detecção de títulos: "N. Título" com N sequencial (1, 2, 3...). A sequência evita confundir
os títulos com as listas numeradas do §7.2 ("1. Saudação...", "2. Entendimento...").
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

# tópico exposto ao LLM -> números das seções do manual
TOPICS: dict[str, list[str]] = {
    "sobre_a_loja": ["1"],        # endereço, telefone, e-mail, CNPJ, o que a loja vende
    "horario": ["2"],
    "pagamento": ["3"],
    "trocas_devolucoes": ["4"],
    "frete_entrega": ["5"],       # inclui código de rastreamento
    "promocoes": ["6"],
    "atendimento": ["7"],         # tom de voz, escopo, situações especiais
    "garantia": ["8"],
    "privacidade": ["9"],
    "disposicoes_finais": ["10"],
}

_HEADER_RE = re.compile(r"^Empório da Música\s+Manual de Políticas e Procedimentos$")
_FOOTER_RE = re.compile(r"^Página\s+\d+$")
_TOP_HEADING_RE = re.compile(r"^(\d{1,2})\.\s+(\S.*)$")
EXPECTED_SECTIONS = 10


@dataclass(frozen=True)
class PolicySection:
    number: str
    title: str
    text: str
    page: int
    end_page: int

    @property
    def pages_label(self) -> str:
        return str(self.page) if self.page == self.end_page else f"{self.page}–{self.end_page}"


def parse_pages(page_texts: list[str]) -> list[PolicySection]:
    """Converte o texto de cada página (1-indexado pela posição) em seções."""
    sections: list[dict] = []
    expected = 1
    for page_no, raw in enumerate(page_texts, start=1):
        for line in (ln.strip() for ln in raw.splitlines()):
            if not line or _HEADER_RE.match(line) or _FOOTER_RE.match(line):
                continue
            match = _TOP_HEADING_RE.match(line)
            if match and int(match.group(1)) == expected:
                sections.append({"number": match.group(1), "title": match.group(2).strip(),
                                 "lines": [], "page": page_no, "end_page": page_no})
                expected += 1
                continue
            if sections:  # ignora a capa (antes do §1)
                sections[-1]["lines"].append(line)
                sections[-1]["end_page"] = page_no
    if len(sections) != EXPECTED_SECTIONS:
        raise ValueError(
            f"PDF de políticas com estrutura inesperada: {len(sections)} seções encontradas, "
            f"esperadas {EXPECTED_SECTIONS}."
        )
    return [
        PolicySection(s["number"], s["title"], "\n".join(s["lines"]).strip(), s["page"], s["end_page"])
        for s in sections
    ]


def load_sections(pdf_path: Path) -> list[PolicySection]:
    with pdfplumber.open(pdf_path) as pdf:
        return parse_pages([page.extract_text() or "" for page in pdf.pages])


def get_policy(topic: str, sections: list[PolicySection]) -> list[PolicySection]:
    if topic not in TOPICS:
        raise ValueError(f"Tópico desconhecido: {topic}")
    wanted = set(TOPICS[topic])
    return [s for s in sections if s.number in wanted]
