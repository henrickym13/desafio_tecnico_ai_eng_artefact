"""Notas internas por seção: como o agente deve tratar contradições e lacunas do manual.

São as suposições documentadas no README ("Suposições"), entregues junto com o texto do manual
para o agente aplicá-las sempre do mesmo jeito. NÃO são texto do manual: o agente não deve
dizer ao cliente "o manual diz" sobre elas.
"""
from __future__ import annotations

STORE_PHONE = "(67) 3341-4444"

INTERNAL_NOTES: dict[str, list[str]] = {
    "1": [
        "O manual cita 'mais de 300 instrumentos' e linhas de sopro e cordas orquestrais, mas o catálogo "
        "real é menor e algumas categorias estão sem produtos: nunca cite quantidade nem prometa "
        "categoria sem consultar buscar_produtos.",
        "Contato oficial: telefone/WhatsApp (67) 3341-4444 e e-mail contato@emporiodamusica.com.br "
        "(sem acento; a tabela do §1.2 grafa o domínio com acento, provável erro de digitação).",
    ],
    "2": [
        "O manual não traz lista de feriados. Para 'estão abertos agora?', use loja_aberta_agora.",
    ],
    "3": [
        "A tabela diz parcela mínima de R$ 100 para todo crédito, mas o §3.1 escalona por número de "
        "parcelas. Prevalece o §3.1. Use o parcelamento já calculado por detalhes_produto.",
        "O desconto de 5% do PIX não vale para preço promocional (§6.2). Use o preco_pix de "
        "detalhes_produto, nunca calcule.",
    ],
    "4": [
        "Troca por defeito é de 30 dias (§4.2), mas a garantia legal é de 90 dias (§8.1). Depois dos "
        "30 dias, oriente acionar a garantia com o fabricante (a loja pode intermediar). Para prazos "
        "de um pedido, use verificar_elegibilidade_devolucao: nunca conte dias por conta própria.",
        "O manual não diz se o arrependimento vale para compra presencial nem como cancelar um pedido "
        "ainda não enviado. Nesses casos, use encaminhar_atendente e diga ao cliente que a equipe vai confirmar.",
    ],
    "7": [
        "O §7 cita o WhatsApp (67) 3321-4500, diferente do telefone/WhatsApp do §1.2. Use sempre "
        "(67) 3341-4444.",
    ],
    "8": [
        "Garantia legal: 90 dias após o recebimento (§8.1). O prazo de troca por defeito (30 dias) "
        "está no §4.2.",
    ],
}
