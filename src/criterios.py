"""Regras de pontuação dos leads.

Os valores abaixo são as regras PADRÃO, usadas no modo demonstração e por quem
nunca personalizou. Cada conta pode mudar os pesos, os limites de classificação,
os segmentos-alvo e o tamanho mínimo da descrição na página Critérios.
A pontuação continua sempre calculada em Python (src/scoring.py), nunca pela IA.
"""

import copy

# ---------- Pontuação máxima de cada critério (pesos padrão) ----------
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

# Todos os segmentos que aparecem no formulário
SEGMENTOS_DISPONIVEIS = SEGMENTOS_ALVO + SEGMENTOS_SECUNDARIOS + ["Outro"]

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


# ---------- Regras personalizáveis ----------

NOMES_CRITERIOS = {
    "orcamento": "Orçamento",
    "prazo": "Prazo",
    "segmento": "Segmento",
    "necessidade": "Necessidade",
    "decisor": "Contato decisor",
}

PESOS_PADRAO = {
    "orcamento": MAX_ORCAMENTO,
    "prazo": MAX_PRAZO,
    "segmento": MAX_SEGMENTO,
    "necessidade": MAX_NECESSIDADE,
    "decisor": MAX_DECISOR,
}

CRITERIOS_PADRAO = {
    "versao": 0,  # 0 = regras padrão; contas personalizadas começam na versão 1
    "pesos": dict(PESOS_PADRAO),
    "limite_quente": LIMITE_QUENTE,
    "limite_morno": LIMITE_MORNO,
    "segmentos_alvo": list(SEGMENTOS_ALVO),
    "segmentos_secundarios": list(SEGMENTOS_SECUNDARIOS),
    "tamanho_minimo_descricao": TAMANHO_MINIMO_DESCRICAO,
}


def criterios_padrao():
    """Cópia das regras padrão (cópia para ninguém alterar o original sem querer)."""
    return copy.deepcopy(CRITERIOS_PADRAO)


def completar_criterios(config):
    """Preenche com o padrão o que faltar numa configuração salva.

    Serve para configurações antigas continuarem funcionando se um campo novo
    for criado no futuro.
    """
    completa = criterios_padrao()
    if not config:
        return completa
    for chave, valor in config.items():
        if chave == "pesos":
            completa["pesos"].update(valor or {})
        elif chave in completa:
            completa[chave] = valor
    return completa


def _inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def validar_criterios(config):
    """Confere uma configuração de regras. Devolve uma lista de erros (vazia = válida)."""
    erros = []
    pesos = config.get("pesos", {})

    if set(pesos) != set(PESOS_PADRAO):
        erros.append("Informe o peso dos 5 critérios.")
    else:
        for chave, peso in pesos.items():
            if not _inteiro(peso) or not 0 <= peso <= 100:
                erros.append(f"O peso de {NOMES_CRITERIOS[chave]} precisa ser um número inteiro de 0 a 100.")
        if not erros and sum(pesos.values()) != 100:
            erros.append(f"Os pesos precisam somar 100. Hoje somam {sum(pesos.values())}.")

    quente = config.get("limite_quente")
    morno = config.get("limite_morno")
    if not _inteiro(quente) or not 1 <= quente <= 100:
        erros.append("O limite de Quente precisa ser um número inteiro de 1 a 100.")
    elif not _inteiro(morno) or not 1 <= morno < quente:
        erros.append("O limite de Morno precisa ser maior que 0 e menor que o limite de Quente.")

    alvo = config.get("segmentos_alvo", [])
    secundarios = config.get("segmentos_secundarios", [])
    desconhecidos = [s for s in alvo + secundarios if s not in SEGMENTOS_DISPONIVEIS]
    if desconhecidos:
        erros.append(f"Segmentos desconhecidos: {', '.join(desconhecidos)}.")
    repetidos = set(alvo) & set(secundarios)
    if repetidos:
        erros.append(f"Um segmento não pode ser alvo e secundário ao mesmo tempo: {', '.join(sorted(repetidos))}.")

    tamanho = config.get("tamanho_minimo_descricao")
    if not _inteiro(tamanho) or not 0 <= tamanho <= 500:
        erros.append("O tamanho mínimo da descrição precisa ser um número inteiro de 0 a 500.")

    return erros
