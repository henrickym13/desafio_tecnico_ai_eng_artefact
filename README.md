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
src/tools/       products, orders, policies (schemas + handlers); errors
src/data/        loader (limpeza) e repositories (único acesso aos dados)
src/policies/    sectioner do PDF por seção/página (Fase 3)
src/services/    pricing (PIX, parcelamento), returns (prazos), memory (sessão)
tests/           conftest.py + unit/ (e integration/ nas próximas fases)
examples/        3–5 conversas de exemplo
```

## Decisões técnicas  _(preencher)_
- Framework/abordagem: function calling, agente único
- Modelo e provedor: **Google Gemini**, via API. O agente depende de function calling nativo,
  que o Gemini oferece. O modelo exato é configurável por `LLM_MODEL` no `.env` (ver
  `.env.example`), e o orquestrador é agnóstico de provedor (recebe o cliente LLM por injeção),
  então trocar de modelo ou provedor não afeta tools, dados nem testes.
- Políticas: manual seccionado por tópico (enum) + página; sem embeddings
- Persistência: SQLite só para histórico/estado de sessão
- Busca de produtos: casamento por prefixo de palavra em nome/categoria/descrição/specs, com
  fallback tolerante a typos via `difflib` (stdlib). O catálogo tem 65 itens, então não há
  motivo para busca vetorial nem dependência extra.
- Cálculos fora do LLM: preço final, desconto PIX (§3/§6.2), parcelamento (§3.1) e prazos de
  troca/devolução (§4, §8.1) são feitos em Python e entregues prontos às tools.
- Segurança de pedidos: o `customer_id` verificado vive no estado da sessão (nunca é argumento
  de tool). Verificação = número do pedido + telefone/email do dono daquele pedido; falhas
  retornam sempre a mesma mensagem genérica e há bloqueio após 5 tentativas inválidas.
- Validação de argumentos das tools: coerção/validação própria por schema no `ToolRegistry`
  (tipos, enum, obrigatórios, campos desconhecidos); falhas viram erro estruturado, não exceção.

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
## Uso de assistentes de código

**Ferramentas:**
- **ChatGPT (OpenAI):** rascunho inicial da arquitetura (monólito modular, agente único,
  function calling e RAG), antes de eu ter visto os dados.
- **Claude (Anthropic), modelo Claude Sonnet 5.5:** pela interface de chat do claude.ai, com
  execução de código e leitura dos arquivos do desafio. Foi meu par de programação e revisão
  de arquitetura, em uma conversa contínua, da revisão da proposta até a implementação.

O Gemini é o LLM **do produto** (o que atende o cliente), não foi usado para escrever o código.

**Como usei, por etapa:**
1. **Arquitetura:** o ChatGPT gerou o rascunho inicial. Levei esse rascunho ao Claude, que o
   confrontou com o enunciado e sugeriu enxugar a estrutura de pastas e decidir sobre RAG só
   depois de ver o PDF. A arquitetura final é o resultado dessa revisão.
2. **Análise dos dados:** o assistente leu os 6 CSVs e o PDF e levantou inconsistências
   (disponibilidade versus status, promoções inativas, email duplicado, divergências no
   manual). Aceitei as conclusões depois de conferir os casos, e elas estão em
   "Dados" e "Suposições".
3. **Implementação por fases:** o assistente gerou o esqueleto do projeto, o `loader`, os
   repositórios, as tools, o registro de tools e os testes. Trabalhamos em fases pequenas,
   uma por commit, e a cada fase eu revisei o código e as decisões antes de seguir.
4. **Testes:** o assistente escreveu os testes unitários contra os CSVs reais e os executou no
   ambiente dele com um runner mínimo, porque o `pytest` não estava disponível lá. Os testes
   foram escritos para rodar com `pytest` normal, e eu os executo localmente a cada fase.

**O que decidi eu:** o escopo e a ordem das fases, o uso do Gemini, o que entra no README e
quais sugestões aceitar (por exemplo, dispensar ChromaDB/embeddings e usar o manual seccionado).

**Limites que reconheço:** código gerado por IA precisa de revisão humana. Mantive os testes
como rede de segurança e documentei como suposições os pontos em que o manual é omisso ou
contraditório, em vez de deixar o modelo ou o assistente decidirem em silêncio.