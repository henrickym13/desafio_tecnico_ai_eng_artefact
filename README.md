# Empório da Música — Agente de Atendimento

Agente de atendimento (Python) para a loja fictícia Empório da Música: Monólito Modular +
agente único + function calling. Sem RAG vetorial: o manual cabe no contexto.

> Status: estrutura inicial. Implementação por fases, um commit por fase.

## Como rodar
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencher provedor/modelo/chave
python -m src.main                         # data real
python -m src.main --today 2026-02-20      # reproduz cenário de devolução
pytest
```

## Estrutura
```
data/raw/        CSVs (categories, customers, order_items, orders, products, promotions)
data/policies/   manual de políticas (PDF)
src/agent/       orchestrator, prompt, tool_registry
src/tools/       products, orders, policies (schemas + handlers)
src/data/        loader (limpeza) e repositories (único acesso aos dados)
src/policies/    sectioner do PDF por seção/página
src/services/    memória (SQLite) e estado de sessão
tests/           unit/ e integration/
examples/        3–5 conversas de exemplo
```

## Decisões técnicas  _(preencher)_
- Framework/abordagem: function calling, agente único
- Modelo e provedor: _a definir_
- Políticas: manual seccionado por tópico (enum) + página; sem embeddings
- Persistência: SQLite só para histórico/estado de sessão

## Dados: o que encontrei e como tratei

Antes de definir a arquitetura, inspecionei os 6 CSVs e o PDF. O tratamento está em
`src/data/loader.py` (roda uma vez no start, tudo em memória) e é coberto por
`tests/unit/test_loader.py`, executado contra os CSVs reais.

| O que encontrei | Como tratei |
|---|---|
| Disponibilidade inconsistente com `status`: produto 96 `active` com estoque 0; produto 136 `discontinued` com estoque 13; produto 130 `coming_soon` com estoque 2 (e já vendido nos pedidos 3 e 14) | `available = status == "active" and stock_quantity > 0`. Descontinuado e "em breve" nunca são oferecidos, mesmo com estoque |
| 25 promoções, só 4 ativas (ids 12, 14, 19, 24), sem datas de vigência; 3 produtos têm 2 promoções inativas | Só `is_active == 1` entra no catálogo. Se houver mais de uma ativa no mesmo produto, vale a de maior desconto (manual §6.2: não cumulativas). Preço promocional calculado em Python (`final_price_brl`) |
| Takamine GD20 (id 95) tem promoção de 12%, mas inativa | Preço de tabela (R$ 2.199,00). O agente informa que a promoção encerrou, sem prometer desconto (manual §7.3) |
| Categorias 6, 7 e 8 (sopros e cordas orquestrais) existem, mas não têm produtos. O manual fala em "300+ instrumentos"; o CSV tem 65 | Nenhum dado inventado: o agente informa que não há itens no momento. Teste fixa as categorias vazias |
| `specs` é JSON em string; nomes com acento e pequenos typos | `specs` vira dict. `name_norm` (minúsculas, sem acento) para busca; fuzzy será aplicado na Fase 2 |
| Pedidos 3 e 20 têm `total_brl` diferente da soma dos itens (−R$ 48 e −R$ 88), provavelmente por preço/desconto da época da compra | `total_brl` é a fonte de verdade do valor pago. Não recalculo pedidos |
| Não existe data real de entrega, só `estimated_delivery` | Usada como proxy da data de recebimento nas regras de prazo (ver Suposições) |
| Email duplicado entre os clientes 11 e 43 (mesmo email, nomes parecidos, mesma cidade); telefones são únicos | `phone_digits` (só dígitos, sem DDI) e `email_norm` (minúsculas). Email nunca identifica um cliente sozinho: a verificação exige o número do pedido e telefone/email que batam com o dono daquele pedido |
| Pedidos pending/confirmed sem rastreio nem estimativa; `payment_method` em código (ex.: `credit_6x`) | Campos nulos viram vazio, e o agente não inventa prazo. `payment_label` legível ("Cartão de crédito em 6x") |

**Integridade referencial:** pedidos, itens, clientes e produtos se relacionam sem registros
órfãos (verificado em teste).
## Suposições  _(preencher)_
- Data de referência (`--today`), entrega real = `estimated_delivery`, contato canônico,
  parcelamento (§3.1 prevalece), lacunas do manual -> encaminhar a atendente.
## Limitações conhecidas e próximos passos  _(preencher)_
## Uso de assistentes de código  _(preencher — registrar desde já)_