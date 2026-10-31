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

## Dados: o que encontrei e como tratei  _(preencher)_
## Suposições  _(preencher)_
- Data de referência (`--today`), entrega real = `estimated_delivery`, contato canônico,
  parcelamento (§3.1 prevalece), lacunas do manual -> encaminhar a atendente.
## Limitações conhecidas e próximos passos  _(preencher)_
## Uso de assistentes de código  _(preencher — registrar desde já)_
