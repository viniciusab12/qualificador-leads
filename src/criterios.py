"""Regras de pontuação dos leads.

Para ajustar a qualificação, altere apenas os valores deste arquivo.
A soma das pontuações máximas deve ser 100.
"""

# ---------- Pontuação máxima de cada critério ----------
MAX_ORCAMENTO = 30
MAX_PRAZO = 25
MAX_SEGMENTO = 20
MAX_NECESSIDADE = 15
MAX_DECISOR = 10

# ---------- Orçamento (em reais) ----------
# Cada par é (valor mínimo da faixa, pontos). Da maior faixa para a menor.
FAIXAS_ORCAMENTO = [
    (15000, 30),
    (5000, 25),
    (2000, 15),
    (1, 5),
]

# ---------- Prazo para começar o projeto ----------
PONTOS_PRAZO = {
    "Até 1 mês": 25,
    "1 a 3 meses": 18,
    "3 a 6 meses": 10,
    "Mais de 6 meses": 3,
    "Indefinido": 3,
}

# ---------- Segmento da empresa ----------
SEGMENTOS_ALVO = ["Varejo", "Alimentação", "Saúde", "Educação"]
SEGMENTOS_SECUNDARIOS = ["Serviços", "Indústria", "Tecnologia"]
PONTOS_SEGMENTO_ALVO = 20
PONTOS_SEGMENTO_SECUNDARIO = 10

# ---------- Necessidade ----------
SERVICOS_OFERECIDOS = [
    "Site institucional",
    "Loja virtual",
    "Landing page",
    "Sistema de gestão",
    "Manutenção de site",
]
PONTOS_SERVICO_OFERECIDO = 10
PONTOS_DESCRICAO_CLARA = 5
TAMANHO_MINIMO_DESCRICAO = 30  # número de caracteres

# ---------- Contato é quem decide a compra ----------
PONTOS_DECISOR = 10
PONTOS_NAO_DECISOR = 3

# ---------- Classificação final ----------
LIMITE_QUENTE = 70  # nota >= 70
LIMITE_MORNO = 40   # nota >= 40 (abaixo disso: frio)